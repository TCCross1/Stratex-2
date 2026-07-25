# EXPLANATION PIPELINE SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 013 · OPERATION INTELLIGENCE EXPLAINER
**Status:** DESIGN COMPLETE  
**Scope:** Ingestion, processing, traversal, reasoning, and narrative generation pipelines.

---

## 1. Pipeline Overview & Flow Architecture

The **Explanation Pipeline™** is a monotonic, deterministic-to-probabilistic processing chain that transforms raw, disjointed physical observations into coherent, multi-level explanations. Every stage in the pipeline is strictly sequenced, ensuring that narrative summaries (AI-driven) are mathematically and structurally bound to immutable source evidence.

```
+───────────────────────────+
│   1. EVIDENCE LAYER       │ <-- Raw media, contractor receipts, sensor streams
+─────────────┬─────────────+
              │ Ingestion & Verification
              ▼
+───────────────────────────+
│   2. PASSPORT LEDGER      │ <-- Hardened passport entries and approved findings
+─────────────┬─────────────+
              │ Traversal Indexing
              ▼
+───────────────────────────+
│   3. KNOWLEDGE GRAPH      │ <-- Node connections, system causal relations, paths
+─────────────┬─────────────+
              │ Dimensional Aggregation
              ▼
+───────────────────────────+
│   4. PROPERTY DNA         │ <-- Multi-dimensional health, risk, lifecycle state
+─────────────┬─────────────+
              │ Structured Contextualization (RAG)
              ▼
+───────────────────────────+
│   5. AI REASONING         │ <-- Model inference, guardrails against fabrication
+─────────────┬─────────────+
              │ Multi-Level Adaptation
              ▼
+───────────────────────────+
│   6. HUMAN EXPLANATION    │ <-- Levels 1-4 markdown outputs for consumers
+───────────────────────────+
```

---

## 2. Detailed Pipeline Stages

### Stage 1: Evidence Ingestion (The Foundation)
*   **Description:** The process begins with raw physical data. This includes high-resolution thermal imaging from inspect missions, LiDAR structural scans, drone aerial photography, dampness sensor arrays, and direct contractor invoices.
*   **Pipeline Input:** Raw byte streams, geo-tagged image metadata, sensor timeseries data, and OCR/structured contractor closeouts.
*   **Transformation Logic:** 
    *   Images and files are validated for integrity, checked for cryptographic signatures, and parsed for Metadata (Exif geo-coordinates, timestamps).
    *   Deep-learning vision models identify localized defects (e.g., shingle loss count, water stains).
    *   Sensor data is processed for anomaly detection (e.g., relative humidity exceeding 75% for over 48 hours).
*   **Pipeline Output:** Verified, timestamped, and cryptographically hashed raw evidence payloads bound to an `evidence_id`.
*   **Stage Gate / Validation:** All metadata must match the active `mission_id`. Un-geocoded or time-mismatched files are flagged for manual QA.

### Stage 2: Passport Fact Recording (The Ledger)
*   **Description:** Raw evidence is promoted into official Passport Entries and Findings. This represents the authoritative, legally defensible, and peer-reviewed physical state of the building.
*   **Pipeline Input:** Outbox-emitted `evidence_id` payloads and inspector-submitted field reports.
*   **Transformation Logic:**
    *   The Stratex Consensus Validation Engine compares inspector inputs against vision model findings.
    *   If consensus is achieved, an immutable `PassportEntry` is written to the ledger.
    *   A corresponding `Finding` is generated with structural attributes (Severity, Priority, System, Component).
*   **Pipeline Output:** MongoDB `passport_entries` and `findings` records, fully APPROVED, containing absolute state facts.
*   **Stage Gate / Validation:** Writes must be co-signed by an authorized inspector profile and cannot be updated once co-signed.

### Stage 3: Knowledge Graph Traversal (The Map)
*   **Description:** Rather than treating findings in isolation, the Explainer maps the physical relations between components. For example, a "shingle leak" in the Roof system is connected via a "gravity path" to a "water stain" in the Attic system, which in turn explains "mold risk" on the Bedroom ceiling.
*   **Pipeline Input:** Newly minted findings and the canonical Property Knowledge Graph schema.
*   **Transformation Logic:**
    *   The system executes Graph Traversal algorithms (DFS/BFS and Dijkstra-weighted risk searches) starting from the primary finding node.
    *   It identifies all neighboring physical components (edges representing "TOUCHES", "DRAINS_TO", "FEEDS", "CONTAINS", "PREVENTS").
    *   It compiles the causal path of secondary and tertiary impacts.
*   **Pipeline Output:** A structured `KnowledgeGraphPath` (e.g., `ROOF_SHINGLES` ──[DRAINS_TO]──► `FOUNDATION_GRADING` ──[EXPOSES_TO]──► `CRAWLSPACE`).
*   **Stage Gate / Validation:** Paths must be acyclic. Circular paths trigger a topology-resolution exception.

