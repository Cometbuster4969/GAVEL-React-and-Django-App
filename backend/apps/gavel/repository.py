from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId
from pymongo import ReturnDocument, WriteConcern
from pymongo.errors import DuplicateKeyError
from mongoengine import Q

from apps.shared.errors import AppError

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


def _cursor_filter(query, marker, timestamp_field):
    """Apply the same compound key used by the descending sort.

    Q objects preserve visibility OR predicates when combining with cursor ORs.
    """
    if marker is None:
        return query
    timestamp = getattr(marker, timestamp_field)
    return query.filter(
        Q(**{f"{timestamp_field}__lt": timestamp})
        | (Q(**{timestamp_field: timestamp}) & Q(id__lt=marker.id))
    )


def _marker(query, cursor):
    if not cursor:
        return None
    oid = valid_id(cursor)
    marker = query.filter(id=oid).first() if oid else None
    if marker is None:
        raise AppError(400, "INVALID_CURSOR", "The cursor is invalid or no longer available in this result set.")
    return marker


def list_campaigns(limit=50, cursor=None, owner_id=None):
    query = Campaign.objects(deleted__ne=True)
    if owner_id is not None:
        query = query(owner_id=owner_id)
    query = _cursor_filter(query, _marker(query, cursor), "updated_at")
    return list(query.order_by("-updated_at", "-id").limit(min(max(int(limit), 1), 100)))


def find_campaign(campaign_id):
    object_id = valid_id(campaign_id)
    return Campaign.objects(id=object_id, deleted__ne=True).first() if object_id else None


def list_submissions(campaign_id, limit=50, cursor=None):
    query = Submission.objects(campaign_id=campaign_id)
    query = _cursor_filter(query, _marker(query, cursor), "created_at")
    return list(query.order_by("-created_at", "-id").limit(min(max(int(limit), 1), 100)))


def find_submission(submission_id):
    object_id = valid_id(submission_id)
    return Submission.objects(id=object_id).first() if object_id else None


def list_reviews(campaign_id=None, limit=50, cursor=None, status=None, reviewer_id=None):
    query = ReviewAssignment.objects
    if campaign_id:
        object_id = valid_id(campaign_id)
        if not object_id:
            return []
        query = query(campaign_id=object_id)
    if status:
        query = query(status=status)
    if reviewer_id is not None:
        query = query.filter(Q(status="available") | Q(reviewer_id=reviewer_id))
    query = _cursor_filter(query, _marker(query, cursor), "created_at")
    return list(query.order_by("-created_at", "-id").limit(min(max(int(limit), 1), 100)))


def find_review(review_id):
    object_id = valid_id(review_id)
    return ReviewAssignment.objects(id=object_id).first() if object_id else None


def list_adjudications(campaign_id=None, limit=50, cursor=None, campaign_ids=None):
    query = Adjudication.objects
    if campaign_id:
        object_id = valid_id(campaign_id)
        if not object_id:
            return []
        query = query(campaign_id=object_id)
    if campaign_ids is not None:
        query = query(campaign_id__in=campaign_ids)
    query = _cursor_filter(query, _marker(query, cursor), "updated_at")
    return list(query.order_by("-updated_at", "-id").limit(min(max(int(limit), 1), 100)))


def find_adjudication(adjudication_id):
    object_id = valid_id(adjudication_id)
    return Adjudication.objects(id=object_id).first() if object_id else None


def list_audit(limit=60, cursor=None, owner_id=None, campaign_ids=None):
    query = AuditEvent.objects
    if owner_id is not None:
        ids = [str(value) for value in campaign_ids or []]
        query = query.filter(Q(details__ownerId=str(owner_id)) | Q(details__campaignId__in=ids)
                             | (Q(entity_type="campaign") & Q(entity_id__in=ids)))
    query = _cursor_filter(query, _marker(query, cursor), "created_at")
    return list(query.order_by("-created_at", "-id").limit(min(max(int(limit), 1), 100)))


