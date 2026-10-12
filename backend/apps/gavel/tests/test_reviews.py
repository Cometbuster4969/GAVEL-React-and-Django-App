"""Review claiming, independence, blindness, and refusals."""
from apps.gavel import services
from apps.shared.errors import AppError

from .support import IsolatedTestCase


class ReviewRuleTests(IsolatedTestCase):
    def test_adjudicator_cannot_access_the_review_queue(self):
        with self.assertRaises(AppError) as error:
            services.list_reviews(self.adjudicator)
        self.assertEqual(error.exception.code, "ROLE_FORBIDDEN")
        campaign, pair = self.pair()
        with self.assertRaises(AppError) as error:
            services.claim_review(self.adjudicator, str(pair[0].id))
        self.assertEqual(error.exception.code, "ROLE_FORBIDDEN")

    def test_campaign_owner_cannot_review_their_own_campaign(self):
        campaign, pair = self.pair()
        with self.assertRaises(AppError) as error:
            services.claim_review(self.owner, str(pair[0].id))
        self.assertEqual(error.exception.code, "REVIEW_CONFLICT")

    def test_submit_without_claim_is_refused(self):
        campaign, pair = self.pair()
        with self.assertRaises(AppError) as error:
            services.submit_review(self.reviewer, str(pair[0].id), {
                "choice": "a",
                "criterionScores": {"quality": {"a": 5, "b": 3}},
            })
        self.assertEqual(error.exception.code, "REVIEW_NOT_OWNED")

    def test_release_by_another_reviewer_is_refused(self):
        campaign, pair = self.pair()
        services.claim_review(self.reviewer, str(pair[0].id))
        with self.assertRaises(AppError) as error:
            services.release_review(self.peer, str(pair[0].id))
        self.assertEqual(error.exception.code, "REVIEW_NOT_OWNED")

    def test_second_claim_on_the_same_slot_is_refused(self):
        campaign, pair = self.pair()
        services.claim_review(self.reviewer, str(pair[0].id))
        with self.assertRaises(AppError) as error:
            services.claim_review(self.peer, str(pair[0].id))
        self.assertEqual(error.exception.code, "REVIEW_ALREADY_CLAIMED")

    def test_same_independence_group_cannot_take_both_slots(self):
        campaign, pair = self.pair()
        first = self.user("reviewer", "verified-person-42")
        alias = self.user("reviewer", "verified-person-42")
        services.claim_review(first, str(pair[0].id))
        with self.assertRaises(AppError) as error:
            services.claim_review(alias, str(pair[1].id))
        self.assertEqual(error.exception.code, "REVIEW_CONFLICT")

    def test_blind_payload_hides_model_identity(self):
        campaign, pair = self.pair()
        payload = services.claim_review(self.reviewer, str(pair[0].id))
        dumped = str(payload)
        self.assertNotIn("modelName", dumped)
        self.assertNotIn("submissionAId", dumped)
        self.assertNotIn("submissionBId", dumped)
        self.assertIn("left", payload)
        self.assertIn("right", payload)
        first = services.deterministic_side(pair[0], self.reviewer.id)
        self.assertEqual(first, services.deterministic_side(pair[0], self.reviewer.id))

    def test_claim_release_and_submit_complete_a_slot(self):
        campaign, pair = self.pair()
        claimed = services.claim_review(self.reviewer, str(pair[0].id))
        self.assertEqual(claimed["status"], "claimed")
        released = services.release_review(self.reviewer, str(pair[0].id))
        self.assertEqual(released["status"], "available")
        services.claim_review(self.reviewer, str(pair[0].id))
        result = services.submit_review(self.reviewer, str(pair[0].id), {
            "choice": "a",
            "notes": "Clearer answer.",
            "criterionScores": {"quality": {"a": 5, "b": 3}},
        })
        self.assertEqual(result["review"]["status"], "completed")
        self.assertFalse(result["disagreementDetected"])

    def test_opposing_reviews_open_adjudication(self):
        campaign, pair = self.pair()
        services.claim_review(self.reviewer, str(pair[0].id))
        result = services.submit_review(self.reviewer, str(pair[0].id), {
            "choice": "a",
            "notes": "Prefer A.",
            "criterionScores": {"quality": {"a": 5, "b": 2}},
        })
        winner_output = result["review"]["left"]["output"] if result["review"]["myChoice"] == "a" else result["review"]["right"]["output"]
        second = services.claim_review(self.peer, str(pair[1].id))
        sam_choice = "a" if second["left"]["output"] != winner_output else "b"
        opposed = services.submit_review(self.peer, str(pair[1].id), {
            "choice": sam_choice,
            "notes": "Prefer the other response.",
            "criterionScores": {"quality": {"a": 2, "b": 5}},
        })
        self.assertTrue(opposed["disagreementDetected"])
        cases = services.list_adjudications(self.adjudicator, str(campaign.id))
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["status"], "open")
        with self.assertRaises(AppError) as error:
            services.transition_campaign(self.owner, str(campaign.id), "completed")
        self.assertEqual(error.exception.code, "REVIEWS_REMAIN")
