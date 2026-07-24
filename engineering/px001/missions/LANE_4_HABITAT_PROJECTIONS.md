# Mission Record — LANE_4 Habitat Projection Contracts

**Lane:** `LANE_4_HABITAT`
**Mission:** `LANE_4_HABITAT_PROJECTIONS`
**Role:** Builder (implementation only — never authority)
**Branch / worktree:** `cursor/lane4-habitat-projection-contracts` · `/tmp/stratex-lane4`
**Base SHA:** `0c09b0cf44fb133852ddbb9ce96cea2e137ade6d`
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY

## Objective

Prepare Habitat projection consumer contracts and compatibility tests so
Habitat can later render homeowner-safe projections without mutating
canonical Passport truth.

## In scope (contracts / read-only)

1. `HabitatPropertyProjection` executable schema (**PROPOSED**)
2. Homeowner-safe finding projection schema
3. Homeowner-safe estimate-summary projection schema
4. Report-publication reference schema
5. Project-opportunity status projection schema
6. Provenance + confidence display contract with
   `unknown` / `unavailable` / `awaiting_review` honesty states
7. Compatibility + Habitat write-authority ABSENT proofs
8. `backend/tests/test_habitat_projection_contracts.py`

## Out of scope / forbidden

- Canonical Passport writes (`append_entry`, `governed_publish`,
  `passport_entries.insert_one`)
- Marking contracts **FROZEN** / **ACCEPTED**
- Habitat feature UX redesign, proposed-design editing, Homeowner Architect
- Contractor-private pricing exposure
- Fabricated property info
- Push/merge to `main`, force-push, secrets

## Contracts

| Contract / schema | Registry status | Artifact |
| --- | --- | --- |
| HabitatPropertyProjection | PROPOSED 0.0.0 | `engineering/contracts/schemas/habitat/habitat_property_projection.json` + `backend/nextgen/schemas/habitat/property_projection.py` |
| HomeownerFindingProjection | PROPOSED companion | `…/homeowner_finding_projection.json` + `finding_projection.py` |
| HomeownerEstimateSummaryProjection | PROPOSED companion | `…/homeowner_estimate_summary_projection.json` + `estimate_summary.py` |
| ReportPublicationReference | PROPOSED companion (package NOT_IMPLEMENTED) | `…/report_publication_reference.json` + `report_reference.py` |
| ProjectOpportunityStatusProjection | PROPOSED companion (package NOT_IMPLEMENTED) | `…/project_opportunity_status_projection.json` + `opportunity_status.py` |
| Provenance / Confidence / Unknown display | required on all | `common_display.json` + `common.py` |
| ProjectOpportunityPackage | NOT_IMPLEMENTED | registry only — status projection stub only |
| ReportPublicationPackage | NOT_IMPLEMENTED | reference stub only |

### Provenance / confidence / unknown_state

- Provenance identifies `source_type`, `source_id`, `publication_context`,
  optional `passport_revision`, and projector identity
  (`habitat.projection` — never a Passport writer).
- Confidence is display-band only (`high|medium|low|unknown`), inherited or
  reduced for audience — never inflated; no `confidence_pct` /
  `confidence_source` methodology on homeowner payloads.
- Unknown states are explicit: `known`, `unknown`, `unavailable`,
  `awaiting_review`. Non-authoritative states set
  `blocks_authoritative_presentation=true`.

## Habitat write authority

**ABSENT.** `backend/nextgen/routes/habitat.py` and
`backend/nextgen/schemas/habitat/*` must not import or invoke Passport
writers. Enforced by:

- `backend/tests/test_writer_authority.py`
- `backend/tests/test_habitat_projection_contracts.py`
- `./stratex verify --architecture`

## Verification

```text
cd /tmp/stratex-lane4
python3 -m pytest backend/tests/test_habitat_projection_contracts.py \
  backend/tests/test_writer_authority.py -q
```

## Handoff

- Diff: shared Habitat contract schemas + consumer validation tests + this mission record
- Merge authorization: **Atlas only** (`ATLAS_MERGE_AUTHORIZATION`)
- Open risk: upstream `PropertyProjection` / `ApprovedFinding` freeze still
  pending Atlas; EstimateResult / ReportPublicationPackage remain
  NOT_IMPLEMENTED — Habitat must keep honesty states until producers publish
