# EXPLANATION REPRODUCIBILITY
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Principles of Deterministic Explanation

Traditional AI architectures suffer from non-deterministic variance, producing different reasoning, metrics, and tones when presented with the same query twice. 

The Stratex-2 platform implements a strict **Reproducibility Mandate**: **Regenerating an explanation from the same frozen inputs must produce semantically equivalent facts, confidence, limitations, and recommendations.**

We achieve this by binding every explanation document to an immutable metadata block defining the exact versions, configs, and inputs used during its compilation.

---

## 2. The 11 Input Vectors of Reproducibility

To recreate any explanation, the regeneration pipeline must freeze and supply exactly 11 structural input vectors:

```
  ┌────────────────────────────────────────────────────────┐
  │              11 REPRODUCIBILITY INPUT VECTORS          │
  ├────────────────────────────────────────────────────────┤
  │ 1. Explanation Schema Version (v1.0, v2.0, etc.)       │
  │ 2. Prompt / Template Version (e.g. ROOF_v1.04)         │
  │ 3. Model Identifier (e.g. claude-sonnet-4.6)           │
  │ 4. Model Configuration (temperature: 0.0, top_p)       │
  │ 5. Passport Ledger Version (Tx Sequence ID)            │
  │ 6. Property DNA Version (Monotonically rising integer) │
  │ 7. Knowledge Graph Snapshot (Git/DB SHA)               │
  │ 8. Evidence Identifiers (Array of UUIDs and Hashes)     │
  │ 9. Confidence-Model Version (Locked algorithm code ID) │
  │ 10. Standards References (ASTM/ASCE identifiers)       │
  │ 11. Generation Timestamp (ISO 8601 UTC)                │
  └────────────────────────────────────────────────────────┘
```

1.  **Explanation Schema Version:** Dictates the JSON structure mapping and field compliance checks (e.g., Draft 2020-12 Schema v1.0).
2.  **Prompt / Template Version:** The specific structural template utilized from `EXPLANATION_TEMPLATES.md` (e.g. `ROOF_v1.4`).
3.  **Model Identifier:** The exact LLM model string (e.g., `claude-sonnet-4.6`, `gpt-5.5`).
4.  **Model Configuration:** Hyperparameters locked to deterministic seeds (e.g. `temperature = 0.00`, `max_tokens = 2000`, `top_p = 1.00`).
5.  **Passport Version:** The unique transaction number representing the active state of the Passport ledger.
6.  **Property DNA Version:** The version integer of the active DNA projection.
7.  **Knowledge Graph Snapshot:** The database timestamp or transaction ID capturing the exact relationship paths active during generation.
8.  **Evidence Identifiers:** The complete list of ingested evidence file paths and their associated cryptographic SHA-256 hashes.
9.  **Confidence-Model Version:** The software release version of the confidence algorithm code.
10. **Standards References:** The specific building code, municipal standard, or regulatory references used during compilation.
11. **Generation Timestamp:** The creation time (ISO 8601 UTC) used to calculate temporal decay relative to evidence ages.

---

## 3. The Semantic Equivalence Audit Protocol

The validation pipeline asserts semantic equivalence by checking 5 core areas across subsequent generation passes:

```
  PASS 1: Raw Output Compile     ───►  [Semantic Equivalence Audit Engine]  ◄───  PASS 2: Regenerated Compile
                                                   │
                ┌──────────────────────────────────┼──────────────────────────────────┐
                ▼                                  ▼                                  ▼
      [ Factual Congruency ]            [ Confidence Lock ]               [ Recommendation Match ]
      - Extract entities & values       - Compare score percentages       - Compare action verbs
      - Assert 100% equivalence         - Assert identical bands          - Verify identical scope
```

### A. Factual Congruency
An entity extraction model parses both explanations (Pass 1 and Pass 2) and lists all core assertions (e.g. "5 damaged shingles on the northeast slope"). The test fails if any entity or quantity changes across runs.

### B. Confidence Match
The system asserts that both calculated confidence percentages and their natural-language explanation notes are identical.

### C. Recommendation Match
The system compares the generated "Next Steps". While minor phrasing can vary slightly under LLM limits, the core actionable scope (e.g. "Replace shingles using ASTM-D3462 materials") must remain identical.

### D. Limitation & Unknowns Invariance
The identified physical limitations (e.g., "Under-deck sheathing is obscured from view") must remain congruent.

---

## 4. Reproducibility Test Suite Execution

The automated test harness executes the following check:

```bash
# Programmatic command to execute a reproducibility comparison
python3 -m pytest tests/test_reproducibility.py \
  --property-id="prop_99182_valley_heights" \
  --schema-version="1.0" \
  --template-version="ROOF_v1.0" \
  --model-id="claude-sonnet-4.6" \
  --passes=5
```

If any of the 5 runs produces a factual divergence or confidence mismatch, the test fails, and the prompt configuration must be adjusted for higher determinism.
