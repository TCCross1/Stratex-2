# Property Intelligence Engine (PIE) — Phase 3

**Status:** Delivered · Feb 2026 (Directive 009)
**Scope:** Findings model, approval workflow, Passport rule enforcement,
homeowner-safe projections, reusable summary component.

> The Property Intelligence Engine (PIE) is the single, authoritative
> source of truth for property findings. Reports, Passports, AWE
> aggregates, timeline, and homeowner Habitat projections all read from
> the PIE. Nothing else authors these facts.

## 1. Pipeline

The end-to-end lifecycle a finding travels through:

```
Mission → Evidence → (Vision Grounding — future) → Manual Analyst Draft
     │
     ▼
 DRAFT ──submit──▶ PENDING_REVIEW ──approve──▶ APPROVED ──resolve──▶ RESOLVED
                          │                        │
                          └──reject──▶ REJECTED    └──supersede──▶ SUPERSEDED
                                                                (via new APPROVED finding)
```

## 2. Data Model — `nextgen_findings`

| Field | Type | Notes |
|---|---|---|
| `canonical_id` | ULID | Server-issued |
| `tenant_id` | string | Multi-tenant scope |
| `property_id` | string | **Required** |
| `job_id` / `mission_id` | string? | Optional bindings |
| `evidence_ids` | list<str> | Optional. Empty = MANUAL OBSERVATION |
| `taxonomy_category` | string | Building system (`ROOF`, `DRAINAGE`, …) |
| `taxonomy_component` | string? | Component within category |
| `severity` | enum | `INFORMATIONAL`…`CRITICAL` |
| `priority` | enum | `MONITOR`…`IMMEDIATE` |
| `risk_tier` | derived | From severity |
| `description` | string | Human observation |
| `confidence_pct` | float? | Only when `confidence_source` is set |
| `confidence_source` | string? | e.g. `human_field_observation` |
| `manual_observation` | bool | True when no evidence linked |
| `status` | enum | `DRAFT`/`PENDING_REVIEW`/`APPROVED`/`REJECTED`/`RESOLVED`/`SUPERSEDED` |
| `version` | int | Increments across supersession |
| `author_id`, `author_role` | string | Creator |
| `approval` | object? | Populated on approve: `{reviewer_id, reviewer_role, at, signature, notes}` |
| `rejected` | object? | Populated on reject |
| `resolved_at` | ISO ts? | Populated on resolve |
| `passport_entry_id` | string? | Set when Passport append succeeds |
| `passport_seq`, `passport_content_hash` | Passport receipt |
| `supersedes_finding_id` / `superseded_by_finding_id` | Supersession links |
| `review_history` | list<object> | Append-only audit trail on the finding |
| `content_hash` | sha256 | Over stable identity fields |
| `habitat_visible`, `insurance_relevant` | bool | Projection flags |

## 3. Approval Authority (Phase 3 Mandate)

| Role | Create Draft | Submit | Approve | Reject | Resolve | Supersede |
|---|---|---|---|---|---|---|
| CEO | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GM | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Contractor | ✅ (own tenant) | ✅ | ❌ | ❌ | ❌ | draft-only |
| Operator / Pilot | ✅ (submit for review) | ✅ | ❌ | ❌ | ❌ | draft-only |
| Insurance / Adjuster | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### Separation of Duties (SoD)

The finding **author cannot approve or reject their own finding**. A
different authorized reviewer (CEO / Admin / GM) must act. There is no
self-approval bypass in Phase 3.

## 4. Passport Rule (Absolute)

Only **APPROVED** findings become Passport-eligible.

On approval the endpoint atomically:
1. Signs the finding: `sha256(content_hash + reviewer_id + timestamp)`.
2. Appends a hash-chained `INTELLIGENCE_APPROVED` entry to the
   `nextgen_passport_entries` ledger via `passport_service.append_entry`.
3. Records the resulting passport `seq` and `content_hash` back on the
   finding.
4. Writes a `INTELLIGENCE_APPROVED` timeline entry with the passport link.
5. Enqueues a durable outbox event `FINDING_APPROVED` (idempotent).
6. Writes an audit event.

If any of these fail the state transition fails (no half-applied writes).

### Prohibited Effects on the Passport

