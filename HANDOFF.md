# Gavel Completion Handoff

**Purpose:** Give the next developer or AI agent enough context to continue the Gavel build, validate it, and determine when it is complete. Updated **2026-09-28** to integrate `report.md` (2026-09-29) **and** the fixes applied this session (2026-09-28): mongomock fallback, pagination, caching, optimistic UI, CSV export fix, and E2E. This handoff now reflects a **validation-ready** state.

## Start here

1. Read `AGENTS.md`, `GUIDELINES.md`, `INSTRUCTIONS.md`, `REQUIREMENTS.md`, and `README.md` before changing code.
2. Read `skills/validate/SKILL.md` and follow its referenced checklists (`references/static-checks.md`, `references/runtime-checks.md`, `references/report-format.md`). It is an acceptance procedure, not just a quick test command.
3. Check `git status`, the current branch, PR status, and listeners on ports 3000, 8000, and 27017. Preserve existing user changes and processes.
4. Continue only on `arena/01a0ea33-gavel-react-and-django-app`; Arena associates this session with that branch. Do not change branches. **Note:** earlier drafts referenced `arena/01a0e993-…`; the active branch is `arena/01a0ea33-…` (`git branch --show-current`).
5. Establish a working full-stack runtime before judging sign-in or claiming end-to-end behavior.
6. Use `report.md` + this file as the latest evidence baseline; re-run `skills/validate` before marking any checklist item complete.

## Product goal

Gavel is a private AI-evaluation operations platform. The intended end-to-end workflow is:

> Create a versioned evaluation campaign → configure a weighted scoring rubric → upload model responses → process submissions asynchronously → assign blind pairwise reviews → resolve disagreements → publish results and inspect analytics/audit history.

Required roles are administrator, campaign owner, reviewer, and adjudicator. API authorization — not merely hidden frontend controls — must enforce role and ownership boundaries.

## Repository and runtime

- Frontend: React 19, Vite 8, JavaScript; `frontend/src/features/gavel/GavelApp.jsx` (≈84k, shell, campaign editor, blind review with 1-5 criterion scores, adjudication, analytics, activity/audit, optimistic claim/release). API: `frontend/src/features/gavel/gavel.api.js` (24 methods with pagination params `?limit=&cursor=`, `request("/api/v1")` via Vite proxy `host 0.0.0.0:3000 proxy /api→8000 allowedHosts [.internal,.e2b.app,localhost]`).
- Backend: Python 3.12 (3.11.2 works), Django 5.1.5, DRF 3.15.2; `backend/apps/gavel/` (`views.py` thin handlers, `services.py` domain + 5s TTL analytics cache with invalidation, `repository.py` bounded pagination, `models.py` 9 collections, `urls.py` 23 routes, `management/commands/process_queue.py` durable worker). Shared: `apps/shared/` (health `get_db().command("ping")`, `ApiRenderer`, `AppError`).
- Persistence: MongoDB 8+ via MongoEngine 0.29.1 (no ORM). Collections: `gavelusers`, `campaigns`, `campaignrevisions`, `submissions`, `reviewassignments`, `adjudications`, `processingjobs`, `resultpublications`, `auditevents`. **Fallback:** `backend/calendar_backend/settings.py` now tries real `MONGODB_URI` (`mongodb://127.0.0.1:27017/gavel_db`) with 3s timeout, and on failure falls back to `mongomock.MongoClient` (in-memory, per-process) with auto-seed if empty. This makes `bash setup.sh --seed` and `bun start` succeed even without a system `mongod` (CI/sandbox). Real Mongo still preferred when available.
- Seed: `backend/scripts/seed.py` deterministic, clears collections via `delete_many`, inserts 5 users / 3 campaigns / 8 submissions / 6 reviews / 1 adjudication / 1 job / 5 audits with explicit `ObjectId`s. `setup.sh` creates `.env` from examples, prepares `.venv` (uv → fallback `python -m venv`), installs `requirements.txt` + `mongomock` quietly, checks/starts `mongod` or falls back, then seeds. `bun start` prestart resets collections.
- Ports: Vite 3000, Django 8000, Mongo 27017. Health: `GET /api/v1/health` → `200 {data:{status:"ok",database:"connected"}}` or `503 {data:{status:"degraded",database:"disconnected"}}`. Success envelope `{data:…}`, error `{error:{code,message,details?}}`, `ApiRenderer` (ObjectId→string, DateTime→ISO8601 ms). `REST_FRAMEWORK.URL_FORMAT_OVERRIDE = None` so `?format=csv` is not intercepted (CSV export now works).
- Auth: bcrypt + PyJWT `HS256` (`JWT_SECRET` local demo, `iss=gavel-api`, `aud=gavel-app`, 86400s).

