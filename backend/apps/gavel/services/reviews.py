import hashlib
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError
from mongoengine.errors import NotUniqueError

from apps.shared.errors import AppError

from .. import audit, repository
from ..models import Adjudication, CampaignRevision, GavelUser, ReviewAssignment, Submission
from .common import (
    REVIEW_ROLES,
    current_revision,
    ensure_campaign,
    invalidate_analytics_cache,
    iso,
    mark_reviewing,
)


def deterministic_side(review, reviewer_id):
    digest = hashlib.sha256(f"{review.pair_key}:{reviewer_id}".encode()).digest()
    return "a" if digest[0] % 2 == 0 else "b"


def public_review(review, user):
    campaign = ensure_campaign(str(review.campaign_id))
    revision = CampaignRevision.objects(id=review.revision_id).first() if review.revision_id else current_revision(campaign)
    submission_a = repository.find_submission(str(review.submission_a_id))
    submission_b = repository.find_submission(str(review.submission_b_id))
    if not submission_a or not submission_b:
        raise AppError(409, "PAIR_UNAVAILABLE", "A response in this comparison is no longer available.")
    left_first = deterministic_side(review, user.id) == "a"
    left, right = (submission_a, submission_b) if left_first else (submission_b, submission_a)
    case = next((item for item in revision.test_cases if item.get("id") == review.case_id), None) or {"prompt": "Test case"}
    result = {
        "id": str(review.id),
        "campaignId": str(campaign.id),
        "campaignName": campaign.name,
        "caseId": review.case_id,
        "prompt": case.get("prompt", ""),
        "rubric": revision.rubric,
        "status": review.status,
        "notes": review.notes,
        "rubricVersion": review.rubric_version,
        "claimedByMe": review.reviewer_id is not None and str(review.reviewer_id) == str(user.id),
        "claimedBy": "You" if review.reviewer_id is not None and str(review.reviewer_id) == str(user.id) else ("Another reviewer" if review.reviewer_id else None),
        "left": {"label": "Response A", "output": left.output},
        "right": {"label": "Response B", "output": right.output},
        "createdAt": iso(review.created_at),
        "criterionScores": review.criterion_scores if review.status == "completed" and str(review.reviewer_id) == str(user.id) else {},
        "weightedScore": review.weighted_score if review.status == "completed" and str(review.reviewer_id) == str(user.id) else {},
    }
    if review.status == "completed" and review.reviewer_id and str(review.reviewer_id) == str(user.id):
        chosen = review.winner_id
        result["myChoice"] = "a" if str(chosen) == str(left.id) else "b"
    return result


def list_reviews(user, campaign_id=None, status=None, limit=None, cursor=None):
    if user.role not in REVIEW_ROLES:
        raise AppError(403, "ROLE_FORBIDDEN", "Only reviewers and administrators can access the review queue.")
    if campaign_id:
        ensure_campaign(campaign_id)
    if status and status not in ("available", "claimed", "completed"):
        raise AppError(400, "INVALID_REVIEW_STATUS", "Select a valid review status.")
    try:
        lim = max(1, min(int(limit), 100)) if limit is not None else 50
    except Exception:
        lim = 50
    rows = repository.list_reviews(campaign_id, limit=lim, cursor=cursor, status=status,
                                   reviewer_id=user.id if user.role == "reviewer" else None)
    items = [public_review(row, user) for row in rows]
    if limit is not None or cursor is not None:
        next_cursor = str(rows[-1].id) if len(rows) == lim else None
        return {"items": items, "nextCursor": next_cursor}
    return items


def independence_group(user):
    # Groups are administrator-maintained; account id is always the default.
    return "group:" + user.independence_group.strip().casefold() if user.independence_group.strip() else "user:" + str(user.id)


