# Local Verification Checklist — Gavel

Run these on a clean checkout, exactly as HackerRank will. Check each box only with direct evidence (file opened, command output, live API response, or DB observation). Do **not** mark PASS from inference.

---

## 0) Prerequisites

- [ ] Bun `>=1.3` — `bun --version` (repo uses 1.4.2 locally)
- [ ] Python `3.12` (3.11.2 also works with mongomock fallback) — `python --version` / `python3 --version`
- [ ] `uv` for `.venv` — `uv --version` (fallback: `python -m venv`)
- [ ] MongoDB `8+` on `127.0.0.1:27017` **or** allow mongomock fallback (repo now auto-falls back to `mongomock` in-memory per-process when `mongod` unreachable — `setup.sh` installs it quietly)
- [ ] Free ports `3000` (Vite) and `8000` (Django) — `lsof -i :3000 -i :8000` or `ss -lntp` shows no listener before start
- [ ] Branch is `arena/01a0ea33-gavel-react-and-django-app` — `git branch --show-current`

Seeded credentials (`gavel2026!`):

| role | email |
|---|---|
| owner | `maya.chen@gavel.test` |
| reviewer | `jordan.lee@gavel.test` |
| reviewer | `sam.rivera@gavel.test` |
| adjudicator | `priya.shah@gavel.test` |
| admin | `elena.park@gavel.test` |

---

## 1) Install — `R01` (exact HackerRank command)

From repo root:

```bash
bun install && bash setup.sh --seed
```

Expected:

- [ ] `bun install` exits 0, creates `bun.lock`-consistent `node_modules` (no new lockfiles)
- [ ] `bash setup.sh --seed` exits 0:
  - creates `.env`/`frontend/.env`/`backend/.env` from `.example` if missing
  - checks/starts `mongod` **or** prints `WARN … will use mongomock…` and continues
  - installs `backend/requirements.txt` + `mongomock` into `.venv`
  - prints twice `Gavel database seeded successfully` (auto-seed + explicit seed) with
    `Users: 5 | Campaigns: 3 | Submissions: 8 | Review assignments: 6` (+ revisions/jobs/audits)
- [ ] No manual `.env` edits required

If `mongod` missing and `mongomock` not installed → setup still exits 0 but health will be `503 degraded`; install `mongomock` via `.venv/bin/pip install mongomock` and re-run `bash setup.sh --seed`.

---

## 2) Static checks — `S02–S19` (no servers needed)

Run from repo root:

```bash
# S02/S11/S18/S19 — repo shape, YAML, archive, debugger
cat hackerrank.yml                          # must parse, install= bun install && bash setup.sh --seed, run= bun start
cat .gitattributes                          # must exclude GUIDELINES.md, skills/, keep README.md
cat .gitignore | grep -E "^\.env|node_modules|dist|\.venv"
cat .vscode/launch.json                     # must point to real backend entry/port
git archive --format=tar HEAD | wc -c       # must be < 5242880 (5 MB) — current ~360k
git archive --format=tar HEAD | tar -t | grep -E "README.md|GUIDELINES.md|skills/"

# S16 — formatting
npx prettier --check "frontend/src/**/*.{js,jsx,css,json}"  # or: npx --yes prettier --check ...
npx prettier --check "backend/**/*.py" 2>/dev/null || python -m py_compile backend/apps/gavel/*.py

# S04–S06 — stack/dependencies
cat package.json | grep -E "workspaces|concurrently"
cat frontend/package.json 2>/dev/null || echo "root workspace only (expected)"
cat backend/requirements.txt
git diff $(git merge-base HEAD origin/main 2>/dev/null || echo HEAD~1) -- package.json bun.lock backend/requirements.txt 2>/dev/null | head -n 80
# must show NO added runtime dep (only removals/normalization allowed); mongomock is intentionally NOT in requirements.txt

# S08–S10 — Mongo, seed, env
grep -R "MongoEngine\|pymongo\|MONGODB_URI" backend --include="*.py" | head
cat backend/scripts/seed.py | grep -E "delete_many|ObjectId|GavelUser|Campaign"
cat backend/.env.example frontend/.env.example

# S07/S14/S15 — feature trace (open and read, not just ls)
# frontend surface → API client → backend route → service → repository → collection
grep -R "gavelApi\.\|/api/v1" frontend/src --include="*.js" --include="*.jsx" | head
grep -R "path\|include" backend/apps/gavel/urls.py backend/calendar_backend/urls.py
grep -R "def.*campaign\|def.*submission\|def.*review\|def.*adjudic" backend/apps/gavel/services.py | head
grep -R "class Campaign\|class Submission\|class ReviewAssignment\|class Adjudication" backend/apps/gavel/models.py
```

