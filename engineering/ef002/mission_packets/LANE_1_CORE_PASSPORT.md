# Mission Packet — LANE 1 Core / Passport Integrity (EF-002)

**Lane:** `LANE_1_CORE_PASSPORT`
**Wave:** W1
**Feature implementation in this packet:** NO

## Mission

Prepare contract freeze candidates for `PropertyProjection` and
`ApprovedFinding`. Preserve singular Passport writer and governed publisher.

## Owned authority (do not duplicate)

- `nextgen.passport_service.append_entry`
- `nextgen.governed_publish_service.governed_publish`
- `nextgen.approval_policy.evaluate_approval_policy`

## Allowed work (planning / contracts only)

- Contract proposal docs referencing registry entries
- Test plans for future freeze
- Evidence packages via `./stratex evidence`

## Forbidden

- C-P-003
- New Passport writer/publisher
- Changing OCC / idempotency / SoD laws without Atlas architecture approval
- Habitat or ATC feature code

## Required gates before Builder start

1. Atlas issues `ATLAS_LANE_START` for LANE_1.
2. `./stratex verify --architecture` PASS on current main.
3. Mission packet accepted by Atlas.

## Exit criteria (EF-002 packet)

- Freeze matrix updated only with Atlas-approved status changes
- No product code changes required for packet completion
- Auditor confirms authority singularity unchanged
