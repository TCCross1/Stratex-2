# Mission Packet — LANE 2 ATC / Field Capture (EF-002)

**Lane:** `LANE_2_ATC_FIELD`
**Wave:** W1
**Feature implementation in this packet:** NO

## Mission

Prepare contract freeze candidates for `EvidenceManifest` and
`ApprovedGeometry`. Plan field-validation parallelism without fabricating
device evidence.

## Authority

This lane owns **no** Passport mutation authority. Prohibited paths include
`passport_service.py` and `governed_publish_service.py`.

## Allowed work (planning / contracts only)

- Contract proposals for evidence/geometry packages
- Field-validation checklists for governed test properties
- Mission/orchestration planning notes

## Forbidden

- ATC-001 feature implementation
- Live device evidence fabrication
- Passport ledger writes
- Production deployment

## Required gates before Builder start

1. `ATLAS_LANE_START` for LANE_2
2. W0 runtime gates green
3. Contract freeze matrix reviewed

## Exit criteria (EF-002 packet)

- Evidence/geometry freeze candidates documented
- Field-validation plan remains planning-only
- Auditor confirms no Passport authority contamination
