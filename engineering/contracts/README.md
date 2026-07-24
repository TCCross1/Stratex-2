# Stratex shared contracts (EF-001)

Contract-first development is mandatory for shared surfaces across lanes.

## Law

1. Register the contract in `registry.yaml` **before** large dependent implementations.
2. Unfinished contracts are `PROPOSED` or `NOT_IMPLEMENTED` — never claim `ACCEPTED` during EF-001.
3. Atlas is the sole approval authority for shared contracts and breaking changes.
4. Every contract must declare `provenance`, `confidence`, `unknown_state`, `compatibility`, and `breaking_change` rules.
5. Preferred delivery pattern: `contract → service → tests → route → interface → end-to-end proof`.

## Registry

Machine-readable registry: [`registry.yaml`](./registry.yaml).

| Contract | Status | Version |
| --- | --- | --- |
| PropertyProjection | PROPOSED | 0.0.0 |
| ApprovedGeometry | PROPOSED | 0.0.0 |
| EvidenceManifest | PROPOSED | 0.0.0 |
| ApprovedFinding | PROPOSED | 0.0.0 |
| EstimateInputPackage | NOT_IMPLEMENTED | 0.0.0 |
| EstimateResult | NOT_IMPLEMENTED | 0.0.0 |
| EstimateCalculationLedger | NOT_IMPLEMENTED | 0.0.0 |
| ReportPublicationPackage | NOT_IMPLEMENTED | 0.0.0 |
| HabitatPropertyProjection | PROPOSED | 0.0.0 |
| ProjectOpportunityPackage | NOT_IMPLEMENTED | 0.0.0 |

## Consuming a contract

- Lanes may implement against a `PROPOSED` contract only behind feature flags / non-production paths.
- `NOT_IMPLEMENTED` means schema intent only — do not ship dependent production routes.
- Breaking field renames or authority changes require `ATLAS_ARCHITECTURE_APPROVAL`.

## Out of scope for EF-001

Estimator, Habitat feature delivery, ATC-001, and new Passport authority changes are not accepted by registering these contracts.
