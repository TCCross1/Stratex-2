# Integration Mission Template (EF-001)

**Role:** Integration
**Authority:** Synchronize lane outputs against accepted main under Atlas merge gate
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY

## Mission identity

- Integration window / date:
- Lanes included:
- Target base (accepted main SHA):
- Atlas merge authorization present? (`ATLAS_MERGE_AUTHORIZATION`):

## Preconditions

1. Each lane completed Builder → Auditor (and Repair if needed).
2. Shared contracts merged or registered before dependent large implementations.
3. Daily synchronization with accepted main already attempted by each lane.
4. Evidence packages exist under `.atlas/evidence/` (gitignored, redacted).

## Integration checklist

1. Confirm no duplicate authority_modules across `engineering/lanes.yaml`.
2. Confirm only LANE_1 owns:
   - `nextgen.passport_service.append_entry`
   - `nextgen.governed_publish_service.governed_publish`
   - `nextgen.approval_policy.evaluate_approval_policy`
3. Resolve shared_paths_requiring_atlas_approval with `ATLAS_ARCHITECTURE_APPROVAL`.
4. Run:

```bash
./stratex verify --architecture
./stratex verify --security
./stratex verify --full
./stratex evidence
./stratex lane list
```

5. Classify missing deps honestly as `INTEGRATION_ENVIRONMENT_UNAVAILABLE`.
6. Keep PRs small; one authority change / one migration / one major state-machine change per PR when possible.

## Conflict policy

- Prefer contract-compatible merges.
- Never silently rewrite Passport history or invent a second writer.
- Habitat integrations remain read-only for canonical Passport truth.
- Scope overrides require `ATLAS_SCOPE_OVERRIDE` JSON:
  `reason`, `changed_paths`, `approving_authority=Atlas`, `evidence_reference`.

## Explicit prohibitions

- No automatic push
- No automatic merge
- No secrets upload to CI artifacts
- No elevation of EF-001 contracts to ACCEPTED without Atlas

## Result

- [ ] Ready for Atlas merge authorization review
- [ ] Blocked — list blockers
- Integration notes / evidence references:
