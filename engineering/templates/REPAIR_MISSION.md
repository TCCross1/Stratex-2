# Repair Mission Template (EF-001)

**Role:** Repair
**Authority:** Close only verified Auditor findings — no scope expansion
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY

## Mission identity

- Source Auditor mission / report:
- Lane ID:
- Finding IDs in scope:

## Strict scope

Repair may change only what is required to close listed findings. No opportunistic refactors, no new features, no authority moves.

## Finding closure log

| Finding ID | Root cause | Fix summary | Test proving closure | Status |
| --- | --- | --- | --- | --- |

## Required verification

```bash
./stratex verify --architecture
./stratex verify --security
./stratex verify --fast
./stratex evidence
```

## Closure rules

1. A finding is closed only when a concrete test or architecture/security check proves it.
2. Do not mark unavailable environments as passed.
3. Do not push or merge; return to Auditor for re-review.
4. If a fix requires shared-path or authority change, stop and request `ATLAS_ARCHITECTURE_APPROVAL`.

## Out of scope

- Unrelated lint churn
- Dependency upgrades not required by the finding
- Contract status elevation to ACCEPTED
- Automatic merge authorization

## Handoff back to Auditor

- Remaining open findings:
- New risks introduced:
- Evidence path:
