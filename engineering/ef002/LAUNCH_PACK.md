# EF-002 — Parallel Execution Launch Pack

**Status:** Planning / contract-governance / scheduling checkpoint
**Baseline main:** `63164e85d8168d6abea46a040368f15c9fd48354` (EF-001 squash)
**Production readiness:** NOT READY

**Official law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.

## Purpose

This pack authorizes **governed parallel planning** for Stratex execution lanes
after EF-001. It does **not** implement product features.

### Explicitly out of scope

- ATC-001 feature implementation
- Estimator feature implementation
- Habitat feature implementation
- C-P-003
- New Passport authority
- Production deployment
- Automatic merge or push

## Preconditions (satisfied)

1. C-P-002 / C-P-002A closed on main (`b877f46`).
2. EF-001 closed on main (`63164e8`) with local + GitHub Actions proof.
3. One-command verification (`./stratex`) available on main.
4. Five lanes registered in `engineering/lanes.yaml`.
5. Contract registry present; unfinished contracts are `PROPOSED` /
   `NOT_IMPLEMENTED` only.

## Parallelization rules

1. Implementation lanes may start **only** after Atlas freezes the relevant
   contracts and authority boundaries.
2. No lane may own another lane’s canonical authority.
3. Shared path edits require `ATLAS_ARCHITECTURE_APPROVAL`.
4. Each lane works on an isolated branch/worktree via
   `./stratex lane create … --dry-run` then `--confirm`.
5. Daily sync with accepted main; no multi-week unreviewed drift.
6. Builders never self-authorize merge. Auditors remain read-only.
7. Integration handoffs use registered contracts only.

## Launch sequence

```
Atlas contract freeze (per packet)
→ Builder mission packet accepted
→ Isolated lane worktree/branch
→ contract → service → tests → route → interface → e2e proof
→ Auditor packet
→ Repair (if required)
→ Integration handshake
→ Atlas merge authorization
```

Preferred PR limits remain EF-001 defaults (one authority change, one
migration, generally <20–25 files, daily sync).

## Pack contents

| Path | Role |
|------|------|
| `engineering/ef002/LAUNCH_PACK.md` | This document |
| `engineering/ef002/contract_freeze_matrix.yaml` | Contract readiness / freeze gates |
| `engineering/ef002/schedules/parallel_waves.yaml` | Wave schedule and dependencies |
| `engineering/ef002/mission_packets/*.md` | Per-lane Builder launch packets |
| `engineering/ef002/atlas_authorization_checklist.md` | Atlas go / no-go gates |
| `engineering/ef002/integration_handshake.md` | Cross-lane handshake template |

## Field validation (planning only)

Field validation may run **in parallel** with software work using governed
test properties. Do not fabricate device evidence. ATC-001 remains
**NOT STARTED** as feature implementation.

## Atlas action

**STOP — EF-002 MERGE NOT AUTHORIZED PENDING ATLAS REVIEW** until this launch
pack is accepted. Even after merge of EF-002 docs, feature lanes remain
blocked until Atlas issues explicit per-lane start authorization.
