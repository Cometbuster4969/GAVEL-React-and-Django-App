"""Audit-outbox regression tests — durable audit intent, retries, and idempotency.

Run: cd backend && ../.venv/bin/python -m unittest apps.gavel.test_outbox
These tests exercise the real repository + mongomock persistence, not stubs.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calendar_backend.settings")

import django

django.setup()

from apps.gavel import repository, services
from apps.gavel.models import AuditEvent, AuditOutbox

CAMPAIGN_ID = "64a200000000000000000001"


class AuditOutboxTests(unittest.TestCase):
    def setUp(self):
        self.maya = repository.find_user_by_email("maya.chen@gavel.test")
        assert self.maya is not None, "seeded baseline missing — run scripts/seed.py"
        # The outbox is an operational queue (never seeded); isolate each test case.
        AuditOutbox.objects.delete()

    def test_record_delivers_inline_and_marks_outbox_delivered(self):
        event_id = services.record(self.maya, "test.inline", "campaign", CAMPAIGN_ID, {"note": "inline"})
        self.assertIsNotNone(event_id)
        entry = AuditOutbox.objects(event_id=event_id).first()
        self.assertEqual(entry.status, "delivered")
        self.assertIsNotNone(entry.delivered_at)
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 1)

    def test_failed_delivery_is_retried_by_the_worker(self):
        with mock.patch.object(repository, "deliver_audit_event", side_effect=RuntimeError("audit store unavailable")):
            event_id = services.record(self.maya, "test.retry", "campaign", CAMPAIGN_ID, {"note": "retry"})
        entry = AuditOutbox.objects(event_id=event_id).first()
        self.assertEqual(entry.status, "pending")
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 0)

        stats = services.drain_audit_outbox(limit=10)
        self.assertGreaterEqual(stats["delivered"], 1)
        self.assertEqual(AuditOutbox.objects(event_id=event_id).first().status, "delivered")
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 1)

    def test_worker_does_not_claim_entries_before_their_backoff_window(self):
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        entry = AuditOutbox(
            event_id="backoff-window-test",
            actor_id=self.maya.id,
            actor_name=self.maya.name,
            action="test.backoff",
            entity_type="campaign",
            entity_id=CAMPAIGN_ID,
            details={},
            status="pending",
            available_at=future,
        ).save()

        stats = services.drain_audit_outbox(limit=10)
        self.assertEqual(stats["scanned"], 0)
        self.assertEqual(AuditOutbox.objects(event_id=entry.event_id).first().status, "pending")

        AuditOutbox._get_collection().update_one(
            {"eventId": entry.event_id}, {"$set": {"availableAt": datetime.now(timezone.utc) - timedelta(seconds=1)}}
        )
        stats = services.drain_audit_outbox(limit=10)
        self.assertEqual(stats["delivered"], 1)
        self.assertEqual(AuditOutbox.objects(event_id=entry.event_id).first().status, "delivered")

    def test_repeated_delivery_is_idempotent(self):
        event_id = services.record(self.maya, "test.idempotent", "campaign", CAMPAIGN_ID, {})
        entry = AuditOutbox.objects(event_id=event_id).first()
        self.assertFalse(repository.deliver_audit_event(entry))
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 1)

        services.drain_audit_outbox(limit=10)
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 1)

    def test_dead_letter_after_max_attempts(self):
        with mock.patch.object(repository, "deliver_audit_event", side_effect=RuntimeError("audit store down")):
            event_id = services.record(self.maya, "test.deadletter", "campaign", CAMPAIGN_ID, {})
            stats = services.drain_audit_outbox(limit=5, max_attempts=1, base_delay=0)

        self.assertEqual(stats["failed"], 1)
        entry = AuditOutbox.objects(event_id=event_id).first()
        self.assertEqual(entry.status, "failed")
        self.assertIn("audit store down", entry.last_error)
        # Dead-lettered intent is retained for operators instead of being dropped.
        self.assertEqual(AuditEvent.objects(event_id=event_id).count(), 0)

    def test_stale_running_entries_are_recovered(self):
        entry = AuditOutbox(
            event_id="stale-running-test",
            actor_id=self.maya.id,
            actor_name=self.maya.name,
            action="test.stale",
            entity_type="campaign",
            entity_id=CAMPAIGN_ID,
            details={},
            status="running",
            available_at=datetime.now(timezone.utc),
            locked_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        ).save()

        services.drain_audit_outbox(limit=10)
        self.assertEqual(AuditOutbox.objects(event_id=entry.event_id).first().status, "delivered")
        self.assertEqual(AuditEvent.objects(event_id=entry.event_id).count(), 1)

    def test_audit_history_still_serves_outbox_events(self):
        event_id = services.record(self.maya, "test.history", "campaign", CAMPAIGN_ID, {"campaignId": CAMPAIGN_ID})
        listed = services.audit_log(self.maya, limit=50)
        rows = [row for row in listed["items"] if row["action"] == "test.history"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actor"], self.maya.name)
        self.assertIsNotNone(AuditEvent.objects(event_id=event_id).first())


if __name__ == "__main__":
    unittest.main()
