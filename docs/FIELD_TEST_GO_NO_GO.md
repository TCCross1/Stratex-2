# Field test GO / NO-GO

**Branch:** `field-test/ready-v1`  
**Repo:** Stratex-2 (Core)  
**Date basis:** Audit of code on branch + commands actually run in field-test sessions (Aug 2026)  
**Scope:** Software readiness for first real roof capture — not FAA, weather, pilot currency, or property permission.

---

## 1) Software dry-run status

What exists in the repo and what was **actually executed** in this environment.

| Capability | In repo? | Actually run? | Result |
|------------|----------|---------------|--------|
| **Seal** (`mission_package_seal.py`) | Yes | Yes | Pass — `verify_seal` fixed; lab CLI + pipeline both seal |
| **Handoff** (`mission_to_passport.py`) | Yes | Yes | Pass — `READY_FOR_GOVERNED_PUBLISH`, `publication_request` built |
| **Habitat export (preview)** | Yes | Yes | Pass — `habitat.projection.v1` JSON written locally (`authoritative: false`) |
| **Habitat export (authoritative)** | Yes | Yes (once) | Pass — re-export after live publish: `authoritative: true` when Passport head at **revision 1** |
| **Unit / integration tests** (field-test slice) | Yes | Yes | **25/25 passed** (`test_mission_package_seal`, `test_mission_to_passport`, `test_field_test_pipeline`, `test_passport_property_registry`, `test_atc_seal_readiness`, `test_atc_readiness`, `test_field_test_governed_publish_demo`) |
| **Claim codes** (`passport_property_registry.py`) | Yes | Yes | Pass — demo prints `STRX-…` code; 5 registry tests passed |
| **ATC preflight** (`atc/readiness.py`) | Yes | Yes (via pipeline) | Pass — blocks pipeline when battery/pilot flags fail (tested) |
| **ATC pre-seal checklist** (`atc/seal_readiness.py`) | Yes | Yes (via pipeline only) | Pass — 4E RGB / 4T thermal rules; blocks seal on failure (tested) |
| **Official path** (`field_test_pipeline.py`) | Yes | Yes | Pass — preflight → ingest → pre-seal ATC → seal → report |
| **Governed publish dry-run** (`field_test_governed_publish_demo --dry-run`) | Yes | Yes | Pass — `DRY_RUN_OK`, shape validation only |
| **Governed publish live** | Yes | **Yes (once)** | **Pass** — demo top-level `"status": "SUCCESS"`, inner `"message": "COMMITTED"`, `publish_result.result.status`: **`COMMITTED`**, `receipt.commit_status`: **`COMMITTED`**, passport **revision 1**, entry `01KZH6XKTQ6J5YPGR2XP9S6PTC`, property `prop-1234-infinity-orlando` |
| **`pip install -r backend/requirements.txt`** | Yes | Yes | Pass (after removing invalid `logging==` pin) |
| **Lab CLIs** (`sample_field_test_package`, `export_sample_habitat_projection`, `field_test_claim_code_demo`) | Yes | Yes | Pass — convenience only; **bypass pre-seal ATC** |

**Live publish proof (Aug 2026 session):**

```bash
export PYTHONPATH=/workspace/backend
export MONGO_URL="mongodb://127.0.0.1:27017"
export DB_NAME="stratex_field_test"
export PASSPORT_TRANSACTIONS_AVAILABLE=0
python3 -m backend.nextgen.field_test_governed_publish_demo   # no --dry-run
```

- Demo wrapper: `"status": "SUCCESS"`, `"message": "COMMITTED"`
- Inner ledger: `publish_result.result.status` = **`COMMITTED`**
- Passport head after commit: **revision 1**, `head_hash` set
- Mongo after commit: 1 passport, 1 `MISSION_EVIDENCE` entry (idempotent re-run did not duplicate)
- Authoritative re-export: `export_habitat_projection(..., authoritative=True)` → **`authoritative: true`** when head at revision 1

**Caveats on that proof:** ephemeral local `mongod` (not durable production Mongo); demo uses hardcoded `field-test-demo-key` for pipeline seal (not production `MISSION_SEAL_KEY` wiring); entry `seal_status: UNSEALED_DEV`; HTTP publish route not exercised (Python demo module only).

**Dry-run verdict:** Core software spine (seal → handoff → pipeline ATC → live publish → authoritative re-export) is **exercised and green** in tests, CLIs, and **one live Mongo commit**.

---

## 2) Live flight status

