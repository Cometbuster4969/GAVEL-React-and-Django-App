"""Regression checks for audit atomicity, cursors, identity, and HTTP security."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest import mock
from django.http import JsonResponse
from django.test import RequestFactory, override_settings
from mongoengine.connection import get_db
from pymongo.errors import DuplicateKeyError

from apps.gavel import audit, auth, repository, services
from apps.gavel.models import Adjudication, AuditEvent, AuditOutbox, Campaign, GavelUser, ReviewAssignment, Submission
from apps.shared.errors import AppError
from calendar_backend.security_middleware import RateLimitMiddleware

from .support import IsolatedTestCase


class HardeningTests(IsolatedTestCase):
    def test_failed_relay_keeps_change_and_intent_together_then_worker_recovers(self):
        campaign = self.campaign()
        with mock.patch.object(repository, "persist_audit_intent", side_effect=RuntimeError("outbox down")):
            with self.assertLogs("apps.gavel.audit", level="WARNING"):
                services.update_campaign(self.owner, str(campaign.id), {"summary": "Changed atomically"})
        campaign.reload()
        self.assertEqual(campaign.summary, "Changed atomically")
        self.assertEqual(len(campaign.audit_pending), 1)
        event_id = campaign.audit_pending[0]["eventId"]
        services.drain_audit_outbox()
        self.assertEqual(len(campaign.reload().audit_pending), 0)
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 1)

    def test_failed_business_write_creates_neither_change_nor_event(self):
        campaign = self.campaign()
        previous = AuditEvent.objects.count()
        with mock.patch.object(audit, "collection") as collection:
            collection.return_value.find_one_and_update.side_effect = RuntimeError("write failed")
            with self.assertRaises(RuntimeError):
                services.update_campaign(self.owner, str(campaign.id), {"summary": "must not persist"})
        self.assertEqual(campaign.reload().summary, "Regression fixture")
        self.assertEqual(AuditEvent.objects.count(), previous)

    def test_delete_tombstone_preserves_pending_intent(self):
        campaign = self.campaign()
        with mock.patch.object(audit, "relay_document"):
            services.delete_campaign(self.owner, str(campaign.id))
        self.assertIsNone(repository.find_campaign(str(campaign.id)))
        self.assertTrue(campaign.reload().deleted)
        event_id = campaign.audit_pending[0]["eventId"]
        audit.relay_pending()
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 1)
        self.assertTrue(any(e["id"] == str(AuditEvent.objects(event_id=event_id).first().id)
                            for e in services.audit_log(self.owner)["items"]))

    def test_relay_replay_after_outbox_write_and_concurrent_push_loses_nothing(self):
        campaign = self.campaign()
        with mock.patch.object(audit, "relay_document"):
            services.update_campaign(self.owner, str(campaign.id), {"summary": "first"})
        first = dict(campaign.reload().audit_pending[0])
        repository.persist_audit_intent(first)  # crash before pull
        with mock.patch.object(audit, "relay_document"):
            services.update_campaign(self.owner, str(campaign.id), {"summary": "second"})
        ids = [e["eventId"] for e in campaign.reload().audit_pending]
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: audit.relay_document(Campaign, campaign.id), range(2)))
        self.assertEqual(len(campaign.reload().audit_pending), 0)
        for event_id in ids:
            self.assertEqual(AuditOutbox.objects(event_id=event_id).count(), 1)
            self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 1)

    def test_delivery_after_pull_failure_is_recovered_from_outbox(self):
        campaign = self.campaign()
        with mock.patch.object(repository, "deliver_audit_event", side_effect=RuntimeError("history down")):
            with self.assertLogs("apps.gavel.audit", level="WARNING"):
                services.update_campaign(self.owner, str(campaign.id), {"summary": "survives"})
        self.assertEqual(len(campaign.reload().audit_pending), 0)
        event = AuditOutbox.objects(entity_id=str(campaign.id), action="campaign.updated").first()
        self.assertEqual(event.status, "pending")
        services.drain_audit_outbox()
        self.assertEqual(AuditEvent.objects(event_id=event.event_id).count(), 1)

    def test_stale_document_save_cannot_overwrite_pending_events(self):
        campaign = self.campaign()
        with mock.patch.object(audit, "relay_document"):
            services.update_campaign(self.owner, str(campaign.id), {"summary": "pending"})
        campaign.summary = "stale"
        with self.assertRaises(RuntimeError):
            campaign.save()
        self.assertEqual(len(campaign.reload().audit_pending), 1)

    def test_audit_backlog_fails_closed(self):
        campaign = self.campaign()
        Campaign._get_collection().update_one({"_id": campaign.id}, {"$set": {"auditPending": [{}] * 1000}})
        with self.assertRaises(AppError) as error:
            services.update_campaign(self.owner, str(campaign.id), {"summary": "must not persist"})
        self.assertEqual(error.exception.code, "AUDIT_BACKLOG")
        self.assertEqual(campaign.reload().summary, "Regression fixture")

    def test_owner_scope_before_limit_and_tied_timestamps(self):
        owner = self.user()
        own = [self.campaign(owner) for _ in range(3)]
        other = self.campaign()
        moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
        Campaign.objects(id__in=[c.id for c in own] + [other.id]).update(set__updated_at=moment)
        seen, cursor = [], None
        for _ in range(4):
            page = services.list_campaigns(owner, limit=1, cursor=cursor)
            seen.extend(item["id"] for item in page["items"])
            cursor = page["nextCursor"]
            if not cursor:
                break
        self.assertEqual(set(seen), {str(c.id) for c in own})
        self.assertEqual(len(seen), 3)
        with self.assertRaises(AppError):
            services.list_campaigns(owner, limit=1, cursor=str(other.id))

    def test_review_scope_or_is_combined_with_cursor_or(self):
        campaign, pair = self.pair()
        available, mine = pair
        services.claim_review(self.reviewer, str(mine.id))
        moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
        ReviewAssignment.objects(campaign_id=campaign.id).update(set__created_at=moment)
        first = services.list_reviews(self.reviewer, str(campaign.id), limit=1)
        second = services.list_reviews(self.reviewer, str(campaign.id), limit=1, cursor=first["nextCursor"])
        self.assertNotEqual(first["items"][0]["id"], second["items"][0]["id"])
        self.assertEqual(len(services.list_reviews(self.peer, str(campaign.id))), 1)

    def test_legacy_missing_default_fields_remain_visible_and_claimable(self):
        user = self.user("reviewer")
        campaign, pair = self.pair()
        Campaign._get_collection().update_one({"_id": campaign.id}, {"$unset": {"deleted": ""}})
        GavelUser._get_collection().update_one({"_id": user.id}, {"$unset": {"independenceGroup": "", "reviewIdentityLocked": ""}})
        self.assertIsNotNone(repository.find_campaign(str(campaign.id)))
        self.assertEqual(services.claim_review(user.reload(), str(pair[0].id))["status"], "claimed")

    def test_management_command_registered_and_stale_identity_claim_rejected(self):
        from django.core.management import call_command, get_commands
        from io import StringIO
        self.assertIn("set_review_identity", get_commands())
        user = self.user("reviewer")
        campaign, pair = self.pair()
        call_command("set_review_identity", user.email, "Verified-Person", stdout=StringIO())
        with self.assertRaises(AppError) as error:
            services.claim_review(user, str(pair[0].id))
        self.assertEqual(error.exception.code, "IDENTITY_CHANGED")
        self.assertEqual(services.claim_review(user.reload(), str(pair[0].id))["status"], "claimed")

    def test_all_repository_cursors_handle_equal_timestamps(self):
        owner = self.user()
        campaign = self.campaign(owner)
        moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for n in range(3):
            services.record(owner, "test.cursor", "campaign", str(campaign.id))
            Submission(campaign_id=campaign.id, case_id="case", model_name=str(n), output="out",
                       idempotency_key=str(n)).save()
            Adjudication(campaign_id=campaign.id, pair_key=str(n), case_id="case",
                         submission_a_id=campaign.id, submission_b_id=campaign.id).save()
        for model, fetch, timestamp in (
            (Submission, lambda c: repository.list_submissions(campaign.id, limit=1, cursor=c), "created_at"),
            (Adjudication, lambda c: repository.list_adjudications(str(campaign.id), limit=1, cursor=c), "updated_at"),
            (AuditEvent, lambda c: repository.list_audit(limit=1, cursor=c, owner_id=owner.id, campaign_ids=[campaign.id]), "created_at"),
        ):
            rows = list(model.objects(entity_id=str(campaign.id))) if model is AuditEvent else list(model.objects(campaign_id=campaign.id))
            model.objects(id__in=[row.id for row in rows]).update(**{"set__" + timestamp: moment})
            ids, cursor = [], None
            for _ in range(len(rows) + 1):
                page = fetch(cursor)
                if not page:
                    break
                ids.append(page[0].id)
                cursor = str(page[0].id)
            self.assertEqual(len(ids), len(rows))
            self.assertEqual(set(ids), {row.id for row in rows})

    def test_standalone_record_propagates_outbox_write_failure(self):
        with mock.patch.object(repository, "enqueue_audit_outbox", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                services.record(self.owner, "test.failure", "campaign", "missing")

    def test_processing_job_requeues_until_entire_batch_finishes(self):
        from apps.gavel.jobs import process_next_job
        from apps.gavel.models import ProcessingJob
        campaign = self.campaign(running=True)
        services.ingest_submissions(self.owner, str(campaign.id), [
            {"caseId": "case", "modelName": str(i), "output": "out", "idempotencyKey": str(i)} for i in range(3)])
        for _ in range(3):
            self.assertEqual(process_next_job(limit=1), 1)
        self.assertEqual(Submission.objects(campaign_id=campaign.id, status="ready").count(), 3)
        self.assertEqual(ProcessingJob.objects(campaign_id=campaign.id, status="completed").count(), 1)
        self.assertEqual(campaign.reload().status, "reviewing")

    def test_unknown_and_wrong_password_both_do_bcrypt_once(self):
        for email in (self.owner.email, "missing@test.invalid"):
            with mock.patch.object(auth.bcrypt, "checkpw", return_value=False) as check:
                with self.assertRaises(AppError) as error:
                    auth.login(email, "wrong password")
                check.assert_called_once()
                self.assertEqual(error.exception.code, "INVALID_CREDENTIALS")

    def test_same_user_and_same_group_cannot_take_both_slots(self):
        campaign, pair = self.pair()
        first = self.user("reviewer", "verified-person-42")
        alias = self.user("reviewer", "verified-person-42")
        services.claim_review(first, str(pair[0].id))
        for user in (first, alias):
            with self.assertRaises(AppError) as error:
                services.claim_review(user, str(pair[1].id))
            self.assertEqual(error.exception.code, "REVIEW_CONFLICT")
        with self.assertRaises(DuplicateKeyError):
            ReviewAssignment._get_collection().update_one({"_id": pair[1].id}, {"$set": {
                "status": "claimed", "reviewerGroup": services.independence_group(first), "reviewerKey": str(alias.id)}})
        services.release_review(first, str(pair[0].id))
        self.assertEqual(services.claim_review(alias, str(pair[1].id))["status"], "claimed")

    def test_campaign_owner_cannot_review_even_as_administrator(self):
        owner = self.user("administrator")
        campaign, pair = self.pair(owner)
        with self.assertRaises(AppError) as error:
            services.claim_review(owner, str(pair[0].id))
        self.assertEqual(error.exception.code, "REVIEW_CONFLICT")

    def test_identity_configuration_locked_after_claim(self):
        from django.core.management import call_command, CommandError
        user = self.user("reviewer")
        campaign, pair = self.pair()
        services.claim_review(user, str(pair[0].id))
        with self.assertRaises(CommandError):
            call_command("set_review_identity", user.email, "different")

    def test_conflicts_rechecked_at_submission(self):
        user = self.user("reviewer")
        campaign, pair = self.pair()
        services.claim_review(user, str(pair[0].id))
        user.conflict_campaign_ids = [campaign.id]
        user.save()
        with self.assertRaises(AppError) as error:
            services.submit_review(user, str(pair[0].id), {"choice": "a", "criterionScores": {"quality": {"a": 5, "b": 3}}})
        self.assertEqual(error.exception.code, "REVIEW_CONFLICT")


class RateLimitTests(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        get_db()["ratelimitcounters"].delete_many({})
        self.factory = RequestFactory()

    @override_settings(RATE_LIMIT_MAX=2, RATE_LIMIT_WINDOW=60, TRUSTED_PROXY_CIDRS=[])
    def test_two_middleware_instances_share_limit_and_render_429(self):
        first = RateLimitMiddleware(lambda r: JsonResponse({"ok": True}))
        second = RateLimitMiddleware(lambda r: JsonResponse({"ok": True}))
        request = self.factory.get("/api/v1/campaigns", REMOTE_ADDR="198.51.100.9")
        self.assertEqual(first(request).status_code, 200)
        self.assertEqual(second(request).status_code, 200)
        response = first(request)
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"RATE_LIMITED", response.content)
        self.assertIn("Retry-After", response)

    @override_settings(TRUSTED_PROXY_CIDRS=["10.0.0.0/8"])
    def test_forwarded_headers_require_trusted_peer_and_walk_right_to_left(self):
        limiter = RateLimitMiddleware(lambda r: JsonResponse({}))
        request = self.factory.get("/api/v1/test", REMOTE_ADDR="198.51.100.8", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.assertEqual(limiter._get_client_ip(request), "198.51.100.8")
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        request.META["HTTP_X_FORWARDED_FOR"] = "1.2.3.4, 198.51.100.8, 10.0.0.2"
        self.assertEqual(limiter._get_client_ip(request), "198.51.100.8")
        request.META["HTTP_X_FORWARDED_FOR"] = "malformed"
        self.assertEqual(limiter._get_client_ip(request), "10.0.0.1")

    def test_database_failure_fails_closed(self):
        limiter = RateLimitMiddleware(lambda r: JsonResponse({}))
        with mock.patch.object(limiter, "_counters", side_effect=RuntimeError("offline")):
            response = limiter(self.factory.get("/api/v1/campaigns"))
        self.assertEqual(response.status_code, 503)
