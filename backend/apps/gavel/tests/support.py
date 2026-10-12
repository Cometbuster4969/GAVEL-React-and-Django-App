"""Fixtures for the throwaway-database suite. Never touch gavel_db."""
import unittest
from uuid import uuid4

import bcrypt
from mongoengine.connection import get_db

from apps.gavel.models import GavelUser, ReviewAssignment

TEST_PASSWORD = "test-pass-2026!"
_PASSWORD_HASH = None


def password_hash():
    global _PASSWORD_HASH
    if _PASSWORD_HASH is None:
        _PASSWORD_HASH = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    return _PASSWORD_HASH


def require_throwaway_database():
    name = str(get_db().name)
    if not name.startswith("gavel_test_"):
        raise RuntimeError(
            f"Refusing to run tests against database {name!r}. "
            "Run `bun test` so the suite can create and drop a throwaway gavel_test_* database."
        )
    if "mongomock" in type(get_db().client).__module__:
        raise RuntimeError("Refusing to run tests against an in-memory mock. Start MongoDB and retry with `bun test`.")


def wipe_database():
    require_throwaway_database()
    database = get_db()
    for name in database.list_collection_names():
        if not name.startswith("system."):
            database[name].delete_many({})


def make_user(role, name=None, email=None, group=""):
    return GavelUser(
        name=name or f"Test {role.title()}",
        email=email or f"{role}-{uuid4().hex[:10]}@gavel.example",
        role=role,
        independence_group=group,
        password_hash=password_hash(),
        active=True,
    ).save()


class IsolatedTestCase(unittest.TestCase):
    """Each test starts from an empty throwaway database and its own users."""

    @classmethod
    def setUpClass(cls):
        require_throwaway_database()

    def setUp(self):
        wipe_database()
        self.admin = make_user("administrator", "Ada Admin")
        self.owner = make_user("owner", "Owen Owner")
        self.other_owner = make_user("owner", "Olivia Other")
        self.reviewer = make_user("reviewer", "Riley Reviewer")
        self.peer = make_user("reviewer", "Parker Peer")
        self.adjudicator = make_user("adjudicator", "Avery Adjudicator")

    def tearDown(self):
        wipe_database()

    def user(self, role="owner", group="", name=None):
        return make_user(role, name=name, group=group)

    def campaign(self, owner=None, running=False):
        from apps.gavel import repository, services

        data = services.create_campaign(owner or self.owner, {
            "name": "Hardening " + uuid4().hex[:8],
            "summary": "Regression fixture",
            "testCases": [{"id": "case", "title": "Case", "prompt": "Please evaluate this."}],
            "rubric": [{"id": "quality", "title": "Quality", "weight": 100}],
        })
        if running:
            services.transition_campaign(owner or self.owner, data["id"], "published")
            services.transition_campaign(owner or self.owner, data["id"], "running")
        return repository.find_campaign(data["id"])

    def pair(self, owner=None):
        from apps.gavel import services

        campaign = self.campaign(owner, running=True)
        actor = owner or self.owner
        services.ingest_submissions(actor, str(campaign.id), [
            {"caseId": "case", "modelName": "A", "output": "First output", "idempotencyKey": "one"},
            {"caseId": "case", "modelName": "B", "output": "Second output", "idempotencyKey": "two"},
        ])
        services.process_submissions(actor, str(campaign.id))
        return campaign, list(ReviewAssignment.objects(campaign_id=campaign.id))