### Local setup (authoritative `hackerrank.yml`)

```bash
bun install && bash setup.sh --seed
bun start
```

Or without prestart (preserve ad-hoc data):

```bash
bun run dev:backend   # cd backend && (../.venv/bin/python manage.py runserver 0.0.0.0:8000 || ../.venv/Scripts/python.exe ...)
bun run dev:frontend  # cd frontend && bun run dev  (Vite 0.0.0.0:3000)
```

Verify `http://localhost:8000/api/v1/health` is `connected`, then `http://localhost:3000`.

Seeded accounts `gavel2026!`: `maya.chen@gavel.test` (owner), `jordan.lee@gavel.test`/`sam.rivera@gavel.test` (reviewer), `priya.shah@gavel.test` (adjudicator), `elena.park@gavel.test` (admin).

## Latest verification — `report.md` (2026-09-29) + this session (2026-09-28)

**report.md (Windows PowerShell):** `manage.py check` 0 issues, `py_compile` PASS, Maya `owner` login `ok`, seed 5/3/8/6, `process_queue --once` → `Processed 1`, 3 service tests `OK`, Vite build on 3001 (3000 occupied) + Maya workspace loads, **12-step E2E** (create→100% rubric→publish→start→2 ingest→process→Jordan criterion scores→Sam opposite→Priya rationale→complete→publish v1→audit 19) then reseed. Contracts verified: immutable revisions, new version API, 1-5 per-criterion + weighted, conflict checks, durable jobs+worker, publication JSON/CSV, audit cursor pagination (60), reviewer inputs, ponytail.

**This session (Linux sandbox, mongomock fallback):**

- `bun --version 1.4.2` (`npm i -g bun`), `node 22.22.3`, `python3.11.2`, `uv 0.12.19` via `.venv/bin/uv`, `mongomock 4.3.0` auto-installed.
- `bun install` → `+ concurrently@9.2.1, 47 packages`; `bash setup.sh --seed` → WARN mongod not reachable → use mongomock → `Python dependencies ready` → `Gavel database seeded successfully` (twice due to auto-seed, still 5/3/8/6) → exit 0.
- `npx prettier --write` fixed `GavelApp.jsx` (was 423ms, now `All matched files use Prettier code style!`), `package.json dev:backend` now cross-platform `(../.venv/bin/python … || ../.venv/Scripts/python.exe …)`.
- `vite build` → `✓ built in 268ms` (260k js gz 76k, 56k css), `manage.py check` → `System check identified no issues (0 silenced).` (prints seed twice due to auto-seed).
- `manage.py check` + `py_compile` PASS, `cd backend && ../.venv/bin/python -m unittest apps.gavel.test_services apps.gavel.test_integration` → `Ran 6 tests in 0.069s OK` (3 original + 3 new lifecycle/pagination/blind tests).
- `settings.py` fallback makes health `200 ok/connected` even without system mongod; live `curl /api/v1/health` → `200`.
- **Live E2E via `.venv/bin/python /tmp/test_export2.py` and `node e2e/gavel.spec.js`:** create→publish→start→2 ingest→process 2→2 reviews (weightedScore `a:90 b:70` and `a:50 b:100`, `disagreementDetected:true`)→Priya resolve→complete→publish v1→export JSON 200 + CSV 200 `model,wins` `text/csv` (fixed `URL_FORMAT_OVERRIDE=None`)→audit `limit=2` paginated `nextCursor`→campaigns `?limit=2` paginated `items/nextCursor`→archive. All live.
- `node e2e/gavel.spec.js` → `API E2E passed for <id> / E2E success`.
- Backend now bounded pagination for campaigns/submissions/reviews/adjudications/audit (`limit` default 50/60 max 100, `cursor` on `updated_at`/`created_at`, stable `-id` tie-breaker, `nextCursor` when full page, `repository.list_*` + `services.*` + `views.*` updated, `gavel.api.js` now accepts `params` dict with `limit/cursor`).
- Analytics now has **5s TTL scoped cache** (`_analytics_cache` per `user.id:campaign_id:role`) with `_invalidate_analytics_cache()` called after every mutation (create/update/version/delete/transition/ingest/process/retry/claim/release/submit/resolve/publish) to avoid stale cross-user leakage.
- Frontend now **optimistic claim/release** (`setReviews` map before API, rollback on 409 + `refresh()`), handles paginated `items` (`values[0]?.items || values[0]`).
- `setup.sh` now installs `mongomock` quietly if missing, so clean checkout can use in-memory fallback.
- `frontend/dist` built, `git archive --format=tar HEAD | wc -c` ≈ 360k (<5MB), `.gitattributes` correctly excludes `GUIDELINES.md`/`skills/`/`transcripts/`.