def enqueue_audit_outbox(actor, action, entity_type, entity_id, details=None):
    return AuditOutbox(event_id=uuid4().hex, actor_id=actor.id, actor_name=actor.name,
                       action=action, entity_type=entity_type, entity_id=str(entity_id),
                       details=details or {}, status="pending", available_at=datetime.now(timezone.utc)).save(write_concern={"w": 1, "j": True})


def persist_audit_intent(intent):
    """Journaled insert-only upsert: replay never resets delivery state."""
    now = datetime.now(timezone.utc)
    values = {**intent, "status": "pending", "attempts": 0, "availableAt": now, "updatedAt": now}
    outbox = AuditOutbox._get_collection().with_options(write_concern=WriteConcern(w=1, j=True))
    try:
        outbox.update_one({"eventId": intent["eventId"]}, {"$setOnInsert": values}, upsert=True)
    except DuplicateKeyError:
        # Retry as an acknowledged write, not an unjournaled read-before-pull.
        outbox.update_one({"eventId": intent["eventId"]}, {"$setOnInsert": values}, upsert=True)


def deliver_audit_event(entry):
    if isinstance(entry, dict):
        values = (entry["eventId"], entry["actorId"], entry["actorName"], entry["action"],
                  entry["entityType"], entry["entityId"], entry.get("details") or {})
    else:
        values = (entry.event_id, entry.actor_id, entry.actor_name, entry.action,
                  entry.entity_type, entry.entity_id, entry.details or {})
    event_id, actor_id, actor_name, action, entity_type, entity_id, details = values
    moment = entry.get("createdAt") if isinstance(entry, dict) else entry.created_at
    document = AuditEvent(actor_id=actor_id, actor_name=actor_name, action=action,
                          entity_type=entity_type, entity_id=str(entity_id), details=details,
                          event_id=event_id, created_at=moment, updated_at=moment)
    document.validate()
    collection = AuditEvent._get_collection().with_options(write_concern=WriteConcern(w=1, j=True))
    values = document.to_mongo().to_dict()
    try:
        result = collection.update_one({"eventId": event_id}, {"$setOnInsert": values}, upsert=True)
    except DuplicateKeyError:
        # A journaled replay, rather than a read, acknowledges durable delivery.
        result = collection.update_one({"eventId": event_id}, {"$setOnInsert": values}, upsert=True)
    return result.upserted_id is not None


def claim_audit_outbox(now):
    return AuditOutbox._get_collection().find_one_and_update(
        {"status": "pending", "availableAt": {"$lte": now}},
        {"$set": {"status": "running", "lockedAt": now, "updatedAt": now}, "$inc": {"attempts": 1}},
        sort=[("availableAt", 1), ("_id", 1)], return_document=ReturnDocument.AFTER)


def recover_stale_audit_outbox(stale_before):
    return AuditOutbox._get_collection().update_many(
        {"status": "running", "lockedAt": {"$lt": stale_before}},
        {"$set": {"status": "pending", "availableAt": stale_before, "updatedAt": stale_before}})


def mark_audit_outbox_delivered(event_id, moment):
    return AuditOutbox._get_collection().with_options(write_concern=WriteConcern(w=1, j=True)).update_one(
        {"eventId": event_id, "status": {"$in": ["pending", "running"]}},
        {"$set": {"status": "delivered", "deliveredAt": moment, "updatedAt": moment, "lastError": ""}})


def mark_audit_outbox_failed(event_id, moment, error, max_attempts, base_delay):
    entry = AuditOutbox._get_collection().find_one({"eventId": event_id}) or {}
    attempts = int(entry.get("attempts", 1))
    status = "failed" if attempts >= max_attempts else "pending"
    available_at = moment if status == "failed" else moment + timedelta(seconds=min(base_delay * (2 ** (attempts - 1)), 900))
    AuditOutbox._get_collection().update_one(
        {"eventId": event_id, "status": "running"},
        {"$set": {"status": status, "availableAt": available_at, "lockedAt": None,
                   "lastError": str(error)[:500], "updatedAt": moment}})
    return status


def count_audit_outbox():
    return {"pending": AuditOutbox.objects(status__in=("pending", "running")).count(),
            "delivered": AuditOutbox.objects(status="delivered").count(),
            "failed": AuditOutbox.objects(status="failed").count()}
