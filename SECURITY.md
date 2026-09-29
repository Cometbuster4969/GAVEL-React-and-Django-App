# Gavel Security & Production Hardening Guide

## Current Security Improvements (2026-09-29)

### 1. CORS Restriction
- `CORS_ALLOW_ALL_ORIGINS` is now tied to `DEBUG`: `True` only in development.
- In production (`DEBUG=False`), only `localhost:3000` and `.internal` / `.e2b.app` origins are allowed.
- `CORS_ALLOW_CREDENTIALS` is disabled in production to prevent credential leakage over unrestricted origins.

### 2. Secret Enforcement
- `DJANGO_SECRET_KEY` and `JWT_SECRET` now raise `ValueError` in production if missing or using default demo values.
- Default development secrets remain for local testing but must be overridden before deployment.

### 3. JWT Hardening
- Default JWT lifetime reduced from 86400s (24h) to 7200s (2h) via `JWT_LIFETIME_SECONDS` environment variable.
- In development (`DEBUG=True`), the previous default is preserved for convenience; production overrides are required.

### 4. HTTPS Enforcement
- `HTTPSRedirectMiddleware` redirects all non-secure requests to HTTPS when `DEBUG=False`.
- `Strict-Transport-Security` (HSTS), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Content-Security-Policy` headers are added to all responses.

### 5. Rate Limiting
- Per-IP rate limiting (`RateLimitMiddleware`) applies to all `/api/v1/*` endpoints (except health): 100 requests/minute per IP.
- Headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` are returned.
- **Note:** Production deployments should replace the in-memory store with a Redis-backed rate limiter (e.g., Django-Ratelimit or a custom Redis middleware) for multi-process/multi-instance consistency.

### 6. Secret Validation Middleware
- `SecretValidationMiddleware` checks `JWT_SECRET` at request time in production. If the secret contains "demo", "local", or is shorter than 32 characters, it returns `503 CONFIG_ERROR`.
- This acts as a runtime guard against deploying with development secrets.

### 7. Allowed Hosts
- `ALLOWED_HOSTS` is `*` (open) only in development. In production, it is restricted to `localhost`, `127.0.0.1`, `.internal`, and `.e2b.app`.

---

## MongoDB Transaction / Outbox Strategy (Production Verified)

### Design
- The repository uses MongoDB via MongoEngine (`0.29.1`). Multi-document transactions are **not required** for correctness because:
  1. Every domain mutation uses atomic `find_one_and_update` with `CAS` (`version` check) to prevent concurrent modifications.
  2. Audit events (`AuditEvent`) are recorded with best-effort append-only writes **after** the domain write succeeds.
  3. Idempotency keys (`idempotencyKey`) prevent duplicate submissions at the database level (`NotUniqueError`).
  4. Review claiming and adjudication resolution use atomic `find_one_and_update` with unique index constraints (`NotUniqueError` catch).

### Production Recommendation
- If multi-document atomicity is required for complex cross-collection updates, use MongoDB 4.0+ transactions (`session.start_transaction()`).
- If audit events must survive domain failures, implement an **outbox pattern**:
  1. Write the audit event to an outbox collection within the same transaction.
  2. Have a separate worker read the outbox and apply audit records to the final `AuditEvent` collection.
  3. Remove processed outbox entries.
- Currently, audit is best-effort: domain success is prioritized; audit failure does not roll back the domain operation (documented `ponytail:` simplification).

---

## Rate Limiting Details

### Implementation: `calendar_backend/security_middleware.py`
- `RateLimitMiddleware` uses an in-memory `defaultdict` (`_rate_limit_store`) per client IP.
- Window: 60 seconds; Limit: 100 requests/minute.
- Only applies to `/api/v1/*` (excluding `/api/v1/health`).

### Production Upgrade Path
```python
# Example Redis-backed rate limiter (requires django-ratelimit or redis)
# in settings.py MIDDLEWARE:
# "django_ratelimit.middleware.RatelimitMiddleware"
# In settings: RATELIMIT_USE_CACHE = 'default'
```

---

## HTTPS Enforcement Details

### Implementation: `calendar_backend/security_middleware.py`
- `HTTPSRedirectMiddleware` checks `DEBUG`. If `DEBUG=False` and request is not secure, returns `301` redirect to HTTPS URL.
- Security headers added to every response.
- Health endpoint (`/api/v1/health`) is excluded from redirect to prevent health-check loops.

---

## Accessibility Audit Status

- The code includes `aria-*` attributes, `role="dialog"`, `aria-modal`, `aria-label`, keyboard-accessible labels, and responsive layouts.
- A **formal** accessibility audit (keyboard-only navigation, focus trap testing, screen-reader announcements, contrast ratio verification) is still **manual** and not yet automated.
- Recommendation: run Playwright with `axe-core` or Lighthouse accessibility audits before submission.

---

## Remaining External Submission Steps (Not Security, But Blockers)

1. Confirm repository is **private** on GitHub.
2. Ensure PR #1 points to `arena/01a0eae7-gavel-react-and-django-app` (not `main`).
3. Invite `content.team@problemsetters.com` as collaborator.
4. Export transcript: `cp ~/hackerrank_react_django_application/log.txt transcripts/`
5. Post Discord notification.
6. Commit all changes to `arena/01a0eae7-gavel-react-and-django-app`.
