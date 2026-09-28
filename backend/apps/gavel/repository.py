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


def list_campaigns():
    return list(Campaign.objects.order_by("-updated_at"))


def find_campaign(campaign_id):
    object_id = valid_id(campaign_id)
    return Campaign.objects(id=object_id).first() if object_id else None


def list_submissions(campaign_id):
    return list(Submission.objects(campaign_id=campaign_id).order_by("-created_at"))


def find_submission(submission_id):
    object_id = valid_id(submission_id)
    return Submission.objects(id=object_id).first() if object_id else None


def list_reviews(campaign_id=None):
    query = ReviewAssignment.objects
    if campaign_id:
        object_id = valid_id(campaign_id)
        if not object_id:
            return []
        query = query(campaign_id=object_id)
    return list(query.order_by("status", "created_at"))


def find_review(review_id):
    object_id = valid_id(review_id)
    return ReviewAssignment.objects(id=object_id).first() if object_id else None


def list_adjudications(campaign_id=None):
    query = Adjudication.objects
    if campaign_id:
        object_id = valid_id(campaign_id)
        if not object_id:
            return []
        query = query(campaign_id=object_id)
    return list(query.order_by("status", "-updated_at"))


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
