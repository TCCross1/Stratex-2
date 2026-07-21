"""Stratex Intelligence Explainer Engine™ Core Mathematics & Trace Verification.

Implements Centcom Directive 013 confidence mathematical models and cryptographic 
evidence hash-chain verification logic.
"""
from __future__ import annotations

import math
import json
import hashlib
from typing import Any, Dict, Tuple, List, Optional
from .db import nx_collections


class TraceValidationError(Exception):
    """Raised when an evidence trace is invalid, incomplete, or tampered."""
    pass


def calculate_confidence(
    source_type: str,
    age_days: float,
    system_category: str,
    conflict_level: str = "consensus",
    coverage: str = "complete",
) -> Tuple[float, str]:
    """Calculate confidence score C and its corresponding certainty level.
    
    Formula: C = R_s * D_t * F_c * W_c * 100
    """
    # 1. Base Source Reliability (R_s)
    src_norm = (source_type or "").strip().lower()
    if src_norm in {
        "certified inspector / engineer",
        "certified_inspector",
        "inspector",
        "engineer",
        "certified",
    }:
        r_s = 1.00
    elif src_norm in {
        "calibrated telemetric sensor",
        "calibrated_sensor",
        "sensor",
        "calibrated",
    }:
        r_s = 0.95
    elif src_norm in {
        "high-res vision / thermal uav",
        "uav",
        "drone",
        "high_res_vision",
        "thermal_uav",
    }:
        r_s = 0.85
    elif src_norm in {
        "self-reported / homeowner",
        "homeowner",
        "self_reported",
        "self",
    }:
        r_s = 0.40
    else:
        # "Missing / Unverified Data"
        r_s = 0.00

    if r_s == 0.00:
        return 0.0, "UNKNOWN"

    # 2. Temporal Decay (D_t = e^(-lambda * t))
    cat_norm = (system_category or "").strip().upper()
    if cat_norm in {"WATER_INTRUSION", "HVAC"}:
        lambda_val = 0.0038
    elif cat_norm in {"ROOF", "WINDOWS", "OPENINGS"}:
        lambda_val = 0.00095
    else:
        # Slow-Changing Systems (Foundation, Electrical Panel, etc.)
        lambda_val = 0.00038

    t = max(0.0, float(age_days))
    d_t = math.exp(-lambda_val * t)

    # 3. Evidence Conflict Multiplier (F_c)
    conf_norm = (conflict_level or "").strip().lower()
    if conf_norm in {"consensus", "agree"}:
        f_c = 1.00
    elif conf_norm in {"minor_conflict", "minor", "mild"}:
        f_c = 0.85
    elif conf_norm in {"major_conflict", "major", "severe"}:
        f_c = 0.50
    else:
        f_c = 1.00

    # 4. System Coverage Weight (W_c)
    cov_norm = (coverage or "").strip().lower()
    if cov_norm in {"complete scan", "complete", "full"}:
        w_c = 1.00
    elif cov_norm in {"representative sample", "representative", "sample"}:
        w_c = 0.80
    elif cov_norm in {"partial scan", "partial", "localized"}:
        w_c = 0.50
    else:
        w_c = 1.00

    # 5. Compute C
    score = r_s * d_t * f_c * w_c * 100.0
    # Bound score between 0.0 and 100.0
    score = max(0.0, min(100.0, score))
    # Round to 1 decimal place as standard
    score = round(score, 1)

    # Certainty Level mapping
    if score >= 80.0:
        certainty = "HIGH"
    elif score >= 50.0:
        certainty = "MEDIUM"
    else:
        certainty = "LOW"

    return score, certainty


async def verify_explanation_trace(explanation: dict) -> bool:
    """Verifies that the explanation has a complete, un-tampered evidence trace.
    
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
        passport_entry = await nx_collections.passport_entries.find_one({"canonical_id": entry_id})
        if not passport_entry:
            raise TraceValidationError(f"Referenced Passport Entry {entry_id} not found in database.")
        
        status = passport_entry.get("status") or passport_entry.get("payload", {}).get("status")
        # In findings approval, the finding's status is APPROVED, and the entry's type is INTELLIGENCE_APPROVED
        # To be robust, if it's entry_type == "INTELLIGENCE_APPROVED", it represents an approved entry,
        # but let's check status as well.
        if passport_entry.get("entry_type") != "INTELLIGENCE_APPROVED" and status != "APPROVED" and passport_entry.get("status") != "APPROVED":
            raise TraceValidationError(f"Referenced Passport Entry {entry_id} is not APPROVED.")
            
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
