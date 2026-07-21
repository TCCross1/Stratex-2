# EVIDENCE TRACE SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 013 · OPERATION INTELLIGENCE EXPLAINER
**Status:** DESIGN COMPLETE  
**Scope:** Cryptographic data lineage, evidence binding, and path trace validation specs.

---

## 1. Principles of absolute Traceability

To fulfill the primary engineering law of **"No explanation without evidence; no recommendation without rationale,"** the Stratex platform implements a hardened, cryptographically verified lineage tracking system.

Every explanation output must be structurally linked to its physical origin. This is accomplished by compiling an **Evidence Trace Node** that accompanies the explanation. There are eight mandatory elements that must be exposed:

1.  **Origin Mission:** The physical mission during which the data was collected.
2.  **Evidence IDs:** The direct raw file or database attachment IDs (images, thermal, sensor logs).
3.  **Passport Entries:** The canonical Passport Ledger entry IDs holding the approved findings.
4.  **DNA Nodes:** The specific path nodes within the Property DNA object referenced.
5.  **Knowledge Graph Paths:** The causal relationships traversed to link the finding to other systems.
6.  **Confidence Calculations:** The exact mathematical variables and weights used.
7.  **Applicable Standards:** The regulatory codes or building guidelines referenced.
8.  **Cryptographic Proof (No Hidden Reasoning):** A sha256 hash-chain validating the entire path.

---

## 2. Evidence Trace Architecture & Lineage Mapping

Below is the structured data lineage showing how raw field assets are linked to structural, model-based explanations:

```
  ┌────────────────────────────────────────────────────────┐
  │ 1. Origin Mission (msn_id)                             │
  └───────────────────────────┬────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 2. Raw Evidence Files & Sensors (evidence_id, hashes)   │
  └───────────────────────────┬────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 3. Canonical Passport Entries (passport_id, entry_id)  │
  └───────────────────────────┬────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 4. Property DNA Nodes (dna_category.field)             │
  └───────────────────────────┬────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 5. Knowledge Graph Paths (node --[REL]--> node)        │
  └───────────────────────────┬────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 6. AI & Engineering Rationale                          │
  └────────────────────────────────────────────────────────┘
```

### The 8 Mandatory Trace Elements Detailed

#### A. Origin Mission Binds
Every trace must specify the starting physical mission ID (`origin_mission_ids`). These reference records inside the nextgen `missions` collection.
*   *Example:* `msn_10202_roof_thermal_flyover`
*   *Data Binds:* Timestamp, inspector user ID, weather metadata, and drone telemetry files.

#### B. Evidence ID Pinning
Direct references to raw files and sensor timeseries (`evidence_ids`).
*   *Example:* `ev_file_9a82f1b2c3d4`
*   *Data Binds:* Grid coordinates, file MIME type, file size, and the file's SHA-256 hash.

#### C. Passport Ledger Pinning
The exact canonical Passport Ledger entry IDs (`passport_entry_ids`) that authorized the raw evidence.
*   *Example:* `pass_entry_00994f2b`
*   *Data Binds:* QA tier, reviewer signature, approval timestamp, and consensus status.

#### D. DNA Node Paths
A dot-notation path directly referencing the updated fields in the property's DNA collection (`dna_nodes_referenced`).
*   *Example:* `health.moisture.current_value`, `risk.moisture_exposure.current_value`

#### E. Knowledge Graph Traversal Paths
The sequential traversal steps across the Knowledge Graph (`knowledge_graph_paths`). It documents how a fault in one system propagates to other systems.
*   *Format:* `SystemA_Component1 --[RELATIONSHIP_TYPE]--> SystemB_Component2`
*   *Example:* `ROOF_SHINGLES --[DRAINS_TO]--> ATTIC_RAFTERS --[TOUCHES]--> CEILING_DRYWALL`

#### F. Confidence Calculations
A structured sub-block defining the reliability values, data age decay variables, and source weights used to compute the final confidence percentage. (See `CONFIDENCE_EXPLANATIONS.md` for the complete mathematical models).

#### G. Applicable Standards
Direct references to official building codes, structural engineering specs, or ASTM standards (`applicable_standards`).
*   *Example:* `International Residential Code (IRC) 2021 Section R905.2.8.2 (Valleys)`

#### H. Cryptographic Verification (No Hidden Reasoning)
To ensure that no AI or human operator has fabricated a conclusion or bypassed the evidence ledger, the Explainer Engine calculates an **Evidence Chain Hash**.
Each step in the trace is serialized and combined into a secure hash-chain:

$$H_0 = \text{SHA256}(\text{Origin Mission ID} + \text{Evidence IDs})$$

$$H_1 = \text{SHA256}(H_0 + \text{Passport Entry IDs} + \text{DNA Nodes})$$

$$H_{\text{final}} = \text{SHA256}(H_1 + \text{KG Paths} + \text{Confidence Score} + \text{Standards})$$

The $H_{\text{final}}$ is stored inside the `intelligence_explanations` document as `payload_hash`. Any modification to the source evidence, passport ledger, or the reasoning text will break the hash verification, exposing unauthorized or untraceable reasoning.

---

## 3. The Trace Verification Algorithm

The Stratex platform executes the following verification algorithm on the backend whenever an explanation is loaded, guaranteeing the integrity of the data trace:

```python
def verify_explanation_trace(explanation: dict) -> bool:
    """
    Verifies that the explanation has a complete, un-tampered evidence trace.
    Returns True if valid, raises TraceValidationError on failure.
    """
    trace = explanation.get("evidence_trace", {})
    levels = explanation.get("levels", {})
    
    # Rule 1: No empty trace elements permitted
    required_keys = [
        "origin_mission_ids", "evidence_ids", "passport_entry_ids",
        "dna_nodes_referenced", "knowledge_graph_paths", "applicable_standards"
    ]
    for key in required_keys:
        if not trace.get(key) or len(trace[key]) == 0:
            raise TraceValidationError(f"Missing mandatory trace element: {key}")
            
    # Rule 2: Verify Passport entries are APPROVED in database
    for entry_id in trace["passport_entry_ids"]:
        passport_entry = db.passport_entries.find_one({"canonical_id": entry_id})
        if not passport_entry:
            raise TraceValidationError(f"Referenced Passport Entry {entry_id} not found in database.")
        if passport_entry.get("status") != "APPROVED":
            raise TraceValidationError(f"Referenced Passport Entry {entry_id} is in status: {passport_entry.get('status')}. Must be APPROVED.")
            
    # Rule 3: Re-calculate and verify the Step-Ledger Hashes (Level 4 verification)
    ledger_steps = levels.get("level_4", {}).get("evidence_chain_ledger", [])
    if not ledger_steps:
        raise TraceValidationError("Missing Level 4 Evidence Chain Ledger.")
        
    running_hash = ""
    for step in sorted(ledger_steps, key=lambda x: x["step_index"]):
        step_index = step["step_index"]
        source_type = step["source_type"]
        ref_id = step["reference_id"]
        snapshot = json.dumps(step["fact_snapshot"], sort_keys=True)
        
        # Calculate expected step hash
        step_payload = f"{step_index}:{source_type}:{ref_id}:{snapshot}:{running_hash}"
        computed_hash = hashlib.sha256(step_payload.encode('utf-8')).hexdigest()
        
        if step["payload_hash"] != f"sha256:{computed_hash}":
            raise TraceValidationError(f"Hash mismatch at Level 4 ledger step {step_index}. Chain of custody is compromised.")
            
        running_hash = computed_hash
        
    return True
```
