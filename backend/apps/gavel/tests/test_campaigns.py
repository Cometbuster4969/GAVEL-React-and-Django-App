"""Campaign lifecycle rules and refusals. Uses only throwaway users."""
from uuid import uuid4

from apps.gavel import services
from apps.shared.errors import AppError

from .support import IsolatedTestCase


class CampaignRuleTests(IsolatedTestCase):
    def test_reviewer_cannot_create_a_campaign(self):
        with self.assertRaises(AppError) as error:
            services.create_campaign(self.reviewer, {
                "name": "Should fail",
                "summary": "Reviewers do not own campaigns.",
                "testCases": [{"id": "case", "title": "Case", "prompt": "Please evaluate this."}],
                "rubric": [{"id": "quality", "title": "Quality", "weight": 100}],
            })
        self.assertEqual(error.exception.code, "ROLE_FORBIDDEN")

    def test_other_owner_cannot_manage_someone_elses_campaign(self):
        campaign = self.campaign()
        with self.assertRaises(AppError) as error:
            services.update_campaign(self.other_owner, str(campaign.id), {"summary": "hijack"})
        self.assertEqual(error.exception.code, "CAMPAIGN_FORBIDDEN")
        with self.assertRaises(AppError) as error:
            services.transition_campaign(self.other_owner, str(campaign.id), "published")
        self.assertEqual(error.exception.code, "CAMPAIGN_FORBIDDEN")

    def test_invalid_transition_is_refused(self):
        campaign = self.campaign()
        with self.assertRaises(AppError) as error:
            services.transition_campaign(self.owner, str(campaign.id), "completed")
        self.assertEqual(error.exception.code, "INVALID_TRANSITION")

    def test_publish_requires_rubric_total_of_one_hundred(self):
        campaign = services.create_campaign(self.owner, {
            "name": "Uneven rubric",
            "summary": "Weights do not add to 100.",
            "testCases": [{"id": "case", "title": "Case", "prompt": "Please evaluate this."}],
            "rubric": [{"id": "quality", "title": "Quality", "weight": 40}],
        })
        with self.assertRaises(AppError) as error:
            services.transition_campaign(self.owner, campaign["id"], "published")
        self.assertEqual(error.exception.code, "RUBRIC_TOTAL")

    def test_published_definition_is_frozen(self):
        campaign = self.campaign()
        services.transition_campaign(self.owner, str(campaign.id), "published")
        with self.assertRaises(AppError) as error:
            services.update_campaign(self.owner, str(campaign.id), {"summary": "too late"})
        self.assertEqual(error.exception.code, "CAMPAIGN_FROZEN")

    def test_only_drafts_can_be_deleted(self):
        campaign = self.campaign()
        services.transition_campaign(self.owner, str(campaign.id), "published")
        with self.assertRaises(AppError) as error:
            services.delete_campaign(self.owner, str(campaign.id))
        self.assertEqual(error.exception.code, "CAMPAIGN_NOT_DELETABLE")

    def test_ingest_is_refused_until_the_campaign_is_running(self):
        campaign = self.campaign()
        with self.assertRaises(AppError) as error:
            services.ingest_submissions(self.owner, str(campaign.id), [
                {"caseId": "case", "modelName": "A", "output": "out", "idempotencyKey": "k1"},
            ])
        self.assertEqual(error.exception.code, "CAMPAIGN_NOT_RUNNING")

    def test_complete_is_refused_while_reviews_remain(self):
        campaign, pair = self.pair()
        self.assertTrue(pair)
        with self.assertRaises(AppError) as error:
            services.transition_campaign(self.owner, str(campaign.id), "completed")
        self.assertEqual(error.exception.code, "REVIEWS_REMAIN")

    def test_complete_is_refused_without_processed_responses(self):
        campaign = self.campaign()
        services.transition_campaign(self.owner, str(campaign.id), "published")
        services.transition_campaign(self.owner, str(campaign.id), "running")
        with self.assertRaises(AppError) as error:
            services.transition_campaign(self.owner, str(campaign.id), "completed")
        self.assertEqual(error.exception.code, "NO_PROCESSED_SUBMISSIONS")

    def test_owner_can_publish_start_and_ingest_with_idempotency(self):
        campaign = self.campaign()
        published = services.transition_campaign(self.owner, str(campaign.id), "published")
        self.assertEqual(published["status"], "published")
        running = services.transition_campaign(self.owner, str(campaign.id), "running")
        self.assertEqual(running["status"], "running")
        key = "dup-" + uuid4().hex
        first = services.ingest_submissions(self.owner, str(campaign.id), [
            {"caseId": "case", "modelName": "A", "output": "out", "idempotencyKey": key},
        ])
        second = services.ingest_submissions(self.owner, str(campaign.id), [
            {"caseId": "case", "modelName": "A", "output": "out", "idempotencyKey": key},
        ])
        self.assertFalse(first[0]["duplicate"])
        self.assertTrue(second[0]["duplicate"])

    def test_duplicate_case_ids_are_refused(self):
        with self.assertRaises(AppError) as error:
            services.create_campaign(self.owner, {
                "name": "Duplicate cases",
                "summary": "Invalid suite.",
                "testCases": [
                    {"id": "same", "title": "One", "prompt": "First prompt."},
                    {"id": "same", "title": "Two", "prompt": "Second prompt."},
                ],
                "rubric": [{"id": "quality", "title": "Quality", "weight": 100}],
            })
        self.assertEqual(error.exception.code, "DUPLICATE_CASE_ID")
