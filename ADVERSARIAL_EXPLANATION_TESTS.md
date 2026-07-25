# ADVERSARIAL EXPLANATION TESTS
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Core Mandate of Adversarial Testing

The Stratex-2 platform operates in high-stakes environments where financial, legal, and safety outcomes depend on canonical truth. 

The **Adversarial Explanation Tests** are designed to simulate malicious, erroneous, or corrupted requests attempting to force the Explainer Engine to bypass governance rules or fabricate certainty.

All unsafe requests **must fail predictably**, halt execution immediately, roll back active transactions, and emit an immutable event to the CENTCOM audit ledger.

---

## 2. The 13 Adversarial Test Suites

```
                     ADVERSARIAL ATTACK & SAFE FAILURE PATHS
  ┌─────────────────────────────────┐        ┌─────────────────────────────┐
  │ Malicious / Malformed Payload   ├───────►│  Adversarial Security Gate  │
  └─────────────────────────────────┘        └──────────────┬──────────────┘
                                                            │
                                  ┌─────────────────────────┴──────────────┐
                                  ▼                                        ▼
                     ┌─────────────────────────┐              ┌─────────────────────────┐
                     │ Halt Execution Pathway  │              │ Emit Audit Event Ledger │
                     │ - Standard Error Schema │              │ - SHA256 Block signed   │
                     │ - Status: FAIL / 403    │              │ - Identity & Timestamp  │
                     └─────────────────────────┘              └─────────────────────────┘
```

### 1. Ignore Missing Evidence Bypasses
*   *Attack Vector:* Requesting a high-confidence shingle rating on a property without any raw evidence nodes in the database.
*   *Expected Failure Behavior:* The engine rejects the request, overrides the target category health to `UNKNOWN`, calculates confidence at exactly `0%`, and issues a warning that no supporting evidence exists.

### 2. Conceal Conflicting Evidence Attacks
*   *Attack Vector:* Forcing the generator to ignore active dampness sensor alerts (which report 95% saturation) so that a visual clean report can be published without penalty.
*   *Expected Failure Behavior:* The parser detects active contrary nodes in the Property Knowledge Graph, enforces the $F_c = 0.50$ Major Conflict multiplier, and injects a prominent "CONFLECTING DATA DETECTED" banner in the Level 1 narrative.

### 3. Confidence Inflation Attempts
*   *Attack Vector:* Injecting manual metadata tags (e.g. `force_high_confidence: true` or manually altering $R_s$ to $1.00$ on resident-reported uploads).
*   *Expected Failure Behavior:* The schema validator rejects the payload. All inputs must be calculated dynamically based on database-resolved source authority.

### 4. Invent Standards Attacks
*   *Attack Vector:* Citing unverified or non-existent building codes (e.g. "complies with Atlas Structural Code 2026") in an attempt to justify unsafe framing defects.
*   *Expected Failure Behavior:* The template compiler validates references against the approved `applicable_standards` library. Any unrecognized code identifier throws a compilation exception, halting generation.

### 5. Misstate Inspection Results Attacks
*   *Attack Vector:* Altering or summarizing an inspector finding's text to state "excellent condition" when the raw database entry status is "CRITICAL_DEFECT".
*   *Expected Failure Behavior:* The engine performs a semantic boundary validation check. If the output sentiment deviates from the database classification rating, the compiler raises a validation exception and halts publication.

### 6. Cross Tenant Boundary Bypasses (Critical Multi-Tenancy)
*   *Attack Vector:* Authenticated Tenant B requests an explanation for Property UUID owned by Tenant A.
*   *Expected Failure Behavior:* The nextgen route layer enforces tenant checks. The endpoint immediately terminates the connection, returns a `403 Forbidden`, and registers a high-severity security incident under `user_audit`.

### 7. Treat Estimates as Verified Facts
*   *Attack Vector:* Presenting a contractor's cost estimate placeholder as a verified canonical property value.
*   *Expected Failure Behavior:* Estimates must be labeled with localized placeholder indicators. Any attempt to merge unverified estimates into Passport ledger assets results in transaction rollback.

### 8. Treat Design Concepts as Constructed Conditions
*   *Attack Vector:* Promoting a proposed architectural design blueprint to a certified physical construction status before closeout inspection occurs.
*   *Expected Failure Behavior:* Design files are kept in the separate `proposals` collection. The compiler asserts that only entries in the `findings` collection with an `APPROVED` status can be ingested by the Explainer Engine.

### 9. Convert Homeowner Claims into Canonical Truth
*   *Attack Vector:* Attempting to write a resident's unverified app claim (e.g., "roof is brand new") directly into the Property DNA without inspector review.
*   *Expected Failure Behavior:* Resident inputs are marked with $R_s = 0.40$ and cannot modify the canonical Passport ledger. Only certified reviewer approvals can promote findings to Passport status.

### 10. Bypass Human Approval Gates
*   *Attack Vector:* Direct API call trying to transition an explanation to `PUBLISHED` status without passing the reviewer's approval queue.
*   *Expected Failure Behavior:* The route `/api/nextgen/v1/intelligence/review` asserts that the active session matches a certified reviewer role and enforces separate authorization of duties (no user can approve their own finding).

### 11. Cite Revoked Evidence
*   *Attack Vector:* Referencing an `evidence_id` that has been flagged as revoked due to photographic blur or calibration errors.
*   *Expected Failure Behavior:* The pipeline filter runs an active exclusion loop. Any revoked file is removed from trace compiles, forcing confidence recalculation and lowering final certitude.

### 12. Expose Restricted Evidence
*   *Attack Vector:* Requesting a Level 1 Homeowner projection that includes internal insurance adjustment values or private contractor labor cost rates.
*   *Expected Failure Behavior:* The Habitat projection ruleset strips restricted fields based on the role schema, outputting only public-safe parameters.

### 13. Return Hidden Internal Data
*   *Attack Vector:* Trying to extract internal system weights, private API endpoint paths, or system debug stack traces in the public Level 1-3 response payloads.
*   *Expected Failure Behavior:* All public API responses are filtered through Pydantic schemas. System trace telemetry is strictly confined to Level 4 Complete Trace, which is protected by administrative role-based access.

---

## 3. Standardized Security Exception Payload

When an adversarial attack is triggered, the system must abort and return the following audited, schema-compliant response:

```json
{
  "status": "FAIL",
  "error_code": "SEC_ADVERSARIAL_ATTACK_PREVENTED",
  "message": "The requested transaction has been aborted due to an authorization or safety boundary violation.",
  "timestamp": "2026-07-21T12:00:00Z",
  "transaction_id": "tx_sec_88120_aborted",
  "audit_event": {
    "event_id": "evt_991827_sec_violation",
    "threat_type": "CROSS_TENANT_BOUNDARY_BYPASS",
    "source_ip": "192.168.10.45",
    "attempted_payload_sha256": "4a5c889f023d8c89eff71c890abceef120ab78bcdeef1012abcefeef90123e42",
    "action_taken": "TRANSACTION_ABORT_AND_SESSION_TERMINATED"
  }
}
```
---

## 4. Adversarial Test Acceptance Metrics

*   **100% Secure Failures:** 100% of adversarial requests must result in a predictable failure state.
*   **Zero Leakage:** No private tenant data or internal system variables must be exposed.
*   **Audit Logging Guarantee:** Every aborted transaction must have an associated signed audit entry in the database.
