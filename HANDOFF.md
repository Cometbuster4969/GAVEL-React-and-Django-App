# Gavel Completion Handoff

**Purpose:** Give the next developer or AI agent enough context to continue the Gavel build, validate it, and determine when it is complete. This is a work plan and status report—not a claim that the application is already complete.

## Start here

1. Read `AGENTS.md`, `GUIDELINES.md`, `INSTRUCTIONS.md`, `REQUIREMENTS.md`, and `README.md` before changing code.
2. Read `skills/validate/SKILL.md` and follow its referenced checklists when validating. It is an acceptance procedure, not just a quick test command.
3. Check `git status`, the current branch, PR status, and listeners on ports 3000, 8000, and 27017. Preserve existing user changes and processes.
4. Continue only on `arena/01a0e993-gavel-react-and-django-app`; Arena associates this work with that branch. Do not change branches. The PR is listed below.
5. Establish a working full-stack runtime before judging sign-in or claiming end-to-end behavior.

## Product goal

Gavel is a private AI-evaluation operations platform. The intended end-to-end workflow is:

> Create a versioned evaluation campaign → configure a weighted scoring rubric → upload model responses → process submissions asynchronously → assign blind pairwise reviews → resolve disagreements → publish results and inspect analytics/audit history.

Required roles are administrator, campaign owner, reviewer, and adjudicator. API authorization—not merely hidden frontend controls—must enforce role and ownership boundaries.

## Repository and runtime

- Frontend: React 19, Vite 8, JavaScript; `frontend/src/features/gavel/GavelApp.jsx` contains the main UI.
- Frontend API: `frontend/src/features/gavel/gavel.api.js` and `frontend/src/shared/api/client.js`; requests use the relative `/api/v1` path and Vite proxies to port 8000.
- Backend: Python 3.12, Django 5.1, Django REST Framework; app code is under `backend/apps/gavel/`.
- Persistence: MongoDB 8+ using MongoEngine, not Django ORM. Domain rules are in `backend/apps/gavel/services.py`; documents/indexes in `models.py`; query boundary in `repository.py`; handlers/routes in `views.py` and `urls.py`.
- Seed data: `backend/scripts/seed.py`.
- Expected ports: Vite 3000, Django 8000, MongoDB 27017.
- Success API envelope: `{ "data": ... }`. Health endpoint: `/api/v1/health`.

### Local setup

Prerequisites: Bun 1.3+, Python 3.12, `uv`, and MongoDB 8+ on `127.0.0.1:27017`.

Initial install and seed, from the repository root:

```bash
bun install
bash setup.sh --seed
```

The setup script creates local `.env` files from examples, prepares `.venv`, checks/starts MongoDB if possible, and seeds/reset application collections. **`bun start` also runs setup/seed as a prestart step and resets those collections.** After the first setup, preserve local test data by starting the app without the prestart script, in two root-directory terminals:

```bash
bun run dev:backend
```

```bash
bun run dev:frontend
```

Verify `http://localhost:8000/api/v1/health` reports MongoDB connected, then open `http://localhost:3000`.

Seeded accounts all use `gavel2026!`:

- Owner: `maya.chen@gavel.test`
- Reviewers: `jordan.lee@gavel.test`, `sam.rivera@gavel.test`
- Adjudicator: `priya.shah@gavel.test`
- Administrator: `elena.park@gavel.test`

Never use the demo JWT secret or demo passwords in a deployed environment. Keep MongoDB private and configure production secrets, TLS, hosts, and serving infrastructure before deployment.

## Current implementation status

Implemented in code (but the backend was not runtime-verified at handoff):

- API-layer role checks and ownership checks; bcrypt password hashes and signed JWT authentication.
- Guarded campaign lifecycle transitions; draft test-case/rubric editing; publish-time rubric total validation; published definitions are frozen.
- Separate suite/rubric version counters; submissions and review assignments pin the rubric version.
- Response validation, queued/failed/ready states, idempotency keys, retry limits, and compare-and-set job claiming/recovery.
- Blind pairwise responses with model/submission identities omitted from reviewer payloads and stable deterministic side selection per reviewer.
- Two review slots per candidate pair, atomic claim/release, disagreement detection, rationale-bearing adjudication, campaign analytics, audit events, and draft deletion rules.
- Responsive dashboard, campaign editor, submission entry, blind review, adjudication, analytics, activity/audit UI, loading/error/busy states.
- Deterministic demo seed data and indexes.

