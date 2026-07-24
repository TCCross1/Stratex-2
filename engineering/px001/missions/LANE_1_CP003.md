# Mission Record — LANE_1 C-P-003 Publication Recovery (checkpoint 1)

**Role:** Builder  
**Lane:** `LANE_1_CORE_PASSPORT`  
**Feature:** C-P-003 (first checkpoint ONLY)  
**Branch / worktree:** `cursor/lane1-cp003-publication-recovery` @ `/tmp/stratex-lane1`  
**Base SHA:** `0c09b0cf44fb133852ddbb9ce96cea2e137ade6d`  
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY

## Objective

Ship the bounded durable-delivery foundation for Passport publication recovery:
outbox claim/delivery, backoff, dead-letter, safe replay, backlog health, and
projection reconciliation *stubs* — without a second event/Passport authority.

## Authority preserved (singular)

| Role | Module |
|---|---|
| Passport ledger writer | `nextgen.passport_service.append_entry` |
| Governed publisher | `nextgen.governed_publish_service.governed_publish` |

C-P-003 modules (`outbox_worker`, `projection_reconciliation`) must not call
`append_entry`, `governed_publish`, or `passport_entries.insert_one`.

## In scope (this checkpoint)

1. Outbox worker: idempotent claim, delivery attempts, backoff, dead-letter, inbox receipts
2. Safe replay of dead-lettered / failed events
3. Projection reconciliation stubs (interfaces + FakeMongo tests; no fabricated property truth)
4. Health / readiness helpers for outbox backlog
5. Audit evidence hooks (structured status; no secrets)
6. Tests: `backend/tests/test_cp003_publication_recovery.py`
7. Keep `emit_outbox_event` API stable (`backend/nextgen/outbox.py` write-side)

## Out of scope

- Report rendering, DJI, Estimator, Habitat UI
- Second event authority / broker introduction
- Fabricating Habitat projections or property truth
- Merge / push to `main` / force-push / secrets

## Implementation map

| Path | Purpose |
|---|---|
| `backend/nextgen/outbox.py` | Write-side emit (API stable); lease fields aligned |
| `backend/nextgen/outbox_worker.py` | Claim, deliver, DLQ, replay, health, audit |
| `backend/nextgen/projection_reconciliation.py` | Reconciler port + stub |
| `backend/tests/test_cp003_publication_recovery.py` | FakeMongo unit coverage |
| `engineering/px001/missions/LANE_1_CP003.md` | This mission record |

## Verification

```bash
python3 -m pytest backend/tests/test_cp003_publication_recovery.py backend/tests/test_writer_authority.py -q
./stratex verify --architecture --security
```

## Exit criteria (checkpoint 1)

- [x] Worker + replay + DLQ + receipts implemented behind FakeMongo tests
- [x] Projection reconciler is stub-only (insufficient_data when markers missing)
- [x] Writer-authority tests still pass
- [x] No Habitat / Estimator / DJI / report-render feature work
- [ ] Atlas / Auditor review (not Builder authority)

## Explicit non-claims

FakeMongo concurrency and delivery proofs are **simulation**, not production
transaction or multi-node lease proof. Full Habitat projection sync is deferred.
