# ATC pre-seal readiness checklist (field test v1)

**Branch:** `field-test/ready-v1`  
**Scope:** Matrice 4E and 4T missions processed through `field_test_pipeline` only.

## Purpose

Before Core seals a mission package, ATC runs a **minimum checklist** to confirm the capture path matches the aircraft and that stub/real evidence is present. If any blocking check fails, **seal does not run**.

This is separate from the preflight gate (weather, battery, pilot authorization). Preflight runs at mission start; this checklist runs **after capture assembly, immediately before seal**.

## Checklist (plain language)

### Matrice 4E — daytime RGB mapping

| Check | Pass when |
|-------|-----------|
| Aircraft profile | Profile is `Matrice_4E` |
| Mission type | `DAYTIME_PRECISION_MAPPING` (daytime precision mapping) |
| Capture type in package | Same as mission type above |
| Required evidence | At least one **RGB** image in the evidence manifest (stub hashes OK) |
| Required candidate | At least one **geometry plane** in `geometry_candidate` |

### Matrice 4T — nighttime thermal AWE

| Check | Pass when |
|-------|-----------|
| Aircraft profile | Profile is `Matrice_4T` |
| Mission type | `NIGHTTIME_AWE_VISUAL_THERMAL` (nighttime visual + thermal AWE) |
| Capture type in package | Same as mission type above |
| Required evidence | At least one **THERMAL** or **RADIOMETRIC** item in the evidence manifest |
| Required candidate | At least one **AWE finding** in `awe_candidate` |

## What happens on failure

- Pipeline returns `success: false`
- `sealed_package` stays `null` (no seal attempted)
- Error message includes failed check names, e.g. `Pre-seal ATC checklist failed: ['required_evidence_media']`
- Response includes `seal_readiness` with per-check detail

## What this does NOT do

- No UI, no drone launch, no Passport write
- Does not replace full ATC-001B quality gates or live DJI SDK checks
- Does not run outside `field_test_pipeline` (sample CLIs that call `seal_package` directly are unchanged)

## Code locations

- Checklist: `backend/nextgen/atc/seal_readiness.py` → `evaluate_seal_readiness()`
- Wired in: `backend/nextgen/field_test_pipeline.py` (before `seal_package`)
- Tests: `backend/tests/test_atc_seal_readiness.py`, `backend/tests/test_field_test_pipeline.py`

## Example pipeline call

```python
from backend.nextgen.field_test_pipeline import run_single_path_pipeline
from backend.nextgen.evidence_ingest import ingest_media_item

result = run_single_path_pipeline(
    mission_id="m-4e-001",
    tenant_id="tenant-demo",
    property_id="prop-001",
    mission_type="DAYTIME_PRECISION_MAPPING",
    aircraft_profile="Matrice_4E",
    media_items=[
        ingest_media_item("RGB", "2026-08-01T14:00:00Z", "Matrice 4E Wide", 8_000_000),
    ],
    geometry_candidate={"planes": [{"id": "front", "confidence": 0.9, "area_sqft": 500}]},
)
# result.seal_readiness["ready"] == True when checklist passes
```
