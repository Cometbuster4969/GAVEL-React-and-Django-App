from mongoengine import BooleanField, DateTimeField, DictField, Document, IntField, ListField, ObjectIdField, StringField

from apps.shared.documents import TimestampedDocument


class AuditedDocument(TimestampedDocument):
    meta = {"abstract": True}
    audit_pending = ListField(DictField(), db_field="auditPending", default=list)

    def save(self, *args, **kwargs):
        if not self._created and not kwargs.get("force_insert"):
            raise RuntimeError("Existing audited documents must use audit.update(), not save().")
        return super().save(*args, **kwargs)



class GavelUser(TimestampedDocument):
    meta = {
        "collection": "gavelusers",
        "indexes": [{"fields": ["email"], "unique": True, "name": "gavel_email_unique_idx"}],
    }

    name = StringField(required=True, max_length=120)
    email = StringField(required=True, max_length=254)
    password_hash = StringField(db_field="passwordHash", required=True)
    role = StringField(required=True, choices=("administrator", "owner", "reviewer", "adjudicator"))
    active = BooleanField(default=True)
    review_identity_locked = BooleanField(db_field="reviewIdentityLocked", default=False)
    independence_group = StringField(db_field="independenceGroup", default="", max_length=120)
    conflict_campaign_ids = ListField(ObjectIdField(), db_field="conflictCampaignIds", default=list)
    conflict_model_names = ListField(StringField(max_length=120), db_field="conflictModelNames", default=list)


class Campaign(AuditedDocument):
    meta = {
        "collection": "campaigns",
        "indexes": [{"fields": ["status", "updated_at"], "name": "campaign_status_updated_idx"}],
    }

    deleted = BooleanField(default=False)
    name = StringField(required=True, max_length=120)
    summary = StringField(default="", max_length=500)
    owner_id = ObjectIdField(db_field="ownerId", required=True)
    status = StringField(default="draft", choices=("draft", "published", "running", "reviewing", "completed", "archived"))
    version = IntField(default=1, min_value=1)
    suite_version = IntField(db_field="suiteVersion", default=1, min_value=1)
    rubric_version = IntField(db_field="rubricVersion", default=1, min_value=1)
    test_cases = ListField(DictField(), db_field="testCases", default=list)
    rubric = ListField(DictField(), default=list)


class CampaignRevision(TimestampedDocument):
    meta = {
        "collection": "campaignrevisions",
        "indexes": [{"fields": ["campaign_id", "version"], "unique": True, "name": "campaign_revision_unique_idx"}],
    }

    campaign_id = ObjectIdField(db_field="campaignId", required=True)
    version = IntField(required=True, min_value=1)
    suite_version = IntField(db_field="suiteVersion", required=True, min_value=1)
    rubric_version = IntField(db_field="rubricVersion", required=True, min_value=1)
    test_cases = ListField(DictField(), required=True)
    rubric = ListField(DictField(), required=True)
    immutable = BooleanField(default=True)


class Submission(AuditedDocument):
    meta = {
        "collection": "submissions",
        "indexes": [
            {"fields": ["campaign_id", "idempotency_key"], "unique": True, "name": "campaign_idempotency_unique_idx"},
            {"fields": ["campaign_id", "status"], "name": "campaign_submission_status_idx"},
        ],
    }

    campaign_id = ObjectIdField(db_field="campaignId", required=True)
    case_id = StringField(db_field="caseId", required=True, max_length=80)
    model_name = StringField(db_field="modelName", required=True, max_length=120)
    output = StringField(required=True, max_length=12000)
    idempotency_key = StringField(db_field="idempotencyKey", required=True, max_length=160)
    status = StringField(default="queued", choices=("queued", "processing", "ready", "failed"))
    attempt = IntField(default=0, min_value=0)
    failure_reason = StringField(db_field="failureReason", default="", max_length=240)
    force_failure = BooleanField(db_field="forceFailure", default=False)
    rubric_version = IntField(db_field="rubricVersion", default=1, min_value=1)
    revision_id = ObjectIdField(db_field="revisionId", null=True)


class ReviewAssignment(AuditedDocument):
    meta = {
        "collection": "reviewassignments",
        "indexes": [
            {"fields": ["campaign_id", "pair_key"], "name": "review_pair_idx"},
            {"fields": ["campaign_id", "pair_key", "slot"], "unique": True, "name": "review_pair_slot_unique_idx"},
            {"fields": ["campaign_id", "status", "reviewer_id"], "name": "review_queue_idx"},
            {"fields": ["campaign_id", "pair_key", "reviewer_key"], "unique": True,
             "partialFilterExpression": {"reviewerKey": {"$type": "string"}}, "name": "review_independent_user_idx"},
            {"fields": ["campaign_id", "pair_key", "reviewer_group"], "unique": True,
             "partialFilterExpression": {"reviewerGroup": {"$type": "string"}}, "name": "review_independent_group_idx"},

        ],
    }

    campaign_id = ObjectIdField(db_field="campaignId", required=True)
    pair_key = StringField(db_field="pairKey", required=True, max_length=200)
    case_id = StringField(db_field="caseId", required=True, max_length=80)
    submission_a_id = ObjectIdField(db_field="submissionAId", required=True)
    submission_b_id = ObjectIdField(db_field="submissionBId", required=True)
    slot = IntField(default=0, min_value=0, max_value=1)
    reviewer_id = ObjectIdField(db_field="reviewerId", null=True)
    reviewer_key = StringField(db_field="reviewerKey")
    reviewer_group = StringField(db_field="reviewerGroup")
    status = StringField(default="available", choices=("available", "claimed", "completed"))
    winner_id = ObjectIdField(db_field="winnerId", null=True)
    notes = StringField(default="", max_length=1200)
    rubric_version = IntField(db_field="rubricVersion", default=1, min_value=1)
    revision_id = ObjectIdField(db_field="revisionId", null=True)
    criterion_scores = DictField(db_field="criterionScores", default=dict)
    weighted_score = DictField(db_field="weightedScore", default=dict)
    claimed_at = DateTimeField(db_field="claimedAt", null=True)
    completed_at = DateTimeField(db_field="completedAt", null=True)


