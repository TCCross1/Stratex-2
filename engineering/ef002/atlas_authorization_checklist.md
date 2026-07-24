# Atlas Authorization Checklist — EF-002

Use this checklist before authorizing any parallel lane start.

## Repository gates

- [ ] `origin/main` contains EF-001 squash (`engineering: establish Stratex high-velocity verification system`)
- [ ] `./stratex verify --architecture` PASS
- [ ] `./stratex verify --security` PASS
- [ ] `./stratex verify --fast` PASS
- [ ] GitHub Actions Stratex Verify workflow PASS on latest main PR activity
- [ ] No duplicate `authority_modules` owners in `engineering/lanes.yaml`
- [ ] Habitat canonical write authority ABSENT

## Contract gates

- [ ] Freeze matrix reviewed (`engineering/ef002/contract_freeze_matrix.yaml`)
- [ ] No contract marked ACCEPTED/FROZEN without Atlas schema review
- [ ] Dependent lanes blocked while required contracts are BLOCKED_UNTIL_ATLAS

## Lane start gates (repeat per lane)

- [ ] Mission packet read and accepted
- [ ] `ATLAS_LANE_START` recorded with lane id, wave, approver, evidence ref
- [ ] Isolated worktree plan via `./stratex lane create … --dry-run`
- [ ] Prohibited paths acknowledged
- [ ] Required tests listed

## Hard stops (instant NO-GO)

- C-P-003 start
- ATC-001 / Estimator / Habitat feature implementation
- New Passport writer or publisher
- Production deployment
- Force-push / admin merge bypass / automatic merge

## Decision

Atlas may mark EF-002 docs:

- ACCEPTED FOR PARALLEL PLANNING
- ACCEPTED WITH NON-BLOCKING DEBT
- CHANGES REQUIRED
- REJECTED

Feature lane coding remains unauthorized until explicit `ATLAS_LANE_START`.
