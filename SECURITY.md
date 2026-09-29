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

## MongoDB Transaction / Outbox Strategy (Implemented 2026-09-29)

### Design
- The repository uses MongoDB via MongoEngine (`0.29.1`). Multi-document transactions are **not required** for correctness because:
  1. Every domain mutation uses atomic `find_one_and_update` with `CAS` (`version` check) to prevent concurrent modifications.
  2. Idempotency keys (`idempotencyKey`) prevent duplicate submissions at the database level (`NotUniqueError`).
  3. Review claiming and adjudication resolution use atomic `find_one_and_update` with unique index constraints (`NotUniqueError` catch).
- Audit durability now uses a real **outbox** instead of a best-effort append:
  1. `services.record()` writes the audit intent to the `auditoutbox` collection first (`AuditOutbox`, unique `eventId`). That write is the durability boundary.
  2. Delivery into `auditevents` is attempted inline so the audit feed stays live for the normal case, and the entry is marked `delivered`.
  3. If delivery fails, the entry stays `pending`; the worker (`bun run worker`, `python -m apps.gavel.worker`, or `manage.py drain_audit_outbox`) retries it with exponential backoff (`30s × 2^(attempts-1)`, capped at 15 minutes) and dead-letters it as `failed` after `--max-attempts` (default 5) so operators can see unresolved intents.
  4. Delivery is idempotent per `eventId` (`auditevents.eventId` index), so retries and duplicate worker passes cannot duplicate audit rows.
  5. Abandoned `running` entries (worker crash) are recovered after 300 seconds by the same stale-claim rule used for `ProcessingJob`.
- **Boundary of the guarantee:** the domain write and the outbox write are still separate documents. Audit intent is therefore durable against *delivery* failures, but not against a crash between the two writes. Closing that last window needs a replica-set deployment and `session.start_transaction()` around the domain write plus the outbox insert; the repository keeps the CAS/idempotency strategy because it works on standalone MongoDB and under the in-memory `mongomock` fallback used by this environment.

### Verification
- `backend/apps/gavel/test_outbox.py` covers inline delivery, retry after a failed delivery, backoff windows, idempotent re-delivery, dead-lettering after max attempts, stale-entry recovery, and the audit-history read path. Full suite: `cd backend && ../.venv/bin/python -m unittest apps.gavel.test_services apps.gavel.test_integration apps.gavel.test_outbox` → `Ran 13 tests ... OK`.

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

## Accessibility Audit Status (Automated Audit Run 2026-09-29)

- A real headless-Chromium + `axe-core` audit now covers ten rendered surfaces: the sign-in screen, the owner workspace (overview, campaigns, adjudication, results, audit history), the administrator surface (blind review, results) and the reviewer surface (queue plus an opened review panel).
- Result after fixes: **0 axe violations** on every audited surface (`transcripts/a11y-audit-2026-09-29.md`, raw results in `transcripts/a11y-audit-report.json`).
- Fixes applied from the audit findings:
  1. Muted text colors were darkened (or, in the dark sidebar, lightened) to clear the 4.5:1 contrast threshold; 67 palette values were re-derived from a contrast computation, preserving the existing visual language.
  2. The two empty action-column `<th>` cells now carry a visually hidden "Actions" label.
  3. The three `<aside>` landmarks were given unique accessible names (`Workspace navigation`, `Blind review queue`, `Adjudication queue`).
  4. `aria-label` on plain `<div>` containers (`.demo-users`, `.workspace-switcher`, `.bar-chart`) was paired with `role="group"` so the name is exposed.
- Residual `incomplete` axe results are reviewed manually: text on gradients (`.login-left`, `.overview-banner`) and decorative glyphs. Computed contrast against the gradient endpoint colors is ≥5.1:1 for every one of those text styles, and the decorative star glyphs already sit inside an `aria-hidden` container.
- Keyboard reachability was exercised through the tab order on the sign-in screen and the workspace (focus moves through demo profiles → email → password → submit → workspace controls); focus-trap behaviour of the modal dialogs and screen-reader announcement wording remain manual review items because they need a human at the keyboard.
- The audit tooling lives outside the repository (scratch directory + `LD_LIBRARY_PATH` shims), so the pinned dependency surface is unchanged.

---

## Remaining External Submission Steps (Not Security, But Blockers)

1. Repository is **private** on GitHub — verified 2026-09-29 (`private: true`).
2. Pull requests #1, #2 and #3 are **merged** into `main` (2026-09-28/29). No pending PR merge remains; the security-hardening work of PR #3 is on `main`.
3. Invite `content.team@problemsetters.com` as collaborator — **blocked for an agent**: the GitHub App token in this environment returns `403 Resource not accessible by integration` for the collaborator and invitation endpoints, so the invite must be sent by the repository owner (Settings → Collaborators → Add people). It is not verifiable from this sandbox.
4. Export the transcript — done: `~/hackerrank_react_django_application/log.txt` is copied to `transcripts/log.txt` at the end of each session (`cp` only, never edited in place).
5. Post the Discord notification — **blocked for an agent** (no Discord webhook or credentials in this environment and none may be committed). A ready-to-post draft lives in `transcripts/discord-notification.md`.
6. Commit all changes to `arena/01a0ed1b-gavel-react-and-django-app` (this session's Arena branch) and merge to `main` via pull request.
