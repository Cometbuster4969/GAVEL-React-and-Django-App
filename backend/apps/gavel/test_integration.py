"""
Gavel integration tests — covers the full campaign lifecycle against mongomock.
Run: cd backend && ../.venv/bin/python -m unittest apps.gavel.test_integration
These tests exercise real services + mongomock persistence, not mocks.
"""

import os
import sys
import unittest
import uuid

# Ensure Django settings are loaded before importing app code
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calendar_backend.settings")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import django

django.setup()

from apps.gavel import services, repository
from apps.gavel.models import Campaign, GavelUser


def _login(email):
    # Directly fetch user and issue token via services (bypasses HTTP, tests service layer)
    user = repository.find_user_by_email(email)
    assert user is not None, f"user {email} not found"
    return user


class LifecycleIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Ensure seeded baseline exists (auto-seed in settings should have run)
        self.maya = _login("maya.chen@gavel.test")
        self.jordan = _login("jordan.lee@gavel.test")
        self.sam = _login("sam.rivera@gavel.test")
        self.priya = _login("priya.shah@gavel.test")
        self.elena = _login("elena.park@gavel.test")

    def test_full_lifecycle_with_weighted_scores_and_disagreement(self):
        # Create
        name = f"E2E-{uuid.uuid4().hex[:6]}"
        camp = services.create_campaign(
            self.maya,
            {
                "name": name,
                "summary": "integration test",
                "testCases": [{"id": "c1", "title": "T", "prompt": "Prompt for testing"}],
                "rubric": [
                    {"id": "r1", "title": "Helpfulness", "weight": 50, "description": ""},
                    {"id": "r2", "title": "Accuracy", "weight": 50, "description": ""},
                ],
            },
        )
        camp_id = camp["id"]
        # Publish
        camp = services.transition_campaign(self.maya, camp_id, "published")
        self.assertEqual(camp["status"], "published")
        # Start
        camp = services.transition_campaign(self.maya, camp_id, "running")
        self.assertEqual(camp["status"], "running")
        # Ingest 2
        outcomes = services.ingest_submissions(
            self.maya,
            camp_id,
            [
                {"caseId": "c1", "modelName": "M1", "output": "Out1", "idempotencyKey": f"k1-{uuid.uuid4().hex}"},
                {"caseId": "c1", "modelName": "M2", "output": "Out2", "idempotencyKey": f"k2-{uuid.uuid4().hex}"},
            ],
        )
        self.assertEqual(len(outcomes), 2)
        # Process
        result = services.process_submissions(self.maya, camp_id, limit=25)
        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["reviewAssignmentsCreated"], 2)
        # Reviews
        reviews_j = services.list_reviews(self.jordan, campaign_id=camp_id)
        if isinstance(reviews_j, dict):
            reviews_j = reviews_j["items"]
        self.assertGreaterEqual(len(reviews_j), 1)
        avail = [r for r in reviews_j if r["status"] == "available"]
        self.assertTrue(len(avail) >= 1)
        rid = avail[0]["id"]
        claimed = services.claim_review(self.jordan, rid)
        self.assertEqual(claimed["status"], "claimed")
        # Submit with criterion scores 1-5
        res = services.submit_review(
            self.jordan,
            rid,
            {"choice": "a", "notes": "good", "criterionScores": {"r1": {"a": 5, "b": 3}, "r2": {"a": 4, "b": 4}}},
        )
        self.assertIn("review", res)
        self.assertIn("weightedScore", res["review"])
        # Sam must prefer the other underlying submission, regardless of blind ordering.
        reviews_s = services.list_reviews(self.sam, campaign_id=camp_id)
        avail_s = [r for r in reviews_s if r["status"] == "available"]
        self.assertEqual(len(avail_s), 1)
        rid2 = avail_s[0]["id"]
        claimed_s = services.claim_review(self.sam, rid2)
        jordan_winner = res["review"]["left"]["output"]
        sam_choice = "a" if claimed_s["left"]["output"] != jordan_winner else "b"
        res2 = services.submit_review(self.sam, rid2, {
            "choice": sam_choice, "notes": "other",
            "criterionScores": {"r1": {"a": 2, "b": 5}, "r2": {"a": 3, "b": 5}}})
        self.assertTrue(res2["disagreementDetected"])
        adjs = services.list_adjudications(self.priya, campaign_id=camp_id)
        self.assertEqual(len(adjs), 1)
        self.assertEqual(adjs[0]["status"], "open")
        from apps.shared.errors import AppError
        with self.assertRaises(AppError) as blocked:
            services.transition_campaign(self.maya, camp_id, "completed")
        self.assertEqual(blocked.exception.code, "REVIEWS_REMAIN")
        resolved = services.resolve_adjudication(self.priya, adjs[0]["id"], {
            "choice": "a", "rationale": "Rationale long enough for test."})
        self.assertEqual(resolved["status"], "resolved")
        with self.assertRaises(AppError):
            services.resolve_adjudication(self.priya, adjs[0]["id"], {"choice": "b", "rationale": "Cannot overwrite a decision."})
        # Complete
        camp = services.transition_campaign(self.maya, camp_id, "completed")
        self.assertEqual(camp["status"], "completed")
        # Publish
        pub = services.publish_results(self.maya, camp_id)
        self.assertEqual(pub["version"], 1)
        self.assertIn("snapshot", pub)
        # Export
        fetched = services.get_published_results(self.maya, camp_id)
        self.assertEqual(fetched["id"], pub["id"])
        # Audit pagination
        audit = services.audit_log(self.elena, limit=2)
        self.assertIn("items", audit)
        self.assertEqual(len(audit["items"]), 2)
        self.assertIsNotNone(audit["nextCursor"])
        # Pagination on campaigns
        paged = services.list_campaigns(self.elena, limit=2)
        self.assertIn("items", paged)
        self.assertIn("nextCursor", paged)
        # Idempotency
        dup_key = f"dup-{uuid.uuid4().hex}"
        # Use a fresh draft campaign for idempotency test (need running)
        name2 = f"Idem-{uuid.uuid4().hex[:6]}"
        camp2 = services.create_campaign(
            self.maya,
            {
                "name": name2,
                "summary": "idem",
                "testCases": [{"id": "c1", "title": "T", "prompt": "Prompt"}],
                "rubric": [{"id": "r1", "title": "Helpfulness", "weight": 100, "description": ""}],
            },
        )
        services.transition_campaign(self.maya, camp2["id"], "published")
        services.transition_campaign(self.maya, camp2["id"], "running")
        first = services.ingest_submissions(
            self.maya, camp2["id"], [{"caseId": "c1", "modelName": "M1", "output": "O1", "idempotencyKey": dup_key}]
        )
        second = services.ingest_submissions(
            self.maya, camp2["id"], [{"caseId": "c1", "modelName": "M1", "output": "O1", "idempotencyKey": dup_key}]
        )
        self.assertFalse(first[0]["duplicate"])
        self.assertTrue(second[0]["duplicate"])
        # Cleanup: archive
        services.transition_campaign(self.maya, camp_id, "archived")
        services.transition_campaign(self.maya, camp2["id"], "archived")

    def test_pagination_bounded(self):
        # Ensure list_campaigns respects limit and cursor
        all_camps = services.list_campaigns(self.elena)
        if isinstance(all_camps, dict):
            all_camps = all_camps["items"]
        paged = services.list_campaigns(self.elena, limit=1)
        self.assertIn("items", paged)
        self.assertIn("nextCursor", paged)
        self.assertEqual(len(paged["items"]), 1)
        # Next page
        if paged["nextCursor"]:
            nxt = services.list_campaigns(self.elena, limit=1, cursor=paged["nextCursor"])
            self.assertIn("items", nxt)

    def test_blind_payload_no_leakage(self):
        # Review payload must not contain model names or submission IDs
        # Use seeded reviewing campaign
        camp = Campaign.objects(status="reviewing").first()
        self.assertIsNotNone(camp, "reviewing seed must exist")
        reviews = services.list_reviews(self.jordan, campaign_id=str(camp.id))
        if isinstance(reviews, dict):
            reviews = reviews["items"]
        self.assertTrue(reviews, "review seed must exist")
        payload = reviews[0]
        self.assertNotIn("modelName", str(payload))
        self.assertNotIn("submissionAId", str(payload))
        self.assertNotIn("submissionBId", str(payload))
        # Ordering stable per reviewer
        from apps.gavel.services import deterministic_side

        r = repository.find_review(payload["id"])
        side1 = deterministic_side(r, self.jordan.id)
        side2 = deterministic_side(r, self.jordan.id)
        self.assertEqual(side1, side2)


if __name__ == "__main__":
    unittest.main()