- [ ] `S02` monorepo complete (frontend/backend/seed/setup/README/debugger/hackerrank.yml exist)
- [ ] `S03` README covers 9 areas and matches source (identity/stack/tree/prereqs/Mongo/run/commands/credentials)
- [ ] `S04–S06` Bun workspace + no competing lockfile + no new deps
- [ ] `S07` feature architecture `route → controller → service → repository → DB` visible
- [ ] `S08` only MongoEngine/pymongo, no SQL/ORM
- [ ] `S09` seed clears collections before insert, deterministic ObjectIds
- [ ] `S10` `.env.example` exists, real `.env` ignored, `setup.sh` creates missing
- [ ] `S11` `hackerrank.yml` parses, paths exist
- [ ] `S12` Vite 3000 / Django 8000 / `VITE_API_URL=/api/v1` / proxy `0.0.0.0` + `allowedHosts`
- [ ] `S14/S15` every reachable UI action has an API client → route → service → collection; every product route has a UI consumer (except `/health`)
- [ ] `S16` Prettier clean, no dead imports/logs (lifecycle logs allowed)
- [ ] `S18` archive <5 MB, contains `README.md`, excludes `GUIDELINES.md`/`skills/`
- [ ] `S19` debugger points to real entry

> Note: `S01` repo name `GAVEL-React-and-Django-App` ≠ `coderepo-…` — Arena-assigned, cosmetic only. Mark `MANUAL` with note.

---

## 3) Build & backend check — `R02–R03`

```bash
cd frontend && bun run build
# expected: ✓ built in ~260ms, 20 modules, 261k js (gz 76k)

cd ../backend && ../.venv/bin/python manage.py check
# expected: System check identified no issues (0 silenced).
# (may print "Gavel database seeded successfully" twice — auto-seed per-process, harmless)

# compile gate
python -m py_compile apps/gavel/*.py apps/shared/*.py
```

- [ ] `R02` build exits 0 without manifest changes
- [ ] `R03` Django check exits 0

---

## 4) Full start — `R04–R05` (exact HackerRank run)

In repo root, stop any old listeners first (`lsof -ti :3000 :8000 | xargs kill` if you started them), then:

```bash
bun start
# prestart runs setup.sh --start (reseeds), then concurrently:
#   dev:backend  → Django 0.0.0.0:8000
#   dev:frontend → Vite 0.0.0.0:3000
```

Poll (bounded, not fixed sleep):

```bash
curl -s http://127.0.0.1:8000/api/v1/health
# expected: {"data":{"status":"ok","database":"connected"}}  (200)
# if mongomock fallback still degraded → 503 {"status":"degraded"} → re-seed/install mongomock

curl -s http://127.0.0.1:3000/ | head
# expected: <!doctype html> … Vite app

# without prestart (to preserve ad-hoc data, after first start):
bun run dev:backend   # in one terminal
bun run dev:frontend  # in another
```

- [ ] `R04` both ports respond (frontend 3000, backend 8000)
- [ ] `R05` health reports `connected` (not `disconnected`)

---

## 5) Seed baseline — `R06`

```bash
# via API (works with mongomock)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"elena.park@gavel.test","password":"gavel2026!"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
curl -s http://127.0.0.1:8000/api/v1/campaigns -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head
curl -s "http://127.0.0.1:8000/api/v1/audit?limit=5" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head

# or via mongo shell if real mongod
python backend/scripts/seed.py  # re-seed to baseline
```

- [ ] `R06` seeded baseline after `setup.sh --seed`: 5 users / 3 campaigns / 8 submissions / 6 reviews / 5 audits (verify at least `GET /campaigns` returns 3, audit returns ≥5)

