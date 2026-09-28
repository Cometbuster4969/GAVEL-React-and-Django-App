import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "calendar_backend.settings")

import django

django.setup()

import bcrypt
from bson import ObjectId
from mongoengine.connection import get_db

from apps.gavel.models import Adjudication, AuditEvent, Campaign, GavelUser, ReviewAssignment, Submission


PASSWORD = "gavel2026!"
USERS = [
    ("64a100000000000000000001", "Elena Park", "elena.park@gavel.test", "administrator"),
    ("64a100000000000000000002", "Maya Chen", "maya.chen@gavel.test", "owner"),
    ("64a100000000000000000003", "Jordan Lee", "jordan.lee@gavel.test", "reviewer"),
    ("64a100000000000000000004", "Sam Rivera", "sam.rivera@gavel.test", "reviewer"),
    ("64a100000000000000000005", "Priya Shah", "priya.shah@gavel.test", "adjudicator"),
]

CASES = [
    {"id": "case-retention", "title": "Retention offer", "prompt": "A long-time customer says they are leaving after a delayed delivery. Respond with empathy, acknowledge the issue, and offer an appropriate next step without promising an unapproved refund."},
    {"id": "case-refund", "title": "Refund eligibility", "prompt": "A customer asks for a refund on an order that arrived 18 days ago. Explain the policy clearly, ask only for information needed to resolve the request, and keep the tone helpful."},
    {"id": "case-onboarding", "title": "First-time setup", "prompt": "A new customer cannot connect their workspace during setup. Give concise troubleshooting steps, avoid requesting credentials, and explain how to get further help."},
]

RUBRIC = [
    {"id": "helpfulness", "title": "Helpfulness", "weight": 35, "description": "Moves the customer toward a concrete resolution."},
    {"id": "accuracy", "title": "Accuracy", "weight": 30, "description": "Follows stated policy and avoids unsupported claims."},
    {"id": "empathy", "title": "Empathy", "weight": 20, "description": "Acknowledges the customer's situation with a respectful tone."},
    {"id": "clarity", "title": "Clarity", "weight": 15, "description": "Is concise, structured, and easy to act on."},
]


def stamp(document, moment):
    document.created_at = moment
    document.updated_at = moment
    return document