class Adjudication(AuditedDocument):
    meta = {
        "collection": "adjudications",
        "indexes": [{"fields": ["campaign_id", "pair_key"], "unique": True, "name": "adjudication_pair_unique_idx"}],
    }

    campaign_id = ObjectIdField(db_field="campaignId", required=True)
    pair_key = StringField(db_field="pairKey", required=True, max_length=200)
    case_id = StringField(db_field="caseId", required=True, max_length=80)
    submission_a_id = ObjectIdField(db_field="submissionAId", required=True)
    submission_b_id = ObjectIdField(db_field="submissionBId", required=True)
    status = StringField(default="open", choices=("open", "resolved"))
    decision_id = ObjectIdField(db_field="decisionId", null=True)
    rationale = StringField(default="", max_length=1200)
    adjudicator_id = ObjectIdField(db_field="adjudicatorId", null=True)
    resolved_at = DateTimeField(db_field="resolvedAt", null=True)


class ProcessingJob(TimestampedDocument):
    meta = {
        "collection": "processingjobs",
        "indexes": [
            {"fields": ["campaign_id", "status"], "name": "processing_job_status_idx"},
            {"fields": ["available_at"], "name": "processing_job_available_idx"},
        ],
    }

    campaign_id = ObjectIdField(db_field="campaignId", required=True)
    status = StringField(default="queued", choices=("queued", "running", "completed", "failed"))
    attempts = IntField(default=0, min_value=0)
    available_at = DateTimeField(db_field="availableAt", required=True)
    locked_at = DateTimeField(db_field="lockedAt", null=True)
    error = StringField(default="", max_length=500)


class ResultPublication(AuditedDocument):
    meta = {
        "collection": "resultpublications",
        "indexes": [{"fields": ["campaign_id", "version"], "unique": True, "name": "result_publication_unique_idx"}],
    }

    campaign_id = ObjectIdField(db_field="campaignId", required=True)
    revision_id = ObjectIdField(db_field="revisionId", null=True)
    version = IntField(required=True, min_value=1)
    snapshot = DictField(required=True)
    published_by = ObjectIdField(db_field="publishedBy", required=True)
    published_at = DateTimeField(db_field="publishedAt", required=True)


class AuditEvent(TimestampedDocument):
    meta = {
        "collection": "auditevents",
        "indexes": [
            {"fields": ["created_at"], "name": "audit_created_idx"},
            {"fields": ["event_id"], "name": "audit_event_id_unique_v2", "unique": True,
             "partialFilterExpression": {"eventId": {"$type": "string"}}},
        ],
    }

    actor_id = ObjectIdField(db_field="actorId", required=True)
    actor_name = StringField(db_field="actorName", required=True, max_length=120)
    action = StringField(required=True, max_length=100)
    entity_type = StringField(db_field="entityType", required=True, max_length=80)
    entity_id = StringField(db_field="entityId", required=True, max_length=80)
    details = DictField(default=dict)
    event_id = StringField(db_field="eventId", max_length=64, null=True)


class AuditOutbox(TimestampedDocument):
    """Durable audit intent, delivered into ``auditevents`` by a retrying worker.

    Domain mutations first embed auditPending in the business document; relay
    upserts it here before removing that embedded intent. Delivery is attempted inline for a
    live audit feed and retried with backoff by ``manage.py drain_audit_outbox``
    (the worker mirrors the ``process_queue`` job pattern). ``eventId`` makes
    delivery idempotent: re-running the worker cannot duplicate an audit event.
    """

    meta = {
        "collection": "auditoutbox",
        "indexes": [
            {"fields": ["status", "available_at"], "name": "audit_outbox_status_idx"},
            {"fields": ["event_id"], "unique": True, "name": "audit_outbox_event_unique_idx"},
        ],
    }

    event_id = StringField(db_field="eventId", required=True, max_length=64)
    actor_id = ObjectIdField(db_field="actorId", required=True)
    actor_name = StringField(db_field="actorName", required=True, max_length=120)
    action = StringField(required=True, max_length=100)
    entity_type = StringField(db_field="entityType", required=True, max_length=80)
    entity_id = StringField(db_field="entityId", required=True, max_length=80)
    details = DictField(default=dict)
    status = StringField(default="pending", choices=("pending", "running", "delivered", "failed"))
    attempts = IntField(default=0, min_value=0)
    available_at = DateTimeField(db_field="availableAt", required=True)
    locked_at = DateTimeField(db_field="lockedAt", null=True)
    delivered_at = DateTimeField(db_field="deliveredAt", null=True)
    last_error = StringField(db_field="lastError", default="", max_length=500)