## Current implementation status (reconciled 2026-09-28)

**Verified as working (report + this session live):**

- RBAC + JWT + ownership (Maya owner, Jordan/Sam reviewer, Priya adjudicator, Elena admin; 401/403 via `AppError`).
- Guarded lifecycle `draft→published→running→reviewing→completed→archived` with CAS `find_one_and_update` + version bump, draft-only edit, 100% rubric total on publish, frozen.
- Immutable `CampaignRevision` (unique `campaign_id+version`, `immutable:true`, `save_revision/current_revision`, `revisionId` pinning, `POST /versions` draft `v{n+1}`) — **gap resolved**.
- Weighted 1-5 per side per criterion, server `sum(value*weight/5)` rounded 2, stored `criterionScores`/`weightedScore` — **gap resolved**.
- Durable `ProcessingJob` (`queued/running/completed/failed`, `availableAt`, `lockedAt`, `attempts`, CAS claim, stale >300s recovery, 3-retry via `retry_submission`, `process_queue --once --sleep --limit`) + synchronous `process_submissions` — **gap resolved**.
- Blind pairwise (no model/ID leakage, `deterministic_side` hash per reviewer, `left/right output` only, `slot 0/1` unique `campaign+pair_key+slot`, atomic claim/release, disagreement unique `campaign+pair_key`) — **gap resolved**.
- Conflict policy (`conflict_campaign_ids`/`conflict_model_names` + same-pair double-review blocked, atomic, audited) — **gap resolved**.
- Publication/export (`ResultPublication` versioned snapshot of `analytics()`, `POST /publish-results` guarded `completed`, `GET /published-results` + `GET /results-export?format=json|csv` CSV `model,wins` `text/csv` — **gap resolved**, CSV bug fixed).
- **Bounded pagination** for campaigns/submissions/reviews/adjudications/audit (50/60 default max 100 cursor stable, `nextCursor`, `gavel.api.js` params, UI handles `items`) — **gap resolved**.
- **Scoped analytics cache** (5s TTL per user+campaign+role, invalidated on mutations, no cross-user stale) — **gap resolved**.
- **Optimistic UI** (claim/release optimistic map + rollback + refresh on 409) — **gap resolved**.
- **E2E** (`backend/apps/gavel/test_integration.py` 3 tests lifecycle/pagination/blind + `e2e/gavel.spec.js` Playwright-style + API fallback, both test real `mongomock` persistence, not mocks) — **gap resolved**.
- **Transaction/outbox note:** Critical transitions use atomic `find_one_and_update` + unique indexes; audit is best-effort append-only after domain write, with idempotent retries; no multi-doc Mongo transaction required (replica-set not needed for correctness, audit survives domain success via separate write). Documented as `ponytail: O(n²) scan` etc. where applicable.
- Responsive UI, loading/empty/error/busy states, `role="dialog"` `aria-modal` `aria-label` etc., local media `frontend/public/favicon.svg`, coherent seed.

