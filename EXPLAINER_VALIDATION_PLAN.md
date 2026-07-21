# EXPLAINER VALIDATION PLAN
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Executive Summary & Mission Objective

This document defines the master **Explainer Validation Plan** for the **Stratex-2 Intelligence Explainer Engine™**. The primary objective is to prove that the universal explanation layer preserves canonical truth, traces every conclusion to authorized evidence, handles uncertainty honestly, scales gracefully under stress, and resists adversarial manipulation.

This plan enforces the validation of existing explanation components without redesigning the core architecture, schemas, NextGen API contracts, templates, trace pipelines, or confidence models. We must verify that:
1. **Canonical Truth is Preserved:** Narratives accurately match the underlying database state.
2. **Every Conclusion is Traceable:** No assertion exists without an active, cryptographically hashed evidence trace.
3. **Uncertainty is Handled Honestly:** Missing or low-reliability evidence decays confidence dynamically and prompts fallback warnings.
4. **Audience-Appropriate Adaptability is Verified:** Level 1 (Homeowner), Level 2 (Contractor), Level 3 (Engineering), and Level 4 (Complete Trace) remain factually identical and differ only in tone, language, and detail depth.
5. **Failures are Graceful & Safe:** Infrastructure failures (e.g. database, KG, Redis) never result in fabricated certainties.
6. **Reproducibility is Guaranteed:** Identical frozen inputs reproduce the exact same logical explanation.
7. **Adversarial Attempts Fail Predictably:** Unauthorized cross-tenant queries, unapproved data elevation, and missing evidence bypass attempts fail securely.

---

## 2. System Boundaries & Ownership Matrix

The Stratex-2 platform enforces strict architectural boundaries to prevent leakage or circular reasoning. The validation plan maps all test assertions against this ownership topology:

```
                  ┌────────────────────────────────────────┐
                  │              STRATEX CORE              │
                  │   - Evidence Ingestion (Invoices/UAV)  │
                  │   - Finding Analysis & Review Gates    │
                  │   - Explanation Requests & Presentation│
                  └───────────────────▲────────────────────┘
                                      │ (Ingests / Interrogates)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │           PROPERTY PASSPORT            │
                  │   - Canonical Approved Facts (Ledger)  │
                  │   - Explanation Entity & Versioning    │
                  │   - Cryptographic Evidence Lineage     │
                  └───────────────────▲────────────────────┘
                                      │ (Syncs / Interrogates)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │             PROPERTY DNA               │
                  │   - Real-Time Summary Nodes            │
                  │   - Multi-System Health Projections    │
                  └───────────────────▲────────────────────┘
                                      │ (Syncs / Interrogates)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │        PROPERTY KNOWLEDGE GRAPH        │
                  │   - Evidence-Backed Relationship Paths │
                  │   - Causal Rationale Traversal Paths  │
                  └───────────────────▲────────────────────┘
                                      │ (Syncs / Interrogates)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │                HABITAT                 │
                  │   - Client Projection Consumption Only  │
                  │   - Strictly Prohibited from Generating│
                  │     or Modifying Canonical Explanations│
                  └────────────────────────────────────────┘
```

---

## 3. Dual Validation Methodology

To ensure 100% test coverage and absolute architectural safety, we implement a dual verification pipeline:

### A. Mechanical Validation
1. **JSON Schema Adherence:** Every generated explanation document is validated against the Draft 2020-12 JSON Schema defined in `EXPLANATION_SCHEMA.md`. Any document missing mandatory keys (e.g., `evidence_trace`, `system_category`, `overall_confidence_score`) is rejected immediately.
2. **Cryptographic Integrity Validation:** Every evidence trace contains a SHA-256 hash-chain validating the path from Origin Mission $\rightarrow$ Raw Evidence $\rightarrow$ Passport Entry $\rightarrow$ Property DNA Node $\rightarrow$ KG Path $\rightarrow$ Narrative Rationale.
3. **Multi-Tenant Partition Check:** Automated validation scripts execute cross-tenant queries to guarantee that Tenant B's explanation requests never retrieve Tenant A's evidence or history, raising a 403 Forbidden.

### B. Conceptual & Rationale Validation
1. **Language & Phrasing Guardrails:** Text output is scanned against the Allowed/Prohibited language lists for all 12 domains to ensure that tone remains objective and aligned with the target audience.
2. **Certainty Calibration Assertions:** Confidence calculation is programmatically validated to ensure that:
   - Zero evidence results in exactly `0%` confidence and falls back to `UNKNOWN`.
   - Stale evidence correctly triggers the system-specific temporal decay $\lambda$.
   - Conflicting evidence triggers the `F_c` multiplier (0.85 for minor, 0.50 for major).
3. **Audience-Level Invariance checks:** Text-to-text semantic analysis verifies that while Level 1 uses plain language and Level 3 uses engineering formulas, both describe the exact same underlying facts and confidence levels.

---

## 4. Validation Lifecycle & Quality Gates

The system enforces automated quality gates at four stages of the delivery pipeline:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. Pre-Commit  ├────►│  2. CI Pipeline ├────►│   3. Staging    ├────►│  4. Production  │
│ - Linter check  │     │ - Jest API tests│     │ - Sandbox run   │     │ - Real-time audit│
│ - Schema checks │     │ - Pytest runs   │     │ - Load testing  │     │ - Fail-safe logs │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Pre-Commit Gate:** Validates that any changes to explanation templates or configuration files conform to the `docs/EXPLANATION_SCHEMA.md` and pass local syntax linters.
2. **CI Pipeline Gate:** Runs mock API test suites in Jest (frontend) and Pytest (backend) verifying that `intelligence.py` and `passports.py` routes preserve authorization models.
3. **Staging Validation Gate:** Synthesizes the full 120 golden cases (12 domains $\times$ 10 case archetypes) under simulated high-load, multi-tenant conditions.
4. **Production Operational Gate:** Monitored continuously by the CENTCOM Audit system. If an audit write fails, the Explainer pipeline fails safely, reverting the active transaction and raising a high-priority incident.

---

## 5. Summary of Deliverables

The complete Operation Explainer Validation suite is comprised of 12 integrated, structured documents:
* **EXPLAINER_VALIDATION_PLAN.md:** This master strategy and scope framework.
* **GOLDEN_EXPLANATION_CORPUS.md:** High-fidelity test cases for 12 domains and 10 case variants.
* **CONFIDENCE_CALIBRATION_PLAN.md:** Mathematical verification of the $C = R_s \times D_t \times F_c \times W_c \times 100$ formula.
* **AUDIENCE_FIDELITY_TESTS.md:** Verification of the 4 audience levels.
* **ADVERSARIAL_EXPLANATION_TESTS.md:** Validation of the 13 security/vulnerability test suites.
* **EXPLANATION_REPRODUCIBILITY.md:** Verification of reproducibility matrices for frozen inputs.
* **EXPLANATION_VERSION_IMPACT.md:** Evaluation of life-cycle transitions (Current, Superseded, Stale, etc.).
* **EXPLAINER_FAILURE_MATRIX.md:** Disaster-recovery and fallback validation for 10 failure points.
* **EXPLAINER_PERFORMANCE_BENCHMARKS.md:** SLA/KPI load targets, latency profiles, and cache stats.
* **EXPLANATION_REVIEW_WORKBENCH.md:** Reviewer experience, safety gates, and manual override tracking.
* **EXPLANATION_PUBLICATION_RULES.md:** Publication state machine and boundary projection restrictions.
* **EXPLAINER_ACCEPTANCE_REPORT.md:** Final certification checklist and official executive sign-off.
