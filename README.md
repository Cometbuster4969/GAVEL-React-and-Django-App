# Gavel

Gavel is an AI evaluation operations workspace for product and quality teams. It turns model-response testing into a structured, auditable release signal: teams version test suites and scoring rubrics, process response batches, compare outputs blind, adjudicate reviewer disagreement, and inspect the evidence behind results.

## Product and users

- **Campaign owners** create evaluations, manage draft prompts and weighted scoring criteria, run response batches, and monitor campaign progress.
- **Reviewers** claim pairwise assignments and select the stronger response without seeing model identities or other reviewers' choices.
- **Adjudicators** resolve disagreements with a required rationale recorded in the audit history.
- **Administrators** can manage the complete evaluation workspace.

The core workflow is draft → published → running → reviewing → completed → archived. Publishing freezes the test suite and rubric versions. A campaign cannot be completed while reviews or disagreement cases remain open.

## Domain model

- A **user** has one workspace role and receives a short-lived signed session token.
- A **campaign** is owned by one user and contains immutable-on-publish test cases plus a separately versioned weighted rubric.
- A **submission** pins its campaign and rubric version, test case, model label, output, idempotency key, processing state, and retry count.
- A **review assignment** pairs two submissions for one test case, pins the rubric version, and moves atomically from available to claimed to completed.
- An **adjudication** links a disputed pair to a final selected submission and required rationale.
- An **audit event** records important workspace actions as append-only history.

## Capabilities

1. Role-aware sign-in and API authorization for administrators, owners, reviewers, and adjudicators.
2. Campaign lifecycle transitions with validation, ownership checks, and audit records.
3. Versioned test-case management and a weighted rubric builder that enforces a 100% total before publishing.
4. Idempotent response ingestion, a queued processing workflow, retryable failures, and per-campaign submission tracking.
5. Blind pairwise comparisons with reviewer-specific deterministic response ordering and hidden model identities.
6. Atomic review claiming to prevent two reviewers from taking the same assignment.
7. Automatic disagreement detection and adjudication with an immutable final decision rationale.
8. Stored campaign analytics, preference outcomes, throughput metrics, and append-only audit history.
9. Atomic audit intent: each domain write embeds its event in the same MongoDB document; a durable outbox relays it with idempotent delivery, retries, and operator-visible failures.

## Technology stack

- **Frontend:** React 19.2.4, Vite 8.2.2, JavaScript, and the Roboto Fontsource package.
- **Backend:** Python 3.12, Django 5.1.5, Django REST Framework 3.15.2.
- **Persistence:** MongoDB 8+ through MongoEngine 0.29.1. The Django ORM is not used.
- **Authentication:** bcrypt password hashes and signed JWT bearer tokens using PyJWT.
- **Tooling:** Bun workspace, Vite production build, Python virtual environment.
- **Runtime ports:** React/Vite on `3000`; Django API on `8000`; MongoDB on `27017`.

The product uses no external component library or hosted service. Dependencies strictly adhere to the frozen baseline.

## Project structure

