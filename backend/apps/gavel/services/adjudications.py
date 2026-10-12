import hashlib
from datetime import datetime, timezone

from apps.shared.errors import AppError

from .. import audit, repository
from ..models import Adjudication, Campaign
from .common import (
    campaign_case,
    ensure_campaign,
    ensure_owner,
    invalidate_analytics_cache,
    iso,
)


def deterministic_side_for_adjudication(item):
    return hashlib.sha256(f"adjudication:{item.pair_key}".encode()).digest()[0] % 2 == 0


def public_adjudication(item):
    campaign = ensure_campaign(str(item.campaign_id))
    left = repository.find_submission(str(item.submission_a_id))
    right = repository.find_submission(str(item.submission_b_id))
    case = campaign_case(campaign, item.case_id) or {"prompt": "Test case"}
    left_first = deterministic_side_for_adjudication(item)
    left, right = (left, right) if left_first else (right, left)
    return {
        "id": str(item.id),
        "campaignId": str(campaign.id),
        "campaignName": campaign.name,
        "caseId": item.case_id,
        "prompt": case.get("prompt", ""),
        "left": {"label": "Response A", "output": left.output if left else "Unavailable"},
        "right": {"label": "Response B", "output": right.output if right else "Unavailable"},
        "status": item.status,
        "rationale": item.rationale,
        "createdAt": iso(item.created_at),
    }


def list_adjudications(user, campaign_id=None, limit=None, cursor=None):
    if user.role not in ("administrator", "adjudicator", "owner"):
        raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot view adjudication cases.")
    if campaign_id:
        campaign = ensure_campaign(campaign_id)
        if user.role == "owner":
            ensure_owner(user, campaign)
    try:
        lim = max(1, min(int(limit), 100)) if limit is not None else 50
    except Exception:
        lim = 50
    owned_ids = list(Campaign.objects(owner_id=user.id, deleted__ne=True).scalar("id")) if user.role == "owner" else None
    rows = repository.list_adjudications(campaign_id, limit=lim, cursor=cursor, campaign_ids=owned_ids)
    items = [public_adjudication(row) for row in rows]
    if limit is not None or cursor is not None:
        next_cursor = str(rows[-1].id) if len(rows) == lim else None
        return {"items": items, "nextCursor": next_cursor}
    return items


def resolve_adjudication(user, adjudication_id, payload):
    item = repository.find_adjudication(adjudication_id)
    if item is None:
        raise AppError(404, "ADJUDICATION_NOT_FOUND", "That adjudication could not be found.")
    if item.status != "open":
        raise AppError(409, "ADJUDICATION_RESOLVED", "This disagreement has already been resolved.")
    choice = payload.get("choice")
    rationale = payload.get("rationale", "")
    if choice not in ("a", "b"):
        raise AppError(400, "INVALID_CHOICE", "Select the final preferred response.")
    if not isinstance(rationale, str) or len(rationale.strip()) < 8 or len(rationale) > 1200:
        raise AppError(400, "RATIONALE_REQUIRED", "Add a rationale between 8 and 1,200 characters.")
    left_first = deterministic_side_for_adjudication(item)
    left_id = item.submission_a_id if left_first else item.submission_b_id
    right_id = item.submission_b_id if left_first else item.submission_a_id
    resolved_at = datetime.now(timezone.utc)
    updated = audit.update(Adjudication,
        {"_id": item.id, "status": "open"},
        {"$set": {"decisionId": left_id if choice == "a" else right_id, "rationale": rationale.strip(), "adjudicatorId": user.id, "status": "resolved", "resolvedAt": resolved_at, "updatedAt": resolved_at}},
        user, "adjudication.resolved", {"campaignId": str(item.campaign_id), "decision": choice, "rationale": rationale.strip()},
    )
    if updated is None:
        raise AppError(409, "ADJUDICATION_RESOLVED", "Another adjudicator has already recorded a decision.")
    item.reload()
    invalidate_analytics_cache()
    return public_adjudication(item)
