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

## Technology stack

- **Frontend:** React 19.2.4, Vite 8.2.2, JavaScript, and the existing Roboto Fontsource package.
- **Backend:** Python 3.12, Django 5.1.5, Django REST Framework 3.15.2.
- **Persistence:** MongoDB 8+ through MongoEngine 0.29.1. The Django ORM is not used.
- **Authentication:** bcrypt password hashes and signed JWT bearer tokens using the existing PyJWT dependency.
- **Tooling:** Bun 1.3+ workspace, Vite production build, `uv` for the Python virtual environment, and the supplied repository validation skill.
- **Runtime ports:** React/Vite on `3000`; Django API on `8000`; MongoDB on `27017`.

No external component library, hosted service, or new runtime dependency is used.

## Project structure

```text
.
├── frontend/
│   ├── src/App.jsx                   # React entry boundary
│   ├── src/features/gavel/           # Workspace shell, product flows, and Gavel API client
│   ├── src/shared/api/               # Authenticated JSON API client
│   └── public/                       # Local favicon
├── backend/
│   ├── apps/gavel/                   # Identity, campaigns, submissions, reviews, decisions, analytics
│   │   ├── views.py                  # Thin HTTP handlers
│   │   ├── services.py               # Domain rules and lifecycle workflows
│   │   ├── repository.py             # MongoEngine query boundary
│   │   └── models.py                 # MongoDB documents and indexes
│   ├── apps/shared/                  # MongoDB health, API errors, rendering, timestamps
│   ├── calendar_backend/             # Django settings and URL composition
│   └── scripts/seed.py               # Deterministic demo data and reset
├── skills/validate/                  # Supplied static/runtime repository verifier
├── transcripts/                      # AI interaction log export for submission
├── .vscode/launch.json               # Django debugger configuration
├── hackerrank.yml                    # HackerRank install/run contract
└── setup.sh                          # Environment setup, MongoDB check, and seed reset
```

## Prerequisites

- Bun 1.3 or later
- Python 3.12
- `uv`
- MongoDB 8 or later available at `127.0.0.1:27017`

`setup.sh` creates missing `.env` files from the committed examples, prepares `.venv`, checks MongoDB, and restores the seeded baseline. The connection URI is centralized in `backend/.env` and defaults to `mongodb://127.0.0.1:27017/gavel_db`.

## Install and run

```bash
bun install && bash setup.sh --seed
bun start
```

Open [http://localhost:3000](http://localhost:3000). The backend health endpoint is [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health); it reports API and MongoDB readiness separately.

`bun start` runs the setup/seed prestart step before launching Django and Vite. Starting the product resets its application collections to the documented seed state; do not use this command when you need to preserve ad hoc database records.

## Demo access

All seeded accounts use the demo password `gavel2026!`.

| Role | Email |
|---|---|
| Campaign owner | `maya.chen@gavel.test` |
| Reviewer | `jordan.lee@gavel.test` |
| Reviewer | `sam.rivera@gavel.test` |
| Adjudicator | `priya.shah@gavel.test` |
| Administrator | `elena.park@gavel.test` |

The login screen includes shortcuts for each demo identity. Review assignments hide system identity and randomize left/right ordering independently for each reviewer.

## Commands

| Command | Purpose |
|---|---|
| `bun install` | Install the pinned JavaScript workspace. |
| `bash setup.sh --seed` | Prepare Python/MongoDB and reset seeded application data. |
| `bun start` | Seed the baseline and run the complete frontend and backend. |
| `bun run seed` | Rebuild the deterministic MongoDB demo baseline. |
| `bun run dev:backend` | Run the Django API on port 8000 after setup. |
| `bun run dev:frontend` | Run the Vite app on port 3000. |
| `cd frontend && bun run build` | Build the React application for production. |
| `./.venv/bin/python backend/manage.py check` | Run Django's configuration checks using the prepared Python environment. |

The authoritative HackerRank commands are `bun install && bash setup.sh --seed` for install and `bun start` for run. Before submission, run `skills/validate/SKILL.md`, export the transcript log to `transcripts/`, and resolve every validation failure.
