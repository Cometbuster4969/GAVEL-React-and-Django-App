import hashlib
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo import ReturnDocument
from mongoengine.errors import NotUniqueError

from apps.shared.errors import AppError

from . import repository
from .models import Adjudication, AuditEvent, Campaign, CampaignRevision, ProcessingJob, ResultPublication, ReviewAssignment, Submission


OWNER_ROLES = ("administrator", "owner")
REVIEW_ROLES = ("administrator", "reviewer")

# Scoped analytics cache with 5s TTL and explicit invalidation after mutations
_analytics_cache = {}
_analytics_cache_exp = {}
_ANALYTICS_TTL = 5


def _analytics_cache_key(user, campaign_id):
    return f"{user.id}:{campaign_id}:{user.role}"


def _invalidate_analytics_cache():
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


def record(user, action, entity_type, entity_id, details=None):
    """Write audit intent to the outbox, then attempt inline delivery.

    The outbox write is the durability boundary: if delivery fails, the intent
    stays pending and ``drain_audit_outbox`` retries it with backoff. The inline
    attempt keeps the audit feed live for the common case (no UI lag).
    """
    if user is None:
        return None
    try:
        entry = repository.enqueue_audit_outbox(user, action, entity_type, entity_id, details)
    except Exception:
        # Fall back to the direct append-only write when the outbox is unavailable.
        try:
            repository.record_audit(user, action, entity_type, entity_id, details)
        except Exception:
            pass
        return None
    try:
        repository.deliver_audit_event(entry)
        repository.mark_audit_outbox_delivered(entry.event_id, datetime.now(timezone.utc))
    except Exception:
        # Delivery is retried by the worker; the domain operation is unaffected.
        pass
    return entry.event_id


def drain_audit_outbox(limit=25, max_attempts=5, base_delay=30):
    """Deliver pending audit-outbox entries with bounded retries.

    Returns counters for the worker's log line. Delivery is idempotent per
    ``eventId``, so running this more than once never duplicates audit rows.
    """
    now = datetime.now(timezone.utc)
    repository.recover_stale_audit_outbox(now - timedelta(seconds=300))
    stats = {"scanned": 0, "delivered": 0, "retried": 0, "failed": 0}
    for _ in range(max(int(limit), 1)):
        entry = repository.claim_audit_outbox(now)
        if entry is None:
            break
        stats["scanned"] += 1
        try:
            repository.deliver_audit_event(entry)
            repository.mark_audit_outbox_delivered(entry["eventId"], datetime.now(timezone.utc))
            stats["delivered"] += 1
        except Exception as error:
            outcome = repository.mark_audit_outbox_failed(entry["eventId"], datetime.now(timezone.utc), error, max_attempts, base_delay)
            stats["failed" if outcome == "failed" else "retried"] += 1
    stats.update(repository.count_audit_outbox())
    return stats


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
    result = Campaign._get_collection().update_one(
        {"_id": campaign.id, "status": "running"},
        {"$set": {"status": "reviewing", "updatedAt": now}, "$inc": {"version": 1}},
    )
    if result.modified_count:
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


def public_submission(item):
    return {
        "id": str(item.id),
        "campaignId": str(item.campaign_id),
        "caseId": item.case_id,
        "modelName": item.model_name,
        "output": item.output,
        "status": item.status,
        "attempt": item.attempt,
        "failureReason": item.failure_reason,
        "rubricVersion": item.rubric_version,
        "revisionId": str(item.revision_id) if item.revision_id else None,
        "idempotencyKey": item.idempotency_key,
        "createdAt": iso(item.created_at),
        "updatedAt": iso(item.updated_at),
    }


