from datetime import datetime, timezone

from apps.shared.errors import AppError

from .. import audit, repository
from ..models import Campaign, CampaignRevision, ReviewAssignment, Submission


OWNER_ROLES = ("administrator", "owner")
REVIEW_ROLES = ("administrator", "reviewer")

# Scoped analytics cache with 5s TTL and explicit invalidation after mutations
_analytics_cache = {}
_analytics_cache_exp = {}
_ANALYTICS_TTL = 5


def analytics_cache_key(user, campaign_id):
    return f"{user.id}:{campaign_id}:{user.role}"


def invalidate_analytics_cache():
    _analytics_cache.clear()
    _analytics_cache_exp.clear()


def iso(value):
    if not value:
        return None
    moment = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def campaign_case(campaign, case_id):
    return next((case for case in campaign.test_cases if case.get("id") == case_id), None)


def ensure_campaign(campaign_id):
    campaign = repository.find_campaign(campaign_id)
    if campaign is None:
        raise AppError(404, "CAMPAIGN_NOT_FOUND", "That evaluation campaign could not be found.")
    return campaign


def ensure_owner(user, campaign):
    if user.role == "administrator":
        return
    if user.role != "owner" or str(campaign.owner_id) != str(user.id):
        raise AppError(403, "CAMPAIGN_FORBIDDEN", "You do not have access to manage this campaign.")


def save_revision(campaign):
    return CampaignRevision(
        campaign_id=campaign.id,
        version=campaign.version,
        suite_version=campaign.suite_version,
        rubric_version=campaign.rubric_version,
        test_cases=list(campaign.test_cases),
        rubric=list(campaign.rubric),
    ).save()


def current_revision(campaign):
    revision = CampaignRevision.objects(campaign_id=campaign.id, version=campaign.version).first()
    if revision:
        return revision
    return save_revision(campaign)


def mark_reviewing(campaign):
    now = datetime.now(timezone.utc)
    result = audit.update(Campaign,
        {"_id": campaign.id, "status": "running"},
        {"$set": {"status": "reviewing", "updatedAt": now}, "$inc": {"version": 1}},
        None, "campaign.reviewing", {"to": "reviewing"},
    )
    if result is not None:
        campaign.reload()
        return True
    return False


def public_campaign(campaign, include_details=True):
    submissions = Submission.objects(campaign_id=campaign.id)
    reviews = ReviewAssignment.objects(campaign_id=campaign.id)
    data = {
        "id": str(campaign.id),
        "name": campaign.name,
        "summary": campaign.summary,
        "ownerId": str(campaign.owner_id),
        "ownerName": owner.name if (owner := repository.find_user(campaign.owner_id)) else "Campaign owner",
        "status": campaign.status,
        "version": campaign.version,
        "suiteVersion": campaign.suite_version,
        "rubricVersion": campaign.rubric_version,
        "createdAt": iso(campaign.created_at),
        "updatedAt": iso(campaign.updated_at),
        "revisionId": str(current_revision(campaign).id),
        "testCaseCount": len(campaign.test_cases),
        "submissionCount": submissions.count(),
        "reviewCount": reviews(status="completed").count(),
        "queuedCount": submissions(status__in=("queued", "processing")).count(),
        "failedCount": submissions(status="failed").count(),
    }
    if include_details:
        data["testCases"] = campaign.test_cases
        data["rubric"] = campaign.rubric
    return data


def clean_text(value, field, minimum, maximum):
    if not isinstance(value, str):
        raise AppError(400, "INVALID_INPUT", f"{field} must be text.", {"field": field})
    value = value.strip()
    if len(value) < minimum or len(value) > maximum:
        raise AppError(400, "INVALID_INPUT", f"{field} must be between {minimum} and {maximum} characters.", {"field": field})
    return value


def validate_cases(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 80:
        raise AppError(400, "INVALID_TEST_CASES", "Add between 1 and 80 test cases.")
    cases = []
    ids = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise AppError(400, "INVALID_TEST_CASE", f"Test case {index + 1} must be an object.")
        case_id = clean_text(item.get("id", f"case-{index + 1}"), "testCases.id", 1, 80)
        if case_id in ids:
            raise AppError(400, "DUPLICATE_CASE_ID", "Test case IDs must be unique.")
        ids.add(case_id)
        cases.append({"id": case_id, "title": clean_text(item.get("title", f"Test case {index + 1}"), "testCases.title", 1, 120), "prompt": clean_text(item.get("prompt"), "testCases.prompt", 3, 3000)})
    return cases


def validate_rubric(value, require_total):
    if not isinstance(value, list) or not 1 <= len(value) <= 8:
        raise AppError(400, "INVALID_RUBRIC", "Add between 1 and 8 rubric criteria.")
    rubric = []
    seen = set()
    seen_ids = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise AppError(400, "INVALID_RUBRIC_ITEM", f"Rubric criterion {index + 1} must be an object.")
        criterion_id = clean_text(item.get("id", f"criterion-{index + 1}"), "rubric.id", 1, 80)
        if criterion_id in seen_ids:
            raise AppError(400, "DUPLICATE_RUBRIC_ID", "Rubric criterion IDs must be unique.")
        seen_ids.add(criterion_id)
        title = clean_text(item.get("title"), "rubric.title", 2, 80)
        weight = item.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, int) or not 1 <= weight <= 100:
            raise AppError(400, "INVALID_RUBRIC_WEIGHT", "Each rubric weight must be a whole number from 1 to 100.")
        key = title.lower()
        if key in seen:
            raise AppError(400, "DUPLICATE_RUBRIC", "Rubric criterion names must be unique.")
        seen.add(key)
        rubric.append({"id": criterion_id, "title": title, "weight": weight, "description": clean_text(item.get("description", ""), "rubric.description", 0, 240)})
    total = sum(item["weight"] for item in rubric)
    if total > 100 or (require_total and total != 100):
        raise AppError(400, "RUBRIC_TOTAL", f"Rubric weights must total 100% before publishing. Current total: {total}%.", {"total": total})
    return rubric
