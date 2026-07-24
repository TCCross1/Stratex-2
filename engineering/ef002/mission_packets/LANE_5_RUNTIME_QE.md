# Mission Packet — LANE 5 Runtime / Quality Engineering (EF-002)

**Lane:** `LANE_5_RUNTIME_QE`
**Wave:** W0
**Feature implementation in this packet:** NO

## Mission

Keep the engineering factory green. Operate verification, CI, and Atlas
evidence. Plan (do not deploy) transaction-capable Mongo and object storage.

## Allowed work

- Maintain `./stratex` and CI workflow health
- Evidence package generation (gitignored)
- Environment readiness checklists
- Integration rehearsal facilitation

## Forbidden

- Installing new project dependencies without Atlas approval
- Production deployment
- Automatic merge
- Owning Passport/ATC/Estimator/Habitat product authority

## Required gates

1. `ATLAS_LANE_START` for LANE_5 (may be standing authorization)
2. `./stratex verify --architecture/--security/--fast` PASS on main

## Exit criteria (EF-002 packet)

- CI architecture/security/fast remain the merge gate for lane PRs
- Evidence automation documented and redacting
- Unavailable environments reported as INTEGRATION_ENVIRONMENT_UNAVAILABLE
