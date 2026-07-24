# Builder Mission Template (EF-001)

**Role:** Builder
**Authority:** Implementation only — never merge authorization
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY

## Mission identity

- Lane ID:
- Mission title:
- Branch / worktree:
- Related contracts (from `engineering/contracts/registry.yaml`):
- Atlas approval token required? (`ATLAS_ARCHITECTURE_APPROVAL` / none):

## Objective

One sentence describing the single implementation outcome.

## In scope

- Owned paths only (see `engineering/lanes.yaml`)
-

## Out of scope

- Authority modules owned by another lane
- Shared paths requiring Atlas approval (unless token present)
- Merge, push, or production promotion
-

## Contracts

- Contract name / version / status:
- Provenance / confidence / unknown_state handled how:

## Implementation checklist

1. Confirm lane owned_paths and prohibited_paths.
2. Confirm no duplicate ownership of authority modules.
3. Implement behind the registered contract.
4. Add or update required_tests for this lane.
5. Run `./stratex verify --architecture` and `./stratex verify --security`.
6. Run `./stratex verify --fast` (or `--full` when environment is available).
7. Generate evidence with `./stratex evidence` (redacted; no secrets).
8. Hand off to Auditor — do **not** self-authorize merge.

## Explicit prohibitions

- Do not call `passport_entries.insert_one` outside `passport_service`.
- Do not invent a second `append_entry` / `governed_publish` / approval-policy owner.
- Habitat builders must not write canonical Passport truth.
- Do not push or merge automatically.
- Do not track `.env` or upload secrets into evidence/CI artifacts.

## Handoff package

- Diff summary:
- Tests run / results:
- Evidence path under `.atlas/evidence/`:
- Open risks / unknown_state:
- Auditor request notes:
