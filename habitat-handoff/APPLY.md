# Habitat field-test projection handoff (apply to stratex-habitat)

**Target repo:** `https://github.com/TCCross1/stratex-habitat.git`  
**Base branch:** `field-test/ready-v1`  
**Feature branch name:** `cursor/field-test-projection-handoff-5924`  
**Architecture:** Core seals → Passport stores → Habitat reads only

This cloud agent run could clone and commit on Habitat locally but **could not push** to `TCCross1/stratex-habitat` (GitHub 403 for cursor[bot]). Artifacts below are the completed Habitat change set.

## Apply (preferred)

```bash
git clone https://github.com/TCCross1/stratex-habitat.git
cd stratex-habitat
git checkout field-test/ready-v1
git checkout -b cursor/field-test-projection-handoff-5924
git am ../Stratex-2/habitat-handoff/habitat-field-test-projection-handoff.patch
# or: git apply habitat-handoff/habitat-field-test-projection-handoff.patch && git add -A && git commit
git push -u origin cursor/field-test-projection-handoff-5924
```

Bundle alternative (includes the commit):

```bash
git clone https://github.com/TCCross1/stratex-habitat.git
cd stratex-habitat
git checkout field-test/ready-v1
git fetch ../Stratex-2/habitat-handoff/habitat-field-test-projection-handoff.bundle \
  cursor/field-test-projection-handoff-5924:cursor/field-test-projection-handoff-5924
git checkout cursor/field-test-projection-handoff-5924
git push -u origin cursor/field-test-projection-handoff-5924
```

Or copy files from `habitat-handoff/files/` into the matching paths in stratex-habitat.

## What changed

| Area | Change |
|------|--------|
| `HABITAT_PROJECTION_PATH` | Loads `habitat.projection.v1` JSON for dashboard + openings |
| `GET /api/habitat/dashboard/projection` | Returns real JSON; prefers file path, else adapter/stub |
| UI | **Official** vs **Preview** from `authoritative` |
| Frontend fetch | Uses `REACT_APP_BACKEND_URL` so SPA HTML is not mistaken for projection JSON |
| `POST /api/habitat/v1/claim/redeem` | Read-only lookup stub — no mint, no ledger write, no Core publish |
| Studios / login | Untouched |

## Env vars

| Var | Role |
|-----|------|
| `HABITAT_PROJECTION_PATH` | Absolute path to Core/Passport `habitat.projection.v1.json` |
| `REACT_APP_BACKEND_URL` | Frontend → Habitat API base (required for dashboard JSON) |
| Existing | `MONGO_URL`, `DB_NAME`, `JWT_SECRET` for normal Habitat boot |

Sample preview file (in Habitat after apply):  
`backend/fixtures/habitat.projection.v1.sample.json` (`authoritative: false`)

Point at a sealed/official export by setting `"authoritative": true` in the JSON after governed Passport publish.

## How to run

```bash
# backend
cd backend
export HABITAT_PROJECTION_PATH="$(pwd)/fixtures/habitat.projection.v1.sample.json"
# plus MONGO_URL DB_NAME JWT_SECRET from .env
uvicorn server:app --reload --port 8000

# frontend
cd frontend
# REACT_APP_BACKEND_URL=http://localhost:8000
yarn start
```

Login as usual → `/dashboard`. Footer/badge show Preview or Official.

Claim redeem (read-only):

```bash
curl -s -X POST "$REACT_APP_BACKEND_URL/api/habitat/v1/claim/redeem" \
  -H 'Content-Type: application/json' \
  -d '{"claim_code":"SH-FIELD-TEST-01"}'
```

## Tests run locally

```bash
cd backend
PYTHONPATH=. python -m pytest tests/test_field_test_projection_handoff.py \
  tests/test_habitat_ui_projection.py -n 0 --noconftest
# 13 passed
```