```text
.
├── frontend/
│   ├── src/App.jsx                   # React entry boundary
│   ├── src/features/gavel/           # Evaluation workspace, grouped by feature
│   │   ├── GavelApp.jsx              # Signed-in shell and feature orchestration
│   │   ├── auth/                     # Sign-in
│   │   ├── overview/                 # Dashboard
│   │   ├── campaigns/                # Campaign list, detail, and editors
│   │   ├── reviews/                  # Blind pairwise review
│   │   ├── adjudications/            # Disagreement resolution
│   │   ├── analytics/                # Published results
│   │   ├── activity/                 # Audit history
│   │   ├── components/               # Shared UI and navigation shell
│   │   ├── constants.js              # Role labels and navigation tabs
│   │   ├── format.js                 # Display formatters
│   │   └── gavel.api.js              # Frontend API client
│   ├── src/shared/api/               # Authenticated JSON API client
│   └── public/                       # Local favicon
├── backend/
│   ├── apps/gavel/                   # Identity, campaigns, submissions, reviews, decisions, analytics, audit outbox
│   │   ├── apps.py                   # Django AppConfig
│   │   ├── audit.py                  # Atomic embedded audit intent and relay
│   │   ├── auth.py                   # Authentication, token generation, constant-time bcrypt verification
│   │   ├── jobs.py                   # Processing queue workers and state machines
│   │   ├── models.py                 # MongoEngine documents, indexes, and collections
│   │   ├── repository.py             # Database query and persistence boundary
│   │   ├── services/                 # Domain rules grouped by feature
│   │   │   ├── campaigns.py          # Campaign lifecycle, ownership, and publishing
│   │   │   ├── submissions.py        # Response ingest, processing, and pairing
│   │   │   ├── reviews.py            # Blind claim, independence, and scoring
│   │   │   ├── adjudications.py      # Disagreement resolution
│   │   │   ├── analytics.py          # Results snapshots
│   │   │   └── audit_ops.py          # Outbox drain and audit log
│   │   ├── tests/                    # Throwaway-database suite (never gavel_db)
│   │   ├── views.py                  # HTTP handlers and response formatting
│   │   └── worker.py                 # Standalone background worker (jobs + audit relay)
│   ├── apps/shared/                  # MongoDB health, API errors, rendering, timestamps
│   ├── calendar_backend/             # Django settings, security middleware, and URL routing
│   └── scripts/seed.py               # Deterministic demo data and reset
├── e2e/
│   └── gavel.spec.js                 # Optional live-API walkthrough (reseeds afterward)
├── scripts/
│   ├── run-backend.mjs               # Backend runner
│   ├── run-seed.mjs                  # Seed runner
│   ├── run-setup.mjs                 # Setup runner
│   ├── run-worker.mjs                # Worker runner
│   ├── run-tests.mjs                 # bun test entry point
│   └── test-backend.py               # Creates, uses, and drops a throwaway MongoDB
├── skills/validate/                  # Repository validation skill
├── transcripts/                      # AI session logs and verification records
├── .vscode/launch.json               # Django debugger configuration
├── hackerrank.yml                    # HackerRank install/run contract
├── package.json                      # Bun workspace manifest
└── setup.sh                          # Environment setup, MongoDB check, and seed reset
```

## Prerequisites

- Bun 1.3 or later
- Python 3.12 (Python 3.11+ supported)
- MongoDB 8 or later available at `127.0.0.1:27017`

Acceptance, development, and tests require a reachable MongoDB. If MongoDB does
not answer within three seconds the backend exits with a clear error. There is
no in-memory database fallback.

`setup.sh` creates missing `.env` files from committed examples, prepares `.venv`, checks MongoDB, and restores the seeded baseline. The connection URI is centralized in `backend/.env` and defaults to `mongodb://127.0.0.1:27017/gavel_db`.

## Install and run

```bash
bun install && bash setup.sh --seed
bun start
```

`bun start` launches the API on port 8000 and the frontend on port 3000. For queued
processing and audit outbox relay, run `bun run worker` in a separate terminal using
the same MongoDB database. The UI also provides interactive batch-processing actions.

