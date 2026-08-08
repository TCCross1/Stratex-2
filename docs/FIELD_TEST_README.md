# Field Test Ready — Branch Guide

**Branch:** `field-test/ready-v1`  
**Repos:** Stratex-2 (Core) · stratex-habitat (Habitat)

## Official path vs lab CLI

| | **Official field path** | **Lab / demo CLI** |
|---|-------------------------|---------------------|
| **Use when** | Field test, API flows, governed publish | Local smoke tests, docs, fast iteration |
| **Entry** | `field_test_pipeline.run_single_path_pipeline()` / `run_dual_path_pipeline()` | `python3 -m backend.nextgen.sample_field_test_package`, `export_sample_habitat_projection`, `field_test_claim_code_demo` |
| **Preflight ATC** | Yes (weather, battery, pilot, etc.) | No (unless you call pipeline yourself) |
| **Pre-seal ATC checklist** (4E day RGB / 4T night thermal) | **Yes — required** | **No — bypassed** |
| **Seal** | Only if checklist passes | Calls `seal_package()` directly |
| **Governed publish** | Use `field_test_governed_publish_demo` (no `--dry-run`) or `POST /api/nextgen/field-test/publish` after pipeline | Not included in direct CLIs |

**Rule:** For anything that represents a real field-test mission (seal → Passport → projection), **must** go through `field_test_pipeline` or an API route that uses it (`/field-test/deliverables`, `/field-test/pipeline/*`, governed publish demo). Lab CLIs that call `seal_package` directly are for development convenience only and **do not** satisfy the ATC pre-seal checklist.

See also: `docs/ATC_SEAL_READINESS_CHECKLIST.md`, `docs/FIELD_TEST_GOVERNED_PUBLISH.md`, `docs/LIVE_CAPTURE_EVIDENCE_CONTRACT.md`, `docs/FIELD_TEST_GO_NO_GO.md`, `docs/HABITAT_FIELD_TEST_HANDOFF.md`.

## Quick start (once backend env is up)

```bash
# ATC readiness
POST /api/nextgen/atc/readiness

# Full contractor package (seal + report + materials + HTML)
POST /api/nextgen/field-test/deliverables
{
  "mission_id": "MISSION-001",
  "property_id": "prop-...",
  "geometry_candidate": {
    "planes": [
      {"id": "front", "confidence": 0.93, "area_sqft": 820},
      {"id": "rear", "confidence": 0.91, "area_sqft": 780}
    ],
    "measurements": {
      "total_roof_area_sqft": 1600,
      "ridge_length_ft": 48,
      "eave_length_ft": 100
    }
  },
  "awe_candidate": {
    "findings": [
      {
        "id": "f1",
        "severity": "HIGH",
        "description": "Granule loss on front slope",
        "location": "Front slope",
        "truth_classification": "ESTIMATED"
      }
    ]
  }
}

# Dual 4E + 4T pair path
POST /api/nextgen/field-test/pipeline/dual
POST /api/nextgen/field-test/deliverables/dual
```

## Module map

| Concern | Module |
|---------|--------|
| Readiness | `atc/readiness.py` |
| Ingest | `evidence_ingest.py` |
| Seal | `mission_package_seal.py` |
| Handoff | `mission_to_passport.py` |
| Pipeline | `field_test_pipeline.py` |
| Report | `report_composer.py`, `report_html.py` |
| Materials | `materials_takeoff.py` |
| Deliverables | `deliverables_package.py` |
| State machine | `mission_state_machine.py` (existing) |
| Publish | `governed_publish_service.py` (existing) |
| Habitat consumer | `stratex-habitat/.../habitat_field_test_projection.py` |

**Habitat team:** start with `docs/HABITAT_FIELD_TEST_HANDOFF.md`.

## Invariants

- One Passport writer
- One governed publisher  
- Habitat read-only
- WITHHELD for low-confidence geometry
- Truth classifications on all scores/findings

## Still required for live flight

1. Mongo transactions + seal keys  
2. Real Matrice media → ingest  
3. Mesh/photogrammetry for interactive 3D assets  
4. Controlled dry-run + Atlas sign-off  
