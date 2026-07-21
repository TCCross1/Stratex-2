# EXPLAINER FAILURE MATRIX
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Principles of Graceful Degradation

The **Explainer Failure Matrix** establishes the fallback behaviors when critical infrastructure components fail. 

The primary rule is: **Unknown is preferable to unsupported certainty.** 

The system must degrade safely, returning clean, schema-compliant error structures or fallback values. It is strictly prohibited from fabricating conclusions or confidence scores during an outage.

---

## 2. Infrastructure Failure & Fallback Matrix

The system handles failures at 10 distinct infrastructure points as detailed in the matrix below:

| Fail ID | Failing Component | System Impact | Fallback / Degraded Mode Action | Safety Gate Assertion |
| :--- | :--- | :--- | :--- | :--- |
| **FL-01** | **Knowledge Graph** | Causal relationship paths are unresolvable. | Proceed without causal link notes. Fall back to direct evidence trace only. Mark KG paths as `UNKNOWN`. | Ensure no related-system inferences are drawn. |
| **FL-02** | **Property DNA** | DNA summary nodes are stale, offline, or corrupted. | Fall back to the raw, un-aggregated Passport ledger entries. Raise a warning flag in metadata. | Do not use default/hardcoded placeholder values for active health. |
| **FL-03** | **Redis Cache** | Cache hit fails or cache cluster is entirely offline. | Automatically bypass cache layer. Fetch directly from read-optimized MongoDB instance. | Assert direct DB read is throttled to prevent server thrashing. |
| **FL-04** | **AI Generation** | LLM API outage, rate-limiting, or safety filter block. | Abort natural-language narrative generation. Fall back to pre-defined domain-specific static templates. | Under no circumstances output a raw system trace to public users. |
| **FL-05** | **Template Rendering** | Syntax error or missing variables in narrative templates. | Abort dynamic compile. Fall back to Level 4 structured data payload with system warning. | Prevent half-rendered or malformed markdown outputs. |
| **FL-06** | **Standards Lookup** | Building code/standard API service is unreachable. | Proceed with the explanation, but mark the standard validation field as `PENDING_SERVICE`. | Do not invent or skip mandatory code compliance checks. |
| **FL-07** | **Evidence Retrieval** | Part of the raw evidence files are missing/corrupted. | Exclude the missing files from trace. Calculate confidence based on retrieved files only. | Lower the $W_c$ (Coverage) factor to reflect incomplete data. |
| **FL-08** | **Confidence Calculator** | Arithmetic division-by-zero or missing parameters. | Force overall confidence rating to `0%` and certainty level to `UNKNOWN`. | Raise an immediate high-priority warning flag on the dashboard. |
| **FL-09** | **Passport Transaction** | Ledger write or lock transaction is interrupted/fails. | Immediately roll back all database updates to the last verified checkpoint state. | Do not publish a partial or un-hashed explanation document. |
| **FL-10** | **Audit Logging Write** | Security event database is full or write fails. | Halt the entire generation pipeline. Terminate the active session and raise system block. | No explanation may be created without a verified audit log write. |

---

## 3. High-Fidelity Outage Response Payload

During a catastrophic failure (e.g. LLM API and template engine both offline), the system must degrade safely and return the following schema-compliant fallback document:

```json
{
  "explanation_id": "exp_fallback_hvac_099",
  "property_id": "prop_99182_valley_heights",
  "tenant_id": "tn_4001_west_assets",
  "dna_version_referenced": 0,
  "system_category": "HVAC",
  "created_at": "2026-07-21T12:00:00Z",
  "updated_at": "2026-07-21T12:00:00Z",
  "overall_confidence_score": 0.0,
  "levels": {
    "level_1_homeowner": {
      "conclusion": "HVAC system status is currently UNKNOWN due to a temporary system service interruption.",
      "supporting_evidence": "Please refer to the raw service dispatch queue.",
      "confidence": "UNKNOWN (0%)",
      "why_it_matters": "System performance cannot be verified at this time.",
      "next_steps": "Please contact support or schedule a physical technician inspection."
    }
  },
  "evidence_trace": {
    "origin_mission_ids": [],
    "evidence_ids": [],
    "passport_entry_ids": [],
    "dna_node_paths": [],
    "knowledge_graph_traversal_paths": [],
    "confidence_calculation": {
      "rs_base_reliability": 0.0,
      "dt_temporal_decay": 0.0,
      "fc_evidence_conflict": 0.0,
      "wc_system_coverage": 0.0,
      "overall": 0.0
    },
    "applicable_standards": [],
    "cryptographic_proof_chain": {
      "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
      "data_hash": "0000000000000000000000000000000000000000000000000000000000000000",
      "sha256_chain": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  }
}
```

---

## 4. Failure Acceptance Criteria

The system’s resilience is validated only when:
*   **No Crash Guarantee:** Infrastructure outages must never cause the NextGen API server to crash or leak raw stack traces.
*   **Safe Certainty Limit:** Under any component failure, calculated confidence must never exceed `0%` unless direct, authorized evidence is read.
*   **Audit Lockout:** An audit write failure must prevent the system from performing any further read/write transactions until the database is restored.
