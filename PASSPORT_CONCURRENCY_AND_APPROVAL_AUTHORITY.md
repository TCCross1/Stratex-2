# Passport Concurrency and Approval Authority (C-P-002 / C-P-002A)

**Status:** C-P-002A audit-debt closure on feature branch · **Production readiness: NOT READY**
**Canonical NextGen ledger writer:** `backend/nextgen/passport_service.py::append_entry`
**Governed publication authority:** `backend/nextgen/governed_publish_service.py` (`MODULE_IDENTITY = "nextgen.governed_publish_service"`)

## Authority model

- **Core** performs the work.
- **Passport** remembers the home (append-only ledger).
- **Habitat** sustains the relationship and remains **read-only** for canonical Passport truth.

Findings and Intelligence may approve source records. They must delegate all canonical Passport ledger publication through `governed_publish` → `append_entry`. No second NextGen writer. No second governed publisher.

Accepted Passport history is immutable. Corrections create new entries and versions. Conflicts never overwrite or silently rewrite accepted history.

## Append invariants

1. Each ledger entry has one immutable entry ID (`canonical_id`).
2. Each Passport has a monotonically increasing sequence.
3. A sequence occurs only once per tenant + Passport (unique index).
4. Each entry references the prior accepted entry hash (`prior_hash`).
5. Each accepted entry records resulting Passport `revision`.
6. Governed callers must supply `expected_revision` and/or `expected_head_hash`.
7. Stale callers cannot overwrite or silently append against an old head.
8. Repeated delivery of the same append request cannot create duplicates.
9. A failed append cannot be reported as committed.
10. A committed entry cannot be silently removed or rewritten.
11. All conflicts retain provenance and audit evidence.
12. All approved canonical entries are produced by `append_entry`.
13. No approval endpoint inserts directly into Passport collections.
14. Tenant and property isolation apply to every append.
15. Missing expected state fails conservatively on governed paths.
16. One tenant/property may have only one **active** canonical Property Passport.
17. Critical Passport unique-index failure marks readiness `FAILED` and blocks strict/production publication.

## Expected-state concurrency contract

Governed approval/publication calls must supply at least one of:

- `expected_revision`
- `expected_head_hash`

Behavior:

| Condition | Result |
|-----------|--------|
| Current expected state | Proceed to validation / commit |
| Stale expected state | No overwrite; create/reuse OPEN conflict; controlled conflict response |
| Missing expected state | Reject governed path |
| Duplicate same request | Return original committed result |
| Same idempotency key, different fingerprint | `IDEMPOTENCY_CONFLICT` |

## Idempotency

Collection: `nextgen_passport_idempotency` (tenant + Passport + key unique).

Fingerprint includes material operation content: `tenant_id`, `passport_id`, `property_id`, `source_type`, `source_id`, `entry_type`, `payload`, `schema_version`, `publication_context`, `expected_revision`, `expected_head_hash`, `require_expected_state`. Canonical JSON serialization (sorted keys, stable separators). No secrets, tokens, MFA values, or transient timestamps.

Outcomes: `NEW_REQUEST` → `COMMITTED` | `DUPLICATE_SAME_REQUEST` | `IDEMPOTENCY_CONFLICT` | `FAILED`.

## Transaction requirements

- Strict/production mode (`APP_ENV=production|prod|live` or `PASSPORT_REQUIRE_TRANSACTIONS=1`) **requires** multi-document transactions.
- Transactions are enabled only when `PASSPORT_TRANSACTIONS_AVAILABLE=1` and a Motor session can be opened.
- If transactions are required but unavailable: **fail closed**, execute no partial append, do not claim production-safe atomicity.
- Non-strict local/unit mode may proceed with compare-and-swap on Passport head plus unique indexes. **That path is not production-safe.**

## Index definitions and readiness

Managed by `backend/nextgen/passport_indexes.py`, invoked at application startup.

| Name | Collection | Unique | Critical |
|------|------------|--------|----------|
| `uniq_tenant_passport_seq` | passport_entries | yes | yes |
| `uniq_tenant_passport_entry_id` | passport_entries | yes | yes |
| `idx_tenant_source_lookup` | passport_entries | no | no |
| `uniq_tenant_passport_idempotency_key` | passport_idempotency | yes | yes |
| `idx_conflict_queue_lookup` | passport_conflicts | no | no |
| `uniq_active_conflict_fingerprint` | passport_conflicts | yes (partial active) | yes |
| `idx_passport_head_revision` | passports | no | no |
| `uniq_active_passport_per_tenant_property` | passports | yes (partial `status=active`) | yes |
| `uniq_outbox_idempotency_key` | outbox_events | yes | no |

Readiness states: `NOT_INITIALIZED` → `INITIALIZING` → `READY` | `FAILED`.

Safe readiness metadata only: state, checked_at, failed index name, redacted error classification. No credentials or connection strings.

- **LOCAL/TEST:** startup may continue; readiness reports `FAILED` when indexes fail; governed publication proceeds unless `PASSPORT_REQUIRE_INDEXES=1`.
- **PRODUCTION/STRICT:** critical unique-index failure fails closed; governed append/publication blocked; health must not report Passport READY.

Duplicate active Passports: report redacted tenant/property prefixes via `probe_duplicate_active_passports`; **no automatic deletion**.

Exposed on `GET /api/nextgen/health` as `passport_indexes`.

## Conflict queue and rebase law

Collection: `nextgen_passport_conflicts`.

