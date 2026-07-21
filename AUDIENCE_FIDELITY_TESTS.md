# AUDIENCE FIDELITY TESTS
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Principles of Audience-Level Fidelity

The universal explanation layer generates narratives across **4 discrete stakeholders levels** (Homeowner, Contractor, Engineering, and Complete Trace). While tone, jargon, and depth vary to match stakeholder needs, all four outputs must map to the **same underlying truth**. 

Audience adaptation is strictly prohibited from:
*   Altering the canonical fact (e.g. if shingle damage is 5 shingles, Level 1 cannot say "some wear" and Level 3 say "10 split tabs").
*   Inflating or deflating the confidence value.
*   Altering, hiding, or falsifying the underlying physical provenance and evidence tracing.

---

## 2. The 4 Stakeholder Levels Defined

```
                   AUDIENCE LEVEL RESOLUTION & DETAILS
  ┌─────────────────────────────────────────────────────────────────┐
  │  LEVEL 1: HOMEOWNER                                             │
  │  - Jargon-Free, Calm, Educational, Non-Alarmist, Actionable     │
  ├─────────────────────────────────────────────────────────────────┤
  │  LEVEL 2: CONTRACTOR                                            │
  │  - Repair-Focused, Scope-Aware, Location-Bound, Materials Spec  │
  ├─────────────────────────────────────────────────────────────────┤
  │  LEVEL 3: TECHNICAL / ENGINEERING                               │
  │  - Quantitative, Physics-Based, Dimensional, Code Standards     │
  ├─────────────────────────────────────────────────────────────────┤
  │  LEVEL 4: COMPLETE EVIDENCE TRACE                               │
  │  - Raw Ledger IDs, Trace Chains, Cryptographic Checksums, Math  │
  └─────────────────────────────────────────────────────────────────┘
```

### LEVEL 1 — HOMEOWNER
*   **Target Audience:** Property owners, residents, buyers.
*   **Tone Guardrails:** Plain, empathetic, non-alarmist, educational. Avoid technical terms like "ASCE 7-22 wind-shear", "ASTM D3462 standards", or "micro-cracking apertures".
*   **Core Objective:** Explain what is wrong, why it matters in human terms (safety, cost, comfort), and what practical step to take next.

### LEVEL 2 — CONTRACTOR
*   **Target Audience:** Roofing, plumbing, HVAC, electrical, and structural contractors.
*   **Tone Guardrails:** Highly practical, scope-focused, material-oriented, location-bound.
*   **Core Objective:** Detail the mechanical defect, identify specific material standards for repair, and provide exact coordinate or course positions.

### LEVEL 3 — TECHNICAL / ENGINEERING
*   **Target Audience:** Civil/mechanical engineers, structural QA, energy auditors.
*   **Tone Guardrails:** Quantitative, precise, physics-based, referencing specific architectural or regulatory standards.
*   **Core Objective:** Provide raw dimensions, load ratings, telemetry values, and standard design limit violations.

### LEVEL 4 — COMPLETE EVIDENCE TRACE
*   **Target Audience:** Insurance auditors, compliance agencies, system algorithms.
*   **Tone Guardrails:** Structured, purely data-driven JSON payload. Contains zero natural language embellishment.
*   **Core Objective:** Supply the absolute blockchain-like proof chain (Origin Mission $\rightarrow$ Raw Evidence hashes $\rightarrow$ Passport Entry UUID $\rightarrow$ DNA category $\rightarrow$ KG Path $\rightarrow$ Math calculation).

---

## 3. Semantic Equivalence Verification Rules

To validate that tone adaptation does not distort underlying truth, the test harness runs three semantic consistency engines:

```
  ┌─────────────────────────────┐        ┌─────────────────────────────┐
  │ 1. Numeric Invariance Rule  ├───────►│ Extract and compare all raw │
  │                             │        │ quantities (e.g. "5", "22%")│
  └─────────────────────────────┘        └─────────────────────────────┘
  ┌─────────────────────────────┐        ┌─────────────────────────────┐
  │ 2. Confidence Band Lock     ├───────►│ Assert same confidence rating│
  │                             │        │ and band across Levels 1-3   │
  └─────────────────────────────┘        └─────────────────────────────┘
  ┌─────────────────────────────┐        ┌─────────────────────────────┐
  │ 3. LLM Fact-Cross Audit     ├───────►│ Ask QA evaluator model to   │
  │                             │        │ flag any factual divergence │
  └─────────────────────────────┘        └─────────────────────────────┘
```

1.  **Numeric Invariance Rule:** An automated parser extracts all raw quantities, percentages, dimensions, and times from Levels 1, 2, and 3. The test fails if any level contains contradictory metrics (e.g. if Level 1 says "5 damaged shingles" but Level 2 says "4 shingles").
2.  **Confidence Band Lock:** Programmatically asserts that the overall confidence percentage and certainty level tag (`HIGH`, `MEDIUM`, `LOW`) match identically across all levels.
3.  **Factual Cross-Audit:** The evaluation pipeline feeds the generated Levels 1, 2, and 3 text to an independent evaluation model. The evaluator checks whether the claims are semantically equivalent. Any added, hidden, or shifted facts are flagged as QA failures.

---

## 4. Golden Cross-Level Invariance Test Case: ROOF (RF-01)