---

## 6) Authentication — `R07`

```bash
# ok logins
for E in maya.chen@gavel.test jordan.lee@gavel.test sam.rivera@gavel.test priya.shah@gavel.test elena.park@gavel.test; do
  echo -n "$E: "; curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
    -H "Content-Type: application/json" -d "{\"email\":\"$E\",\"password\":\"gavel2026!\"}" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['user']['role'])"
done
# expected: owner, reviewer, reviewer, adjudicator, administrator

# me + protected route
curl -s http://127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/v1/campaigns | head          # no token → 401
curl -s http://127.0.0.1:8000/api/v1/campaigns -H "Authorization: Bearer $TOKEN" | head  # with token → 200
```

- [ ] Logins succeed per role, `GET /auth/me` returns `role`
- [ ] Protected route without token → `401 AUTH_REQUIRED` (or 403), with token → 200

---

## 7) Feature APIs — `R08` (trace every product group)

For each group, exercise one representative **read** through the real API and confirm live seeded data (not hardcoded):

```bash
# campaigns (owner sees owned, admin sees all)
curl -s "http://127.0.0.1:8000/api/v1/campaigns?limit=2" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -n 30
# expected: {data:{items:[…], nextCursor:"…"}} when ?limit present (bounded pagination)

# rubric/cases are inside campaign object
# submissions (owner)
curl -s http://127.0.0.1:8000/api/v1/campaigns/<CAMPAIGN_ID>/submissions -H "Authorization: Bearer $MAYA_TOKEN" | python3 -m json.tool | head

# reviews (reviewer)
curl -s "http://127.0.0.1:8000/api/v1/reviews?campaignId=<ID>&limit=2" -H "Authorization: Bearer $JORDAN_TOKEN" | python3 -m json.tool | head
# adjudications
curl -s "http://127.0.0.1:8000/api/v1/adjudications?campaignId=<ID>" -H "Authorization: Bearer $PRIYA_TOKEN" | python3 -m json.tool | head
# analytics
curl -s http://127.0.0.1:8000/api/v1/campaigns/<ID>/analytics -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head
# audit (cursor pagination, auth preserved)
curl -s "http://127.0.0.1:8000/api/v1/audit?limit=2" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head
# published results
curl -s http://127.0.0.1:8000/api/v1/campaigns/<ID>/published-results -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head
# export
curl -s "http://127.0.0.1:8000/api/v1/campaigns/<ID>/results-export?format=json" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head
curl -s -i "http://127.0.0.1:8000/api/v1/campaigns/<ID>/results-export?format=csv" -H "Authorization: Bearer $TOKEN" | head
# expected: HTTP/1.1 200 … Content-Type: text/csv … model,wins
```

- [ ] All groups return 200 with expected shape and live data (not empty/substituted)
- [ ] Pagination: `?limit=2` returns paginated `items` (not flat array) with `nextCursor` when full page; next page via `?cursor=<nextCursor>` preserves auth
- [ ] Blind: reviewer `GET /reviews` items have `left`/`right` only, no `modelName`/`submissionId` leakage
- [ ] CSV export is `200 text/csv`, not `404 detail: Not found` (fixed via `URL_FORMAT_OVERRIDE=None`)

---

## 8) Persistence — `R09` (create → read → update → delete via API, confirm in DB)

Use a uniquely named record so cleanup is reversible:

