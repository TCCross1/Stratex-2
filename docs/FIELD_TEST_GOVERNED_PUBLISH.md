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
export MISSION_SEAL_KEY="$(openssl rand -hex 32)"   # field-test mission HMAC key
```

`motor` / `pymongo` are required for live mode but are not yet pinned in `requirements.txt`.

### Mission seal key (`MISSION_SEAL_KEY`)

The governed publish demo and **`field_test_pipeline`** resolve the mission package HMAC key as follows:

| Priority | Source | Behavior |
|----------|--------|----------|
| 1 | `MISSION_SEAL_KEY` env var (non-empty) | Used for `seal_package` and `prepare_for_governed_publish` |
| 2 | Fallback | **`field-test-demo-key`** with a **loud stderr warning** (once per process) |

**Field test / live publish:** always export `MISSION_SEAL_KEY` before running without `--dry-run`. Do **not** commit real secrets to the repo.

Generate a dedicated field-test key (example only — use your own value):

```bash
export MISSION_SEAL_KEY="$(openssl rand -hex 32)"
```

Demo JSON output includes `"seal_key_source": "env"` or `"demo_fallback"` so operators can confirm which key was used.

**Note:** Other lab CLIs (`export_sample_habitat_projection`, `field_test_claim_code_demo`, `sample_field_test_package` direct seal) may still use hardcoded demo keys unless updated separately. The **official path** (`field_test_pipeline`, `field_test_governed_publish_demo`) honors `MISSION_SEAL_KEY` as above.

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

---

## Audit reference (field-test governed publish)

### Code map

| Piece | Path | Role |
|-------|------|------|
| HTTP route | `backend/nextgen/routes/publish_routes.py` | `POST /api/nextgen/field-test/publish` |
| Bridge | `backend/nextgen/publish_bridge.py` | `publish_sealed_package()` — validates request, calls governed publish |
| Authority | `backend/nextgen/governed_publish_service.py` | `governed_publish()` → `append_entry()` (sole ledger writer) |
| Handoff builder | `backend/nextgen/mission_to_passport.py` | `prepare_for_governed_publish()` — builds `publication_request` (does not write DB) |
| Demo / validator | `backend/nextgen/field_test_governed_publish_demo.py` | `--dry-run` shape check; live publish when Mongo available |

Route mounts under shared NextGen router prefix: **`POST /api/nextgen/field-test/publish`**.

### Required environment variables

| Variable | Required when | Purpose |
|----------|---------------|---------|
| `MONGO_URL` | Live publish / server | Mongo connection (asserted by `nextgen/db.py`) |
| `DB_NAME` | Live publish / server | Database name (asserted by `nextgen/db.py`) |
| `PASSPORT_TRANSACTIONS_AVAILABLE` | Recommended field test | Set `0` for standalone Mongo; `1` only on replica-set deployments |
| `MISSION_SEAL_KEY` | **Recommended for live publish** | Mission package HMAC key. **`field_test_pipeline`** and **`field_test_governed_publish_demo`** use this when set; otherwise fall back to `field-test-demo-key` with stderr warning. |
| `PASSPORT_SEAL_KEY_VERSION` | Optional dev; required in strict/prod | Passport entry seal key version |
| `PASSPORT_SEAL_KEY_<version>` | With seal version | Passport entry HMAC secret (e.g. `PASSPORT_SEAL_KEY_v1`) |
| `PASSPORT_SEAL_REQUIRED` | Optional | `1` forces Passport entry sealing keys in non-prod |
| `APP_ENV=production` | Production | Enables strict transaction + index enforcement |

**Python packages for live publish:** `motor`, `pymongo` (not pinned in `requirements.txt` today).

### Mongo requirements

- Standalone MongoDB is enough for field-test demo when `PASSPORT_TRANSACTIONS_AVAILABLE=0`.
- Production / strict mode expects replica-set transactions (`PASSPORT_REQUIRE_TRANSACTIONS=1`).
- Collections written on successful append: `nextgen_passports`, `nextgen_passport_entries`, `nextgen_passport_receipts`, `nextgen_passport_idempotency`, `nextgen_audit_events` (and possibly `nextgen_passport_conflicts` on stale writes).

### Exact HTTP request body

`POST /api/nextgen/field-test/publish` (authenticated NextGen session required):

```json
{
  "correlation_id": "field-test-optional-correlation-id",
  "publication_request": {
    "tenant_id": "tenant-stratex-demo",
    "property_id": "prop-1234-infinity-orlando",
    "source_type": "mission_package",
    "source_id": "<package_id uuid>",
    "entry_type": "MISSION_EVIDENCE",
    "idempotency_key": "mission_package:<package_id>:<content_hash_prefix>",
    "expected_revision": 0,
    "expected_head_hash": null,
    "payload": {
      "package_id": "<package_id uuid>",
      "mission_id": "MISSION-2026-0801-FT-001",
      "content_hash": "<sha256 hex>",
      "capture_type": "DAYTIME_PRECISION_MAPPING",
      "geometry_summary": {
        "plane_count": 4,
        "withheld_count": 1
      },
      "awe_summary": {
        "finding_count": 4
      },
      "seal": {
        "seal_algorithm": "HMAC-SHA256",
        "seal_key_version": "v1",
        "content_hash": "<sha256 hex>",
        "signature": "<hmac hex>",
        "sealed_at": "<iso8601>",
        "sealer_identity": "stratex.core.mission_package_seal"
      }
    }
  }
}
```

**Expected-state rules (required before publish):**

- At least one of `expected_revision` or `expected_head_hash` must be present.
- For a **new property** (no prior Passport entries): use `expected_revision: 0` and `expected_head_hash: null` (from `load_expected_state()` / `get_passport_head()`).
- For subsequent publishes: read current head first; stale values → `409 STALE_EXPECTED_STATE`.

Obtain values programmatically:

```python
from backend.nextgen.governed_publish_service import load_expected_state
head = await load_expected_state(tenant_id=..., property_id=...)
# head["revision"], head["head_hash"]
```

### What success looks like

**HTTP / bridge success (`200`):**

```json
{
  "status": "PUBLISHED",
  "result": {
    "status": "COMMITTED",
    "entry": { "canonical_id": "...", "seq": 1, "revision": 1, ... },
    "receipt": { "canonical_id": "...", "commit_status": "COMMITTED", ... },
    "passport": { "revision": 1, "head_hash": "...", ... }
  }
}
```

**Database changes:**

- New row in `nextgen_passport_entries` (`entry_type: MISSION_EVIDENCE`)
- `nextgen_passports.revision` incremented; `head_hash` / `head_entry_id` updated
- Receipt + idempotency records committed
- Audit events: `PUBLICATION_REQUESTED`, `PUBLICATION_COMMITTED`

**Authoritative Habitat projection:**

- Governed publish **does not** automatically emit `habitat.projection.v1` or set `authoritative: true`.
- After Passport commit, export separately via `export_habitat_projection(sealed_pkg, passport_projection=..., authoritative=True)` (or Habitat read API when wired).
- Field-test demo export defaults to `authoritative: false` until Passport write + explicit export step.

### Dry-run validator (no Mongo)

Already implemented — **does not execute publish**:

```bash
make field-test-publish-dry
# exit 0 + "status": "DRY_RUN_OK"  → pipeline + publication_request shape OK
# exit 1  → pipeline or validation failed
```

Validates required keys: `tenant_id`, `property_id`, `source_type`, `source_id`, `entry_type`, `payload`, `idempotency_key`, and payload fields `package_id`, `mission_id`, `content_hash`, `seal`.

