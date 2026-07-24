# ATC-001B Contract Migration Notes

**Checkpoint:** ATC-001B evidence producer/consumer boundary  
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY  
**Freeze:** Do **not** mark contracts FROZEN / ACCEPTED / PRODUCTION from this lane.

## Alias table (do not silently rename shared contracts)

| ATC-001B name | Binds to | Kind | Notes |
| --- | --- | --- | --- |
| `GeometryCandidate` | `ApprovedGeometryCandidate` (ATC-001A) | Producer alias | Same Pydantic type |
| `AWEEvidenceCandidate` | `AweEvidenceCandidate` (ATC-001A) | Producer alias | Spelling-normalized alias |
| `ApprovedGeometry` | Registry contract `ApprovedGeometry` | Consumer marker | ATC must not emit |
| `ApprovedFinding` | Registry contract `ApprovedFinding` | Consumer marker | ATC must not emit |

## Doctrine

1. Geometry is **not** approved merely because it came from 4E / `M4E_MAPPING` / `M400_P1_MAPPING`.
2. 4T / `M4T_AWE` / `M400_H30T_AWE` are **not** dimensional authority; thermal does **not** change dimensions.
3. Thermal packages must not assert geometry diagnosis; geometry packages must not assert thermal diagnosis.
4. Passport publication (`append_entry` / `governed_publish`) remains LANE_1 only.

## Compatibility

- Contract versions remain `0.0.0` / lifecycle `PROPOSED` or `READY_FOR_FREEZE`.
- Unknown fields are reported by the compatibility validator; they do not auto-freeze schemas.
- Consumers of ATC-001A names remain valid; prefer ATC-001B aliases in new code.

## Collision risk

- Prefer imports from `nextgen.schemas.atc` or `nextgen.atc`.
- Do **not** require edits to `backend/nextgen/schemas/__init__.py` for this checkpoint
  (LANE_4 habitat coexistence on that package root).
