# Stratex High-Velocity Engineering System (EF-001)

**Status:** Established on feature branch · **Production readiness: NOT READY**
**Official law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.

## Permanent productivity doctrine

We will not reduce Stratex quality, completeness, security, architectural
discipline, evidence requirements, testing, or field-validation standards to
move faster.

We will increase productivity through:

1. parallel implementation lanes with centralized architectural authority;
2. contract-first development;
3. specialized Builder, Auditor, and Repair agent roles;
4. permanent reproducible engineering environments;
5. one-command verification;
6. automated Atlas evidence collection;
7. CI-enforced architecture and security boundaries;
8. reusable shared platform services;
9. small daily integration checkpoints;
10. early real-world field validation running alongside software development.

### Operating constitution

1. No quality reduction.
2. No completeness reduction.
3. No security reduction.
4. No architectural-authority duplication.
5. Parallelize implementation, never authority.
6. Contract-first shared development.
7. Builder, Auditor, and Repair agent separation.
8. One canonical owner for each authority module.
9. Small controlled PRs.
10. Daily synchronization with accepted main.
11. Permanent reproducible test infrastructure.
12. Automated evidence generation.
13. CI-enforced architecture boundaries.
14. Shared reusable platform services.
15. Early field validation running in parallel.
16. Explicit handoff and integration contracts.
17. Atlas-controlled merge authorization.

Atlas controls: canonical authority, module boundaries, data contracts, state
machines, security laws, acceptance gates, and merge authorization.
Implementation lanes may execute in parallel only after those boundaries are
frozen.

## Five execution lanes

### LANE 1 — CORE AND PASSPORT INTEGRITY

Owns: canonical Passport services; approval governance; property intelligence;
projections; publication; outbox; audit and timeline.

### LANE 2 — ATC AND FIELD CAPTURE

Owns: 4E mapping missions; 4T AWE missions; readiness; mission orchestration;
evidence manifests; capture-state workflows.

### LANE 3 — ESTIMATOR AND REPORT ENGINE

Owns: construction mathematics; assembly profiles; quantity calculations;
price provenance; estimate ledger; estimate confidence; premium report
composition.

### LANE 4 — HABITAT EXPERIENCE

Owns: homeowner-safe projections; property summary; findings; reports;
estimates; projects; Project Opportunities; homeowner relationship workflows.

### LANE 5 — RUNTIME AND QUALITY ENGINEERING

Owns: transaction-capable Mongo; object storage; CI; deployment; secrets;
environment reproducibility; integration tests; performance and failure
testing; Atlas evidence automation.

### Authority boundaries

- Canonical Passport ledger writer remains solely
  `nextgen.passport_service.append_entry`.
- Governed publication authority remains solely
  `nextgen.governed_publish_service.governed_publish`.
- Habitat remains unable to write canonical Passport truth.
- Shared authority changes require `ATLAS_ARCHITECTURE_APPROVAL`.
- No lane may own another lane’s canonical authority.

Machine-readable registry: `engineering/lanes.yaml`.

## Contract-first development

Shared contracts are registered in `engineering/contracts/` before large
dependent implementations. Unfinished contracts are marked `PROPOSED` or
`NOT_IMPLEMENTED` — never claimed as production contracts during EF-001.

Preferred delivery pattern:

```
contract → service → tests → route → interface → end-to-end proof
```

Preferred operating limits (governance defaults):

- one authority change per PR;
- one migration per PR;
- one major state-machine change per PR;
- generally fewer than 20–25 changed files;
- daily synchronization with accepted main;
- no unreviewed branch drifting for weeks;
- shared contracts merged before dependent large implementations;
- integration tests begin before lane completion.

## One-command verification

```bash
./stratex verify --fast
./stratex verify --full
./stratex verify --architecture
./stratex verify --security
./stratex evidence
./stratex lane list
```

Missing environments and unavailable dependencies are reported honestly.
Unavailable integration proof is classified `INTEGRATION_ENVIRONMENT_UNAVAILABLE`
and is never marked passed.

## Atlas evidence

`./stratex evidence` generates a redacted package under `.atlas/evidence/`
(gitignored). Evidence does not make the final Atlas acceptance decision and
must never include credentials, tokens, environment values, or raw secret
matches.

## Field-validation parallelism (planning only in EF-001)

Software development must not wait until completion to validate:

- real 4E image packages;
- real 4T radiometric packages;
- RTK/control workflow;
- object-storage upload;
- upload duration, file size, battery usage, capture duration;
- evidence completeness, review workload, processing duration;
- operator failure recovery.

Field validation must use governed test properties and must never fabricate
real device evidence. **ATC-001 is not implemented by EF-001.**

## Agent roles

See `engineering/templates/` for Builder, Auditor, Repair, and Integration
mission templates. Builders never self-authorize merge. Auditors remain
read-only. Repair closes only verified findings.

## Out of scope for EF-001

- C-P-003
- ATC-001 feature implementation
- Estimator feature implementation
- Habitat feature implementation
- New Passport authority changes
- Automatic merge or push

Production readiness remains **NOT READY**.
