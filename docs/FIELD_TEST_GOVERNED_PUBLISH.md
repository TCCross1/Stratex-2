# Field-test governed publish demo

**Branch:** `field-test/ready-v1`

Runs the sample Matrice 4E mission through **`field_test_pipeline`** (preflight ATC + pre-seal ATC checklist + seal), then either validates the `publication_request` (**dry-run**) or publishes to Passport via **`publish_sealed_package`** (live).

## Prerequisites

### Always (dry-run or live)

```bash
cd /path/to/Stratex-2
pip install -r backend/requirements.txt
```

### Live publish only

```bash
export MONGO_URL="mongodb://127.0.0.1:27017"
export DB_NAME="stratex_field_test"
pip install motor pymongo
export PASSPORT_TRANSACTIONS_AVAILABLE=0   # standalone Mongo (non-replica-set)
```

`motor` / `pymongo` are required for live mode but are not yet pinned in `requirements.txt`.

## Commands

### Dry-run (no Mongo) — recommended first

Validates pipeline + `publication_request` shape only:

```bash
make field-test-publish-dry
```

Or:

```bash
python3 -m backend.nextgen.field_test_governed_publish_demo --dry-run
```

**Success:** `"status": "DRY_RUN_OK"`, exit code `0`.

### Live governed publish

```bash
make field-test-publish
```

Or:

```bash
python3 -m backend.nextgen.field_test_governed_publish_demo
```

**Success:** `"status": "SUCCESS"`, Passport entry committed.

**Failure:** JSON includes exact `status`, `message`, and `publish_result` (e.g. `MONGO_UNAVAILABLE`, `STALE_EXPECTED_STATE`, `INDEX_NOT_READY`).

## What the demo does

1. **Pipeline** — `run_single_path_pipeline()` with sample mission (`MISSION-2026-0801-FT-001`, Matrice 4E, RGB evidence, geometry + AWE candidates).
2. **ATC** — preflight readiness + pre-seal Matrice checklist (must pass before seal).
3. **Seal** — produces `publication_request` via `prepare_for_governed_publish`.
4. **Live only** — reads passport head via `load_expected_state()`:
   - sets `expected_revision` = current revision (usually `0` on first publish)
   - sets `expected_head_hash` = current head hash (usually `null` on first publish)
5. **Publish** — `publish_sealed_package()` → `governed_publish()` → `append_entry()`.

## Exact steps if Mongo is not available

1. Run dry-run to confirm pipeline + request shape:
   ```bash
   python3 -m backend.nextgen.field_test_governed_publish_demo --dry-run
   ```
2. Start MongoDB locally (Docker example):
   ```bash
   docker run -d --name stratex-mongo -p 27017:27017 mongo:7
   export MONGO_URL="mongodb://127.0.0.1:27017"
   export DB_NAME="stratex_field_test"
   export PASSPORT_TRANSACTIONS_AVAILABLE=0
   pip install motor pymongo
   ```
3. Run live demo:
   ```bash
   python3 -m backend.nextgen.field_test_governed_publish_demo
   ```
4. On success, re-run is idempotent (same `idempotency_key` → duplicate-safe).

## Makefile targets

| Target | Action |
|--------|--------|
| `make field-test-publish-dry` | Pipeline + shape validation, no Mongo |
| `make field-test-publish` | Pipeline + governed publish (needs `MONGO_URL`) |

## Architecture

Core seals via pipeline → Passport stores via governed publish → Habitat reads projections only (not part of this demo).

## Module

`backend/nextgen/field_test_governed_publish_demo.py`