def ensure_independent_reviewer(user, campaign, review):
    if user.role not in REVIEW_ROLES:
        raise AppError(403, "ROLE_FORBIDDEN", "Only reviewers and administrators can review.")
    if campaign.status not in ("running", "reviewing"):
        raise AppError(409, "CAMPAIGN_CLOSED", "This campaign is not accepting reviews.")
    owner = repository.find_user(campaign.owner_id)
    if str(campaign.owner_id) == str(user.id) or (owner and independence_group(owner) == independence_group(user)):
        raise AppError(409, "REVIEW_CONFLICT", "Campaign owners and their independence group cannot review their own campaign.")
    if review.campaign_id in (user.conflict_campaign_ids or []):
        raise AppError(409, "REVIEW_CONFLICT", "You are excluded from reviewing this campaign.")
    conflict_models = {name.casefold() for name in (user.conflict_model_names or [])}
    submissions = [repository.find_submission(str(review.submission_a_id)), repository.find_submission(str(review.submission_b_id))]
    if any(item and item.model_name.casefold() in conflict_models for item in submissions):
        raise AppError(409, "REVIEW_CONFLICT", "You are excluded from reviewing a response from a conflicted model.")
    others = ReviewAssignment.objects(campaign_id=review.campaign_id, pair_key=review.pair_key,
                                     id__ne=review.id, status__in=("claimed", "completed"))
    for other in others:
        peer = repository.find_user(other.reviewer_id)
        if (str(other.reviewer_id) == str(user.id) or other.reviewer_group == independence_group(user)
                or (peer and independence_group(peer) == independence_group(user))):
            raise AppError(409, "REVIEW_CONFLICT", "This identity or independence group already reviewed this comparison.")
    if review.status == "claimed" and review.reviewer_group != independence_group(user):
        raise AppError(409, "REVIEW_CONFLICT", "Your independence group changed. Release this assignment and claim it again.")


def claim_review(user, review_id):
    if user.role not in REVIEW_ROLES:
        raise AppError(403, "ROLE_FORBIDDEN", "Only reviewers and administrators can claim reviews.")
    review = repository.find_review(review_id)
    if review is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "That review assignment could not be found.")
    if review.status != "available":
        raise AppError(409, "REVIEW_ALREADY_CLAIMED", "Another reviewer has already claimed this comparison.")
    campaign = ensure_campaign(str(review.campaign_id))
    ensure_independent_reviewer(user, campaign, review)
    group = independence_group(user)
    # Freeze the verified identity on first claim. The operator command uses
    # the inverse CAS, so configuration cannot race a claim with an old group.
    identity_query = {"independence_group": user.independence_group} if user.independence_group else {"independence_group__in": ["", None]}
    identity = GavelUser.objects(id=user.id, active=True, **identity_query).modify(
        set__review_identity_locked=True, new=True)
    if identity is None:
        raise AppError(409, "IDENTITY_CHANGED", "Your review identity changed. Sign in again.")
    if ReviewAssignment.objects(campaign_id=review.campaign_id, pair_key=review.pair_key,
                                reviewer_group=group, status__in=("claimed", "completed")).first():
        raise AppError(409, "REVIEW_CONFLICT", "This identity or independence group already reviewed this comparison.")
    now = datetime.now(timezone.utc)
    try:
        updated = audit.update(ReviewAssignment,
            {"_id": review.id, "status": "available"},
            {"$set": {"status": "claimed", "reviewerId": user.id, "reviewerGroup": group, "reviewerKey": str(user.id), "claimedAt": now}},
            user, "review.claimed", {"campaignId": str(review.campaign_id)},
        )
    except DuplicateKeyError:
        raise AppError(409, "REVIEW_CONFLICT", "This identity or independence group already claimed the other slot.")
    if updated is None:
        raise AppError(409, "REVIEW_ALREADY_CLAIMED", "Another reviewer has already claimed this comparison.")
    review.reload()
    invalidate_analytics_cache()
    return public_review(review, user)


def release_review(user, review_id):
    review = repository.find_review(review_id)
    if review is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "That review assignment could not be found.")
    if review.status != "claimed" or str(review.reviewer_id) != str(user.id):
        raise AppError(409, "REVIEW_NOT_OWNED", "Only the reviewer who claimed this assignment can release it.")
    now = datetime.now(timezone.utc)
    updated = audit.update(ReviewAssignment,
        {"_id": review.id, "status": "claimed", "reviewerId": user.id},
        {"$set": {"status": "available", "reviewerId": None, "claimedAt": None, "updatedAt": now}, "$unset": {"reviewerGroup": "", "reviewerKey": ""}},
        user, "review.released", {"campaignId": str(review.campaign_id)},
    )
    if updated is None:
        raise AppError(409, "REVIEW_ALREADY_SUBMITTED", "This assignment has already been submitted or released.")
    review.reload()
    invalidate_analytics_cache()
    return public_review(review, user)


