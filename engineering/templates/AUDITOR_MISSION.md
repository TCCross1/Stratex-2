# Auditor Mission Template (EF-001)

**Role:** Auditor
**Authority:** Read-only verification — no implementation edits unless separately chartered as Repair
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY

## Mission identity

- Target lane / PR / branch:
- Builder mission reference:
- Contracts under review:

## Audit posture

- Read-only inspection of code, tests, evidence, and lane boundaries
- No merge authorization (Atlas only: `ATLAS_MERGE_AUTHORIZATION`)
- No silent scope expansion into `.emergent/`, `test_reports/`, `.env`, or screenshots without `ATLAS_SCOPE_OVERRIDE`

## Verification commands

```bash
./stratex verify --architecture
./stratex verify --security
./stratex verify --fast
./stratex evidence
./stratex lane status <LANE_ID>
```

Unavailable integration environments must be classified `INTEGRATION_ENVIRONMENT_UNAVAILABLE` — never marked passed.

## Checklist

1. Lane owned_paths respected; prohibited_paths untouched.
2. Authority modules remain solely on LANE_1:
   - `nextgen.passport_service.append_entry`
   - `nextgen.governed_publish_service.governed_publish`
   - `nextgen.approval_policy.evaluate_approval_policy`
3. `MODULE_IDENTITY` remains `nextgen.governed_publish_service`.
4. Findings/Intelligence use approval_policy + governed_publish only.
5. Habitat has no Passport write path.
6. Frontend has no Passport write path.
7. Contracts remain `PROPOSED` or `NOT_IMPLEMENTED` at `0.0.0` unless Atlas accepted otherwise.
8. Security: no tracked `.env`, no default auth bypass, no hardcoded seal secret.
9. Evidence package is redacted (no env values, tokens, or Mongo URLs).

## Findings format

| ID | Severity | Path | Finding | Evidence | Required repair |
| --- | --- | --- | --- | --- | --- |

## Disposition

- [ ] Pass with notes
- [ ] Fail — send to Repair
- [ ] Block — Atlas architecture decision required

Auditor signature / timestamp:
