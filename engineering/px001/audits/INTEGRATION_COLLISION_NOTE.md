# PX-001 Cross-Lane Integration Collision Note

**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY  
**Baseline:** `0c09b0cf44fb133852ddbb9ce96cea2e137ade6d`  
**Date (UTC):** 2026-07-24

## Confirmed colliding paths

| Path | Lanes | Risk | Repair / merge rule |
| --- | --- | --- | --- |
| `backend/nextgen/schemas/__init__.py` | LANE_2, LANE_4 | HIGH add/add | LANE_2 keeps ATC exports + soft `habitat` import; LANE_4 package root only exports `habitat`. Dual-merge resolution must combine both. |
| `engineering/contracts/registry.yaml` | LANE_2, LANE_3, LANE_4 | MEDIUM | Serialize merges; prefer additive schema_location / status notes; never FROZEN without Atlas |
| `engineering/contracts/README.md` | LANE_2, LANE_3 | MEDIUM | Prefer LANE_3 ledger PROPOSED row + LANE_2 schemas/ pointer |
| `engineering/ef002/contract_freeze_matrix.yaml` | LANE_2, LANE_3 | MEDIUM | Keep both EvidenceManifest schema_location notes and EstimateCalculationLedger READY_FOR_FREEZE |

## Recommended merge order (contracts before large dependents)

1. LANE_5 RT-001 (#6) — runtime scaffolding (no business authority)
2. LANE_2 ATC-001A (#9) — EvidenceManifest / geometry candidates
3. LANE_3 Estimator E-001 (#8) — math + ledger PROPOSED
4. LANE_4 Habitat (#10) — habitat schemas; resolve `__init__.py` with LANE_2
5. LANE_1 C-P-003 (#7) — outbox recovery (wants Lane 5 txn env for final acceptance)

**No automatic merge. Independent audits required. Atlas merge authorization required.**

## Auditor dispositions (checkpoint 1)

| Lane | PR | Disposition |
| --- | --- | --- |
| 1 | #7 | Pass with notes |
| 2 | #9 | Pass with notes |
| 3 | #8 | Pass with notes → Repair F-001 NaN/Inf |
| 4 | #10 | Pass with notes → Repair `__init__.py` coexistence |
| 5 | #6 | Pass with notes |
