# Integration Handshake Template — EF-002

## Purpose

Standardize cross-lane handoffs without duplicating authority.

## Handshake record

```yaml
handshake_id: HS-YYYYMMDD-##
producer_lane: LANE_X
consumer_lane: LANE_Y
contract_id: ContractName
contract_version: "0.0.0"
contract_status: PROPOSED  # must match registry
payload_summary: "non-confidential summary only"
provenance: required
confidence: required
unknown_state_behavior: fail_closed_or_explicit_unknown
producer_evidence_ref: .atlas/evidence/...   # gitignored; cite id only in PRs
consumer_acceptance: PENDING
atlas_approval: REQUIRED_IF_SHARED_AUTHORITY
```

## Rules

1. Consumers must not invent fields absent from the registered contract.
2. Breaking changes require major version + Atlas approval.
3. Habitat consumers remain projection-only.
4. Passport mutation remains LANE_1 only via governed publish → append_entry.
5. Unavailable integration environments are labeled
   `INTEGRATION_ENVIRONMENT_UNAVAILABLE` — never PASS.

## Rehearsal (W3)

Dry-run handshakes for:

- EvidenceManifest → Core/Passport
- ApprovedGeometry → Estimator
- EstimateResult → Habitat
- HabitatPropertyProjection → Habitat UX (later)

No feature code required for rehearsal completion.
