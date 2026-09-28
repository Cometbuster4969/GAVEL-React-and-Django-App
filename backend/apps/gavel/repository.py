from bson import ObjectId

from .models import Adjudication, AuditEvent, Campaign, GavelUser, ReviewAssignment, Submission


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