`DRAFT`, `PENDING_REVIEW`, `REJECTED`, and `RESOLVED`-without-approval and
`SUPERSEDED` transitions **never** modify the Passport ledger. Supersession
does append a `SUPERSEDE_FINDING` entry — but only after the *new*
finding has been approved by a different authorized reviewer.

## 5. Immutability After Approval

Approved findings cannot be edited. Substantive changes require:

1. `POST /findings/{id}/supersede` — creates a new **DRAFT** linked to
   the prior via `supersedes_finding_id`.
2. Independent `submit` → `approve` on the new finding.
3. On approve, the prior finding is transitioned to `SUPERSEDED`, its
   `superseded_by_finding_id` is set, and a `SUPERSEDE_FINDING` entry is
   appended to the Passport ledger.

## 6. Habitat / Homeowner Projections (Safe Subset)

`GET /findings/habitat-projection` and `intelligence-summary?audience=homeowner`
return only homeowner-safe fields:

| Included | Excluded |
|---|---|
| `canonical_id`, `taxonomy_*`, `severity`, `priority`, `description`, `status`, `approved_at`, `manual_observation` | reviewer identity, review notes, confidence methodology, contractor pricing, insurance-only fields, ai reasoning, audit internals |

## 7. Endpoint Surface (`/api/nextgen/v1/*`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/findings` | Create DRAFT |
| PATCH | `/findings/{id}` | Edit DRAFT only |
| POST | `/findings/{id}/submit` | DRAFT → PENDING_REVIEW |
| POST | `/findings/{id}/approve` | PENDING_REVIEW → APPROVED (+ Passport append) |
| POST | `/findings/{id}/reject` | PENDING_REVIEW → REJECTED |
| POST | `/findings/{id}/resolve` | APPROVED → RESOLVED |
| POST | `/findings/{id}/supersede` | Draft a replacement for APPROVED/RESOLVED |
| GET | `/properties/{id}/findings` | List with optional `?status=` filter |
| GET | `/findings/{id}` | Detail (with review history + approval receipt) |
| GET | `/properties/{id}/intelligence-summary` | Aggregate for PIE Summary UI component |
| GET | `/properties/{id}/findings/habitat-projection` | Homeowner-safe projection |

## 8. Reusable Frontend Component — `<PropertyIntelligenceSummary />`

Rendered on every Property Workspace destination that surfaces PIE state
(Overview · Findings · Passport · Reports). Never fabricates data. When
no findings exist it shows `NOT YET ANALYZED`. When no approved findings
exist it renders a persistent banner: *"the Passport cannot be updated
until a CEO / Admin / GM approves a finding."*

Homeowner audience receives only approved counts and severity breakdowns
— no draft / pending totals, no reviewer names, no confidence numbers.

## 9. Tests — `/app/backend/tests/test_pie_lifecycle.py`

- `TestLifecycleHappyPath` — DRAFT → PENDING_REVIEW; author cannot self-approve.
- `TestApprovalRequiresSecondAuthorizedReviewer` — role gate proof.
- `TestRoleBasedApprovalGate` — contractor / operator / pilot cannot approve.
- `TestPassportRuleEnforcement` — pending / rejected findings do not touch Passport.
- `TestImmutability` — DRAFT editable, submitted / approved not editable.
- `TestHabitatProjection` — safe projection strips restricted fields.
- `TestTenantIsolation` — cross-tenant reads / writes blocked.
- `TestManualObservationGuard` — confidence without source is rejected.
- `TestIntelligenceSummary` — aggregate counts correct.
- `TestApproveToPassportFullChain` — end-to-end approve + Passport append
  + immutability + supersession + reject-does-not-append (uses a GM user
  promoted via Mongo to satisfy SoD).

Legacy Wave 2A tests (`test_nextgen_wave2a.py`) continue to pass —
Phase 3 introduces no regressions.

## 10. Future Work

- **Directive 010 — Storage Hardening**: swap `LocalDiskAdapter` for
  S3/GCS; run the outbox worker; deliver notifications for
  `FINDING_APPROVED`.
- **Directive 011 — Vision Grounding**: Gemini-drafted findings enter as
  DRAFT with an AI provenance flag; the CEO / Admin / GM approval rule
  is unchanged.
- **Directive 012 — Customer Reports**: PDF renderer projects approved
  findings only.