def submit_review(user, review_id, payload):
    review = repository.find_review(review_id)
    if review is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "That review assignment could not be found.")
    if review.status != "claimed" or str(review.reviewer_id) != str(user.id):
        raise AppError(409, "REVIEW_NOT_OWNED", "Claim this assignment before submitting a review.")
    ensure_independent_reviewer(user, ensure_campaign(str(review.campaign_id)), review)
    choice = payload.get("choice")
    if choice not in ("a", "b"):
        raise AppError(400, "INVALID_CHOICE", "Choose Response A or Response B.")
    notes = payload.get("notes", "")
    if not isinstance(notes, str) or len(notes) > 1200:
        raise AppError(400, "INVALID_NOTES", "Reviewer notes must be 1,200 characters or fewer.")
    revision = CampaignRevision.objects(id=review.revision_id).first() if review.revision_id else current_revision(ensure_campaign(str(review.campaign_id)))
    raw_scores = payload.get("criterionScores")
    if not isinstance(raw_scores, dict):
        raise AppError(400, "CRITERION_SCORES_REQUIRED", "Score both responses for every rubric criterion.")
    criterion_scores = {}
    weighted_score = {"a": 0, "b": 0}
    for criterion in revision.rubric:
        criterion_id = criterion["id"]
        scores = raw_scores.get(criterion_id)
        if not isinstance(scores, dict):
            raise AppError(400, "CRITERION_SCORE_REQUIRED", f"Scores are required for {criterion['title']}.")
        values = {}
        for side in ("a", "b"):
            value = scores.get(side)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 5:
                raise AppError(400, "INVALID_CRITERION_SCORE", "Criterion scores must be numbers from 1 to 5.")
            values[side] = value
            weighted_score[side] += value * criterion["weight"] / 5
        criterion_scores[criterion_id] = values
    left_first = deterministic_side(review, user.id) == "a"
    first_id = review.submission_a_id if left_first else review.submission_b_id
    second_id = review.submission_b_id if left_first else review.submission_a_id
    completed_at = datetime.now(timezone.utc)
    updated = audit.update(ReviewAssignment,
        {"_id": review.id, "status": "claimed", "reviewerId": user.id},
        {"$set": {"winnerId": first_id if choice == "a" else second_id, "notes": notes.strip(), "criterionScores": criterion_scores, "weightedScore": {key: round(value, 2) for key, value in weighted_score.items()}, "status": "completed", "completedAt": completed_at, "updatedAt": completed_at}},
        user, "review.completed", {"campaignId": str(review.campaign_id)},
    )
    if updated is None:
        raise AppError(409, "REVIEW_ALREADY_SUBMITTED", "This assignment has already been submitted or released.")
    review.reload()
    adjudication = detect_disagreement(review)
    campaign = ensure_campaign(str(review.campaign_id))
    if not Submission.objects(campaign_id=campaign.id, status__in=("queued", "processing", "failed")).count():
        mark_reviewing(campaign)
    invalidate_analytics_cache()
    return {"review": public_review(review, user), "disagreementDetected": bool(adjudication)}


def detect_disagreement(review):
    completed = list(ReviewAssignment.objects(campaign_id=review.campaign_id, pair_key=review.pair_key, status="completed"))
    winners = {str(item.winner_id) for item in completed if item.winner_id}
    if len(winners) < 2:
        return None
    existing = Adjudication.objects(campaign_id=review.campaign_id, pair_key=review.pair_key).first()
    if existing:
        return existing
    adjudication = Adjudication(
        campaign_id=review.campaign_id,
        pair_key=review.pair_key,
        case_id=review.case_id,
        submission_a_id=review.submission_a_id,
        submission_b_id=review.submission_b_id,
        status="open",
    )
    try:
        audit.create(adjudication, repository.find_user(str(review.reviewer_id)), "disagreement.detected", {"caseId": review.case_id, "campaignId": str(review.campaign_id)})
    except NotUniqueError:
        return Adjudication.objects(campaign_id=review.campaign_id, pair_key=review.pair_key).first()
    return adjudication