def create_review_pairs(campaign):
    revision = current_revision(campaign)
    ready = list(Submission.objects(campaign_id=campaign.id, status="ready").order_by("created_at"))
    by_case = defaultdict(list)
    for submission in ready:
        by_case[submission.case_id].append(submission)
    created = 0
    for case_id, candidates in by_case.items():
        for index, first in enumerate(candidates):
            for second in candidates[index + 1 :]:
                if first.model_name.casefold() == second.model_name.casefold():
                    continue
                first_id, second_id = sorted((str(first.id), str(second.id)))
                pair_key = f"{campaign.id}:{case_id}:{first_id}:{second_id}"
                for slot in range(2):
                    if ReviewAssignment.objects(campaign_id=campaign.id, pair_key=pair_key, slot=slot).first():
                        continue
                    submission_a, submission_b = (first, second) if str(first.id) == first_id else (second, first)
                    try:
                        ReviewAssignment(
                            campaign_id=campaign.id,
                            pair_key=pair_key,
                            case_id=case_id,
                            submission_a_id=submission_a.id,
                            submission_b_id=submission_b.id,
                            slot=slot,
                            rubric_version=revision.rubric_version,
                            revision_id=revision.id,
                        ).save()
                        created += 1
                    except NotUniqueError:
                        continue
    return created


