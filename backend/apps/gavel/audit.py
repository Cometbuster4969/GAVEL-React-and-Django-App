"""Single-document transactional audit intents, compatible with standalone MongoDB.

A business write stores its event in that same document. Relay may fail without
losing the intent. Never remove an embedded event before its durable outbox upsert.
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from pymongo import ReturnDocument, WriteConcern

from apps.shared.errors import AppError

from . import repository
from .models import Adjudication, Campaign, ResultPublication, ReviewAssignment, Submission

logger = logging.getLogger(__name__)
SOURCES = (Campaign, Submission, ReviewAssignment, Adjudication, ResultPublication)
SYSTEM_ID = ObjectId("000000000000000000000001")


def collection(model):
    return model._get_collection().with_options(write_concern=WriteConcern(w=1, j=True))


def event(user, action, model, entity_id, details=None):
    return {
        "eventId": uuid4().hex,
        "actorId": user.id if user else SYSTEM_ID,
        "actorName": user.name if user else "Gavel worker",
        "action": action,
        "entityType": {Campaign: "campaign", Submission: "submission", ReviewAssignment: "review",
                       Adjudication: "adjudication", ResultPublication: "publication"}[model],
        "entityId": str(entity_id),
        "details": details or {},
        "createdAt": datetime.now(timezone.utc),
    }


def create(document, user, action, details=None):
    document.id = document.id or ObjectId()
    document.audit_pending = [event(user, action, type(document), document.id, details)]
    document.save(force_insert=True, write_concern={"w": 1, "j": True})
    relay_document(type(document), document.id)
    return document


def update(model, query, changes, user, action, details=None):
    """CAS business fields and append the audit event in ONE journaled write."""
    changes = {key: dict(value) for key, value in changes.items()}
    changes.setdefault("$push", {})["auditPending"] = event(user, action, model, query["_id"], details)
    changes.setdefault("$set", {})["updatedAt"] = datetime.now(timezone.utc)
    # Bound outage growth well below MongoDB's document limit; reject further
    # changes rather than accepting mutations whose audit cannot fit.
    guarded = {**query, "auditPending.999": {"$exists": False}}
    result = collection(model).find_one_and_update(guarded, changes, return_document=ReturnDocument.AFTER)
    if result is None and collection(model).find_one({**query, "auditPending.999": {"$exists": True}}):
        raise AppError(503, "AUDIT_BACKLOG", "Audit delivery needs operator attention before more changes can be accepted.")
    if result is not None:
        relay_document(model, result["_id"])
    return result


def relay_document(model, document_id):
    """Best-effort relay; a failed relay leaves recoverable intent, not data loss."""
    try:
        source = collection(model).find_one({"_id": document_id}, {"auditPending": 1}) or {}
        for intent in source.get("auditPending", []):
            repository.persist_audit_intent(intent)
            collection(model).update_one({"_id": document_id}, {"$pull": {"auditPending": {"eventId": intent["eventId"]}}})
            try:
                repository.deliver_audit_event(intent)
                repository.mark_audit_outbox_delivered(intent["eventId"], datetime.now(timezone.utc))
            except Exception:
                logger.warning("Audit delivery deferred for event %s", intent["eventId"], exc_info=True)
    except Exception:
        logger.warning("Embedded audit intent retained in %s/%s", model.__name__, document_id, exc_info=True)


def relay_pending(limit=100):
    for model in SOURCES:
        for row in collection(model).find({"auditPending.0": {"$exists": True}}, {"_id": 1}).limit(limit):
            relay_document(model, row["_id"])