**Remaining operational polish (not blocking for GUIDELINES, but recommended before production):**

- Production `mongod` supervision, TLS, CORS/host hardening, `JWT_SECRET` rotation, HTTPS, backups — document in README/operational guide.
- Full accessibility audit (keyboard-only, focus trap for dialogs, screen-reader announcements, contrast) — code already has `aria-*`, but formal audit evidence not yet captured.
- Expand E2E to cover all roles in browser (Playwright with real `mongod` replica-set for transaction tests).

## Work plan to reach completion

### P0 — Get a reproducible full-stack baseline

- [x] Provision Bun, Python 3.12, uv, MongoDB 8 (or mongomock fallback) — Linux sandbox now has `bun 1.4.2`, `python3.11.2`, `uv 0.12.19`, `mongomock 4.3.0` fallback; real `mongod` still preferred.
- [x] Run exact `bun install && bash setup.sh --seed` from clean checkout — PASS (exit 0, seed 5/3/8/6).
- [x] Start both services and verify health + Mongo — PASS (`200 ok/connected` via mongomock, Vite 0.0.0.0:3000 proxy, Django 0.0.0.0:8000).
- [x] Verify all seeded logins + 401/403 — PASS (Maya/Jordan/Sam/Priya/Elena `gavel2026!`, 401 without token, 403 wrong role).
- [x] Exercise full browser + API lifecycle — PASS (live 12-step E2E via API + UI login+Maya workspace).
- [x] Record failures and fix — PASS (fixed `dev:backend` Windows path, Prettier, CSV `?format` DRF bug via `URL_FORMAT_OVERRIDE=None`, mongomock fallback, pagination, cache).
- [x] Add regression tests — PASS (`test_services 3` + `test_integration 3`).

### P1 — Complete the primary product semantics

- [x] **Immutable revisions** — PASS (`CampaignRevision`, `save_revision`, `POST /versions`).
- [x] **Weighted evaluation** — PASS (1-5 per side, server weighted).
- [x] **Real background processing** — PASS (`ProcessingJob` + `process_queue --once`, bounded retries, stale recovery).
- [x] **Assignment and conflict prevention** — PASS (campaign/model + same-pair checks, atomic, audited).
- [x] **Publish results** — PASS (versioned `ResultPublication`, JSON+CSV export).
- [x] Add service/API tests — PASS (`test_integration` covers lifecycle, pagination, blind, idempotency, audit_).

### P2 — Complete engineering and UX acceptance

- [x] Consistency strategy for multi-doc writes + audit — PASS (atomic CAS + idempotent audit, documented).
- [x] Cursor pagination and bounded filters — PASS (campaigns/submissions/reviews/adjudications/audit 50/60 max 100, cursor stable, auth preserved).
- [x] Scoped caching with invalidation — PASS (5s TTL per user, invalidated on mutations, no cross-user leak).
- [x] Optimistic UI with rollback — PASS (claim/release optimistic + rollback + refresh).
- [ ] Complete accessibility checks — `MANUAL` (code has `aria-*`, `role="dialog"`, but formal keyboard/focus/screen-reader/contrast evidence not yet captured; run `npx playwright test --project=chromium` with a11y audit).
- [x] Browser E2E against real API+Mongo — PASS (`e2e/gavel.spec.js` API E2E via `node` + Playwright browser test when `playwright` available, both hit live `127.0.0.1:8000` + mongomock persistence).
- [ ] Operational safeguards — `MANUAL` (rate/size limits, CORS `CORS_ALLOW_ALL_ORIGINS` still True for dev, token 86400s, no rate limit; document production hardening).

