# C-P-004 / PX-005 Lane 1 — Contract Readiness

**Lane:** `LANE_1_CORE_PASSPORT`
**Feature:** C-P-004 Report Publication + Timeline foundation (+ C-P-003 D-001)
**Branch:** `cursor/lane1-cp004-report-publication-timeline`
**Disposition:** `READY_FOR_INTEGRATION_AUDIT`
**Contract freeze claim:** **none** (never `FROZEN` from this lane)

## Summary

Lane 1 ships a bounded **ReportPublicationPackage foundation**, resolves
C-P-003 auditor debt **D-001** (DLQ payload scrubbing), and closes PX-005
debts A-N-001 through A-N-004 before controlled merge. This is implementation
parallelization only — not Atlas contract freeze authority.

| Surface | Status |
|---|---|
| `ReportPublicationPackage` (registry) | remains `NOT_IMPLEMENTED` / `0.0.0` — foundation module does not freeze |
| Package runtime module | `backend/nextgen/report_publication.py` — `PROPOSED` foundation |
| Habitat-safe field contract | explicit allowlist in module + tests (A-N-002) |
| Report-audit scrub | reuses `outbox_worker.sanitize_dlq_payload` (A-N-001) |
| Delivery consumer | **UNWIRED** — interface + event contract explicit (A-N-003) |
| Outbox DLQ scrub (D-001) | **RESOLVED** in `backend/nextgen/outbox_worker.py` |
| Passport writer / governed publisher | **unchanged singularity** |

## D-001 resolution

`_move_to_dead_letter` no longer copies raw `event.payload`. Dead-letter rows
store a recursively sanitized payload with:

- nested secret-key detection
- list and tuple traversal
- credential-bearing URL redaction
- private-key text redaction
- binary omission
- depth / value-size / collection-size / byte bounds
- `payload_truncated` + `payload_checksum` for oversized inputs
- explicit `payload_is_canonical_truth: false`

Replay continues to requeue from durable `outbox_events.payload` and never
treats the scrubbed DLQ copy as canonical truth.

## A-N-001 — Report-audit payload scrub

`report_publication._audit` reuses the accepted recursive scrub
(`sanitize_dlq_payload`). There is no weaker second sanitizer. Audit records
never store raw report payloads, object-storage credentials, or signed URLs.

## A-N-002 — Habitat field contract

Exact homeowner-safe fields intended for Habitat:

- `report_publication_id`
- `tenant_id`
- `property_id`
- `passport_id`
- `passport_version`
- `report_type`
- `template_version`
- `publication_status`
- `delivery_status`
- `object_reference_safe_id` (opaque; never credential-bearing URL)
- `checksum`
- `generated_at`
- `approved_at` where applicable
- `superseded`
- `homeowner_safe_limitation_summary`

Internal worker, audit-signature, storage-secret, and contractor financial
fields are excluded.

## A-N-003 — Delivery completeness honesty

The delivery consumer remains **UNWIRED** in this checkpoint:

- interface: `consume_report_delivery_event`
- event contract: `REPORT_DELIVERY_REQUESTED` / `0.0.0` / `consumer_status=UNWIRED`
- unwired consume returns `DELIVERY_CONSUMER_UNWIRED`
- unwired path cannot report `DELIVERED`
- complete delivery is **not** claimed
- recovery still uses the singular accepted outbox worker via `emit_outbox_event`

Missing production consumer is an explicit readiness gap.

## A-N-004 — Lane ownership

`engineering/lanes.yaml` registers Lane 1 ownership of
`backend/nextgen/report_publication.py`, C-P-004 tests, and
`engineering/px004/lane1/`. Lane 5 ownership is preserved. No runtime
infrastructure ownership is assigned to Lane 1. No duplicate authority.

## Authority preserved

| Role | Module |
|---|---|
| Passport ledger writer | `nextgen.passport_service.append_entry` |
| Governed publisher | `nextgen.governed_publish_service.governed_publish` |
| Outbox write-side | `nextgen.outbox.emit_outbox_event` |
| Outbox worker | `nextgen.outbox_worker` (sole delivery worker) |

## In scope (this checkpoint)

1. D-001 DLQ recursive sanitize + replay non-canonical law
2. Report-audit recursive scrub reuse (A-N-001)
3. Habitat-safe field allowlist (A-N-002)
4. Unwired delivery honesty (A-N-003)
5. Lane ownership registration (A-N-004)
6. Report publication package states + durable foundation fields
7. Deterministic report cache identity (stable inputs only)
8. Delivery recovery outbox emission (no second worker)
9. Bounded Passport projection + idempotent timeline producers
10. Tests: `backend/tests/test_cp004_report_publication.py`
11. This readiness note (`READY_FOR_INTEGRATION_AUDIT`, never `FROZEN`)

## Explicit non-claims

- Not a contract freeze / Atlas acceptance of `ReportPublicationPackage`
- Not production report rendering / PDF engine
- Not a wired Habitat delivery consumer
- Not complete report delivery (`DELIVERED` not claimed by unwired consumer)
- FakeMongo tests are **simulation**, not live multi-node proof
- Does not alter Passport ledger truth

## Recommendation for Atlas / Integration

**READY_FOR_INTEGRATION_AUDIT** — proceed with controlled squash-merge under
PX-005 after independent audit. Do **not** mark registry
`ReportPublicationPackage` as `FROZEN` or `ACCEPTED` from this PR.
