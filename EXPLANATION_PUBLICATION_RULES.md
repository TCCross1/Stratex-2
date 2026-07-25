# EXPLANATION PUBLICATION RULES
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Scope & Core Architectural Boundaries

The Stratex-2 platform enforces strict isolation of publication state. 

The primary rule is: **No published explanation without approved canonical facts. Only Approved and Published explanations may project to public endpoints.**

Furthermore, the **Habitat** system consumes approved, audience-safe projections only. **Habitat shall not independently generate canonical property explanations from raw evidence.**

---

## 2. Explanation Publication States & Transitions

The lifecycle of an explanation is governed by a strict state machine:

```
  ┌───────────┐      ┌─────────────┐      ┌─────────────────────────┐
  │  1. DRAFT ├─────►│2. GENERATED ├─────►│3. HUMAN REVIEW REQUIRED │
  └───────────┘      └──────┬──────┘      └────────────┬────────────┘
                            │                          │
                            ▼                          ▼
              ┌─────────────────────────┐        ┌─────────────┐
              │ 4. VALIDATION FAILED    │        │ 5. APPROVED │
              └─────────────────────────┘        └──────┬──────┘
                                                        │
                                                        ▼
              ┌─────────────────────────┐        ┌─────────────┐
              │ 7. REVOKED              │◄───────┤6. PUBLISHED │
              └─────────────────────────┘        └──────┬──────┘
                                                        │
                                                        ▼
                                                 ┌──────────────┐
                                                 │8. SUPERSEDED │
                                                 └──────────────┘
```

1.  **Draft:** Ingestion phase. Evidence is being gathered and mapped.
2.  **Generated:** The compiler has generated the multi-level draft using LLM logic, awaiting schema validation.
3.  **Validation Failed:** If the document fails the JSON Schema checks or has confidence calculation errors, it is moved to this state and excluded from review queues.
4.  **Human Review Required:** Pre-publication state. The document has passed mechanical checks and is queued on the Review Workbench.
5.  **Approved:** A reviewer has signed off on the content. The document is frozen and signed.
6.  **Published:** The explanation is active and eligible for downstream projection.
7.  **Superseded:** A newer approved explanation version has been published, deprecating this one.
8.  **Revoked:** The explanation was manually retracted due to evidence invalidation.

---

## 3. Downstream Projection Rules

Downstream channels can only consume verified and published explanation projections. The table below details what is displayed across channels:

| Downstream Channel | Allowed States | Permitted Levels | Prohibited Fields |
| :--- | :--- | :--- | :--- |
| **Habitat (Homeowner)** | `PUBLISHED` | Level 1 (Homeowner) only | Internal adjuster notes, contractor labor costs, raw database IDs |
| **Client Reports** | `PUBLISHED` | Level 1 & Level 2 | Private internal system weights, debug stack traces |
| **Contractor Packages** | `APPROVED`, `PUBLISHED` | Level 2 (Contractor) | Insurer valuations, proprietary engineering math |
| **Insurance Projections** | `PUBLISHED` | Level 3 & Level 4 | Narrative summaries (strictly facts, ledger traces, and metrics) |
| **External API Integrations**| `PUBLISHED` | Level 4 (Trace) | Unverified draft states, raw model configurations |

### Audience Projection Linkage Rule
All audience projections must reference the canonical Passport explanation entity and its active version number (e.g. `exp_ref: "exp_roof_001", version_ref: 2`). Direct raw rendering of un-hashed templates on the front-end is strictly prohibited.

---

## 4. State Machine Transition Permissions

Transitions across states are protected by NextGen role-based access control (RBAC):

*   **Draft $\rightarrow$ Generated:** Automated system worker accounts only.
*   **Generated $\rightarrow$ Human Review Required:** Automated system validator after passing all schema and cryptographic checks.
*   **Human Review Required $\rightarrow$ Approved:** Restricted to accounts with certified reviewer roles (CEO, GM, or Senior QA).
*   **Approved $\rightarrow$ Published:** System publisher account or certified reviewer.
*   **Published $\rightarrow$ Revoked / Superseded:** Restricted to certified reviewers, requiring a manual reason code and signed audit log entry.