def list_campaigns(user, limit=None, cursor=None):
    # Bounded pagination: default 50, max 100, cursor based on updated_at
    try:
        lim = min(int(limit), 100) if limit is not None else 50
    except Exception:
        lim = 50
    rows = repository.list_campaigns(limit=lim, cursor=cursor)
    if user.role == "owner":
        rows = [row for row in rows if str(row.owner_id) == str(user.id)]
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
    ).save()
    save_revision(campaign)
    record(user, "campaign.created", "campaign", campaign.id, {"name": campaign.name, "ownerId": str(user.id)})
    _invalidate_analytics_cache()
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
    result = Campaign._get_collection().find_one_and_update(
        {"_id": campaign.id, "status": "draft", "version": campaign.version},
        {"$set": updates, "$inc": {"version": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        raise AppError(409, "CAMPAIGN_CHANGED", "The draft changed while you were editing it. Refresh and try again.")
    campaign.reload()
    save_revision(campaign)
    record(user, "campaign.updated", "campaign", campaign.id, {"version": campaign.version})
    _invalidate_analytics_cache()
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
    ).save()
    revision = save_revision(campaign)
    record(user, "campaign.version_created", "campaign", campaign.id, {"sourceCampaignId": str(source.id), "sourceRevisionId": str(source_revision.id), "revisionId": str(revision.id)})
    _invalidate_analytics_cache()
    return public_campaign(campaign)


def delete_campaign(user, campaign_id):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    if campaign.status != "draft":
        raise AppError(409, "CAMPAIGN_NOT_DELETABLE", "Only draft campaigns can be deleted. Archive a published campaign instead.")
    if Submission.objects(campaign_id=campaign.id).count() or ReviewAssignment.objects(campaign_id=campaign.id).count():
        raise AppError(409, "CAMPAIGN_HAS_ACTIVITY", "Campaigns with response or review history cannot be deleted.")
    result = Campaign._get_collection().delete_one({"_id": campaign.id, "status": "draft", "version": campaign.version})
    if result.deleted_count != 1:
        raise AppError(409, "CAMPAIGN_CHANGED", "The draft changed while you were deleting it. Refresh and try again.")
    record(user, "campaign.deleted", "campaign", campaign.id, {"name": campaign.name, "ownerId": str(user.id)})
    _invalidate_analytics_cache()


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
    updated = Campaign._get_collection().find_one_and_update(
        {"_id": campaign.id, "status": before, "version": campaign.version},
        {"$set": {"status": target, "version": campaign.version + 1, "updatedAt": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise AppError(409, "CAMPAIGN_CHANGED", "The campaign changed while this transition was being applied. Refresh and try again.")
    campaign.reload()
    record(user, "campaign.status_changed", "campaign", campaign.id, {"from": before, "to": target})
    _invalidate_analytics_cache()
    return public_campaign(campaign)


def list_submissions(user, campaign_id, limit=None, cursor=None):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    try:
        lim = min(int(limit), 100) if limit is not None else 50
    except Exception:
        lim = 50
    rows = repository.list_submissions(campaign.id, limit=lim, cursor=cursor)
    items = [public_submission(item) for item in rows]
    if limit is not None or cursor is not None:
        next_cursor = str(rows[-1].id) if len(rows) == lim else None
        return {"items": items, "nextCursor": next_cursor}
    return items


def ingest_submissions(user, campaign_id, items):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    if campaign.status != "running":
        raise AppError(409, "CAMPAIGN_NOT_RUNNING", "Submissions are accepted only while a campaign is running.")
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise AppError(400, "INVALID_BATCH", "Submit between 1 and 100 responses per batch.")
    validated = []
    revision = current_revision(campaign)
    batch_models = set()
    batch_keys = set()
    for index, payload in enumerate(items):
        if not isinstance(payload, dict):
            raise AppError(400, "INVALID_SUBMISSION", f"Submission {index + 1} must be an object.")
        case_id = clean_text(payload.get("caseId"), "caseId", 1, 80)
        if not campaign_case(campaign, case_id):
            raise AppError(400, "CASE_NOT_FOUND", f"Test case {case_id} is not part of this campaign.")
        model_name = clean_text(payload.get("modelName"), "modelName", 1, 120)
        output = clean_text(payload.get("output"), "output", 1, 12000)
        key = clean_text(payload.get("idempotencyKey"), "idempotencyKey", 1, 160)
        batch_key = (case_id, model_name.casefold())
        if batch_key in batch_models:
            raise AppError(400, "DUPLICATE_MODEL_RESPONSE", "Submit at most one response per model for each test case in a batch.")
        if key in batch_keys:
            raise AppError(400, "DUPLICATE_IDEMPOTENCY_KEY", "Each response in a batch needs a unique idempotency key.")
        batch_models.add(batch_key)
        batch_keys.add(key)
        simulate_failure = payload.get("simulateFailure", False)
        if not isinstance(simulate_failure, bool):
            raise AppError(400, "INVALID_FAILURE_FLAG", "simulateFailure must be a boolean.")
        existing = Submission.objects(campaign_id=campaign.id, idempotency_key=key).first()
        if existing and (existing.case_id != case_id or existing.model_name != model_name or existing.output != output):
            raise AppError(409, "IDEMPOTENCY_CONFLICT", "That idempotency key was already used for a different response.")
        validated.append({"caseId": case_id, "modelName": model_name, "output": output, "idempotencyKey": key, "simulateFailure": simulate_failure, "existing": existing})

    outcomes = []
    for row in validated:
        existing = row["existing"]
        if existing:
            outcomes.append({"submission": public_submission(existing), "duplicate": True})
            continue
        item = Submission(
            campaign_id=campaign.id,
            case_id=row["caseId"],
            model_name=row["modelName"],
            output=row["output"],
            idempotency_key=row["idempotencyKey"],
            status="queued",
            attempt=0,
            force_failure=row["simulateFailure"],
            rubric_version=revision.rubric_version,
            revision_id=revision.id,
        )
        try:
            item.save()
        except NotUniqueError:
            existing = Submission.objects(campaign_id=campaign.id, idempotency_key=row["idempotencyKey"]).first()
            if not existing or existing.case_id != row["caseId"] or existing.model_name != row["modelName"] or existing.output != row["output"]:
                raise AppError(409, "IDEMPOTENCY_CONFLICT", "That idempotency key was already used for a different response.")
            item = existing
            outcomes.append({"submission": public_submission(item), "duplicate": True})
            continue
        outcomes.append({"submission": public_submission(item), "duplicate": False})
    ProcessingJob(campaign_id=campaign.id, available_at=datetime.now(timezone.utc)).save()
    record(user, "submissions.queued", "campaign", campaign.id, {"count": sum(not row["duplicate"] for row in outcomes)})
    _invalidate_analytics_cache()
    return outcomes


def process_submissions(user, campaign_id, limit=25):
    campaign = ensure_campaign(campaign_id)
    if user is not None:
        ensure_owner(user, campaign)
    if campaign.status != "running":
        raise AppError(409, "CAMPAIGN_NOT_RUNNING", "Only running campaigns can process queued responses.")
    now = datetime.now(timezone.utc)
    stale_before = now.timestamp() - 300
    stale_moment = datetime.fromtimestamp(stale_before, timezone.utc)
    Submission._get_collection().update_many(
        {"campaignId": campaign.id, "status": "processing", "updatedAt": {"$lt": stale_moment}},
        {"$set": {"status": "queued", "updatedAt": now}},
    )
    candidates = list(Submission.objects(campaign_id=campaign.id, status="queued").order_by("created_at").limit(limit))
    processed = 0
    for candidate in candidates:
        claimed = Submission._get_collection().find_one_and_update(
            {"_id": candidate.id, "status": "queued"},
            {"$set": {"status": "processing", "updatedAt": now}, "$inc": {"attempt": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if claimed is None:
            continue
        attempt = claimed.get("attempt", 1)
        should_fail = claimed.get("forceFailure", False) and attempt == 1
        final_status = "failed" if should_fail else "ready"
        failure_reason = "The response payload failed the first processing attempt; retry is available." if should_fail else ""
        Submission._get_collection().update_one(
            {"_id": candidate.id, "status": "processing"},
            {"$set": {"status": final_status, "failureReason": failure_reason, "updatedAt": datetime.now(timezone.utc)}},
        )
        processed += 1
    created_reviews = create_review_pairs(campaign)
    ready_count = Submission.objects(campaign_id=campaign.id, status="ready").count()
    if created_reviews and mark_reviewing(campaign):
        record(user, "reviews.generated", "campaign", campaign.id, {"assignments": created_reviews})
    record(user, "submissions.processed", "campaign", campaign.id, {"processed": processed, "reviewAssignments": created_reviews})
    _invalidate_analytics_cache()
    return {
        "processed": processed,
        "ready": ready_count,
        "queued": Submission.objects(campaign_id=campaign.id, status__in=("queued", "processing")).count(),
        "failed": Submission.objects(campaign_id=campaign.id, status="failed").count(),
        "reviewAssignmentsCreated": created_reviews,
    }


def retry_submission(user, campaign_id, submission_id):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    submission = repository.find_submission(submission_id)
    if submission is None or submission.campaign_id != campaign.id:
        raise AppError(404, "SUBMISSION_NOT_FOUND", "That response could not be found.")
    if submission.status != "failed":
        raise AppError(409, "SUBMISSION_NOT_FAILED", "Only failed responses can be retried.")
    if campaign.status != "running":
        raise AppError(409, "CAMPAIGN_NOT_RUNNING", "Failed responses can be retried only while the campaign is running.")
    if submission.attempt >= 3:
        raise AppError(409, "RETRY_LIMIT_REACHED", "This response has reached the three-attempt retry limit.")
    submission.status = "queued"
    submission.failure_reason = ""
    submission.save()
    record(user, "submission.retry_queued", "submission", submission.id, {"attempt": submission.attempt + 1})
    _invalidate_analytics_cache()
    return public_submission(submission)


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
        lim = min(int(limit), 100) if limit is not None else 50
    except Exception:
        lim = 50
    rows = repository.list_reviews(campaign_id, limit=lim, cursor=cursor, status=status)
    # Post-filter for reviewer visibility (owner sees only own claims)
    if user.role == "reviewer":
        rows = [row for row in rows if row.status == "available" or str(row.reviewer_id) == str(user.id)]
    items = [public_review(row, user) for row in rows]
    if limit is not None or cursor is not None:
        next_cursor = str(rows[-1].id) if len(rows) == lim else None
        return {"items": items, "nextCursor": next_cursor}
    return items


def claim_review(user, review_id):
    review = repository.find_review(review_id)
    if review is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "That review assignment could not be found.")
    if review.status != "available":
        raise AppError(409, "REVIEW_ALREADY_CLAIMED", "Another reviewer has already claimed this comparison.")
    campaign = ensure_campaign(str(review.campaign_id))
    if review.campaign_id in (user.conflict_campaign_ids or []):
        raise AppError(409, "REVIEW_CONFLICT", "You are excluded from reviewing this campaign.")
    conflict_models = {name.casefold() for name in (user.conflict_model_names or [])}
    submissions = [repository.find_submission(str(review.submission_a_id)), repository.find_submission(str(review.submission_b_id))]
    if any(item and item.model_name.casefold() in conflict_models for item in submissions):
        raise AppError(409, "REVIEW_CONFLICT", "You are excluded from reviewing a response from a conflicted model.")
    if ReviewAssignment.objects(campaign_id=review.campaign_id, pair_key=review.pair_key, reviewer_id=user.id, status__in=("claimed", "completed")).first():
        raise AppError(409, "REVIEW_CONFLICT", "A reviewer cannot review both slots of the same comparison.")
    now = datetime.now(timezone.utc)
    updated = ReviewAssignment._get_collection().find_one_and_update(
        {"_id": review.id, "status": "available"},
        {"$set": {"status": "claimed", "reviewerId": user.id, "claimedAt": now}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise AppError(409, "REVIEW_ALREADY_CLAIMED", "Another reviewer has already claimed this comparison.")
    review.reload()
    record(user, "review.claimed", "review", review.id, {"campaignId": str(review.campaign_id)})
    _invalidate_analytics_cache()
    return public_review(review, user)


def release_review(user, review_id):
    review = repository.find_review(review_id)
    if review is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "That review assignment could not be found.")
    if review.status != "claimed" or str(review.reviewer_id) != str(user.id):
        raise AppError(409, "REVIEW_NOT_OWNED", "Only the reviewer who claimed this assignment can release it.")
    now = datetime.now(timezone.utc)
    updated = ReviewAssignment._get_collection().find_one_and_update(
        {"_id": review.id, "status": "claimed", "reviewerId": user.id},
        {"$set": {"status": "available", "reviewerId": None, "claimedAt": None, "updatedAt": now}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise AppError(409, "REVIEW_ALREADY_SUBMITTED", "This assignment has already been submitted or released.")
    review.reload()
    record(user, "review.released", "review", review.id, {"campaignId": str(review.campaign_id)})
    _invalidate_analytics_cache()
    return public_review(review, user)


def submit_review(user, review_id, payload):
    review = repository.find_review(review_id)
    if review is None:
        raise AppError(404, "REVIEW_NOT_FOUND", "That review assignment could not be found.")
    if review.status != "claimed" or str(review.reviewer_id) != str(user.id):
        raise AppError(409, "REVIEW_NOT_OWNED", "Claim this assignment before submitting a review.")
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
    updated = ReviewAssignment._get_collection().find_one_and_update(
        {"_id": review.id, "status": "claimed", "reviewerId": user.id},
        {"$set": {"winnerId": first_id if choice == "a" else second_id, "notes": notes.strip(), "criterionScores": criterion_scores, "weightedScore": {key: round(value, 2) for key, value in weighted_score.items()}, "status": "completed", "completedAt": completed_at, "updatedAt": completed_at}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise AppError(409, "REVIEW_ALREADY_SUBMITTED", "This assignment has already been submitted or released.")
    review.reload()
    adjudication = detect_disagreement(review)
    campaign = ensure_campaign(str(review.campaign_id))
    mark_reviewing(campaign)
    record(user, "review.completed", "review", review.id, {"caseId": review.case_id, "disagreementDetected": bool(adjudication), "campaignId": str(review.campaign_id)})
    _invalidate_analytics_cache()
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
        adjudication.save()
    except NotUniqueError:
        return Adjudication.objects(campaign_id=review.campaign_id, pair_key=review.pair_key).first()
    record_user = repository.find_user(str(review.reviewer_id))
    if record_user:
        record(record_user, "disagreement.detected", "adjudication", adjudication.id, {"caseId": review.case_id, "campaignId": str(review.campaign_id)})
    return adjudication


def list_adjudications(user, campaign_id=None, limit=None, cursor=None):
    if user.role not in ("administrator", "adjudicator", "owner"):
        raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot view adjudication cases.")
    if campaign_id:
        campaign = ensure_campaign(campaign_id)
        if user.role == "owner":
            ensure_owner(user, campaign)
    try:
        lim = min(int(limit), 100) if limit is not None else 50
    except Exception:
        lim = 50
    rows = repository.list_adjudications(campaign_id, limit=lim, cursor=cursor)
    if user.role == "owner":
        rows = [row for row in rows if (campaign := repository.find_campaign(str(row.campaign_id))) and str(campaign.owner_id) == str(user.id)]
    items = [public_adjudication(row) for row in rows]
    if limit is not None or cursor is not None:
        next_cursor = str(rows[-1].id) if len(rows) == lim else None
        return {"items": items, "nextCursor": next_cursor}
    return items


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
    updated = Adjudication._get_collection().find_one_and_update(
        {"_id": item.id, "status": "open"},
        {"$set": {"decisionId": left_id if choice == "a" else right_id, "rationale": rationale.strip(), "adjudicatorId": user.id, "status": "resolved", "resolvedAt": resolved_at, "updatedAt": resolved_at}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise AppError(409, "ADJUDICATION_RESOLVED", "Another adjudicator has already recorded a decision.")
    item.reload()
    record(user, "adjudication.resolved", "adjudication", item.id, {"caseId": item.case_id, "decision": choice, "rationale": item.rationale, "campaignId": str(item.campaign_id)})
    _invalidate_analytics_cache()
    return public_adjudication(item)


def deterministic_side_for_adjudication(item):
    return hashlib.sha256(f"adjudication:{item.pair_key}".encode()).digest()[0] % 2 == 0


def analytics(user, campaign_id=None):
    # Scoped cache check (per-user, per-campaign, 5s TTL, invalidated on mutations)
    _key = _analytics_cache_key(user, campaign_id)
    _now = time.time()
    if _key in _analytics_cache and _now - _analytics_cache_exp.get(_key, 0) < _ANALYTICS_TTL:
        return _analytics_cache[_key]
    campaigns = repository.list_campaigns()
    if campaign_id:
        selected = ensure_campaign(campaign_id)
        if user.role == "owner":
            ensure_owner(user, selected)
        elif user.role not in ("administrator", "adjudicator"):
            raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot access campaign analytics.")
        campaigns = [selected]
    elif user.role == "owner":
        campaigns = [row for row in campaigns if str(row.owner_id) == str(user.id)]
    campaign_ids = [row.id for row in campaigns]
    submissions = list(Submission.objects(campaign_id__in=campaign_ids)) if campaign_ids else []
    reviews = list(ReviewAssignment.objects(campaign_id__in=campaign_ids)) if campaign_ids else []
    adjudications = list(Adjudication.objects(campaign_id__in=campaign_ids)) if campaign_ids else []
    model_wins = defaultdict(int)
    resolved_pairs = 0
    for review in reviews:
        if review.status != "completed" or not review.winner_id:
            continue
        winner = repository.find_submission(str(review.winner_id))
        if winner:
            model_wins[winner.model_name] += 1
    for case in adjudications:
        if case.status == "resolved" and case.decision_id:
            winner = repository.find_submission(str(case.decision_id))
            if winner:
                model_wins[winner.model_name] += 1
            resolved_pairs += 1
    total_completed = sum(1 for row in reviews if row.status == "completed")
    pair_assignments = defaultdict(int)
    pair_votes = defaultdict(list)
    for row in reviews:
        pair_assignments[row.pair_key] += 1
        if row.status == "completed" and row.winner_id:
            pair_votes[row.pair_key].append(str(row.winner_id))
    completed_pairs = [votes for pair, votes in pair_votes.items() if len(votes) == pair_assignments[pair] and pair_assignments[pair] >= 2]
    agreement = sum(1 for votes in completed_pairs if len(set(votes)) == 1)
    campaign_breakdown = []
    for campaign in campaigns:
        campaign_assignments = defaultdict(int)
        campaign_votes = defaultdict(list)
        campaign_reviews = [row for row in reviews if row.campaign_id == campaign.id and row.status == "completed" and row.winner_id]
        for row in reviews:
            if row.campaign_id == campaign.id:
                campaign_assignments[row.pair_key] += 1
        for row in campaign_reviews:
            campaign_votes[row.pair_key].append(str(row.winner_id))
        complete_campaign_pairs = [votes for pair, votes in campaign_votes.items() if len(votes) == campaign_assignments[pair] and campaign_assignments[pair] >= 2]
        campaign_agreement = sum(1 for votes in complete_campaign_pairs if len(set(votes)) == 1)
        campaign_row = public_campaign(campaign, include_details=False)
        campaign_row["agreementRate"] = round((campaign_agreement / len(complete_campaign_pairs)) * 100) if complete_campaign_pairs else 0
        campaign_row["reviewCount"] = len(campaign_reviews)
        campaign_breakdown.append(campaign_row)
    result = {
        "campaigns": len(campaigns),
        "submissions": len(submissions),
        "processed": sum(1 for row in submissions if row.status == "ready"),
        "failed": sum(1 for row in submissions if row.status == "failed"),
        "queued": sum(1 for row in submissions if row.status in ("queued", "processing")),
        "reviewsCompleted": total_completed,
        "reviewsPending": sum(1 for row in reviews if row.status != "completed"),
        "openDisagreements": sum(1 for row in adjudications if row.status == "open"),
        "resolvedDisagreements": resolved_pairs,
        "agreementRate": round((agreement / len(completed_pairs)) * 100) if completed_pairs else 0,
        "modelWins": [{"model": name, "wins": wins} for name, wins in sorted(model_wins.items(), key=lambda row: (-row[1], row[0]))],
        "campaignBreakdown": campaign_breakdown,
    }
    # Store in scoped cache with TTL; invalidated on mutations
    _analytics_cache[_key] = result
    _analytics_cache_exp[_key] = _now
    return result


def publish_results(user, campaign_id):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    if campaign.status != "completed":
        raise AppError(409, "CAMPAIGN_NOT_COMPLETE", "Complete all reviews and disagreements before publishing results.")
    latest = ResultPublication.objects(campaign_id=campaign.id).order_by("-version").first()
    version = latest.version + 1 if latest else 1
    revision = current_revision(campaign)
    publication = ResultPublication(
        campaign_id=campaign.id,
        revision_id=revision.id,
        version=version,
        snapshot=analytics(user, str(campaign.id)),
        published_by=user.id,
        published_at=datetime.now(timezone.utc),
    ).save()
    record(user, "results.published", "publication", publication.id, {"campaignId": str(campaign.id), "version": version, "revisionId": str(revision.id)})
    _invalidate_analytics_cache()
    return public_publication(publication)


def public_publication(publication):
    return {
        "id": str(publication.id),
        "campaignId": str(publication.campaign_id),
        "revisionId": str(publication.revision_id) if publication.revision_id else None,
        "version": publication.version,
        "publishedBy": str(publication.published_by),
        "publishedAt": iso(publication.published_at),
        "snapshot": publication.snapshot,
    }


def get_published_results(user, campaign_id):
    campaign = ensure_campaign(campaign_id)
    if user.role == "owner":
        ensure_owner(user, campaign)
    elif user.role not in ("administrator", "adjudicator"):
        raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot access published results.")
    publication = ResultPublication.objects(campaign_id=campaign.id).order_by("-version").first()
    if publication is None:
        raise AppError(404, "RESULTS_NOT_PUBLISHED", "Results have not been published for this campaign.")
    return public_publication(publication)


def audit_log(user, cursor=None, limit=60):
    if user.role not in ("administrator", "owner", "adjudicator"):
        raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot access the audit history.")
    try:
        lim = min(int(limit), 100) if limit is not None else 60
    except Exception:
        lim = 60
    rows = repository.list_audit(limit=lim, cursor=cursor)
    if user.role == "owner":
        owned_ids = {str(row.id) for row in Campaign.objects(owner_id=user.id)}
        rows = [
            row
            for row in rows
            if str(row.details.get("ownerId", "")) == str(user.id)
            or str(row.details.get("campaignId", "")) in owned_ids
            or (row.entity_type == "campaign" and row.entity_id in owned_ids)
        ]
    return {
        "items": [
            {
                "id": str(row.id),
                "actor": row.actor_name,
                "action": row.action,
                "entityType": row.entity_type,
                "entityId": row.entity_id,
                "details": row.details,
                "createdAt": iso(row.created_at),
            }
            for row in rows
        ],
        "nextCursor": str(rows[-1].id) if len(rows) == lim else None,
    }


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
