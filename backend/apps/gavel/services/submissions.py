from collections import defaultdict
from datetime import datetime, timezone

from mongoengine.errors import NotUniqueError

from apps.shared.errors import AppError

from .. import audit, repository
from ..models import ProcessingJob, ReviewAssignment, Submission
from .common import (
    campaign_case,
    clean_text,
    current_revision,
    ensure_campaign,
    ensure_owner,
    invalidate_analytics_cache,
    iso,
    mark_reviewing,
)


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
                        assignment = ReviewAssignment(
                            campaign_id=campaign.id,
                            pair_key=pair_key,
                            case_id=case_id,
                            submission_a_id=submission_a.id,
                            submission_b_id=submission_b.id,
                            slot=slot,
                            rubric_version=revision.rubric_version,
                            revision_id=revision.id,
                        )
                        audit.create(assignment, None, "review.created", {"campaignId": str(campaign.id)})
                        created += 1
                    except NotUniqueError:
                        continue
    return created


def list_submissions(user, campaign_id, limit=None, cursor=None):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    try:
        lim = max(1, min(int(limit), 100)) if limit is not None else 50
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
            audit.create(item, user, "submission.queued", {"campaignId": str(campaign.id), "caseId": item.case_id})
        except NotUniqueError:
            existing = Submission.objects(campaign_id=campaign.id, idempotency_key=row["idempotencyKey"]).first()
            if not existing or existing.case_id != row["caseId"] or existing.model_name != row["modelName"] or existing.output != row["output"]:
                raise AppError(409, "IDEMPOTENCY_CONFLICT", "That idempotency key was already used for a different response.")
            item = existing
            outcomes.append({"submission": public_submission(item), "duplicate": True})
            continue
        outcomes.append({"submission": public_submission(item), "duplicate": False})
    ProcessingJob(campaign_id=campaign.id, available_at=datetime.now(timezone.utc)).save()
    invalidate_analytics_cache()
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
    for stale in Submission.objects(campaign_id=campaign.id, status="processing", updated_at__lt=stale_moment):
        audit.update(Submission, {"_id": stale.id, "status": "processing", "updatedAt": {"$lt": stale_moment}},
                     {"$set": {"status": "queued"}}, user, "submission.recovered", {"campaignId": str(campaign.id)})
    candidates = list(Submission.objects(campaign_id=campaign.id, status="queued").order_by("created_at").limit(limit))
    processed = 0
    for candidate in candidates:
        claimed = audit.update(Submission,
            {"_id": candidate.id, "status": "queued"},
            {"$set": {"status": "processing", "updatedAt": now}, "$inc": {"attempt": 1}},
            user, "submission.processing", {"campaignId": str(campaign.id)},
        )
        if claimed is None:
            continue
        attempt = claimed.get("attempt", 1)
        should_fail = claimed.get("forceFailure", False) and attempt == 1
        final_status = "failed" if should_fail else "ready"
        failure_reason = "The response payload failed the first processing attempt; retry is available." if should_fail else ""
        audit.update(Submission,
            {"_id": candidate.id, "status": "processing", "attempt": attempt},
            {"$set": {"status": final_status, "failureReason": failure_reason, "updatedAt": datetime.now(timezone.utc)}},
            user, "submission.processed", {"campaignId": str(campaign.id), "status": final_status},
        )
        processed += 1
    created_reviews = create_review_pairs(campaign)
    ready_count = Submission.objects(campaign_id=campaign.id, status="ready").count()
    if created_reviews and not Submission.objects(campaign_id=campaign.id, status__in=("queued", "processing", "failed")).count():
        mark_reviewing(campaign)
    invalidate_analytics_cache()
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
    updated = audit.update(Submission, {"_id": submission.id, "status": "failed", "attempt": submission.attempt},
                           {"$set": {"status": "queued", "failureReason": ""}}, user,
                           "submission.retry_queued", {"attempt": submission.attempt + 1, "campaignId": str(campaign.id)})
    if updated is None:
        raise AppError(409, "SUBMISSION_CHANGED", "This response has already been retried.")
    ProcessingJob(campaign_id=campaign.id, available_at=datetime.now(timezone.utc)).save()
    submission.reload()
    invalidate_analytics_cache()
    return public_submission(submission)