```bash
# helper: get Maya token
MAYA=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"maya.chen@gavel.test","password":"gavel2026!"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")

# 1) CREATE campaign
CID=$(curl -s -X POST http://127.0.0.1:8000/api/v1/campaigns/create -H "Content-Type: application/json" -H "Authorization: Bearer $MAYA" \
  -d '{"name":"Code Repo validation campaign","summary":"r09 check","testCases":[{"id":"c1","title":"Title","prompt":"Prompt"}],"rubric":[{"id":"r1","title":"Helpfulness","weight":100,"description":""}]}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")
echo $CID

# 2) READ
curl -s http://127.0.0.1:8000/api/v1/campaigns/$CID -H "Authorization: Bearer $MAYA" | python3 -m json.tool | head

# 3) UPDATE draft
curl -s -X PATCH http://127.0.0.1:8000/api/v1/campaigns/$CID -H "Content-Type: application/json" -H "Authorization: Bearer $MAYA" \
  -d '{"summary":"updated"}' | python3 -m json.tool | head

# 4) follow-up READ confirms persisted update
curl -s http://127.0.0.1:8000/api/v1/campaigns/$CID -H "Authorization: Bearer $MAYA" | python3 -m json.tool | grep summary

# 5) DELETE (draft only)
curl -s -X DELETE http://127.0.0.1:8000/api/v1/campaigns/$CID -H "Authorization: Bearer $MAYA" -i | head
curl -s http://127.0.0.1:8000/api/v1/campaigns/$CID -H "Authorization: Bearer $MAYA" -i | head  # → 404
```

- [ ] Create 201, read confirms values, update persists, follow-up read agrees, delete removes, second read 404
- [ ] No residue after cleanup

Also verify revision pinning + weighted scores in the same flow (or run the committed integration tests):

```bash
cd backend && ../.venv/bin/python -m unittest apps.gavel.test_services apps.gavel.test_integration
# expected: Ran 6 tests in … OK
```

---

## 9) Full lifecycle (the 12-step) — also covers `R09`/`R10`

Automated (preferred):

```bash
node e2e/gavel.spec.js
# expected: API E2E passed for <id>  /  E2E success
# exercises: create → publish (100% rubric) → start → ingest 2 → process → Jordan claim/submit {criterionScores 1-5} → Sam opposite → disagreement → Priya resolve (rationale 8-1200) → complete → publish v1 → audit pagination → export JSON+CSV → archive
```

Manual API equivalent (if you want to step through with curl — same sequence as above, but add):

```bash
# publish / start / complete are POST /campaigns/:id/transition {status:"published"|"running"|"completed"}
# ingest: POST /campaigns/:id/submissions {items:[{caseId,modelName,output,idempotencyKey},…]} → 202
# process: POST /campaigns/:id/submissions/process {limit:25} → processes 2
# claim:  POST /reviews/:id/claim → 200 (409 if already claimed — optimistic rollback should restore)
# submit: POST /reviews/:id/submit {choice:"a"|"b", notes, criterionScores:{r1:{a:5,b:3},…}} → disagreementDetected on 2nd
# resolve: POST /adjudications/:id/resolve {choice, rationale}
# publish: POST /campaigns/:id/publish-results → 201
```

- [ ] All 12 steps succeed, `weightedScore` computed server-side, disagreement created exactly once

---

## 10) Validation & errors — `R10`

```bash
# no auth
curl -s http://127.0.0.1:8000/api/v1/campaigns -i | head          # → 401
# malformed input (missing name, or rubric sum ≠100 on publish)
curl -s -X POST http://127.0.0.1:8000/api/v1/campaigns/create -H "Content-Type: application/json" -H "Authorization: Bearer $MAYA" \
  -d '{"name":"","summary":"x"}' | python3 -m json.tool | head        # → 400 {error:{code:"INVALID_INPUT"}}  no stack trace
# invalid id
curl -s http://127.0.0.1:8000/api/v1/campaigns/000000000000000000000000 -H "Authorization: Bearer $MAYA" -i | head  # → 404 {error:{code:"CAMPAIGN_NOT_FOUND"}}
# ownership/role boundary
JORDAN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"jordan.lee@gavel.test","password":"gavel2026!"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['token'])")
curl -s -X POST http://127.0.0.1:8000/api/v1/campaigns/create -H "Content-Type: application/json" -H "Authorization: Bearer $JORDAN" \
  -d '{"name":"x","summary":"x"}' | head                         # → 403
# idempotency duplicate
curl -s -X POST http://127.0.0.1:8000/api/v1/campaigns/<ID>/submissions -H "Content-Type: application/json" -H "Authorization: Bearer $MAYA" \
  -d '{"items":[{"caseId":"c1","modelName":"m","output":"o","idempotencyKey":"dup"}]}' | head  # → 202
curl -s -X POST http://127.0.0.1:8000/api/v1/campaigns/<ID>/submissions -H "Content-Type: application/json" -H "Authorization: Bearer $MAYA" \
  -d '{"items":[{"caseId":"c1","modelName":"m","output":"o","idempotencyKey":"dup"}]}' | head  # → same id or duplicate:true, second with different key+same payload → 409 IDEMPOTENCY_CONFLICT if enforced
```

