import os
import unittest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calendar_backend.settings")

import django

django.setup()

from apps.gavel.services import deterministic_side, validate_cases, validate_rubric
from apps.shared.errors import AppError


class ServiceContractTests(unittest.TestCase):
    def test_rubric_requires_exact_total_when_publishing(self):
        rubric = [{"id": "accuracy", "title": "Accuracy", "weight": 100, "description": "Policy correctness."}]
        self.assertEqual(validate_rubric(rubric, require_total=True)[0]["weight"], 100)
        with self.assertRaises(AppError):
            validate_rubric([{**rubric[0], "weight": 99}], require_total=True)

    def test_case_ids_are_unique_and_prompts_are_retained(self):
        cases = validate_cases([{"id": "case-1", "title": "Setup", "prompt": "Help the customer connect."}])
        self.assertEqual(cases[0]["prompt"], "Help the customer connect.")
        with self.assertRaises(AppError):
            validate_cases([
                {"id": "same", "title": "One", "prompt": "First prompt."},
                {"id": "same", "title": "Two", "prompt": "Second prompt."},
            ])

    def test_blind_side_is_stable_per_reviewer(self):
        first = deterministic_side(type("Review", (), {"pair_key": "pair-1"})(), "reviewer-1")
        self.assertIn(first, ("a", "b"))
        self.assertEqual(first, deterministic_side(type("Review", (), {"pair_key": "pair-1"})(), "reviewer-1"))


if __name__ == "__main__":
    unittest.main()