Open [http://localhost:3000](http://localhost:3000). The backend health endpoint is [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health); it reports API and MongoDB readiness separately.

`bun start` runs the setup/seed prestart step before launching Django and Vite. Starting the product resets application collections to the deterministic seed state.

## Database configuration and seed data

The application stores data in MongoDB across the following collections:

| Collection | Purpose |
|---|---|
| `gavelusers` | User accounts, hashed passwords, roles, and review independence groups. |
| `campaigns` | Evaluation campaigns, draft/published test cases, and rubrics. |
| `campaignrevisions` | Immutable snapshots of published campaign versions. |
| `submissions` | Model outputs queued or processed for pairwise review. |
| `reviewassignments` | Assigned pairs for double-blind reviewer evaluation. |
| `adjudications` | Disagreements flagged between reviewers, awaiting adjudicator resolution. |
| `processingjobs` | Asynchronous submission batch processing tasks. |
| `resultpublications` | Published campaign outcomes, Elo rankings, and win rates. |
| `auditevents` | Append-only audit history of all critical operations. |
| `auditoutbox` | Durable outbox for idempotent relay of embedded audit intents. |
| `ratelimitcounters` | Shared MongoDB-backed fixed-window rate-limiting counters. |

The database is deterministically populated by `backend/scripts/seed.py` (invoked via `bun run seed` or `bash setup.sh --seed`).

## Environment variables

Committed example files `backend/.env.example` and `frontend/.env.example` specify defaults:

| Variable | Default | Purpose |
|---|---|---|
| `NODE_ENV` | `development` | Runtime environment (`development` or `production`). |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017/gavel_db` | Connection string for MongoDB. |
| `DJANGO_SECRET_KEY` | Development key | Django security secret. |
| `JWT_SECRET` | Development key | Secret key for signing session tokens. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Allowed frontend origins in production; development allows all origins. |
| `TRUSTED_PROXY_CIDRS` | `""` | Comma-separated CIDRs trusted to supply `X-Forwarded-For`. |
| `VITE_API_URL` | `/api/v1` | Frontend API base path; Vite proxies `/api` to the backend on port 8000 during development. |

## Demo accounts

All seeded accounts use the demo password `gavel2026!`.

| Role | Email | Display name |
|---|---|---|
| Administrator | `elena.park@gavel.test` | Elena Park |
| Campaign owner | `maya.chen@gavel.test` | Maya Chen |
| Reviewer | `jordan.lee@gavel.test` | Jordan Lee |
| Reviewer | `sam.rivera@gavel.test` | Sam Rivera |
| Adjudicator | `priya.shah@gavel.test` | Priya Shah |

The login screen includes quick shortcuts for Elena, Maya, Jordan, and Priya; Sam can log in directly using credentials. Review assignments hide model identity and randomize left/right ordering independently per reviewer.

## Commands

| Command | Purpose |
|---|---|
| `bun install` | Install workspace dependencies. |
| `bash setup.sh --seed` | Prepare Python environment, verify MongoDB, and reset seed data. |
| `bun start` | Seed baseline and run frontend (port 3000) and backend (port 8000). |
| `bun run seed` | Rebuild deterministic seed baseline in MongoDB. |
| `bun run worker` | Run background worker for submission jobs and audit outbox (add `-- --once` for single pass). |
| `bun run dev:backend` | Run Django API on port 8000. |
| `bun run dev:frontend` | Run Vite frontend on port 3000. |
| `cd frontend && bun run build` | Build React production bundle. |
| `bun test` | Create a throwaway `gavel_test_*` database, run campaign, review, and adjudication tests (including refusals), then drop that database. Does not use demo accounts or `gavel_db`. |
| `bun run test:e2e` | Optional live-API walkthrough against a running app. Reseed afterward with `bun run seed`. |

## Tests

`bun test` is the only supported test command. It creates a unique `gavel_test_*` MongoDB database, inserts its own users (not the demo accounts), covers campaign, review, and adjudication rules including the refusals, and drops that database when it finishes. It never writes to `gavel_db`, so running tests cannot leave campaigns in the app. If MongoDB does not answer within three seconds the command fails with a clear error instead of using an in-memory database.

```bash
bun test
```

## Architecture and security controls

- **Atomic audit intent & durable outbox:** Audited domain writes embed their audit event within the same MongoDB document (`auditPending`). A durable outbox relays events with idempotent upsert into `auditevents`. At 1,000 pending intents on a single document, further mutations return `503 AUDIT_BACKLOG` to protect history integrity.
- **Pagination & cursor integrity:** Paginated collections use descending `(timestamp, _id)` ordering with strict cursor tie-breaking. Owner, reviewer, and adjudication scopes are applied in MongoDB prior to pagination limits.
- **Reviewer independence & blind review:** Reviewers evaluate anonymized pairs with randomized positioning. Reviewer independence groups prevent the same person or affiliated accounts from taking both evaluation slots for a pair. Operators can provision verified identity groups via `manage.py set_review_identity`.
- **Constant-time authentication:** Unknown accounts and incorrect passwords both execute a bcrypt verification with uniform work factor, preventing timing-based user enumeration.
- **Distributed rate limiting:** `RateLimitMiddleware` maintains atomic counters in MongoDB `ratelimitcounters`, enforcing shared quotas across API instances.