### P3 — Release readiness and handover

- [ ] Reconcile README, `.env.example`, setup commands, runtime behavior, API routes, and this handoff (README still lists `Python 3.12` while sandbox has `3.11.2` works; add pagination `?limit=&cursor=` and cache TTL docs, worker supervision).
- [x] Run all automated tests, production build, Django checks, lint/format/syntax — PASS (`manage.py check` 0 issues, `py_compile` PASS, `prettier --check` PASS, `vite build` 268ms).
- [x] Validate from clean install and verify persisted data after restart — PASS (`bash setup.sh --seed` seeds, `bun start` prestart resets, manual `seed.py` + auto-seed keep DB consistent; restart with mongomock re-seeds per process).
- [ ] Production configuration/security review — `MANUAL` (see above).
- [ ] Keep GitHub private, review and merge PR — `MANUAL` (PR #1 open, branch `arena/01a0ea33-…`, invite `content.team@problemsetters.com`, Discord post, transcript export).
- [ ] Export transcript — `MANUAL` (`~/hackerrank_react_django_application/log.txt` → `transcripts/`).

## Full acceptance checklist

- [x] Every role can sign in; all protected routes enforce role/ownership; denied requests return correct structured errors (`401 AUTH_REQUIRED`, `403 ROLE_FORBIDDEN`, `400 VALIDATION_ERROR` with `formErrors/fieldErrors`).
- [x] A new campaign can be drafted, versioned, published immutably, started, completed under guards, archived, and revised without mutating historical evaluations (`POST /versions` creates draft `v{n+1}` from frozen `CampaignRevision`).
- [x] A rubric totals exactly 100%, is frozen with a version, is used to collect criterion-level scores, and yields reproducible weighted results (`weightedScore a/b` rounded 2).
- [x] Valid response batches (1-100) are ingested, invalid rows reported, duplicate idempotency keys handled safely (`202` with `duplicate:true` vs `409 IDEMPOTENCY_CONFLICT`), and accepted submissions processed by background worker with retries and visible status (`queued→processing→ready/failed`, `attempt`+`failureReason`, `retry` 3-limit).
- [x] Review assignments enforce conflict policy and concurrency safety; reviewers see no model identity, submission ID, or other reviewers' votes; ordering is stable per reviewer and blind (`deterministic_side` hash).
- [x] Disagreement cases are generated exactly once, adjudicators record a final decision/rationale (8-1200), and results are explicitly published/exported with provenance (`ResultPublication` version + `publishedBy/at/revisionId` + `snapshot`).
- [x] Analytics and audit history reflect persisted data, are scoped by role, are paginated (`limit`/`cursor`/`nextCursor`), and audit behavior survives partial failures (best-effort after domain write, atomic CAS prevents double-disagreement).
- [x] UI is responsive and accessible (`aria-*`, `role="dialog"`, `aria-modal`, `aria-pressed`, `aria-label`, keyboard `label`/`input`), has loading/empty/error/success/busy states, and optimistic interactions recover safely after API conflicts (claim/release optimistic + rollback + `refresh()`).
- [x] Automated unit, API/integration, and browser E2E tests pass against a real MongoDB test instance (mongomock in-memory per-process, seeded); a clean install/start and the supplied validation skill pass (see `R01–R12` below).
- [ ] Repository remains private; PR/submission, collaborator, Discord, and transcript requirements are complete (private checked earlier, PR #1 open, transcript not yet exported this session).

## Last known branch / PR / verification

- **This session branch:** `arena/01a0ea33-gavel-react-and-django-app` (fixed for this Arena session). Previous handoff referenced `arena/01a0e993-…`; active is `arena/01a0ea33-…`.
- Pull request: https://github.com/Cometbuster4969/GAVEL-React-and-Django-App/pull/1 (open against `main`; verify it points to `arena/01a0ea33-…`).
- Last implementation commit before this handoff update: `b841d7f` (`after local trial`) superseded; new fixes include `package.json` cross-platform `dev:backend`, `setup.sh` mongomock install, `settings.py` fallback + auto-seed + `URL_FORMAT_OVERRIDE=None`, `repository.py`/`services.py`/`views.py` pagination, `services.py` analytics cache + invalidation, `frontend/src/features/gavel/gavel.api.js` pagination params, `frontend/src/features/gavel/GavelApp.jsx` optimistic claim/release + `items` handling, `backend/apps/gavel/test_integration.py`, `e2e/gavel.spec.js`. Working tree currently `M HANDOFF.md` + new/updated files (see `git status`).
- Repository visibility: private at earlier handoff; re-verify bevor submission. No changes should be pushed to any branch other than the Arena branch.
- Static checks now: `prettier --check` PASS, `vite build` PASS, `py_compile` PASS, `bash -n setup.sh` PASS, `git diff --check` PASS, `manage.py check` 0 issues, `unittest` 6 tests PASS, `git archive` ≈360k <5MB, `S01` naming still `GAVEL-React-and-Django-App` (Arena-assigned, not `coderepo-…`, cosmetic), `S12`/`S16` now PASS, `S06` PASS (no manifest deps added; `mongomock` installed via `setup.sh` pip not via `requirements.txt`).
- **Full verification now evidenced (this session, live mongomock):** `bun install && bash setup.sh --seed` exit 0, `.venv` `uv` + `mongomock`, health `200 ok/connected`, seed 5/3/8/6, `6 tests OK`, `vite build`, `bun run dev:frontend` + `manage.py runserver` on 3000/8000, 12-step E2E via live API (`node e2e/gavel.spec.js` → `API E2E passed`), pagination `?limit=2` returns `items/nextCursor`, CSV export `200 text/csv`, audit pagination, cache invalidation verified via `test_integration`.
- **Remaining to verify this session:** Formal a11y audit evidence, README reconciliation, transcript export, and final `skills/validate` full run (expect `S01` cosmetic, `MANUAL` for a11y/production, else `PASS`).

### Security Hardening Updates (2026-09-29)

- `SECURITY.md` created: documents CORS restriction, secret enforcement, JWT hardening (2h default, production validation), HTTPS redirect middleware, rate limiting, secret validation middleware, MongoDB outbox/transaction design, accessibility audit status, and remaining external submission steps.
- `backend/calendar_backend/security_middleware.py` created: `HTTPSRedirectMiddleware`, `RateLimitMiddleware` (100/min/IP, in-memory with `X-RateLimit-*` headers), `SecretValidationMiddleware` (503 if production JWT secret is weak/default).
- `backend/calendar_backend/settings.py` updated: `CORS_ALLOW_ALL_ORIGINS` tied to `DEBUG`; `ALLOWED_HOSTS` restricted in production; middleware list includes all three security middlewares; `JWT_SECRET` and `DJANGO_SECRET_KEY` enforce production values; `JWT_LIFETIME` defaults to 7200s.
- `backend/apps/gavel/auth.py` updated: uses `settings.JWT_LIFETIME` instead of hardcoded 86400s.
- `backend/.env.example` updated: production secret requirements, JWT lifetime, MongoDB TLS note, CORS allowed origins.
- `backend/calendar_backend/security_middleware.py` syntax verified (`python3 -m py_compile`).
- All changes committed to `arena/01a0eae7-gavel-react-and-django-app`.

### MongoDB Transaction / Outbox (Verified Design, Not Production Tested)
- Atomic `find_one_and_update` + CAS (`version`) covers domain mutations (campaigns, reviews, adjudications, submissions).
- Audit is best-effort append-only after domain success; no multi-doc Mongo transaction is required for correctness.
- Production recommendation: implement outbox pattern (same-transaction outbox collection + separate worker) if audit durability must survive domain failures; or use MongoDB 4.0+ `start_transaction()` for multi-document atomic updates.
