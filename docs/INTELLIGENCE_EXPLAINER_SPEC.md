# INTELLIGENCE EXPLAINER ENGINE™ SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 013 · OPERATION INTELLIGENCE EXPLAINER
**Status:** DESIGN COMPLETE · STANDARDIZED  
**Scope:** Universal explanation layer across the entire Stratex ecosystem (Core, Passport, DNA, Habitat, Reports, and AI).

---

## 1. Mission, Vision & Philosophies

The **Intelligence Explainer Engine™** is the core transparency engine of the Stratex platform. Its primary mandate is simple yet uncompromising: **No conclusion, score, recommendation, or warning shall ever be presented without explaining exactly HOW it was reached.**

```
 ┌───────────────────────────────────────────────────────────┐
 │                   INPUT INTEL ENGINE                      │
 │    (Property DNA, Passport, KG Path, AI Predictions)      │
 └─────────────────────────────┬─────────────────────────────┘
                               │
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │               INTELLIGENCE EXPLAINER ENGINE™              │
 │  (Pipeline, Multi-level Schema, Trace logs, Confidence)   │
 └─────────────────────────────┬─────────────────────────────┘
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
 ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
 │   Habitat    │      │   Reports    │      │  Insurance   │
 │ (Homeowner)  │      │ (Contractor) │      │  (Adjusters) │
 └──────────────┘      └──────────────┘      └──────────────┘
```

The Stratex platform earns the ultimate trust of homeowners, contractors, insurers, and engineers alike. Rather than relying on black-box, opaque AI predictions, the Explainer Engine transforms complex multi-modal engineering, inspection, and sensor intelligence into clear, structured, evidence-backed narratives. 

---

## 2. The Immutable Engineering Laws of Explanation

The Explainer Engine enforces five core engineering laws:

1. **No Explanation Without Evidence:** Any claim made by Stratex (e.g., "The roof shingles are damaged") must point directly to one or more verified physical observations, mission records, or raw sensor feeds.
2. **No Recommendation Without Rationale:** Any proposed action or maintenance step must be accompanied by a logical "Why", stating the physical consequence of inaction or the structural standard driving the fix.
3. **No Score Without Provenance:** Every health rating, risk index, or index derivative (such as AWE index) must expose its calculation method, the reliability weights of its inputs, and their timestamp.
4. **Prefer Unknown Over Fabricated Certainty:** If data is missing or incomplete, the system must explicitly state `UNKNOWN` and rate confidence as 0%. Opaque inferences, hallucinations, or "highly likely" fabricated data are strictly prohibited.
5. **Expose Confidence & Supporting Evidence:** All outputs must be paired with an audited confidence calculation and a traversable evidence trace.

---

## 3. High-Level Architecture & Core Components

The Explainer Engine lives at the boundary of Stratex nextgen APIs, processing data from the **Property DNA Engine**, the **Property Passport Canonical Ledger**, and the **Property Knowledge Graph**.

```
                ┌────────────────────────────────┐
                │     Property Knowledge Graph    │
                └──────────────┬─────────────────┘
                               │ Traversal Paths
                               ▼
 ┌──────────────┐      ┌───────────────┐      ┌──────────────┐
 │   Passport   ├─────►│ Property DNA  ├─────►│ Explainer    │
 │ (Canonical)  │      │  (Projection) │      │ Engine       │
 └──────────────┘      └───────────────┘      └──────┬───────┘
                                                     │ Generates Output
                                                     ▼
                                              ┌──────────────┐
                                              │ Multi-Level  │
                                              │  Narrative   │
                                              └──────────────┘
```

### Key Subsystems
1. **The Explanation Pipeline (`EXPLANATION_PIPELINE.md`):** Consumes multi-tiered evidence inputs and steps sequentially through data ingestion, knowledge graph traversal, schema compilation, AI rationale generation, and human narrative output.
2. **The Schema Validator (`EXPLANATION_SCHEMA.md`):** Guarantees that every generated explanation includes all core parameters (Conclusion, Evidence, Confidence, Why this Matters, Next Steps, Related Systems, Assumptions, Unknowns) and supports explanation levels 1 to 4.
3. **The Template Registry (`EXPLANATION_TEMPLATES.md`):** Maintains pre-defined structured blueprints for the 12 critical building systems, allowing specialized, contextual, and domain-appropriate phrasing.
4. **The Evidence Trace Module (`EVIDENCE_TRACE_SPEC.md`):** Calculates structural chains of custody, maps origin missions, binds evidence IDs, and preserves cryptographic and path lineages.
5. **The Confidence Engine (`CONFIDENCE_EXPLANATIONS.md`):** Evaluates mathematical confidence ratings dynamically, factoring in source trust, sensor drift, temporal decay, and conflicting data inputs.