### Stage 4: Property DNA Summary (The Projection)
*   **Description:** The complete graph state is projected into the highly optimized, seven-category `property_dna` document, calculating real-time composite health, risk, lifecycle, and AWE index numbers.
*   **Pipeline Input:** The current `KnowledgeGraphPath` and all active Passport Findings.
*   **Transformation Logic:**
    *   The DNA engine executes weighted scoring algorithms. A "Major" severity finding on a load-bearing column strips 40 points from the Structural Health sub-category.
    *   Risk models evaluate the decay curves of mechanical elements (e.g., an 11-year-old HVAC compressor is projected to have 4 years of remaining life, elevating risk to "MEDIUM").
    *   Confidence levels are updated based on evidence age and reliability weights.
*   **Pipeline Output:** A read-optimized, version-controlled JSON document representing the property's state profile.
*   **Stage Gate / Validation:** The DNA document hash must match the state-chain ledger check.

### Stage 5: AI Reasoning (The Brain)
*   **Description:** To turn raw numbers and paths into human-comprehensible narratives, the pipeline passes the assembled context to the Stratex AI Project Intelligence module.
*   **Pipeline Input:** A consolidated Retrieval-Augmented Generation (RAG) payload consisting of the Property DNA category data, the Knowledge Graph causal path, the Passport Ledger history, and relevant building standards (e.g., IRC 2021).
*   **Transformation Logic:**
    *   The prompt payload is injected with rigid **System Directives** that block speculation.
    *   The LLM is tasked with generating explaining rationales, consequences, next steps, and assumptions.
    *   The LLM outputs a strictly formatted JSON matching the `ExplanationSchema` fields.
    *   A secondary parser strips out any phrases that signal hallucinated certainty (e.g., "I am sure that...", "Undoubtedly...") and replaces them with standard, confidence-calibrated phrases.
*   **Pipeline Output:** Structured JSON containing the draft natural-language fields (Why this matters, Next steps, Assumptions, Unknowns) across Levels 1, 2, and 3.
*   **Stage Gate / Validation:** The output must contain zero fabricated parameters. If an attribute has no direct evidence linkage, its field value must be strictly written as `UNKNOWN` with confidence at 0.

### Stage 6: Human Explanation Generation (The Output)
*   **Description:** The final rendering step. The structured, AI-reasoned JSON is formatted into specific markdown layouts using the Template Registry, ready to be displayed in applications or embedded in reports.
*   **Pipeline Input:** Validated AI Reasoning JSON and the requested template ID (e.g., `ROOF_TEMPLATE_V1`).
*   **Transformation Logic:**
    *   The engine extracts the narrative blocks corresponding to the requested Explanation Level (Level 1 to 4).
    *   It resolves Markdown place-holders with specific property variables (e.g., replacement of `{size}` with `2,450 sq ft`).
    *   It attaches the raw, tabular Evidence Trace at the footer (Level 4 details) for structural transparency.
*   **Pipeline Output:** The final Markdown or HTML document tailored to the user profile.
*   **Stage Gate / Validation:** Visual rendering checks verify that no raw brackets or curly braces (e.g. `{}`) leak into the final viewport.

---

## 3. Error Handling & Fallback States

When data is missing or pipeline stages fail, the engine must never stall or output default "hallucinations". It falls back to safe states:

```
┌─────────────────────────────────┐
│     Critical Pipeline Error     │
└────────────────┬────────────────┘
                 │ (No active data / timeout / schema break)
                 ▼
┌─────────────────────────────────┐
│       DEGRADED MODE ACTIVE      │
│  - System State: UNKNOWN        │
│  - Confidence Score: 0%         │
│  - Narrative: "Data Unavailable"│
└─────────────────────────────────┘
```

1. **Missing Evidence / Incomplete Passport Records:**
   *   *Action:* The DNA Summary immediately marks the affected component as `UNKNOWN`.
   *   *AI Instruction:* The reasoning engine is instructed to explicitly state that an assessment could not be made due to missing physical inspections. It triggers a recommended next step: "Schedule a field verification mission."
2. **Knowledge Graph Disconnection:**
   *   *Action:* If a finding has no valid paths to other systems, the traversal is skipped, and "Related Systems" is set to an empty array. No imaginary links are drawn.
3. **AI Generation Timeout or Timeout Failures:**
   *   *Action:* If the AI reasoning step takes longer than 2.5 seconds or fails to return valid JSON, the pipeline falls back to a **Deterministic Rule-Based Explainer Engine**. This rule engine compiles pre-written template text based on the severity and component name (e.g., "Standard shingle damage identified. Action: Repair recommended.").
