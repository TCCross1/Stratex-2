# Mission Packet — LANE 4 Habitat Experience (EF-002)

**Lane:** `LANE_4_HABITAT`
**Wave:** W2
**Feature implementation in this packet:** NO

## Mission

Prepare Habitat projection and Project Opportunity contracts. Reaffirm
Habitat cannot write canonical Passport truth.

## Authority

Prohibited: Passport mutation modules. Habitat remains read-projection /
relationship UX owner only.

## Allowed work (planning / contracts only)

- HabitatPropertyProjection / ProjectOpportunityPackage proposals
- Homeowner-safe projection mapping plans
- Integration handshake with Estimator/Passport consumers

## Forbidden

- Habitat feature UX implementation
- Importing `append_entry` / `governed_publish`
- Fabricating homeowner data
- Production deployment

## Required gates before Builder start

1. Upstream PropertyProjection / ApprovedFinding freeze path clear
2. `ATLAS_LANE_START` for LANE_4
3. Architecture verify PASS (Habitat write absent)

## Exit criteria (EF-002 packet)

- Habitat write prohibition still enforced by `./stratex verify --architecture`
- Contracts remain PROPOSED/NOT_IMPLEMENTED unless Atlas freezes later
- No feature code
