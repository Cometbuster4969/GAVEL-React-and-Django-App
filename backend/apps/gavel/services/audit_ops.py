from datetime import datetime, timedelta, timezone

from apps.shared.errors import AppError

from .. import audit, repository
from ..models import Campaign
from .common import iso


def record(user, action, entity_type, entity_id, details=None):
    """Record a standalone event, not a domain mutation.

    Domain mutations MUST use audit.create/update to bind intent atomically.

    The outbox write is the durability boundary: if delivery fails, the intent
    stays pending and ``drain_audit_outbox`` retries it with backoff. The inline
    attempt keeps the audit feed live for the common case (no UI lag).
    """
    if user is None:
        return None
    # Never silently discard audit intent. Callers must see the failure so they
    # can fail closed rather than acknowledge an unaudited mutation.
    entry = repository.enqueue_audit_outbox(user, action, entity_type, entity_id, details)
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
    audit.relay_pending()
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


def audit_log(user, cursor=None, limit=60):
    if user.role not in ("administrator", "owner", "adjudicator"):
        raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot access the audit history.")
    try:
        lim = max(1, min(int(limit), 100)) if limit is not None else 60
    except Exception:
        lim = 60
    # Include deleted campaigns so their owners retain the full audit trail.
    owned_ids = list(Campaign.objects(owner_id=user.id).scalar("id")) if user.role == "owner" else None
    rows = repository.list_audit(limit=lim, cursor=cursor, owner_id=user.id if user.role == "owner" else None,
                                 campaign_ids=owned_ids)
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