This case proves that all levels describe the exact same underlying truth of 5 broken shingles with 95% confidence on the North Slope.

### A. Level 1 (Homeowner) Output
> **Conclusion:** Your roof has a minor section of shingle damage on the north slope.  
> **Supporting Evidence:** High-resolution photos from our recent drone survey showed exactly 5 cracked asphalt shingles.  
> **Confidence:** High (95%). This is based on clear optical proof taken under direct sunlight yesterday.  
> **Why this Matters:** Cracked shingles let rainwater seep beneath your roof. Over time, this leads to attic ceiling leaks, mold, and wood rot.  
> **Next Steps:** Have a licensed roofing contractor replace the 5 damaged shingles before winter.  
> **Related Systems:** Attic ceiling drywall, home insulation layers.  
> **Assumptions:** The shingles are 12-year-old standard asphalt shingles with typical weathering.  
> **Unknowns:** We cannot see the wood boards directly beneath the shingles without removing them.  

### B. Level 2 (Contractor) Output
> **Conclusion:** Localized mechanical fracture of 5 asphalt shingle tabs on the northeast quadrant, course 14.  
> **Supporting Evidence:** Flight ID `msn_1001`, high-res image `img_4021` showing tab delamination and hairline cracking.  
> **Confidence:** 95% based on visual observation with zero obstructions or shadows.  
> **Why this Matters:** Exposed underlayment creates a point of entry for rain, lowering water-tightness and threatening structural decking beneath.  
> **Next Steps:** Remove affected courses, replace with matching ASTM D3462 shingles, and reseal adjacent tabs with asphalt mastic.  
> **Related Systems:** Ridge cap vents, starter strip course, gutter run-off.  
> **Assumptions:** Plywood sheathing is standard 1/2-inch CDX.  
> **Unknowns:** Integrity of organic felt layer under the broken shingle tabs.  

### C. Level 3 (Technical / Engineering) Output
> **Conclusion:** Localized failure of asphalt shingles on the northeast slope due to thermal splitting and wind-shear delamination of tab adhesive layers.  
> **Supporting Evidence:** Photogrammetry telemetry (`img_4021`) indicating crack apertures of 1.5mm and loss of granular mineral layer.  
> **Confidence:** 95% calculated from dual-pass aerial optical capture at 2cm per-pixel resolution.  
> **Why this Matters:** The split tabs expose the asphalt-saturated organic felt layer. The decay rate of felt under UV exposure exceeds 0.5mm per month, leading to rapid moisture-barrier degradation.  
> **Next Steps:** Repair shingles to maintain wind uplift resistance of 110mph under ASCE 7-22 structural wind load standards.  
> **Related Systems:** Roof membrane, under-roof ventilation draft envelope.  
> **Assumptions:** Roof pitch is 6:12; structural dead load rating is 15 lbs/sq ft.  
> **Unknowns:** Dynamic load bearing capacity of structural rafters around the northeast slope interface.  

### D. Level 4 (Complete Trace) Output
```json
{
  "explanation_id": "exp_roof_001_v1",
  "property_id": "prop_99182_valley_heights",
  "tenant_id": "tn_4001_west_assets",
  "dna_version_referenced": 34,
  "system_category": "ROOF",
  "created_at": "2026-07-21T12:00:00Z",
  "updated_at": "2026-07-21T12:00:00Z",
  "overall_confidence_score": 95.0,
  "evidence_trace": {
    "origin_mission_ids": ["msn_1001_uav_thermal"],
    "evidence_ids": ["ev_9001_shingle_fracture_ortho"],
    "passport_entry_ids": ["pe_1201_roof_approved_finding"],
    "dna_node_paths": ["roof.shingles.physical_damage_pct"],
    "knowledge_graph_traversal_paths": [
      "ROOF_SHINGLES --[HAS_DEFECT]--> SHINGLE_DELAMINATION --[COULD_CAUSE]--> ATTIC_WATER_INTRUSION"
    ],
    "confidence_calculation": {
      "rs_base_reliability": 1.00,
      "dt_temporal_decay": 1.00,
      "fc_evidence_conflict": 1.00,
      "wc_system_coverage": 1.00,
      "overall": 95.00
    },
    "applicable_standards": [
      {
        "code_id": "ASTM-D3462",
        "title": "Standard Specification for Asphalt Shingles Made from Glass Felt and Surfaced with Mineral Granules"
      },
      {
        "code_id": "ASCE-7-22",
        "title": "Minimum Design Loads and Associated Criteria for Buildings and Other Structures"
      }
    ],
    "cryptographic_proof_chain": {
      "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
      "data_hash": "a4d8ef290b343ef2119c8f00db751bf870349ff0890bcfeef676239bc7a00f2e",
      "sha256_chain": "782cd4e0f34de9a3feef21087cb32de071bcfe89f78bcdeef90ab78bcdeef102"
    }
  }
}
```

---

## 5. Audience Fidelity Test Harness Acceptance Criteria

Audience validation passes only when:
*   **Zero-Divergence Rule:** Evaluator models return `DIVERGENCE_SCORE = 0.00` across all generated test runs.
*   **Perfect Numeric Lock:** Extracted integers and floats are 100% congruent across Levels 1-3.
*   **Level 4 Compliance:** JSON output validates against schema rules with no missing parameters.
