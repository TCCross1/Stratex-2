# CONTRACT_READINESS — PX-004 / HABITAT-P-002 (Lane 4)

**Lane:** `LANE_4_HABITAT`  
**Mission:** `HABITAT-P-002` homeowner-safe read-model consumer  
**Branch:** `cursor/lane4-habitat-read-model-consumer`  
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY  
**Merge authorization:** Atlas only (`ATLAS_MERGE_AUTHORIZATION`)

## Scope delivered

| Item | Status |
| --- | --- |
| Homeowner-safe property read-model consumer | Implemented (`backend/nextgen/habitat/read_model.py`) |
| Reality-model reference states (`no_scan` → `superseded`) | Implemented (`reality_model.py`) |
| Existing / proposed / completed-as-built separation | Implemented (three isolated layers) |
| Provenance + unknown display rules (`unknown≠0`, `awaiting≠approved`) | Implemented (`display_rules.py`) |
| Report reference consumer (delivery-approved only) | Implemented |
| Estimate summary consumer (no contractor margins) | Implemented |
| Project opportunity status (no unsupported contract/payment claims) | Implemented |
| Privacy redaction of secrets / private costs | Implemented (`privacy.py`) |
| Canonical Passport write authority | **ABSENT** |

## Contracts

| Contract | Registry | Consumer readiness |
| --- | --- | --- |
| `HabitatPropertyProjection` | PROPOSED `0.0.0` | Consumer builds validated instances |
| `HomeownerFindingProjection` | PROPOSED companion | Approved/Resolved only |
| `HomeownerEstimateSummaryProjection` | PROPOSED companion | Honesty states; margins redacted |
| `ReportPublicationReference` | PROPOSED companion | Emitted only when approved for delivery |
| `ProjectOpportunityStatusProjection` | PROPOSED companion | No fabricated contracts/payments |
| `ProjectOpportunityPackage` | NOT_IMPLEMENTED | Status projection only |
| `ReportPublicationPackage` | NOT_IMPLEMENTED | Reference stub only |

**Recommendation:** Keep all Habitat contracts **PROPOSED / NOT_IMPLEMENTED**. Do **not** mark FROZEN or ACCEPTED from this lane. Atlas freeze remains upstream after producer packages (`EstimateResult`, `ReportPublicationPackage`, `ProjectOpportunityPackage`) stabilize.

## Canonical-write confirmation

**ABSENT.** The Habitat consumer package and routes do not import or invoke:

- `append_entry`
- `governed_publish`
- `passport_entries.insert_one` / `property_passports`
- `approval_policy` mutation paths

Proof: `backend/tests/test_habitat_p002_read_model.py` + existing writer-authority tests + `./stratex verify --architecture`.

## schemas/__init__.py

**Not modified** by HABITAT-P-002. Package root already coexists with ATC exports and the `habitat` subpackage from prior waves.

## Verification

```bash
cd /tmp/stratex-px004-lane4
python3 -m pytest backend/tests/test_habitat_p002_read_model.py \
  backend/tests/test_habitat_projection_contracts.py \
  backend/tests/test_writer_authority.py -q
./stratex verify --architecture
```

## Out of scope / forbidden (honored)

- Passport append / governed publish
- Broad Habitat UI redesign
- Fabricated property facts or zero-filled unknowns
- Contractor-private pricing exposure
- Self-authorization of merge / freeze
