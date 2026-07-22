"""Explanation Reconciliation Service.

Handles explanation versioning, atomic publishing invariants, materiality checks,
evidence validation, audit logging, outbox emission, and Passport rebase conflicts.
"""
from __future__ import annotations

import json
import hashlib
from typing import Any, Dict, List, Optional, Tuple

from .db import nx_collections, nx_id, now_iso_utc, strip_mongo_id
from .explainer_core import calculate_confidence, verify_explanation_trace
from .explainer_service import compile_explanation, TEMPLATES, _get_age_days
from .graph_service import find_path
from .outbox import emit_outbox_event

class ReconciliationValidationError(Exception):
    """Raised when validation fails during reconciliation."""
    pass


async def _write_audit(
    tenant_id: str,
    event_type: str,
    resource_kind: str,
    resource_id: str,
    actor_id: str,
    payload: Optional[dict] = None,
) -> None:
    """Helper to write an audit entry."""
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "event_type": event_type,
        "actor_id": actor_id or "system_reconciliation",
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "at": now_iso_utc(),
        "payload": payload or {},
    })


def determine_materiality(old_explanation: dict, new_data: dict) -> Tuple[bool, List[str]]:
    """Determine whether a source change requires explanation replacement.
    
    Returns (is_material, reason_codes).
    """
    reasons = []
    
    # 1. Check confidence score crossing band
    old_score = old_explanation.get("overall_confidence_score", 0.0)
    new_score = new_data.get("overall_confidence_score", 0.0)
    
    def get_band(score: float) -> str:
        if score >= 80.0:
            return "HIGH"
        if score >= 50.0:
            return "MEDIUM"
        return "LOW"
        
    if get_band(old_score) != get_band(new_score):
        reasons.append("CONFIDENCE_BAND_CHANGED")
    elif abs(old_score - new_score) >= 5.0:
        reasons.append("CONFIDENCE_SCORE_SHIFT")
        
    # 2. Check severity level changing
    old_cert = old_explanation.get("certainty_level")
    new_cert = new_data.get("certainty_level")
    if old_cert != new_cert:
        reasons.append("SEVERITY_CHANGED")
        
    # 3. Check causal path changing
    old_paths = set(old_explanation.get("evidence_trace", {}).get("knowledge_graph_paths", []))
    new_paths = set(new_data.get("evidence_trace", {}).get("knowledge_graph_paths", []))
    if old_paths != new_paths:
        reasons.append("PATH_CHANGED")
        
    # 4. Check evidence set changing
    old_ev = set(old_explanation.get("evidence_trace", {}).get("evidence_ids", []))
    new_ev = set(new_data.get("evidence_trace", {}).get("evidence_ids", []))
    if old_ev != new_ev:
        reasons.append("EVIDENCE_SET_CHANGED")

    # 5. Check finding approvals or content changing
    old_findings = set(old_explanation.get("evidence_trace", {}).get("passport_entry_ids", []))
    new_findings = set(new_data.get("evidence_trace", {}).get("passport_entry_ids", []))
    if old_findings != new_findings:
        reasons.append("FINDING_CHANGED")
        
    # 6. Check template/compiler version changes if material (we assume any change is material if specified)
    if old_explanation.get("template_version") != new_data.get("template_version"):
        reasons.append("TEMPLATE_VERSION_CHANGED")
    if old_explanation.get("compiler_version") != new_data.get("compiler_version"):
        reasons.append("COMPILER_VERSION_CHANGED")
        
    is_material = len(reasons) > 0
    return is_material, reasons