Statuses: `OPEN` → `UNDER_REVIEW` → `REBASE_APPROVED` → `REBASED` | `REJECTED` | `SUPERSEDED` | `RESOLVED`.

Identical stale retries share a deterministic `conflict_fingerprint` and reuse one active OPEN conflict (`duplicate_delivery_count` increments). Resolved/rejected history remains immutable and is not overwritten.

Conflict routes enforce **tenant + property authorization** (404 on unauthorized to avoid existence leaks).

Rebase must:

- preserve the original failed attempt (immutable provenance fields);
- reload current Passport state;
- require a new expected revision/head hash;
- create a new append with a **new** idempotency key;
- retain lineage to the original conflict;
- pass the same approval/publication gates;
- never rewrite the historical conflict;
- never automatically merge incompatible property facts.

Reviewer roles (minimum): `admin`, `ceo`, `passport_reviewer`, `engineer_reviewer`, `gm`.

## Hash-chain verification

Service: `backend/nextgen/passport_verify.py`
Endpoint: `GET /api/nextgen/passports/{passport_id}/verify-chain`

Bounded by `PASSPORT_VERIFY_MAX_ENTRIES` (default **10000**, positive integer; zero/negative/malformed → default). Cursor iteration; no unlimited list materialization. Truncation returns `INCOMPLETE` with reason and inspected count — **never** `VALID` for a partial chain. Large histories require a later governed background verification job (not implemented in this phase).

Verification never mutates the ledger. Responses are operator-safe (no signing keys, no stack traces, no raw confidential findings).

## Cryptographic sealing (prospective)

Module: `backend/nextgen/passport_seal.py`

- Algorithm: HMAC-SHA256
- Env: `PASSPORT_SEAL_KEY_VERSION`, `PASSPORT_SEAL_KEY_<version>`
- Production fails closed when sealing is required and key material is absent
- Historical hash-only / tenant-salt entries classified as `LEGACY_UNSEALED` — not rewritten
- HMAC is integrity sealing, **not** legal notarization or an external timestamp
- No secrets committed; tests use ephemeral keys

## Unified approval policy

Module: `backend/nextgen/approval_policy.py`
Used by Findings approve and Intelligence review-approve.

Uniform separation of duties:

- An author may not approve their own record
- Creating, editing, processing, or materially revising counts as authorship where tracked
- Admin / CEO / superadmin status alone must **not** silently bypass SoD
- No emergency override in this phase

## Intelligence publication consistency (C-P-002A)

```
review request
→ approval-policy evaluation
→ governed publication
→ Passport receipt
→ Intelligence → passport_committed (+ approval metadata)
→ outbox / timeline / audit
```

Do **not** persist plain `approved` before governed publication succeeds. On failure: set `publication_failed` (retryable), emit `PUBLICATION_FAILED` audit, do not emit success outbox. Retry with the same idempotency key (`intelligence.publish:{id}`) reclaims the committed Passport receipt without a second entry.

## Audit events (minimum)

`PASSPORT_APPEND_REQUESTED`, `PASSPORT_APPEND_COMMITTED`, `PASSPORT_APPEND_DUPLICATE`, `PASSPORT_APPEND_CONFLICT`, `PASSPORT_APPEND_FAILED`, `PASSPORT_CONFLICT_REVIEWED`, `PASSPORT_REBASE_APPROVED`, `PASSPORT_REBASE_COMMITTED`, `PASSPORT_CONFLICT_REJECTED`, `PASSPORT_CHAIN_VERIFIED`, `PASSPORT_CHAIN_INVALID`, `SOURCE_APPROVAL_REQUESTED`, `SOURCE_APPROVAL_REJECTED`, `SOURCE_APPROVAL_BLOCKED_SOD`, `SOURCE_APPROVED`, `PUBLICATION_REQUESTED`, `PUBLICATION_COMMITTED`, `PUBLICATION_FAILED`.

Never log: signing secrets, authorization headers, passwords, MFA values, complete confidential payloads, raw environment values.

## Runtime limitations (disclosed)

- Multi-document transactions require a transaction-capable MongoDB deployment and `PASSPORT_TRANSACTIONS_AVAILABLE=1`.
- Unit/concurrency stress tests use an in-memory FakeCollections double; simulated concurrency is **not** production proof.
- Legacy Passport compatibility writers remain disclosed and gated (C-P-001C); they are not the NextGen canonical writer.
- Full backend boot may be unavailable without `emergentintegrations` / live Mongo.
- Production readiness remains **NOT READY** pending independent Atlas audit, transaction-capable deployment validation, and seal key operationalization.

## Test commands

```bash
# Focused C-P-002 / C-P-002A
python -m pytest backend/tests/test_cp002_passport_concurrency.py \
  backend/tests/test_cp002a_audit_debt.py \
  backend/tests/test_cp002_concurrency_stress.py \
  backend/tests/test_writer_authority.py -q

# C-P-001C regression
python -m pytest backend/tests/test_dev_auth.py \
  backend/tests/test_mfa_debug_locks.py \
  backend/tests/test_passport_authority.py \
  backend/tests/test_writer_authority.py -q
```

## Compatibility / migration law

Do not rewrite historical Passport entries. New stronger requirements apply prospectively. Historical integrity problems appear as reviewable verification findings — never silent resequence, auto-sign, or destructive duplicate cleanup.

C-P-003: NOT STARTED. ATC-001: NOT STARTED. Merge: STOP — not authorized pending Atlas review.