Important constraints and gaps—the plan is **not complete**:

1. **No independent worker:** queued work is processed in a batch only when the API process endpoint is called. There is no autonomous background worker, scheduler, or progress polling.
2. **No retained definition history:** suite/rubric versions are counters on a campaign document. Prior snapshots are not retained, and there is no clone/create-new-version workflow.
3. **Rubric is not actually scored per criterion:** reviewers pick the preferred response and may add notes. Rubric weights are displayed as guidance; the app does not collect criterion scores or compute a weighted score.
4. **Assignment policy is limited:** atomic claim/release prevents two users claiming the same slot concurrently. Reviewers self-claim from a shared queue; there is no explicit conflict-of-interest policy or deterministic load-balanced assignment.
5. **No separate results-publication/export flow:** campaign completion and analytics exist, but there is no publish-results snapshot or export action.
6. **No database transaction strategy:** related writes (for example a domain update and its audit event) are separate operations. Unique indexes and atomic conditional updates help, but do not make multi-document work transactional.
7. **No caching or cursor pagination:** repository listing is generally unbounded; audit listing has a fixed limit. Implement if these remain acceptance requirements.
8. **No optimistic UI mutations:** most actions wait for the API and refresh state; busy/loading/error feedback exists.
9. **No automated end-to-end proof:** no dedicated backend integration or browser E2E suite was found during the initial review. Accessibility has not been formally audited.
10. **Response ingestion is manual in the UI:** the backend accepts batches, but the UI is a small form, not a CSV/file upload or external model-response connector.
11. **Audit is application-level append-only only:** no edit/delete product routes exist, but MongoDB administrators could still alter records; audit writes are not transactionally coupled to domain writes.

## Work plan to reach completion

Work in this order; update this file as tasks are completed. Do not mark a task complete based only on source inspection—record test/runtime evidence.

### P0 — Get a reproducible full-stack baseline

- [ ] Provision Bun, Python 3.12, `uv`, and MongoDB 8 in a supported environment.
- [ ] Run the exact install command and setup/seed flow above from a clean checkout.
- [ ] Start both services and verify frontend, backend health, and MongoDB connectivity.
- [ ] Verify all seeded accounts can log in; test protected route rejection without auth and role/owner boundaries with auth.
- [ ] Exercise create → edit → publish → start → submit → process → review → adjudicate → complete/archive through the browser and API.
- [ ] Record observed failures and fix them before feature expansion; specifically confirm Vite proxy and login work with the backend.
- [ ] Add regression tests for any bugs found.

### P1 — Complete the primary product semantics

- [ ] **Immutable revisions:** persist immutable test-suite and rubric revision snapshots (or a versioned definition model). Publishing freezes a revision. Editing published work must create a new version while preserving the old one and linking submissions/reviews to the exact version.
- [ ] **Weighted evaluation:** define how each reviewer scores each response on each rubric criterion; validate numeric ranges and required criterion completion; calculate the weighted result server-side; preserve the pairwise preference only if it remains part of the intended workflow. Validate total weights equals 100 before publish and freeze the published rubric.
- [ ] **Real background processing:** move processing out of the request handler into a durable worker/queue with idempotent job creation, claim leases, bounded retries/backoff, failure reporting, stale-job recovery, and observable progress. Preserve pinned versions. Keep dependencies within the approved stack unless new dependencies are explicitly approved and pinned.
- [ ] **Assignment and conflict prevention:** define conflicts (including whether one person may review both slots of the same pair, campaign/model affiliations, and self-review); enforce the policy in the service/API under concurrency; make assignment decisions auditable.
- [ ] **Publish results:** add an explicit guarded results-publication action, immutable publication snapshot/version, and suitable read/export path. Decide which roles can publish and view results.
- [ ] Add service/API tests for lifecycle guards, version pinning, weight validation/scoring, retries/idempotency, auth/ownership, blind payload leakage, concurrent claim/release, disagreements, adjudication, and audit behavior.

### P2 — Complete engineering and UX acceptance

