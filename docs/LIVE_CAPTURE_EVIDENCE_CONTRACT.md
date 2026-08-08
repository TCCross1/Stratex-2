# Live capture evidence contract (field test v1)

**Branch:** `field-test/ready-v1`  
**Audience:** Pilots, field ops, and engineers preparing the **first real Matrice flight**  
**Scope:** Software contract only — what Core expects before seal. This doc does **not** define a photogrammetry or mesh pipeline.

## Where this fits

```
Preflight ATC (atc/readiness.py)
  → evidence ingest (evidence_ingest.py) — assemble mission package from media + candidates
  → pre-seal ATC checklist (atc/seal_readiness.py) — inside field_test_pipeline only
  → seal (mission_package_seal.py)
  → Passport handoff / publish
```

**Official path:** `field_test_pipeline` (or API routes that use it).  
**Lab CLIs** (`sample_field_test_package`, etc.) call `seal_package()` directly and **skip** the pre-seal checklist — see `docs/FIELD_TEST_README.md`.

---

## Matrice 4E — daytime RGB mapping

### Mission profile (software)

| Field | Required value |
|-------|----------------|
| `aircraft_profile` | `Matrice_4E` |
| `mission_type` / `capture_type` | `DAYTIME_PRECISION_MAPPING` |
| Pipeline `kind` | geometry (`geometry_candidate` path) |

### Evidence manifest — required inputs

Each item in `evidence_manifest.items` is built via `ingest_media_item()` (or equivalent dict). Minimum for checklist pass:

| Field | Required | Notes |
|-------|----------|--------|
| `media_type` | **`RGB`** (at least one item) | Case-insensitive in checklist |
| `content_hash` | SHA-256 of file bytes | Sample code uses placeholder if omitted — **live flight must use real file hashes** |
| `capture_timestamp` | ISO-8601 UTC | From image EXIF or flight log |
| `camera_model` | string | e.g. `Matrice 4E Wide` |
| `size_bytes` | integer | Actual file size |
| `geolocation` | optional | Lat/lon if RTK/GPS available |

**Checklist minimum today:** ≥1 manifest item with `media_type: RGB`. More images are expected operationally but not enforced by code yet.

### Geometry candidate — required inputs

| Field | Required | Notes |
|-------|----------|--------|
| `geometry_candidate.planes` | ≥1 plane object | Each plane should include `confidence` (seal withholds if `< 0.65`) |
| `geometry_candidate.measurements` | recommended | Areas, ridge/eave lengths — used in reports, not checked by pre-seal checklist |

Planes are **candidates**, not approved truth. Low-confidence planes are marked `WITHHELD` at seal time and do not count as published geometry.

### Preflight (before capture)

`evaluate_readiness()` blocking checks include: weather, airspace, geofence, battery ≥40%, sensors, storage, network, calibration, RTK, pilot authorization, equipment health, mission plan. Failure stops pipeline before ingest (`state: PREFLIGHT_FAILED`).

---

## Matrice 4T — nighttime thermal AWE

### Mission profile (software)

| Field | Required value |
|-------|----------------|
| `aircraft_profile` | `Matrice_4T` |
| `mission_type` / `capture_type` | `NIGHTTIME_AWE_VISUAL_THERMAL` |
| Pipeline `kind` | awe (`awe_candidate` path) |

### Evidence manifest — required inputs

| Field | Required | Notes |
|-------|----------|--------|
| `media_type` | **`THERMAL`** or **`RADIOMETRIC`** (≥1 item) | RGB reference images may exist on disk but are **not** what the 4T checklist looks for |
| `content_hash` | SHA-256 of file bytes | Real radiometric JPEG/R-JPEG or equivalent |
| `capture_timestamp` | ISO-8601 UTC | Night capture window |
| `camera_model` | string | e.g. `Matrice 4T Thermal` |
| `size_bytes` | integer | Actual file size |
| `geolocation` | optional | If available |

### AWE candidate — required inputs

| Field | Required | Notes |
|-------|----------|--------|
| `awe_candidate.findings` | ≥1 finding object | Each finding should carry `truth_classification` (`ESTIMATED`, `VERIFIED`, etc.) |
| Finding fields | `id`, `severity`, `description` recommended | Seal sets unknown classifications to `UNKNOWN` if missing |

Findings are **candidates** until Passport publish and downstream review. They are not homeowner-authoritative on ingest.

### Dual-path field test

Full property handoff expects **both** a 4E mapping mission and a 4T AWE mission (`run_dual_path_pipeline` + pair validation). Each path has its own manifest and candidate section.

---

## How the checklist fails closed

Pre-seal checks run in `field_test_pipeline` **immediately before** `seal_package()`. All checks are **blocking** (`blocking: true`).

| Stage | If check fails | Result |
|-------|----------------|--------|
| Preflight ATC | Any blocking failure | `success: false`, `state: PREFLIGHT_FAILED`, **no package assembly, no seal** |
| Pre-seal ATC | Any blocking failure | `success: false`, `sealed_package: null`, **seal not attempted** |
| Seal | `SealingError` (missing sections, bad identity) | Exception caught; **no handoff** |
| Handoff | `HandoffError` (invalid seal) | **No publication_request** |