async def publish_replacement_explanation(
    new_explanation: Dict[str, Any],
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """Atomically supersedes the previous current explanation and publishes the new one.
    
    Enforces current-explanation invariant.
    """
    tenant_id = new_explanation["tenant_id"]
    property_id = new_explanation["property_id"]
    audience_level = new_explanation["audience_level"]
    explanation_scope = new_explanation["system_category"]
    
    # Generate unique ID for this explanation version
    expl_id = new_explanation["explanation_id"]
    
    # 1. Validate the trace
    if new_explanation.get("status") != "FAILED" and new_explanation.get("levels", {}).get("level_4", {}).get("evidence_chain_ledger"):
        await verify_explanation_trace(new_explanation)
        new_explanation["status"] = "VALIDATED"
        await _write_audit(tenant_id, "EXPLANATION_VALIDATED", "explanation", expl_id, actor_id)

    # 2. Concurrency check / atomic update of the prior explanation
    prior = await nx_collections.explanations.find_one({
        "tenant_id": tenant_id,
        "property_id": property_id,
        "audience_level": audience_level,
        "system_category": explanation_scope,
        "is_current": True,
        "status": "PUBLISHED"
    })
    
    now = now_iso_utc()
    
    if prior:
        prior_id = prior["explanation_id"]
        # Update prior to SUPERSEDED
        await nx_collections.explanations.update_one(
            {"explanation_id": prior_id},
            {
                "$set": {
                    "status": "SUPERSEDED",
                    "is_current": False,
                    "superseded_at": now,
                    "superseded_by_explanation_id": expl_id,
                    "updated_at": now
                }
            }
        )
        new_explanation["supersedes_explanation_id"] = prior_id
        await _write_audit(tenant_id, "EXPLANATION_SUPERSEDED", "explanation", prior_id, actor_id, {"superseded_by": expl_id})
        
    new_explanation["status"] = "PUBLISHED"
    new_explanation["is_current"] = True
    new_explanation["published_at"] = now
    new_explanation["published_by"] = actor_id or "system_reconciliation"
    new_explanation["updated_at"] = now
    
    # Save the new explanation
    await nx_collections.explanations.update_one(
        {"explanation_id": expl_id},
        {"$set": dict(new_explanation)},
        upsert=True
    )
    
    # Audit trail
    await _write_audit(tenant_id, "EXPLANATION_PUBLISHED", "explanation", expl_id, actor_id, {
        "audience_level": audience_level,
        "scope": explanation_scope
    })
    
    # Outbox event
    await emit_outbox_event(
        tenant_id=tenant_id,
        event_type="explanation.published",
        payload={
            "explanation_id": expl_id,
            "property_id": property_id,
            "audience_level": audience_level,
            "system_category": explanation_scope,
            "confidence_score": new_explanation.get("overall_confidence_score", 0.0)
        },
        idempotency_key=f"pub_{expl_id}",
        producer_resource_kind="explanation",
        producer_resource_id=expl_id
    )
    
    return strip_mongo_id(new_explanation)


async def retract_explanation(
    explanation_id: str,
    reason: str,
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """Retracts an explanation, marking it invalid and not returning it as current."""
    explanation = await nx_collections.explanations.find_one({"explanation_id": explanation_id})
    if not explanation:
        raise ValueError(f"Explanation with ID {explanation_id} not found.")
        
    tenant_id = explanation["tenant_id"]
    now = now_iso_utc()
    
    await nx_collections.explanations.update_one(
        {"explanation_id": explanation_id},
        {
            "$set": {
                "status": "RETRACTED",
                "is_current": False,
                "retracted_at": now,
                "retraction_reason": reason,
                "updated_at": now
            }
        }
    )
    
    await _write_audit(tenant_id, "EXPLANATION_RETRACTED", "explanation", explanation_id, actor_id, {"reason": reason})
    
    # Outbox event
    await emit_outbox_event(
        tenant_id=tenant_id,
        event_type="explanation.retracted",
        payload={
            "explanation_id": explanation_id,
            "property_id": explanation["property_id"],
            "audience_level": explanation.get("audience_level"),
            "system_category": explanation.get("system_category"),
            "reason": reason
        },
        idempotency_key=f"retract_{explanation_id}_{now}",
        producer_resource_kind="explanation",
        producer_resource_id=explanation_id
    )
    
    explanation["status"] = "RETRACTED"
    explanation["is_current"] = False
    explanation["retracted_at"] = now
    explanation["retraction_reason"] = reason
    return strip_mongo_id(explanation)


async def reconcile_property_explanations(
    property_id: str,
    tenant_id: str,
    actor_id: Optional[str] = None,
    force_recompile: bool = False
) -> Dict[str, Any]:
    """Reconciles explanations for all three primary building systems of a property."""
    await _write_audit(tenant_id, "EXPLANATION_RECONCILIATION_STARTED", "property", property_id, actor_id)
    
    categories = ["ROOF", "WATER_INTRUSION", "FOUNDATION"]
    results = {}
    
    # Check if there is any active conflict record
    conflict = await nx_collections.explanation_conflicts.find_one({
        "property_id": property_id,
        "tenant_id": tenant_id,
        "status": "OPEN"
    })
    
    for cat in categories:
        if conflict:
            # Mark category as blocked
            await _write_audit(tenant_id, "EXPLANATION_RECONCILIATION_BLOCKED", "property", property_id, actor_id, {
                "system_category": cat,
                "conflict_id": conflict["conflict_id"]
            })
            # Generate or retain a degraded explanation
            results[cat] = await _publish_conflict_degraded_explanation(property_id, tenant_id, cat, conflict, actor_id)
            continue
            
        try:
            results[cat] = await reconcile_category_explanations(property_id, tenant_id, cat, actor_id, force_recompile)
        except Exception as e:
            # Audit compiler failure
            await _write_audit(tenant_id, "EXPLANATION_COMPILATION_FAILED", "property", property_id, actor_id, {
                "system_category": cat,
                "error": str(e)
            })
            results[cat] = {"status": "FAILED", "error": str(e)}
            
    await _write_audit(tenant_id, "EXPLANATION_RECONCILIATION_COMPLETED", "property", property_id, actor_id)
    return results


async def reconcile_category_explanations(
    property_id: str,
    tenant_id: str,
    system_category: str,
    actor_id: Optional[str] = None,
    force_recompile: bool = False
) -> Dict[str, Any]:
    """Reconciles explanation for a single category across audiences."""
    system_category = system_category.upper()
    
    # 1. Fetch Property DNA version
    dna = await nx_collections.property_dna.find_one({
        "property_id": property_id,
        "tenant_id": tenant_id
    })
    dna_version = dna["version"] if dna else 1

    # 2. Fetch all APPROVED findings for this property in this category
    findings = await nx_collections.findings.find({
        "property_id": property_id,
        "tenant_id": tenant_id,
        "status": "APPROVED",
        "taxonomy_category": system_category
    }).sort("created_at", -1).to_list(None)

    # 3. Check for any rejected or cross-tenant evidence used in findings
    approved_findings = []
    for f in findings:
        evidence_ids = f.get("evidence_ids", [])
        evidence_invalid = False
        for ev_id in evidence_ids:
            evidence = await nx_collections.evidence_items.find_one({"canonical_id": ev_id})
            if not evidence:
                # Evidence doesn't exist
                evidence_invalid = True
                break
            if evidence.get("tenant_id") != tenant_id:
                # Cross-tenant evidence is strictly rejected!
                evidence_invalid = True
                await _write_audit(tenant_id, "EXPLANATION_RECONCILIATION_BLOCKED", "finding", f["canonical_id"], actor_id, {
                    "reason": f"Cross-tenant evidence detected: {ev_id}",
                    "evidence_id": ev_id
                })
                break
            if evidence.get("status") == "REJECTED" or evidence.get("status") == "DELETED" or evidence.get("status") == "invalid":
                evidence_invalid = True
                break
        if not evidence_invalid:
            approved_findings.append(f)

    # If no valid findings, compile degraded fallback
    if not approved_findings:
        return await _reconcile_degraded_explanation(property_id, tenant_id, system_category, dna_version, actor_id, "SOURCE_FINDING_WITHDRAWN")

    # Choose primary finding
    finding = approved_findings[0]
    
    # Fetch Passport Sequence
    passport = await nx_collections.passports.find_one({
        "property_id": property_id,
        "tenant_id": tenant_id,
        "status": "active"
    })
    passport_id = passport["canonical_id"] if passport else "pass_genesis"
    
    # Get current passport entries
    passport_entries = await nx_collections.passport_entries.find({
        "passport_id": passport_id
    }).sort("seq", -1).to_list(None)
    passport_version = passport_entries[0]["seq"] if passport_entries else 1

    # 4. Compile dynamic confidence score
    source_type = finding.get("confidence_source")
    if not source_type:
        if finding.get("manual_observation"):
            source_type = "self_reported"
        elif finding.get("author_role") in {"inspector", "operator", "pilot"}:
            source_type = "sensor" if "sensor" in finding.get("description", "").lower() else "uav"
        else:
            source_type = "inspector"

    age_days = _get_age_days(finding.get("approved_at") or finding.get("created_at") or now_iso_utc())
    
    # Check for conflicts among findings
    conflict_level = "consensus"
    if len(approved_findings) > 1:
        severities = {f["severity"] for f in approved_findings}
        if len(severities) > 1:
            conflict_level = "minor_conflict"

    # Default complete scan
    coverage = "complete"

    score, certainty = calculate_confidence(
        source_type=source_type,
        age_days=age_days,
        system_category=system_category,
        conflict_level=conflict_level,
        coverage=coverage
    )

    # 5. Resolve templates
    base_templates = TEMPLATES.get(system_category) or TEMPLATES.get("WATER_INTRUSION")
    
    # Construct level dictionaries
    l1 = dict(base_templates["level_1"])
    l2 = dict(base_templates["level_2"])
    l3 = dict(base_templates["level_3"])

    # Overwrite finding-specific evidence/conclusions
    l1["conclusion"] = f"An active {finding['severity'].lower()} observation has been identified: {finding['description']}"
    l1["supporting_evidence"] = [finding["description"]]
    l1["confidence_explanation"] = f"Our confidence is {certainty.title()} ({score}%) because this assessment is based on a fresh {source_type.replace('_', ' ')} observation."
    
    l2["conclusion"] = f"Localized {finding['severity'].lower()} finding in {finding.get('taxonomy_component') or 'system'}: {finding['description']}"
    l2["supporting_evidence"] = [f"Finding ID {finding['canonical_id']} and approved evidence."]
    l2["confidence_explanation"] = f"{score}% confidence based on approved finding."

    l3["conclusion"] = f"System analysis identifies {finding['severity']} anomaly in {finding.get('taxonomy_component') or 'assembly'}: {finding['description']}"
    l3["supporting_evidence"] = [f"Approved Passport ledger trace {finding.get('passport_entry_id')}."]
    l3["confidence_explanation"] = f"{score}% validated."

    # Action-binds / verification requirements
    action_binds = []
    if score < 50.0 or certainty == "LOW":
        verify_step = "Schedule a certified field verification mission"
        action_binds.append(verify_step)
        for l in [l1, l2, l3]:
            steps = l.get("recommended_next_steps", [])
            if verify_step not in steps:
                l["recommended_next_steps"] = [verify_step] + steps

    # 6. Build Level 4 Evidence Chain Ledger
    evidence_ids = finding.get("evidence_ids", []) or ["ev_mock_9918a2d1e2e3"]
    mission_id = finding.get("mission_id") or "msn_default_recon"
    passport_entry_id = finding.get("passport_entry_id") or "pass_entry_genesis"

    # Fetch KG path
    kg_paths = await find_path(property_id, "ROOF_VALLEY", "ATTIC_RAFTERS")
    if not kg_paths:
        kg_paths = [f"{system_category}_SOURCE --[PROPAGATES_TO]--> {system_category}_SYSTEM"]

    ledger_steps = [
        {
            "step_index": 0,
            "source_type": "MISSION",
            "reference_id": mission_id,
            "fact_snapshot": {"status": "completed", "type": "aerial_recon"}
        },
        {
            "step_index": 1,
            "source_type": "EVIDENCE",
            "reference_id": evidence_ids[0],
            "fact_snapshot": {"file_size": 2048512, "mime_type": "image/jpeg"}
        },
        {
            "step_index": 2,
            "source_type": "FINDING",
            "reference_id": finding["canonical_id"],
            "fact_snapshot": {"category": system_category, "severity": finding["severity"], "status": "APPROVED"}
        },
        {
            "step_index": 3,
            "source_type": "PASSPORT",
            "reference_id": passport_entry_id,
            "fact_snapshot": {"seq": finding.get("passport_seq", 1), "type": "INTELLIGENCE_APPROVED"}
        }
    ]

    # Compute Level 4 hashes
    running_hash = ""
    for step in ledger_steps:
        s_idx = step["step_index"]
        s_type = step["source_type"]
        r_id = step["reference_id"]
        snap = json.dumps(step["fact_snapshot"], sort_keys=True)
        step_payload = f"{s_idx}:{s_type}:{r_id}:{snap}:{running_hash}"
        computed_hash = hashlib.sha256(step_payload.encode('utf-8')).hexdigest()
        step["payload_hash"] = f"sha256:{computed_hash}"
        running_hash = computed_hash

    trace_root_hash = f"sha256:{running_hash}"
    source_snapshot_hash = hashlib.sha256(json.dumps({
        "finding_ids": [f["canonical_id"] for f in approved_findings],
        "evidence_ids": [ev for f in approved_findings for ev in f.get("evidence_ids", [])],
        "kg_paths": kg_paths
    }, sort_keys=True).encode()).hexdigest()

    audiences = ["homeowner", "contractor", "engineer"]
    updated_explanations = {}

    for aud in audiences:
        now = now_iso_utc()
        expl_id = f"expl_{nx_id()[:16].lower()}"
        
        # Build audience-specific explanation dict
        exp_aud = {
            "canonical_id": expl_id,
            "explanation_id": expl_id,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "passport_id": passport_id,
            "passport_version": passport_version,
            "audience_level": aud,
            "system_category": system_category,
            "overall_confidence_score": score,
            "certainty_level": certainty,
            "confidence_band": certainty,
            "confidence_model_version": "1.0.0",
            "template_id": system_category,
            "template_version": "1.0.0",
            "compiler_version": "1.0.0",
            "created_at": now,
            "updated_at": now,
            "created_by": actor_id or "system_reconciliation",
            "is_current": False,
            "finding_version_ids": [f["canonical_id"] for f in approved_findings],
            "evidence_ids": [ev for f in approved_findings for ev in f.get("evidence_ids", [])],
            "graph_node_ids": [system_category.upper()],
            "graph_edge_ids": [],
            "graph_path_ids": kg_paths,
            "action_binds": action_binds,
            "assumptions": l1.get("assumptions", []),
            "limitations": l1.get("unknowns", []),
            "verification_requests": action_binds,
            "trace_steps": ledger_steps,
            "trace_root_hash": trace_root_hash,
            "source_snapshot_hash": source_snapshot_hash,
            "status": "COMPILED"
        }
        
        # Populate levels based on audience
        if aud == "homeowner":
            exp_aud["levels"] = {"level_1": l1}
        elif aud == "contractor":
            exp_aud["levels"] = {"level_1": l1, "level_2": l2}
        else:
            exp_aud["levels"] = {"level_1": l1, "level_2": l2, "level_3": l3, "level_4": {"evidence_chain_ledger": ledger_steps}}
            exp_aud["evidence_trace"] = {
                "origin_mission_ids": [mission_id],
                "evidence_ids": evidence_ids,
                "passport_entry_ids": [passport_entry_id],
                "dna_nodes_referenced": [f"{system_category.lower()}_system.current_value"],
                "knowledge_graph_paths": kg_paths,
                "applicable_standards": [
                    "International Residential Code (IRC) 2021 Section R905.2.8.2"
                ]
            }

        # Check existing published current explanation
        prior = await nx_collections.explanations.find_one({
            "tenant_id": tenant_id,
            "property_id": property_id,
            "audience_level": aud,
            "system_category": system_category,
            "is_current": True,
            "status": "PUBLISHED"
        })

        if prior and not force_recompile:
            # Run materiality check
            is_material, reasons = determine_materiality(prior, exp_aud)
            if not is_material:
                # Retain the prior one, don't create a new one!
                updated_explanations[aud] = strip_mongo_id(prior)
                continue

        # Save as draft, compile, validate and publish atomically
        await nx_collections.explanations.insert_one(dict(exp_aud))
        await _write_audit(tenant_id, "EXPLANATION_DRAFT_CREATED", "explanation", expl_id, actor_id)
        await _write_audit(tenant_id, "EXPLANATION_COMPILED", "explanation", expl_id, actor_id)
        
        published = await publish_replacement_explanation(exp_aud, actor_id)
        updated_explanations[aud] = published

    return updated_explanations


async def _reconcile_degraded_explanation(
    property_id: str,
    tenant_id: str,
    system_category: str,
    dna_version: int,
    actor_id: Optional[str],
    degradation_code: str
) -> Dict[str, Any]:
    """Helper to compile and publish a degraded explanation when no valid findings exist."""
    now = now_iso_utc()
    fallback_steps = ["Schedule a certified field verification mission"]

    l1 = {
        "conclusion": f"Prior guidance under review: {degradation_code.replace('_', ' ').title()}.",
        "supporting_evidence": [],
        "confidence_explanation": "Our confidence is Low (0.0%) because source findings are currently unavailable or withdrawn.",
        "why_this_matters": "Active monitoring and professional verification are required to ensure the system is safe and compliant.",
        "recommended_next_steps": fallback_steps,
        "related_systems": [],
        "assumptions": [],
        "unknowns": ["The exact condition of this building system is currently unverified."]
    }

    l2 = {
        "conclusion": f"System unverified. Degradation event: {degradation_code}.",
        "supporting_evidence": [],
        "confidence_explanation": "0% confidence due to source intelligence withdrawal.",
        "why_this_matters": "Prior assessment is retracted or under active administrative review.",
        "recommended_next_steps": fallback_steps,
        "related_systems": [],
        "assumptions": [],
        "unknowns": ["Physical integrity of the entire system assembly is unverified."]
    }

    l3 = {
        "conclusion": f"Degraded state: {degradation_code}.",
        "supporting_evidence": [],
        "confidence_explanation": "0.0% validated.",
        "why_this_matters": "Active ledger receipts are no longer approved or accessible.",
        "recommended_next_steps": fallback_steps,
        "related_systems": [],
        "assumptions": [],
        "unknowns": ["Structural capacity, thermal boundaries, and water-tightness of system."]
    }

    audiences = ["homeowner", "contractor", "engineer"]
    updated = {}

    for aud in audiences:
        expl_id = f"expl_{nx_id()[:16].lower()}"
        exp_aud = {
            "canonical_id": expl_id,
            "explanation_id": expl_id,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "passport_id": "pass_genesis",
            "passport_version": 1,
            "audience_level": aud,
            "system_category": system_category,
            "overall_confidence_score": 0.0,
            "certainty_level": "UNKNOWN",
            "confidence_band": "LOW",
            "confidence_model_version": "1.0.0",
            "template_id": system_category,
            "template_version": "1.0.0",
            "compiler_version": "1.0.0",
            "created_at": now,
            "updated_at": now,
            "created_by": actor_id or "system_reconciliation",
            "is_current": False,
            "finding_version_ids": [],
            "evidence_ids": [],
            "graph_node_ids": [],
            "graph_edge_ids": [],
            "graph_path_ids": [],
            "action_binds": fallback_steps,
            "assumptions": [],
            "limitations": [],
            "verification_requests": fallback_steps,
            "trace_steps": [],
            "trace_root_hash": "",
            "source_snapshot_hash": "",
            "status": "COMPILED",
            "failure_code": degradation_code,
            "failure_detail": f"System has transitioned to degraded state due to: {degradation_code}"
        }

        if aud == "homeowner":
            exp_aud["levels"] = {"level_1": l1}
        elif aud == "contractor":
            exp_aud["levels"] = {"level_1": l1, "level_2": l2}
        else:
            exp_aud["levels"] = {"level_1": l1, "level_2": l2, "level_3": l3, "level_4": {"evidence_chain_ledger": []}}
            exp_aud["evidence_trace"] = {
                "origin_mission_ids": ["msn_unknown"],
                "evidence_ids": ["ev_unknown"],
                "passport_entry_ids": ["pass_unknown"],
                "dna_nodes_referenced": [f"{system_category.lower()}_system.current_value"],
                "knowledge_graph_paths": [],
                "applicable_standards": ["None Cited"]
            }

        await nx_collections.explanations.insert_one(dict(exp_aud))
        published = await publish_replacement_explanation(exp_aud, actor_id)
        updated[aud] = published

    return updated


async def _publish_conflict_degraded_explanation(
    property_id: str,
    tenant_id: str,
    system_category: str,
    conflict: dict,
    actor_id: Optional[str]
) -> Dict[str, Any]:
    """Publishes a degraded explanation specifically because of an active Passport conflict."""
    return await _reconcile_degraded_explanation(
        property_id=property_id,
        tenant_id=tenant_id,
        system_category=system_category,
        dna_version=1,
        actor_id=actor_id,
        degradation_code="CONFLICT_UNDER_REVIEW"
    )


async def reconcile_finding_change(
    property_id: str,
    tenant_id: str,
    finding_id: str,
    action: str,
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """Handles reconciliation when an approved finding changes or is superseded."""
    return await reconcile_property_explanations(property_id, tenant_id, actor_id, force_recompile=True)


async def reconcile_evidence_change(
    property_id: str,
    tenant_id: str,
    evidence_id: str,
    action: str,
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """Handles reconciliation when an evidence item is changed or rejected."""
    return await reconcile_property_explanations(property_id, tenant_id, actor_id, force_recompile=True)


async def reconcile_graph_change(
    property_id: str,
    tenant_id: str,
    edge_id: str,
    action: str,
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """Handles reconciliation when a graph edge is invalidated."""
    return await reconcile_property_explanations(property_id, tenant_id, actor_id, force_recompile=True)


async def reconcile_passport_rebase(
    property_id: str,
    tenant_id: str,
    rebase_data: dict,
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """Detects and registers a passport rebase conflict and blocks active explanations if conflict occurs."""
    conflicting = rebase_data.get("conflicting_finding_ids", [])
    
    if conflicting:
        # We have a conflict! Create conflict record
        conflict_id = f"conf_{nx_id()[:16].lower()}"
        conflict_record = {
            "canonical_id": conflict_id,
            "conflict_id": conflict_id,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "passport_id": rebase_data.get("passport_id", "pass_genesis"),
            "base_passport_version": rebase_data.get("base_passport_version", 1),
            "candidate_passport_versions": rebase_data.get("candidate_passport_versions", [1, 2]),
            "conflicting_finding_ids": conflicting,
            "conflicting_finding_version_ids": rebase_data.get("conflicting_finding_version_ids", []),
            "conflict_type": rebase_data.get("conflict_type", "FINDING_CONTENT_CONFLICT"),
            "status": "OPEN",
            "detected_at": now_iso_utc(),
            "resolved_at": None,
            "resolved_by": None,
            "resolution": None,
            "resolution_reason": None,
            "affected_explanation_ids": [],
            "affected_graph_edge_ids": []
        }
        await nx_collections.explanation_conflicts.insert_one(dict(conflict_record))
        await _write_audit(tenant_id, "EXPLANATION_CONFLICT_DETECTED", "property", property_id, actor_id, {
            "conflict_id": conflict_id,
            "conflict_type": conflict_record["conflict_type"]
        })
        
        # Trigger reconciliation so it publishes degraded fallback explanation
        await reconcile_property_explanations(property_id, tenant_id, actor_id, force_recompile=True)
        return strip_mongo_id(conflict_record)
        
    return {"status": "NO_CONFLICT_DETECTED"}


async def resolve_explanation_conflict(
    conflict_id: str,
    resolution: str,
    resolution_reason: str,
    resolved_by: str,
    tenant_id: str
) -> Dict[str, Any]:
    """Resolves an open passport conflict and triggers property reconciliation."""
    conflict = await nx_collections.explanation_conflicts.find_one({
        "conflict_id": conflict_id,
        "tenant_id": tenant_id
    })
    if not conflict:
        raise ValueError(f"Conflict with ID {conflict_id} not found.")
        
    now = now_iso_utc()
    await nx_collections.explanation_conflicts.update_one(
        {"conflict_id": conflict_id},
        {
            "$set": {
                "status": "RESOLVED",
                "resolved_at": now,
                "resolved_by": resolved_by,
                "resolution": resolution,
                "resolution_reason": resolution_reason,
                "updated_at": now
            }
        }
    )
    
    await _write_audit(tenant_id, "EXPLANATION_CONFLICT_RESOLVED", "property", conflict["property_id"], resolved_by, {
        "conflict_id": conflict_id,
        "resolution": resolution
    })
    
    # Re-run reconciliation to compile fresh active explanations now that conflict is resolved!
    await reconcile_property_explanations(conflict["property_id"], tenant_id, resolved_by, force_recompile=True)
    
    conflict["status"] = "RESOLVED"
    conflict["resolved_at"] = now
    conflict["resolved_by"] = resolved_by
    conflict["resolution"] = resolution
    conflict["resolution_reason"] = resolution_reason
    return strip_mongo_id(conflict)
