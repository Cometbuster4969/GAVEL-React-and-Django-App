from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId
from pymongo import ReturnDocument

from .models import Adjudication, AuditEvent, AuditOutbox, Campaign, GavelUser, ReviewAssignment, Submission


def valid_id(value):
    if isinstance(value, ObjectId):
        return value
    if not isinstance(value, str) or not ObjectId.is_valid(value):
        return None
    return ObjectId(value)


def find_user_by_email(email):
    return GavelUser.objects(email=email.lower(), active=True).first()


def find_user(user_id):
    object_id = valid_id(user_id)
    return GavelUser.objects(id=object_id, active=True).first() if object_id else None


def list_campaigns(limit=50, cursor=None):
    query = Campaign.objects
    if cursor:
        marker = Campaign.objects(id=valid_id(cursor)).first()
        if marker and marker.updated_at:
            query = query.filter(updated_at__lt=marker.updated_at)
    return list(query.order_by("-updated_at", "-id").limit(min(int(limit) if limit else 50, 100)))


def find_campaign(campaign_id):
    object_id = valid_id(campaign_id)
    return Campaign.objects(id=object_id).first() if object_id else None


def list_submissions(campaign_id, limit=50, cursor=None):
    query = Submission.objects(campaign_id=campaign_id)
    if cursor:
        marker = Submission.objects(id=valid_id(cursor)).first()
        if marker and marker.created_at:
            query = query.filter(created_at__lt=marker.created_at)
    return list(query.order_by("-created_at", "-id").limit(min(int(limit) if limit else 50, 100)))


def find_submission(submission_id):
    object_id = valid_id(submission_id)
    return Submission.objects(id=object_id).first() if object_id else None


def list_reviews(campaign_id=None, limit=50, cursor=None, status=None):
    query = ReviewAssignment.objects
    if campaign_id:
        object_id = valid_id(campaign_id)
        if not object_id:
            return []
        query = query(campaign_id=object_id)
    if status and status in ("available", "claimed", "completed"):
        query = query.filter(status=status)
    if cursor:
        marker = ReviewAssignment.objects(id=valid_id(cursor)).first()
        if marker and marker.created_at:
            query = query.filter(created_at__lt=marker.created_at)
    # Bounded pagination with stable ordering; status filter applied before cursor
    return list(query.order_by("-created_at", "-id").limit(min(int(limit) if limit else 50, 100)))


def find_review(review_id):
    object_id = valid_id(review_id)
    return ReviewAssignment.objects(id=object_id).first() if object_id else None


def list_adjudications(campaign_id=None, limit=50, cursor=None):
    query = Adjudication.objects
    if campaign_id:
        object_id = valid_id(campaign_id)
        if not object_id:
            return []
        query = query(campaign_id=object_id)
    if cursor:
        marker = Adjudication.objects(id=valid_id(cursor)).first()
        if marker and marker.updated_at:
            query = query.filter(updated_at__lt=marker.updated_at)
    return list(query.order_by("-updated_at", "-id").limit(min(int(limit) if limit else 50, 100)))


def find_adjudication(adjudication_id):
    object_id = valid_id(adjudication_id)
    return Adjudication.objects(id=object_id).first() if object_id else None


def list_audit(limit=60, cursor=None):
    query = AuditEvent.objects
    if cursor:
        marker = AuditEvent.objects(id=cursor).first()
        if marker:
            query = query.filter(created_at__lt=marker.created_at)
    return list(query.order_by("-created_at", "-id").limit(min(limit, 100)))


def record_audit(actor, action, entity_type, entity_id, details=None):
    AuditEvent(
        actor_id=actor.id,
        actor_name=actor.name,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
    ).save()


def enqueue_audit_outbox(actor, action, entity_type, entity_id, details=None):
    """Persist the audit intent before delivery so it survives a failed delivery."""
    return AuditOutbox(
        event_id=uuid4().hex,
        actor_id=actor.id,
        actor_name=actor.name,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
        status="pending",
        available_at=datetime.now(timezone.utc),
    ).save()


def deliver_audit_event(entry):
    """Idempotently append one outbox entry to the audit history.

    Accepts an ``AuditOutbox`` document or a raw outbox document. A second call
    for the same ``eventId`` is a no-op, so retries cannot duplicate audit rows.
    """
    if isinstance(entry, dict):
        event_id = entry["eventId"]
        actor_id = entry["actorId"]
        actor_name = entry["actorName"]
        action = entry["action"]
        entity_type = entry["entityType"]
        entity_id = entry["entityId"]
        details = entry.get("details") or {}
    else:
        event_id = entry.event_id
        actor_id = entry.actor_id
        actor_name = entry.actor_name
        action = entry.action
        entity_type = entry.entity_type
        entity_id = entry.entity_id
        details = entry.details or {}
    if AuditEvent.objects(event_id=event_id).first():
        return False
    AuditEvent(
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
        event_id=event_id,
    ).save()
    return True


def claim_audit_outbox(now):
    """Atomically claim one due outbox entry (mirrors the ProcessingJob claim)."""
    return AuditOutbox._get_collection().find_one_and_update(
        {"status": "pending", "availableAt": {"$lte": now}},
        {"$set": {"status": "running", "lockedAt": now, "updatedAt": now}, "$inc": {"attempts": 1}},
        sort=[("availableAt", 1), ("_id", 1)],
        return_document=ReturnDocument.AFTER,
    )


def recover_stale_audit_outbox(stale_before):
    """Return entries abandoned by a crashed worker to the pending queue."""
    return AuditOutbox._get_collection().update_many(
        {"status": "running", "lockedAt": {"$lt": stale_before}},
        {"$set": {"status": "pending", "availableAt": stale_before, "updatedAt": stale_before}},
    )


def mark_audit_outbox_delivered(event_id, moment):
    # Matches both the inline path (still "pending") and the worker path ("running").
    return AuditOutbox._get_collection().update_one(
        {"eventId": event_id, "status": {"$in": ["pending", "running"]}},
        {"$set": {"status": "delivered", "deliveredAt": moment, "updatedAt": moment, "lastError": ""}},
    )


def mark_audit_outbox_failed(event_id, moment, error, max_attempts, base_delay):
    """Schedule a retry with exponential backoff, or dead-letter after max attempts."""
    entry = AuditOutbox._get_collection().find_one({"eventId": event_id}) or {}
    attempts = int(entry.get("attempts", 1))
    if attempts >= max_attempts:
        status = "failed"
        available_at = moment
    else:
        status = "pending"
        available_at = moment + timedelta(seconds=min(base_delay * (2 ** (attempts - 1)), 900))
    AuditOutbox._get_collection().update_one(
        {"eventId": event_id, "status": "running"},
        {
            "$set": {
                "status": status,
                "availableAt": available_at,
                "lockedAt": None,
                "lastError": str(error)[:500],
                "updatedAt": moment,
            }
        },
    )
    return status


def count_audit_outbox():
    pending = AuditOutbox.objects(status__in=("pending", "running")).count()
    delivered = AuditOutbox.objects(status="delivered").count()
    failed = AuditOutbox.objects(status="failed").count()
    return {"pending": pending, "delivered": delivered, "failed": failed}
