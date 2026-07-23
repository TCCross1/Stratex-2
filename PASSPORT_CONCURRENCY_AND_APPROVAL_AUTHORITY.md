# Passport Concurrency and Approval Authority (C-P-002)

**Status:** Implemented on feature branch · **Production readiness: NOT READY**
**Canonical NextGen ledger writer:** `backend/nextgen/passport_service.py::append_entry`
**Governed publication authority:** `backend/nextgen/governed_publish_service.py` (`workflow.governed_publish_service`)

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

## Expected-state concurrency contract

Governed approval/publication calls must supply at least one of:

- `expected_revision`
- `expected_head_hash`

Behavior:

| Condition | Result |
|-----------|--------|
| Current expected state | Proceed to validation / commit |
| Stale expected state | No overwrite; create OPEN conflict; controlled conflict response |
| Missing expected state | Reject governed path |
| Duplicate same request | Return original committed result |
| Same idempotency key, different fingerprint | `IDEMPOTENCY_CONFLICT` |

## Idempotency

Collection: `nextgen_passport_idempotency` (tenant + Passport + key unique).

Stored fields: tenant ID, Passport ID, idempotency key, request fingerprint, entry ID, sequence, revision, entry hash, receipt ID, commit status, created timestamp. No secrets.

Outcomes: `NEW_REQUEST` → `COMMITTED` | `DUPLICATE_SAME_REQUEST` | `IDEMPOTENCY_CONFLICT` | `FAILED`.

Receipts (`nextgen_passport_receipts`) retain the original committed result and fingerprint for audit.

## Transaction requirements

- Strict/production mode (`APP_ENV=production|prod|live` or `PASSPORT_REQUIRE_TRANSACTIONS=1`) **requires** multi-document transactions.
- Transactions are enabled only when `PASSPORT_TRANSACTIONS_AVAILABLE=1` and a Motor session can be opened.
- If transactions are required but unavailable: **fail closed**, execute no partial append, do not claim production-safe atomicity.
- Non-strict local/unit mode may proceed with compare-and-swap on Passport head plus unique indexes. **That path is not production-safe.**

## Index definitions

Managed by `backend/nextgen/passport_indexes.py`, invoked at application startup.

| Name | Collection | Unique |
|------|------------|--------|
| `uniq_tenant_passport_seq` | passport_entries | yes |
| `uniq_tenant_passport_entry_id` | passport_entries | yes |
| `idx_tenant_source_lookup` | passport_entries | no |
| `uniq_tenant_passport_idempotency_key` | passport_idempotency | yes |
| `idx_conflict_queue_lookup` | passport_conflicts | no |
| `idx_passport_head_revision` | passports | no |
| `uniq_outbox_idempotency_key` | outbox_events | yes |

Index creation is idempotent, uses stable names, discloses failures, never silently drops indexes, and never automatically deletes conflicting historical records. Duplicate data blocking a unique index leaves production readiness **NOT READY**.

## Conflict queue and rebase law

Collection: `nextgen_passport_conflicts`.

Statuses: `OPEN` → `UNDER_REVIEW` → `REBASE_APPROVED` → `REBASED` | `REJECTED` | `SUPERSEDED` | `RESOLVED`.

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

Routes under `/api/nextgen/passports/...`.

## Hash-chain verification

Service: `backend/nextgen/passport_verify.py`
Endpoint: `GET /api/nextgen/passports/{passport_id}/verify-chain`

Evaluates identity, sequence continuity, duplicates/gaps, previous-hash linkage, content hash, head hash/revision, seal status, schema version, receipt consistency.

Results include: `VALID`, `VALID_WITH_LEGACY_UNSEALED_ENTRIES`, `INVALID_SEQUENCE`, `INVALID_PREVIOUS_HASH`, `INVALID_ENTRY_HASH`, `INVALID_SIGNATURE`, `HEAD_MISMATCH`, `DUPLICATE_SEQUENCE`, `MISSING_ENTRY`, `UNSUPPORTED_SCHEMA`, `INCOMPLETE`, `UNAVAILABLE`.

Verification never mutates the ledger. Responses are operator-safe (no signing keys, no stack traces, no raw confidential findings).

## Cryptographic sealing (prospective)

Module: `backend/nextgen/passport_seal.py`

- Algorithm: HMAC-SHA256
- Env: `PASSPORT_SEAL_KEY_VERSION`, `PASSPORT_SEAL_KEY_<version>`
- Production fails closed when sealing is required and key material is absent
- Key version recorded on each sealed entry; rotation verifies old versions while signing with the active version
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

Risk-tier reviewer role differences remain configurable for Intelligence; SoD and audit law remain uniform.

## Publication sequence

```
source candidate
→ evidence validation
→ approval policy evaluation
→ separation-of-duties validation
→ approved source state
→ governed publication request
→ canonical append_entry
→ Passport receipt
→ projection/outbox event
→ audit event
```

Failed append does **not** mark the source `passport_committed` / Passport-linked APPROVED commit fields.

## Audit events (minimum)

`PASSPORT_APPEND_REQUESTED`, `PASSPORT_APPEND_COMMITTED`, `PASSPORT_APPEND_DUPLICATE`, `PASSPORT_APPEND_CONFLICT`, `PASSPORT_APPEND_FAILED`, `PASSPORT_CONFLICT_REVIEWED`, `PASSPORT_REBASE_APPROVED`, `PASSPORT_REBASE_COMMITTED`, `PASSPORT_CONFLICT_REJECTED`, `PASSPORT_CHAIN_VERIFIED`, `PASSPORT_CHAIN_INVALID`, `SOURCE_APPROVAL_REQUESTED`, `SOURCE_APPROVAL_REJECTED`, `SOURCE_APPROVAL_BLOCKED_SOD`, `SOURCE_APPROVED`, `PUBLICATION_REQUESTED`, `PUBLICATION_COMMITTED`, `PUBLICATION_FAILED`.

Never log: signing secrets, authorization headers, passwords, MFA values, complete confidential payloads, raw environment values.

## Runtime limitations (disclosed)

- Multi-document transactions require a transaction-capable MongoDB deployment and `PASSPORT_TRANSACTIONS_AVAILABLE=1`.
- Unit/concurrency stress tests use an in-memory FakeCollections double; simulated concurrency is **not** production proof.
- Legacy Passport compatibility writers remain disclosed and gated (C-P-001C); they are not the NextGen canonical writer.
- Production readiness remains **NOT READY** pending independent Atlas audit, transaction-capable deployment validation, and seal key operationalization.

## Test commands

```bash
# Focused C-P-002
python -m pytest backend/tests/test_cp002_passport_concurrency.py \
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