---

## 4. Multi-Level Explanation Architecture

To serve diverse stakeholders, explanations are structured into four discrete levels of resolution:

*   **Level 1: Simple Homeowner Explanation**
    *   *Audience:* Property owners, residents.
    *   *Tone:* Empathetic, jargon-free, actionable, safety and cost-focused.
*   *   **Level 2: Contractor Explanation**
    *   *Audience:* Certified service providers, estimators, field teams.
    *   *Tone:* Direct, physical, trade-oriented, prioritizing actionable repair scopes and localized component specifications.
*   *   **Level 3: Engineering Explanation**
    *   *Audience:* Structural/civil engineers, energy modelers, advanced QA.
    *   *Tone:* Technical, quantitative, referencing exact structural dimensions, materials performance, physics-based factors, and diagnostic telemetry.
*   *   **Level 4: Complete Evidence Chain**
    *   *Audience:* Insurance adjusters, auditing bodies, internal AI agents, and legal teams.
    *   *Tone:* Purely data-driven, chronological ledger traces, raw sensor arrays, and cryptographic checksum pathways with zero narrative embellishment.

---

## 5. Ecosystem Integrations

The Explainer Engine acts as the central intelligence nexus, integrating deeply with eight major platform systems:

### A. CENTCOM
*   **Role:** The operational monitoring and command-and-control platform.
*   **Integration:** Explainer provides live audit feeds to Centcom dashboards. Whenever an AI agent or analyst flags a system state change, Centcom calls the Explainer API to display the underlying reason on the live mission map.

### B. Core
*   **Role:** The basic property physical and geographical identity layer.
*   **Integration:** Core feeds basic property characteristics (build year, size, envelope dimensions) into the pipeline, establishing the default physical assumptions for physical decay models.

### C. Passport
*   **Role:** The immutable, write-hardened evidence ledger.
*   **Integration:** Passport serves as the ultimate source of evidence IDs, origin missions, and verified field notes. The Explainer Engine queries the Passport database to populate the supporting evidence traces and verification timestamps.

### D. Habitat
*   **Role:** The interactive homeowner interface.
*   **Integration:** Calls the Explainer Engine at Level 1 to render natural-language explanation cards on the homeowner's dashboard, ensuring they understand why their roof health is at "82%" or why a "Sewer line cleaning" is being recommended.

### E. Reports
*   **Role:** The generation engine for official engineering, assessment, and insurance PDFs.
*   **Integration:** Consumes Level 2 (Contractor) and Level 3 (Engineering) explanation nodes to compile structural risk, HVAC, and energy performance annexes, embedding rich markdown charts and evidence tables into hard-copy deliverables.

### F. Design Studio
*   **Role:** The interactive property workspace and renovation sandbox.
*   **Integration:** Evaluates hypothetical design scenarios (e.g., "What happens if we install Solar Panels on this Roof deck?"). Design Studio requests real-time explanations comparing current baseline health/risk against projected future states.

### G. Project Opportunity Engine
*   **Role:** The algorithm that groups deferred maintenance and asset decay states into high-value projects (e.g., combining Roof Repair with Solar installation).
*   **Integration:** Calls Explainer to justify the logic of project proposals, clearly stating cost-efficiency gains, mechanical overlaps, and combined risk reductions.

### H. AI Project Intelligence
*   **Role:** Deep learning models assessing overall property viability, lifespan projections, and risk exposures.
*   **Integration:** Feeds raw inferences into the Explainer Pipeline. The Explainer acts as a structural guardrail, verifying and translating those neural-net outputs into clear, audited narrative chains, preventing hallucinations.

---

## 6. Success Metrics & Quality Gates

An explanation is deemed **valid and successful** only when it satisfies all of the following conditions:

*   **100% Traceability:** Zero manual entry of "inferred" or "estimated" states without linking to a verified PassportEntry or sensor ID.
*   **Complete Schema Validation:** Any JSON returned must fully pass the `ExplanationSchema` validation without missing fields.
*   **Cohesive Level Progression:** Level 1 through Level 4 representations must stay consistent. Higher technical details in Level 3 must not contradict the simple narrative of Level 1.
*   **Dynamic Confidence Bounds:** The confidence score matches the strict mathematical decay and reliability bounds specified in the confidence specifications, showing absolute transparency when certainty is low.
