from datetime import datetime, timezone

from apps.shared.errors import AppError

from .. import audit
from ..models import Adjudication, Campaign, ReviewAssignment, Submission
from .common import (
    OWNER_ROLES,
    clean_text,
    current_revision,
    ensure_campaign,
    ensure_owner,
    invalidate_analytics_cache,
    public_campaign,
    save_revision,
    validate_cases,
    validate_rubric,
)


def list_campaigns(user, limit=None, cursor=None):
    # Bounded pagination: default 50, max 100, cursor based on updated_at
    try:
        lim = max(1, min(int(limit), 100)) if limit is not None else 50
    except Exception:
        lim = 50
    rows = repository.list_campaigns(limit=lim, cursor=cursor, owner_id=user.id if user.role == "owner" else None)
    items = [public_campaign(row) for row in rows]
    # Provide cursor pagination when client requests it (limit/cursor present)
    if limit is not None or cursor is not None:
        next_cursor = str(rows[-1].id) if len(rows) == lim else None
        return {"items": items, "nextCursor": next_cursor}
    return items


def create_campaign(user, payload):
    if user.role not in OWNER_ROLES:
        raise AppError(403, "ROLE_FORBIDDEN", "Only campaign owners can create campaigns.")
    name = clean_text(payload.get("name"), "name", 3, 120)
    summary = clean_text(payload.get("summary", ""), "summary", 0, 500)
    cases = validate_cases(payload.get("testCases", []))
    rubric = validate_rubric(payload.get("rubric", []), require_total=False)
    campaign = Campaign(
        name=name,
        summary=summary,
        owner_id=user.id,
        test_cases=cases,
        rubric=rubric,
        status="draft",
        version=1,
        suite_version=1,
        rubric_version=1,
    )
    audit.create(campaign, user, "campaign.created", {"name": name, "ownerId": str(user.id)})
    save_revision(campaign)
    invalidate_analytics_cache()
    return public_campaign(campaign)


def update_campaign(user, campaign_id, payload):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    if campaign.status != "draft":
        raise AppError(409, "CAMPAIGN_FROZEN", "Published campaign definitions are frozen. Create a new version to change them.")
    updates = {"updatedAt": datetime.now(timezone.utc)}
    if "name" in payload:
        updates["name"] = clean_text(payload["name"], "name", 3, 120)
    if "summary" in payload:
        updates["summary"] = clean_text(payload["summary"], "summary", 0, 500)
    if "testCases" in payload:
        updated_cases = validate_cases(payload["testCases"])
        if updated_cases != campaign.test_cases:
            updates["testCases"] = updated_cases
            updates["suiteVersion"] = campaign.suite_version + 1
    if "rubric" in payload:
        updated_rubric = validate_rubric(payload["rubric"], require_total=False)
        if updated_rubric != campaign.rubric:
            updates["rubric"] = updated_rubric
            updates["rubricVersion"] = campaign.rubric_version + 1
    result = audit.update(Campaign,
        {"_id": campaign.id, "status": "draft", "version": campaign.version},
        {"$set": updates, "$inc": {"version": 1}},
        user, "campaign.updated", {"version": campaign.version + 1},
    )
    if result is None:
        raise AppError(409, "CAMPAIGN_CHANGED", "The draft changed while you were editing it. Refresh and try again.")
    campaign.reload()
    save_revision(campaign)
    invalidate_analytics_cache()
    return public_campaign(campaign)


def create_campaign_version(user, campaign_id):
    source = ensure_campaign(campaign_id)
    ensure_owner(user, source)
    source_revision = current_revision(source)
    campaign = Campaign(
        name=f"{source.name} v{source.version + 1}",
        summary=source.summary,
        owner_id=source.owner_id,
        status="draft",
        version=1,
        suite_version=source_revision.suite_version,
        rubric_version=source_revision.rubric_version,
        test_cases=list(source_revision.test_cases),
        rubric=list(source_revision.rubric),
    )
    audit.create(campaign, user, "campaign.version_created", {"sourceCampaignId": str(source.id), "sourceRevisionId": str(source_revision.id)})
    save_revision(campaign)
    invalidate_analytics_cache()
    return public_campaign(campaign)


def delete_campaign(user, campaign_id):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    if campaign.status != "draft":
        raise AppError(409, "CAMPAIGN_NOT_DELETABLE", "Only draft campaigns can be deleted. Archive a published campaign instead.")
    if Submission.objects(campaign_id=campaign.id).count() or ReviewAssignment.objects(campaign_id=campaign.id).count():
        raise AppError(409, "CAMPAIGN_HAS_ACTIVITY", "Campaigns with response or review history cannot be deleted.")
    result = audit.update(Campaign, {"_id": campaign.id, "status": "draft", "deleted": {"$ne": True}, "version": campaign.version},
                          {"$set": {"deleted": True}, "$inc": {"version": 1}}, user,
                          "campaign.deleted", {"name": campaign.name, "ownerId": str(user.id)})
    if result is None:
        raise AppError(409, "CAMPAIGN_CHANGED", "The draft changed while you were deleting it. Refresh and try again.")
    invalidate_analytics_cache()


def transition_campaign(user, campaign_id, target):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    allowed = {
        "draft": {"published", "archived"},
        "published": {"running", "archived"},
        "running": {"reviewing", "completed", "archived"},
        "reviewing": {"completed", "archived"},
        "completed": {"archived"},
        "archived": set(),
    }
    if target not in allowed.get(campaign.status, set()):
        raise AppError(409, "INVALID_TRANSITION", f"A campaign cannot move from {campaign.status} to {target}.")
    if target == "published":
        if not campaign.test_cases:
            raise AppError(409, "TEST_CASES_REQUIRED", "Add at least one test case before publishing.")
        validate_rubric(campaign.rubric, require_total=True)
    if target == "completed":
        pending = ReviewAssignment.objects(campaign_id=campaign.id, status__ne="completed").count()
        open_cases = Adjudication.objects(campaign_id=campaign.id, status="open").count()
        unfinished_submissions = Submission.objects(campaign_id=campaign.id, status__in=("queued", "processing", "failed")).count()
        processed_submissions = Submission.objects(campaign_id=campaign.id, status="ready").count()
        if unfinished_submissions:
            raise AppError(409, "SUBMISSIONS_REMAIN", "Process queued responses or retry failed responses before closing this campaign.")
        if not processed_submissions:
            raise AppError(409, "NO_PROCESSED_SUBMISSIONS", "Process at least one response before completing this campaign.")
        if pending or open_cases:
            raise AppError(409, "REVIEWS_REMAIN", "Complete all reviews and resolve open disagreements before closing this campaign.")
    before = campaign.status
    updated = audit.update(Campaign,
        {"_id": campaign.id, "status": before, "version": campaign.version},
        {"$set": {"status": target, "version": campaign.version + 1, "updatedAt": datetime.now(timezone.utc)}},
        user, "campaign.status_changed", {"from": before, "to": target},
    )
    if updated is None:
        raise AppError(409, "CAMPAIGN_CHANGED", "The campaign changed while this transition was being applied. Refresh and try again.")
    campaign.reload()
    invalidate_analytics_cache()
    return public_campaign(campaign)
