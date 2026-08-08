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
| **Habitat export** (`habitat_projection_export.py`) | Yes | Yes | Pass — `habitat.projection.v1` JSON written locally (`authoritative: false`) |
| **Unit / integration tests** (field-test slice) | Yes | Yes | **25/25 passed** (`test_mission_package_seal`, `test_mission_to_passport`, `test_field_test_pipeline`, `test_passport_property_registry`, `test_atc_seal_readiness`, `test_atc_readiness`, `test_field_test_governed_publish_demo`) |
| **Claim codes** (`passport_property_registry.py`) | Yes | Yes | Pass — demo prints `STRX-…` code; 5 registry tests passed |
| **ATC preflight** (`atc/readiness.py`) | Yes | Yes (via pipeline) | Pass — blocks pipeline when battery/pilot flags fail (tested) |
| **ATC pre-seal checklist** (`atc/seal_readiness.py`) | Yes | Yes (via pipeline only) | Pass — 4E RGB / 4T thermal rules; blocks seal on failure (tested) |
| **Official path** (`field_test_pipeline.py`) | Yes | Yes | Pass — preflight → ingest → pre-seal ATC → seal → report |
| **Governed publish dry-run** (`field_test_governed_publish_demo --dry-run`) | Yes | Yes | Pass — `DRY_RUN_OK`, shape validation only |
| **Governed publish live** | Yes (code) | **No** | **Not run** — `MONGO_URL` unset, `motor`/`pymongo` not installed |
| **`pip install -r backend/requirements.txt`** | Yes | Yes | Pass (after removing invalid `logging==` pin) |
| **Lab CLIs** (`sample_field_test_package`, `export_sample_habitat_projection`, `field_test_claim_code_demo`) | Yes | Yes | Pass — convenience only; **bypass pre-seal ATC** |

**Dry-run verdict:** Core software spine (seal → export → claim code → pipeline ATC) is **exercised and green** in tests and CLIs. Governed publish to Passport is **not** proven live in this environment.

---

## 2) Live flight status

| Area | Status | Facts |
|------|--------|-------|
| **Passport publish** | **Not proven live** | `publish_bridge` → `governed_publish_service` exists; `POST /api/nextgen/field-test/publish` registered. Live demo returned `MONGO_UNAVAILABLE`. Dry-run validates `publication_request` only. |
| **Real Matrice media ingest** | **Stub only** | `evidence_ingest.py` builds manifest rows from `ingest_media_item()` calls. **No folder scanner**, no DJI export auto-import. Real flight requires manual/scripted hashes + metadata. |
| **Mesh / 3D twin** | **Not present** | `habitat.projection.v1` export sets `twin.mesh_ref: null`. No photogrammetry pipeline in this branch. |
| **Habitat wiring** | **Not in this repo** | Habitat is read-only consumer (`stratex-habitat`). Claim redemption documented; **no Habitat repo or live dashboard hookup verified here**. |
| **Secrets / seal keys** | **Dev defaults** | `MISSION_SEAL_KEY` defaults to insecure dev key. Passport entry sealing optional unless `PASSPORT_SEAL_REQUIRED` / production. **Production seal keys not configured in field-test sessions.** |
| **Mongo / DB** | **Not available in audit env** | `MONGO_URL` / `DB_NAME` unset. Transaction-capable Mongo not exercised. |
| **Authoritative projection** | **Not achieved** | Exports use `authoritative: false` until Passport publish + explicit authoritative export. |
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
- [ ] `sealed_package` non-null; `verify_seal` passes with intended `MISSION_SEAL_KEY`
- [ ] Low-confidence geometry withheld as expected (`truth_classification: WITHHELD`)

### Passport & downstream

- [ ] `MONGO_URL`, `DB_NAME`, `motor`, `pymongo` configured
- [ ] Passport head read; `expected_revision` / `expected_head_hash` set on publish request
- [ ] Governed publish returns `COMMITTED` (not dry-run)
- [ ] Claim code registered for property address if no Habitat owner (`passport_property_registry`)
- [ ] Habitat projection exported or consumed with correct `authoritative` flag after publish

### Operational (out of software scope but required for real roof)

- [ ] Property permission, pilot Part 107 / waivers, insurance, site safety — **not covered by this repo**

---

## 4) Are we 100% ready for live field test?

**No. We are not 100% ready for a live field test end-to-end.**

**What we are ready for (software dry-run):**

- Sealing sample and pipeline-assembled missions in dev
- Validating Matrice 4E/4T pre-seal checklist on the official path
- Exporting non-authoritative `habitat.projection.v1` JSON
- Minting address-keyed claim codes
- Proving `publication_request` shape via `--dry-run`

**What we are not ready for (live field test):**

- Unattended ingest from a real Matrice media folder
- Proven governed publish to Mongo / Passport in a configured environment
- Authoritative Habitat projection after publish
- Interactive 3D mesh (`mesh_ref` remains null)
- Habitat consumer integration verified in `stratex-habitat`
- Production seal keys and transaction-capable Mongo signed off

**Strict summary:** Software supports a **controlled first flight** only if the field team supplies a **manual or custom ingest script** (real file hashes + candidate JSON) and runs the **official pipeline**, then completes **live publish setup** separately. The repo alone does not close the loop from SD card → Passport → authoritative Habitat without additional operator steps and infrastructure not yet verified here.

---

## Related docs

- `docs/FIELD_TEST_README.md` — branch guide; official path vs lab CLI
- `docs/LIVE_CAPTURE_EVIDENCE_CONTRACT.md` — 4E/4T evidence requirements
- `docs/ATC_SEAL_READINESS_CHECKLIST.md` — pre-seal checklist
- `docs/FIELD_TEST_GOVERNED_PUBLISH.md` — publish path and dry-run
- `docs/HABITAT_CLAIM_CODE_REDEEM.md` — claim codes and Habitat redemption (design)