def seed():
    database = get_db()
    database.command("ping")
    for model in (GavelUser, Campaign, Submission, ReviewAssignment, Adjudication, AuditEvent):
        model.ensure_indexes()
    collection_names = {"gavelusers", "campaigns", "submissions", "reviewassignments", "adjudications", "auditevents"}
    for name in collection_names:
        if name in database.list_collection_names():
            database[name].delete_many({})

    now = datetime.now(timezone.utc)
    password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=10)).decode()
    users = []
    for user_id, name, email, role in USERS:
        users.append(stamp(GavelUser(id=ObjectId(user_id), name=name, email=email, password_hash=password_hash, role=role), now))
    GavelUser.objects.insert(users)
    by_role = {user.role: user for user in users}

    campaign_reviewing = Campaign(
        id=ObjectId("64a200000000000000000001"),
        name="Support response quality",
        summary="Compare two model releases on high-stakes customer support conversations.",
        owner_id=by_role["owner"].id,
        status="reviewing",
        version=3,
        suite_version=2,
        rubric_version=3,
        test_cases=CASES,
        rubric=RUBRIC,
    )
    campaign_running = Campaign(
        id=ObjectId("64a200000000000000000002"),
        name="Onboarding assistant robustness",
        summary="Evaluate clear, safe setup guidance across common onboarding blockers.",
        owner_id=by_role["owner"].id,
        status="running",
        version=2,
        suite_version=1,
        rubric_version=2,
        test_cases=[CASES[2], {"id": "case-access", "title": "Access recovery", "prompt": "A user is locked out after changing devices. Give safe account recovery steps and never ask for their password or authentication code."}],
        rubric=RUBRIC,
    )
    campaign_draft = Campaign(
        id=ObjectId("64a200000000000000000003"),
        name="Policy answer consistency",
        summary="A draft evaluation for consistent, policy-aligned answers.",
        owner_id=by_role["owner"].id,
        status="draft",
        version=1,
        suite_version=1,
        rubric_version=1,
        test_cases=[{"id": "case-policy", "title": "Policy explanation", "prompt": "Explain a policy decision in plain language and suggest the next step."}],
        rubric=RUBRIC,
    )
    Campaign.objects.insert([stamp(campaign_reviewing, now), stamp(campaign_running, now), stamp(campaign_draft, now)])

    outputs = [
        ("64a300000000000000000001", "case-retention", "Aster-2", "I understand how frustrating a delayed delivery can be, especially after relying on us for so long. I can check the shipment status and review the options available for your order. Could you share the order number?"),
        ("64a300000000000000000002", "case-retention", "Nimbus-4", "Sorry about that. We can help. Send your order number and I will check where the package is. I cannot confirm a refund until I review the order, but I can explain the next steps."),
        ("64a300000000000000000003", "case-refund", "Aster-2", "Thanks for checking with us. Refund eligibility depends on the item and its condition. Please share the order number and item name, and I can confirm the available options under the return policy."),
        ("64a300000000000000000004", "case-refund", "Nimbus-4", "You can request a refund within 30 days, so your order is eligible. I have started the refund and it should arrive soon."),
        ("64a300000000000000000005", "case-onboarding", "Aster-2", "Let's get your workspace connected. First, confirm the setup link is still open, then try refreshing the page. If the issue continues, tell me which step shows an error. Never share your password here."),
        ("64a300000000000000000006", "case-onboarding", "Nimbus-4", "Try signing out and back in. If that does not work, send your login details to support so we can connect the workspace for you."),
    ]
    submissions = []
    for submission_id, case_id, model_name, output in outputs:
        submissions.append(stamp(Submission(
            id=ObjectId(submission_id),
            campaign_id=campaign_reviewing.id,
            case_id=case_id,
            model_name=model_name,
            output=output,
            idempotency_key=f"seed:{submission_id}",
            status="ready",
            attempt=1,
            rubric_version=3,
        ), now))

    queued = stamp(Submission(
        id=ObjectId("64a300000000000000000007"),
        campaign_id=campaign_running.id,
        case_id="case-onboarding",
        model_name="Aster-2.1",
        output="Start by checking that the workspace URL is correct, then refresh the setup page. If the issue remains, note the exact error message and contact support through the help center. Do not share your password or verification code.",
        idempotency_key="seed:queued-onboarding-v1",
        status="queued",
        attempt=0,
        rubric_version=2,
    ))
    submissions.append(queued)
    failed = stamp(Submission(
        id=ObjectId("64a300000000000000000008"),
        campaign_id=campaign_running.id,
        case_id="case-onboarding",
        model_name="Nimbus-3.0",
        output="First-attempt payload retained for safe retry testing. The response can be retried without duplicating the submission.",
        idempotency_key="seed:failed-onboarding-v1",
        status="failed",
        attempt=1,
        failure_reason="The response payload failed the first processing attempt; retry is available.",
        force_failure=True,
        rubric_version=2,
    ), now)
    submissions.append(failed)
    Submission.objects.insert(submissions)

    pair_data = [
        ("64a400000000000000000001", "64a300000000000000000001", "64a300000000000000000002", "case-retention"),
        ("64a400000000000000000002", "64a300000000000000000003", "64a300000000000000000004", "case-refund"),
        ("64a400000000000000000003", "64a300000000000000000005", "64a300000000000000000006", "case-onboarding"),
    ]
    assignments = []
    for pair_index, (_, first_id, second_id, case_id) in enumerate(pair_data, start=1):
        first = ObjectId(first_id)
        second = ObjectId(second_id)
        pair_key = f"{campaign_reviewing.id}:{case_id}:{first}:{second}"
        if pair_index == 1:
            states = [(by_role["reviewer"], first), (users[3], first)]
        elif pair_index == 2:
            states = [(users[2], first), (users[3], second)]
        else:
            states = [(users[2], second), (None, None)]
        for offset, (reviewer, winner) in enumerate(states, start=1):
            assignment_id = ObjectId(f"64a400{pair_index:06d}{offset:06d}000001")
            status = "completed" if reviewer else "available"
            assignments.append(stamp(ReviewAssignment(
                id=assignment_id,
                campaign_id=campaign_reviewing.id,
                pair_key=pair_key,
                case_id=case_id,
                submission_a_id=first,
                submission_b_id=second,
                slot=offset - 1,
                reviewer_id=reviewer.id if reviewer else None,
                status=status,
                winner_id=winner if reviewer else None,
                notes="Clearer and more policy-aware response." if reviewer and winner == first else ("The preferred response is concise and safe." if reviewer else ""),
                rubric_version=3,
                claimed_at=now if reviewer else None,
                completed_at=now if reviewer else None,
            ), now))
    ReviewAssignment.objects.insert(assignments)

    case_two_pair = assignments[2].pair_key
    Adjudication(
        id=ObjectId("64a500000000000000000001"),
        campaign_id=campaign_reviewing.id,
        pair_key=case_two_pair,
        case_id="case-refund",
        submission_a_id=ObjectId("64a300000000000000000003"),
        submission_b_id=ObjectId("64a300000000000000000004"),
        status="open",
    ).save()

    seed_events = [
        (users[0], "campaign.published", "campaign", str(campaign_reviewing.id), {"name": campaign_reviewing.name}),
        (users[1], "submissions.queued", "campaign", str(campaign_reviewing.id), {"count": 6}),
        (users[0], "reviews.generated", "campaign", str(campaign_reviewing.id), {"assignments": 6}),
        (users[2], "review.completed", "review", str(assignments[0].id), {"caseId": "case-retention", "campaignId": str(campaign_reviewing.id)}),
        (users[3], "disagreement.detected", "adjudication", "64a500000000000000000001", {"caseId": "case-refund", "campaignId": str(campaign_reviewing.id)}),
    ]
    AuditEvent.objects.insert([
        stamp(AuditEvent(actor_id=actor.id, actor_name=actor.name, action=action, entity_type=entity_type, entity_id=entity_id, details=details), now)
        for actor, action, entity_type, entity_id, details in seed_events
    ])

    print("Gavel database seeded successfully")
    print(f"  Users: {len(users)} | Campaigns: 3 | Submissions: {len(submissions)} | Review assignments: {len(assignments)}")
    print(f"  Demo password: {PASSWORD}")
    for _, name, email, role in USERS:
        print(f"  {role:14} {name:12} {email}")


if __name__ == "__main__":
    seed()
