# Mission Record — ATC-001A first checkpoint (LANE_2_ATC_FIELD)

**Mission ID:** `ATC-001A`
**Lane:** `LANE_2_ATC_FIELD`
**Branch:** `cursor/lane2-atc001a-contract-orchestration`
**Base SHA:** `0c09b0cf44fb133852ddbb9ce96cea2e137ade6d`
**Role:** Builder
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY

## Objective

Deliver the **contract orchestration foundation** for ATC field capture:
aircraft profiles, mission-type / EvidenceManifest executable schemas,
ApprovedGeometry and AWE evidence **candidates**, deterministic mission
state machine, preflight + capture-package contracts, and fixture tests.

## Doctrine encoded

- Matrice 4E — daytime precision mapping (dimensional candidate path).
- Matrice 4T — nighttime AWE visual/thermal (condition evidence path).
- ATC validates **both** before Passport may accept **either**.
- **4T is not** primary dimensional authority; **thermal does not** change dimensions.
- Geometry is **not** approved merely because it came from 4E.
- Future profile stubs: `M400_P1_MAPPING`, `M400_H30T_AWE`.

## In scope (this checkpoint)

- `backend/nextgen/aircraft_profiles.py`
- `backend/nextgen/mission_state_machine.py`
- `backend/nextgen/schemas/*` (pydantic executable schemas)
- `engineering/contracts/schemas/*` (JSON Schema mirrors)
- `backend/tests/test_atc001a_contract_orchestration.py`
- Registry notes / `schema_location` for EvidenceManifest + ApprovedGeometry
  (status remains **PROPOSED** / freeze matrix **READY_FOR_FREEZE**)

## Out of scope / explicit non-claims

- Real DJI SDK integration
- Physical capture / live device preflight
- RTK accuracy claims
- Production-approved geometry
- Automated thermal diagnosis
- Production flight authority
- Passport publication (`append_entry` / `governed_publish`) — LANE_1 only
- Estimate calculations — LANE_3
- Habitat canonical state — LANE_4
- Production deployment / merge to main / force-push

## Contract statuses

| Contract | Registry status | Freeze gate | Notes |
| --- | --- | --- | --- |
| EvidenceManifest | PROPOSED | READY_FOR_FREEZE | schema_location set; executable pydantic + JSON Schema |
| ApprovedGeometry | PROPOSED | READY_FOR_FREEZE | **candidate** schema only; not production-approved |
| AweEvidenceCandidate | PROPOSED (lane-local) | READY_FOR_FREEZE | not a Passport writer input by itself |
| MissionType / Preflight / CapturePackage | PROPOSED | READY_FOR_FREEZE | ATC orchestration support contracts |

**Never mark FROZEN / ACCEPTED / PRODUCTION without Atlas.**

## Architecture guards

- ATC modules must not import or call Passport writers.
- Candidate schemas forbid `is_production_approved=True` and 4E-implies-approved.
- State machine raises `AuthorityViolation` on Passport write or fabricated approval.

## Tests

```bash
pytest backend/tests/test_atc001a_contract_orchestration.py -q
```

## Blockers / handoff

1. Atlas contract freeze still required before large dependent Passport consumers.
2. Live field validation packages remain future work (governed test properties only).
3. Pair-gate handoff to LANE_1 is readiness signaling only — no ledger write from ATC.
4. Auditor review required before merge authorization.

## Handoff

Builder does **not** self-authorize merge. Push branch only; Atlas / merge gate owns promotion.