| Area | Status | Facts |
|------|--------|-------|
| **Passport publish** | **Proven once (sample mission)** | `field_test_governed_publish_demo` (no `--dry-run`) returned **`SUCCESS` / `COMMITTED`**, revision **1**. Not repeated on durable/production Mongo or via `POST /api/nextgen/field-test/publish`. |
| **Authoritative projection** | **Proven once (re-export)** | After COMMITTED publish, `export_habitat_projection(..., authoritative=True)` produced `authoritative: true` with passport head at revision 1. Lab CLI still defaults to `authoritative: false`. No Habitat consumer verified. |
| **Real Matrice media ingest** | **Stub only** | `evidence_ingest.py` builds manifest rows from `ingest_media_item()` calls. **No folder scanner**, no DJI export auto-import. Real flight requires manual/scripted hashes + metadata. |
| **Mesh / 3D twin** | **Not present** | `habitat.projection.v1` export sets `twin.mesh_ref: null`. No photogrammetry pipeline in this branch. |
| **Habitat wiring** | **Not in this repo** | Habitat is read-only consumer (`stratex-habitat`). Claim redemption documented; **no Habitat repo or live dashboard hookup verified here**. |
| **Secrets / seal keys** | **Dev defaults** | Governed publish demo uses hardcoded `field-test-demo-key`; `MISSION_SEAL_KEY` env not wired into demo. Passport entry sealing optional unless `PASSPORT_SEAL_REQUIRED` / production. **Production seal key wiring not signed off.** |
| **Mongo / DB** | **Ephemeral local only** | Live proof used local `mongod` on `127.0.0.1:27017` with `DB_NAME=stratex_field_test`. **Durable Mongo** (RT001 replica set, Atlas, transactions) not signed off for field ops. |
| **Dual 4E + 4T pair gate** | **Code + tests only** | `run_dual_path_pipeline` and pair validation exist; **not run against real paired flights**. |

---

## 3) Must-pass checklist before first real roof

Use the **official path** (`field_test_pipeline` or API that delegates to it). Lab CLIs alone do **not** satisfy this list.

### Preflight & capture assembly

- [ ] Pilot authorized, weather/airspace/geofence acceptable (`evaluate_readiness` inputs set honestly)
- [ ] Correct aircraft profile selected (`Matrice_4E` day or `Matrice_4T` night)
- [ ] Real media hashed (SHA-256 of file bytes) and loaded via `ingest_media_item()` — not placeholder hashes
- [ ] 4E: ≥1 RGB manifest item + `geometry_candidate.planes` attached
- [ ] 4T: ≥1 THERMAL or RADIOMETRIC manifest item + `awe_candidate.findings` attached
- [ ] Dual-path property: both 4E and 4T missions completed before pair handoff

### Pipeline & seal (official path)

- [ ] `run_single_path_pipeline` (or `/field-test/deliverables`) returns `success: true`
- [ ] `seal_readiness.ready == true` (pre-seal ATC checklist passed)
- [ ] `sealed_package` non-null; `verify_seal` passes with intended production `MISSION_SEAL_KEY`
- [ ] Low-confidence geometry withheld as expected (`truth_classification: WITHHELD`)

### Passport & downstream

- [x] `MONGO_URL`, `DB_NAME`, `motor`, `pymongo` configured *(proven once on ephemeral local Mongo)*
- [x] Passport head read; `expected_revision` / `expected_head_hash` set on publish request *(revision 0 → 1 on first commit)*
- [x] Governed publish returns **`COMMITTED`** (not dry-run) *(proven once: demo `SUCCESS`, inner `COMMITTED`, revision 1)*
- [ ] Claim code registered for property address if no Habitat owner (`passport_property_registry`) — registry proven in-process; not tied to live publish session
- [x] Habitat projection exported with `authoritative: true` after publish *(proven once via re-export; Habitat consumer not verified)*

### Operational (out of software scope but required for real roof)

- [ ] Property permission, pilot Part 107 / waivers, insurance, site safety — **not covered by this repo**

---

## 4) Are we 100% ready for live field test?

**No. We are not 100% ready for a live field test end-to-end.**

**What we are ready for (software):**

- Sealing sample and pipeline-assembled missions in dev
- Validating Matrice 4E/4T pre-seal checklist on the official path
- Exporting preview `habitat.projection.v1` JSON (`authoritative: false`)
- Minting address-keyed claim codes
- Proving `publication_request` shape via `--dry-run`
- **One live governed publish** to Mongo returning **`SUCCESS` / `COMMITTED`** with passport **revision 1**
- **One authoritative re-export** (`authoritative: true`) after that commit

**What we are not ready for (live field test):**

- Unattended ingest from a real Matrice media folder
- **Durable / production Mongo** signed off for field ops (proof used ephemeral local `mongod`)
- **Production seal key wiring** (`MISSION_SEAL_KEY` not used by governed publish demo today)
- Habitat consumer integration verified in `stratex-habitat`
- Interactive 3D mesh (`mesh_ref` remains null)
- Closing SD card → Passport → authoritative Habitat dashboard without operator scripts and Habitat repo work

**Strict summary:** Core has **proven the publish spine once** (pipeline → governed publish → **`COMMITTED`** at revision 1 → authoritative re-export). A **controlled first flight** still requires real media ingest, durable Mongo, production seal keys, and Habitat consumer work before calling the loop production-ready.

---

## Related docs

- `docs/FIELD_TEST_README.md` — branch guide; official path vs lab CLI
- `docs/LIVE_CAPTURE_EVIDENCE_CONTRACT.md` — 4E/4T evidence requirements
- `docs/ATC_SEAL_READINESS_CHECKLIST.md` — pre-seal checklist
- `docs/FIELD_TEST_GOVERNED_PUBLISH.md` — publish path and dry-run
- `docs/HABITAT_CLAIM_CODE_REDEEM.md` — claim codes and Habitat redemption (design)
- `docs/HABITAT_FIELD_TEST_HANDOFF.md` — stratex-habitat integration handoff