- [ ] No `500`, no stack traces, concise `{error:{code,message,details?}}`
- [ ] 401 / 400 / 404 / 403 as above

---

## 11) Restart reset — `R11`

```bash
# create a second reversible record
CID2=$(curl -s -X POST http://127.0.0.1:8000/api/v1/campaigns/create -H "Content-Type: application/json" -H "Authorization: Bearer $MAYA" \
  -d '{"name":"Code Repo validation campaign 2","summary":"r11","testCases":[{"id":"c1","title":"T","prompt":"P"}],"rubric":[{"id":"r1","title":"R","weight":100,"description":""}]}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['id'])")

# restart via exact HackerRank run (must restore baseline)
# stop current (only if you started it)
# pkill -f "manage.py runserver" ; pkill -f "vite"
bun start
# wait for health 200 ok/connected, then:
curl -s http://127.0.0.1:8000/api/v1/campaigns/$CID2 -H "Authorization: Bearer $MAYA" -i | head  # → 404 (removed by seed reset)
curl -s http://127.0.0.1:8000/api/v1/campaigns -H "Authorization: Bearer $MAYA" | python3 -c "import sys,json;print(len(json.load(sys.stdin)['data']['items' if 'items' in json.load(sys.stdin)['data'] else '']))" 2>/dev/null || curl -s http://127.0.0.1:8000/api/v1/campaigns -H "Authorization: Bearer $MAYA" | python3 -m json.tool | grep '"name"' | head
# → back to 3 seeded campaigns
```

- [ ] Reversible record disappears after `bun start` restart
- [ ] Baseline (3 campaigns / 8 submissions / 6 reviews) restored

---

## 12) Cleanup — `R12`

```bash
# stop only what you started
# if you used bun start, Ctrl+C or: pkill -f "concurrently" ; pkill -f "manage.py runserver" ; pkill -f "vite"
lsof -i :3000 -i :8000  # → no listeners you started (do not kill pre-existing ones)
git status --porcelain   # → empty (or only ignored files) — must equal starting state
# remove any /tmp scratch you created
```

- [ ] Ports released, `git status` clean

---

## 13) Final verdict — is it complete after this?

**Complete if ALL of these are true:**

- [ ] `S01` is `MANUAL` only for the cosmetic repo name (`GAVEL-…` vs `coderepo-…` — Arena-assigned)
- [ ] Every other `S02–S19` is `PASS` with evidence (archive <5 MB, Prettier clean, build ok, no new deps, routes traced)
- [ ] `R01–R05` `PASS` (install/build/check/health all `ok/connected`)
- [ ] `R06–R09` `PASS` (seed counts match, auth works, every product group responds with live data, create/update/read/delete persists and cleans up; `node e2e/gavel.spec.js` or the 12-step manual flow succeeds with weighted scores + adjudication)
- [ ] `R10` `PASS` (400/401/404/403 without stack traces)
- [ ] `R11–R12` `PASS` (restart resets, cleanup restores git status)

**Operational items that are intentionally `MANUAL` and do NOT block “complete” per report.md:**

- MongoDB transaction/outbox for audit (repo uses atomic CAS + best-effort audit; replica-set transactions not required for correctness — document as such)
- Formal a11y audit (keyboard-only, focus trap, screen-reader, contrast — code has `aria-*`/`role=dialog` but evidence capture is manual)
- Production hardening (CORS `ALLOW_ALL`, 86400s JWT, no rate limit — dev defaults, document prod overrides)

If any `S` or `R` above is `FAIL` (not `MANUAL` with unavailable infra), it is **not complete** — fix the failing area and re-run this file from the top. When all checked, the repo is submission-ready: push to `arena/01a0ea33-gavel-react-and-django-app`, keep the repo **private**, merge PR #1, invite `content.team@problemsetters.com`, export `~/hackerrank_react_django_application/log.txt` → `transcripts/`, post Discord.