Failure output includes:

- `errors`: e.g. `Pre-seal ATC checklist failed: ['required_evidence_media']`
- `seal_readiness.blocking_failures`: list of failed check names
- `seal_readiness.checks`: per-check pass/fail + detail string

There is **no fallback seal** on checklist failure. Partial packages are not sealed “for debugging” on the official path.

### Pre-seal check names (reference)

1. `aircraft_profile` — must be `Matrice_4E` or `Matrice_4T`
2. `mission_type_profile` — mission type matches aircraft
3. `capture_type` — package metadata matches mission type
4. `required_evidence_media` — correct media types in manifest
5. `required_candidate` — geometry planes (4E) or AWE findings (4T)

---

## Sample / synthetic packages vs real capture folders

### What samples do today

| Aspect | Sample / lab (`sample_field_test_package`, `build_demo_capture_package`) | Real Matrice flight folder |
|--------|---------------------------------------------------------------------------|----------------------------|
| **Media files** | No files on disk; manifest entries only | Folder of `.jpg` / `.JPG` / radiometric images + flight logs |
| **content_hash** | Fixed hex strings or `_sha256_placeholder(label)` | Must be `SHA-256` of each file’s bytes |
| **Ingest path** | Hand-built dicts or `ingest_media_item()` with fake hash | Operator/script must read each file, hash it, call `ingest_media_item(..., content_hash=real_hash)` |
| **Timestamps** | Hard-coded ISO strings | From EXIF or DJI flight record |
| **Geometry** | Hand-authored `planes` + `measurements` | Must be supplied by field analysis step (manual, tooling, or future ingest — **not auto from folder today**) |
| **AWE findings** | Hand-authored list | Must be supplied from thermal analysis step |
| **Folder walk** | **Not implemented** in `evidence_ingest.py` | Expected operationally; software does not scan directories yet |
| **Checklist** | Bypassed if using lab CLI; enforced via `field_test_pipeline` | Must use pipeline for official path |
| **Truth labels** | Mostly `ESTIMATED` | Must be set honestly per finding/plane |

### What `evidence_ingest.py` actually implements

- `ingest_media_item()` — builds one manifest row (metadata + hash)
- `assemble_package_from_capture()` — attaches manifest + optional candidates to a package skeleton
- `build_demo_capture_package()` — synthetic 4E example for tests/demos

It does **not**:

- Read a DJI export directory
- Validate file existence on disk
- Run photogrammetry or auto-extract planes
- Pair RGB ↔ thermal frames (4T ATC-001B fixtures describe that for future quality gates, not this minimal checklist)

### Recommended operator flow for first live flight (manual bridge)

1. Fly 4E (day) or 4T (night) and land with media on disk.
2. For each file: compute SHA-256, build `ingest_media_item(...)` with real metadata.
3. Attach `geometry_candidate` (4E) or `awe_candidate` (4T) from your analysis output.
4. Call `run_single_path_pipeline(...)` with those inputs (or POST to a field-test API that does the same).
5. Confirm `seal_readiness.ready == true` before expecting a seal.
6. Proceed to governed publish separately.

---

## Related docs

- `docs/ATC_SEAL_READINESS_CHECKLIST.md` — checklist detail + official vs lab path
- `docs/MISSION_PACKAGE_SEALING_CONTRACT.md` — sealed package sections
- `docs/FIELD_TEST_GOVERNED_PUBLISH.md` — publish after seal

---

## First live capture — software GO / NO-GO

Software-side only (does not cover weather, FAA, pilot currency, or property permission).

### GO (ready)

- [x] `field_test_pipeline` runs preflight + pre-seal checklist + seal
- [x] 4E / 4T profile rules coded and tested (`test_atc_seal_readiness.py`)
- [x] `evidence_ingest` can assemble packages from explicit media item lists
- [x] Fail-closed behavior verified (checklist failure → no seal)
- [x] Lab vs official path documented
- [x] Governed publish dry-run validates `publication_request` shape

### NO-GO (gaps before relying on software alone for first real flight)

- [ ] **No directory ingest** — real folders must be converted to `ingest_media_item()` calls manually or by a script you provide
- [ ] **No automatic real SHA-256 from disk** in Core — caller must supply `content_hash`
- [ ] **No automatic geometry/AWE extraction** — candidates must be attached separately (not photogrammetry in this branch)
- [ ] **Live governed publish not verified** in all environments — requires `MONGO_URL`, `motor`, `pymongo`, passport head tokens
- [ ] **Minimum media count = 1** — operational flights should use many images; stricter gates may be added later
- [ ] **4T RGB reference pairing** not enforced by pre-seal checklist (only THERMAL/RADIOMETRIC presence)

### Verdict (software only)

**NO-GO for unattended first live capture** — checklist and pipeline are ready, but **real media → manifest → candidates** is still a manual/operator step.

**GO for first live capture with a prepared ingest script** — if the field team supplies real hashes, timestamps, and candidate JSON into `run_single_path_pipeline`, the official path will enforce ATC and fail closed before seal.
