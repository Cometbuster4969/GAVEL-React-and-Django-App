from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from .models import ProcessingJob
from .services import process_submissions


def process_next_job(limit=25):
    """Claim the next due ProcessingJob and process its campaign.

    Shared by ``manage.py process_queue`` and the standalone worker entry point
    (``python -m apps.gavel.worker`` / ``bun run worker``), so both paths claim
    jobs with the same atomic compare-and-set. Returns 1 when a job was claimed.
    """
    now = datetime.now(timezone.utc)
    ProcessingJob._get_collection().update_many(
        {"status": "running", "lockedAt": {"$lt": now - timedelta(minutes=5)}},
        {"$set": {"status": "queued", "availableAt": now}})
    job = ProcessingJob._get_collection().find_one_and_update(
        {"status": "queued", "availableAt": {"$lte": now}},
        {"$set": {"status": "running", "lockedAt": now}, "$inc": {"attempts": 1}},
        sort=[("availableAt", 1), ("_id", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if job is None:
        return 0
    try:
        result = process_submissions(None, str(job["campaignId"]), limit)
        ProcessingJob._get_collection().update_one(
            {"_id": job["_id"], "status": "running", "lockedAt": job["lockedAt"]},
            {"$set": {"status": "queued" if result["queued"] else "completed", "updatedAt": datetime.now(timezone.utc)}},
        )
    except Exception as error:
        ProcessingJob._get_collection().update_one(
            {"_id": job["_id"], "status": "running", "lockedAt": job["lockedAt"]},
            {"$set": {"status": "failed", "error": str(error)[:500], "updatedAt": datetime.now(timezone.utc)}},
        )
    return 1