- [ ] Choose and implement a consistency strategy for multi-document writes and audit events (MongoDB transactions require replica-set support; an outbox/compensation strategy is an alternative). Test failure between writes.
- [ ] Add cursor pagination and bounded filters for campaigns, submissions, reviews, adjudications, and audit. Document cursor stability and authorization scope.
- [ ] Add caching only for safe, scoped, invalidated data; test that role-specific or newly published data cannot leak across users.
- [ ] Add optimistic UI updates only where safe, with rollback and conflict refresh. Keep clear pending/success/error feedback for background jobs.
- [ ] Complete accessibility checks: keyboard-only navigation, focus management for dialogs, labels/instructions, screen-reader state announcements, contrast, and responsive layout. Record the audit evidence.
- [ ] Add browser E2E tests for each role and the full lifecycle; test actual API + MongoDB persistence, not local/mock substitutes.
- [ ] Add operational safeguards: rate/size limits appropriate to the API, secure CORS/hosts, token expiry/logout behavior, structured logs/health, and backup/recovery guidance as required by deployment scope.

### P3 — Release readiness and handover

- [ ] Reconcile README, `.env.example`, setup commands, runtime behavior, API routes, and this handoff. Remove inaccurate promises.
- [ ] Run all automated tests, production frontend build, Django checks, lint/format/syntax checks, and the full validation skill. Resolve every `FAIL`; provide evidence and repeat steps for any unavoidable `MANUAL` result.
- [ ] Validate the application from a clean install and verify persisted data after restart. Confirm seed reset behavior is documented and production startup never resets user data.
- [ ] Perform a production configuration/security review (secrets, HTTPS, host/origin settings, MongoDB auth/network exposure, backups, worker supervision, migrations/index rollout, logging/monitoring).
- [ ] Keep the GitHub repository private. Review and merge the PR only after acceptance criteria pass.
- [ ] Complete assignment handover requirements: invite `content.team@problemsetters.com`, post the required Discord submission/notification, and export the complete append-only external AI session log from `$HOME/hackerrank_react_django_application/log.txt` into repository `/transcripts/` at submission. Do not rewrite the external log; retain it append-only.

## Full acceptance checklist

Call the project complete only when all applicable items below are evidenced, not merely implemented:

- [ ] Every role can sign in; all protected routes enforce role and resource ownership; denied requests return correct structured errors.
- [ ] A new campaign can be drafted, versioned, published immutably, started, completed under guards, archived, and revised without mutating historical evaluations.
- [ ] A rubric totals exactly 100%, is frozen with a version, is used to collect criterion-level scores, and yields reproducible weighted results.
- [ ] Valid response files/batches are ingested, invalid rows reported, duplicate idempotency keys handled safely, and accepted submissions processed by a background worker with retries and visible status.
- [ ] Review assignments enforce conflict policy and concurrency safety; reviewers see no model identity, submission ID, or other reviewers' votes; ordering is stable per reviewer and blind.
- [ ] Disagreement cases are generated exactly once, adjudicators record a final decision/rationale, and results are explicitly published/exported with provenance.
- [ ] Analytics and audit history reflect persisted data, are scoped by role, are paginated, and audit behavior survives partial failures.
- [ ] UI is responsive and accessible, has loading/empty/error/success states, and optimistic interactions recover safely after API conflicts.
- [ ] Automated unit, API/integration, and browser end-to-end tests pass against a real MongoDB test instance; a clean install/start and the supplied validation skill pass.
- [ ] Repository remains private; PR/submission, collaborator, Discord, and transcript requirements are complete.

## Last known branch / PR / verification

- Branch: `arena/01a0e993-gavel-react-and-django-app` (fixed for this Arena session).
- Pull request: https://github.com/Cometbuster4969/GAVEL-React-and-Django-App/pull/1 (open against `main` at handoff).
- Last implementation commit before this handoff file: `3f9a479` (`Build Gavel AI evaluation operations platform`).
- Repository visibility was checked as private. No changes should be pushed to any branch other than the Arena branch.
- Static checks previously passed: frontend production build, Prettier check, Python compilation, `bash -n setup.sh`, and `git diff --check`.
- Full prescribed `bun install && bash setup.sh --seed`, backend runtime, MongoDB persistence, login, and full validation skill were **not** verified at that time. The available environment lacked Bun, Python 3.12, `uv`, and `mongod`; the Vite-only preview therefore returned 502 for API requests on port 8000.
- Recheck the environment and current PR/branch state rather than assuming these conditions still hold.
