"""Adjudication rules, including refusals and immutable decisions."""
from apps.gavel import services
from apps.shared.errors import AppError

from .support import IsolatedTestCase


class AdjudicationRuleTests(IsolatedTestCase):
    def _open_disagreement(self):
        campaign, pair = self.pair()
        services.claim_review(self.reviewer, str(pair[0].id))
        result = services.submit_review(self.reviewer, str(pair[0].id), {
            "choice": "a",
            "notes": "Prefer A.",
            "criterionScores": {"quality": {"a": 5, "b": 2}},
        })
        winner_output = result["review"]["left"]["output"] if result["review"]["myChoice"] == "a" else result["review"]["right"]["output"]
        second = services.claim_review(self.peer, str(pair[1].id))
        opposed_choice = "a" if second["left"]["output"] != winner_output else "b"
        services.submit_review(self.peer, str(pair[1].id), {
            "choice": opposed_choice,
            "notes": "Prefer the other response.",
            "criterionScores": {"quality": {"a": 2, "b": 5}},
        })
        cases = services.list_adjudications(self.adjudicator, str(campaign.id))
        return campaign, cases[0]

    def test_reviewer_cannot_view_or_resolve_adjudications(self):
        with self.assertRaises(AppError) as error:
            services.list_adjudications(self.reviewer)
        self.assertEqual(error.exception.code, "ROLE_FORBIDDEN")

    def test_short_rationale_is_refused(self):
        campaign, item = self._open_disagreement()
        with self.assertRaises(AppError) as error:
            services.resolve_adjudication(self.adjudicator, item["id"], {"choice": "a", "rationale": "short"})
        self.assertEqual(error.exception.code, "RATIONALE_REQUIRED")

    def test_invalid_choice_is_refused(self):
        campaign, item = self._open_disagreement()
        with self.assertRaises(AppError) as error:
            services.resolve_adjudication(self.adjudicator, item["id"], {
                "choice": "c",
                "rationale": "This rationale is long enough.",
            })
        self.assertEqual(error.exception.code, "INVALID_CHOICE")

    def test_resolved_decision_cannot_be_overwritten(self):
        campaign, item = self._open_disagreement()
        resolved = services.resolve_adjudication(self.adjudicator, item["id"], {
            "choice": "a",
            "rationale": "Response A follows the policy more closely.",
        })
        self.assertEqual(resolved["status"], "resolved")
        with self.assertRaises(AppError) as error:
            services.resolve_adjudication(self.adjudicator, item["id"], {
                "choice": "b",
                "rationale": "Cannot overwrite a recorded decision.",
            })
        self.assertEqual(error.exception.code, "ADJUDICATION_RESOLVED")

    def test_campaign_cannot_complete_until_disagreement_is_resolved(self):
        campaign, item = self._open_disagreement()
        with self.assertRaises(AppError) as error:
            services.transition_campaign(self.owner, str(campaign.id), "completed")
        self.assertEqual(error.exception.code, "REVIEWS_REMAIN")
        services.resolve_adjudication(self.adjudicator, item["id"], {
            "choice": "a",
            "rationale": "Response A is the safer customer answer.",
        })
        completed = services.transition_campaign(self.owner, str(campaign.id), "completed")
        self.assertEqual(completed["status"], "completed")
        published = services.publish_results(self.owner, str(campaign.id))
        self.assertEqual(published["version"], 1)

    def test_publish_results_refused_before_completion(self):
        campaign, item = self._open_disagreement()
        with self.assertRaises(AppError) as error:
            services.publish_results(self.owner, str(campaign.id))
        self.assertEqual(error.exception.code, "CAMPAIGN_NOT_COMPLETE")
