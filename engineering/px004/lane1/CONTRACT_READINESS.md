# C-P-004 / PX-004 Lane 1 — Contract Readiness

**Lane:** `LANE_1_CORE_PASSPORT`
**Feature:** C-P-004 Report Publication + Timeline foundation (+ C-P-003 D-001)
**Branch:** `cursor/lane1-cp004-report-publication-timeline`
**Disposition:** `READY_FOR_INTEGRATION_AUDIT`
**Contract freeze claim:** **none** (never `FROZEN` from this lane)

## Summary

Lane 1 ships a bounded **ReportPublicationPackage foundation** and resolves
C-P-003 auditor debt **D-001** (DLQ payload scrubbing). This is implementation
parallelization only — not Atlas contract freeze authority.

| Surface | Status |
|---|---|
| `ReportPublicationPackage` (registry) | remains `NOT_IMPLEMENTED` / `0.0.0` — foundation module does not freeze |
| Package runtime module | `backend/nextgen/report_publication.py` — `PROPOSED` foundation |
| Habitat `ReportPublicationReference` | unchanged companion stub |
| Outbox DLQ scrub (D-001) | **RESOLVED** in `backend/nextgen/outbox_worker.py` |
| Passport writer / governed publisher | **unchanged singularity** |

## D-001 resolution

`_move_to_dead_letter` no longer copies raw `event.payload`. Dead-letter rows
store a recursively sanitized payload with:

- secret key redaction (`password` / `token` / `authorization` / `secret` /
  `api_key` / private-key variants)
- credential URL redaction
- depth + byte bounds
- binary omission
- `payload_truncated` + `payload_checksum` for oversized inputs
- explicit `payload_is_canonical_truth: false`

Replay continues to requeue from durable `outbox_events.payload` and never
treats the scrubbed DLQ copy as canonical truth.

## Authority preserved

| Role | Module |
|---|---|
| Passport ledger writer | `nextgen.passport_service.append_entry` |
| Governed publisher | `nextgen.governed_publish_service.governed_publish` |
| Outbox write-side | `nextgen.outbox.emit_outbox_event` |
| Outbox worker | `nextgen.outbox_worker` (sole delivery worker) |

`report_publication` must not call `append_entry` / `governed_publish` and must
not introduce a second outbox worker. Delivery recovery emits via
`emit_outbox_event` only.

## In scope (this checkpoint)

1. D-001 DLQ recursive sanitize + replay non-canonical law
2. Report publication package states + durable foundation fields
3. Deterministic report cache identity (stable inputs only)
4. Delivery recovery outbox emission (no second worker)
5. Bounded Passport projection + idempotent timeline producers
6. Tests: `backend/tests/test_cp004_report_publication.py` (+ D-001 coverage)
7. This readiness note (`READY_FOR_INTEGRATION_AUDIT`, never `FROZEN`)

## Explicit non-claims

- Not a contract freeze / Atlas acceptance of `ReportPublicationPackage`
- Not production report rendering / PDF engine
- Not Habitat UI delivery
- FakeMongo tests are **simulation**, not live multi-node proof
- Does not alter Passport ledger truth

## Recommendation for Atlas / Integration

**READY_FOR_INTEGRATION_AUDIT** — proceed with cross-lane integration audit of
package field shapes vs Habitat `ReportPublicationReference` and Estimator
handshakes. Do **not** mark registry `ReportPublicationPackage` as `FROZEN`
or `ACCEPTED` from this PR.
