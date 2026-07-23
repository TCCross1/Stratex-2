"""Property Intelligence Engine — Directive 007.

Approved intelligence objects (PIOs) are the SINGLE source of truth for
reports, Passport, AWE aggregates, timeline, twin, and downstream
recommendations. Reports are projections; they never author values.

Route surface: `/api/nextgen/v1/intelligence/*`.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from ..approval_policy import evaluate_approval_policy
from ..auth import NxSession, nx_session
from ..db import now_iso_utc, nx_collections, nx_id, strip_mongo_id
from ..governed_publish_service import governed_publish, load_expected_state
from ..outbox import emit_outbox_event
from ..passport_errors import (
    IdempotencyConflictError,
    MissingExpectedStateError,
    PassportAppendError,
    StaleExpectedStateError,
    TransactionUnavailableError,
)
from ..taxonomy import (
    AWE_CATEGORIES, BUILDING_SYSTEMS, PRIORITY, REPORT_TEMPLATES,
    RISK_LEVEL, RISK_TIER, SEVERITY, TIMELINE_KINDS, VISIBILITY_SCOPES,
    flatten_taxonomy, tier_for_severity,
)
from ._router import nextgen_r

V1 = "/v1"


# ── Schemas ──────────────────────────────────────────────────────────────
class AweImpact(BaseModel):
    air: bool = False
    water: bool = False
    energy: bool = False
    rationale: Optional[str] = None


class Visibility(BaseModel):
    contractor: bool = True
    homeowner: bool = False
    adjuster: bool = False
    insurer: bool = False
    public: bool = False
    internal: bool = True


class IntelligenceCreate(BaseModel):
    mission_id: str
    evidence_ids: List[str]
    building_system: str  # e.g. "ROOF"
    building_component: str  # e.g. "SHINGLES"
    observation: str  # short human-readable statement
    classification: Optional[str] = None  # optional AI class label
    severity: str = "MINOR"  # SEVERITY
    priority: str = "SCHEDULE"  # PRIORITY
    risk_level: str = "LOW"  # RISK_LEVEL
    awe_impact: AweImpact = Field(default_factory=AweImpact)
    recommended_action: Optional[str] = None
    maintenance_recommendation: Optional[str] = None
    repair_recommendation: Optional[str] = None
    replacement_recommendation: Optional[str] = None
    estimated_remaining_life_years: Optional[float] = None
    warranty_impact: Optional[str] = None
    insurance_relevance: Optional[str] = None
    code_compliance_flag: bool = False
    estimated_cost_placeholder_usd: Optional[float] = None
    notes: Optional[str] = None
    visibility: Visibility = Field(default_factory=Visibility)
    ai_confidence_pct: Optional[float] = None  # 0..100, None = human-authored


class IntelligenceReviewBody(BaseModel):
    decision: str  # approve | reject | request_rework | request_field_verification
    notes: Optional[str] = None
    expected_revision: Optional[int] = None
    expected_head_hash: Optional[str] = None
    correlation_id: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────
def _validate_taxonomy(system: str, component: str) -> None:
    if system not in BUILDING_SYSTEMS:
        raise HTTPException(400, f"Unknown building_system: {system}")
    if component not in BUILDING_SYSTEMS[system]:
        raise HTTPException(
            400,
            f"Component {component!r} not in system {system!r}. "
            f"Allowed: {BUILDING_SYSTEMS[system]}",
        )


def _validate_enums(payload: IntelligenceCreate) -> None:
    if payload.severity not in SEVERITY:
        raise HTTPException(400, f"severity must be one of {SEVERITY}")
    if payload.priority not in PRIORITY:
        raise HTTPException(400, f"priority must be one of {PRIORITY}")
    if payload.risk_level not in RISK_LEVEL:
        raise HTTPException(400, f"risk_level must be one of {RISK_LEVEL}")


async def _authorize_mission(session: NxSession, mission_id: str) -> Dict[str, Any]:
    m = await nx_collections.missions.find_one({
        "canonical_id": mission_id, "tenant_id": session.tenant_id,
    })
    if not m:
        raise HTTPException(404, "Mission not found on your tenant")
    return m


async def _write_audit(session: NxSession, event_type: str, resource_kind: str,
                        resource_id: str, payload: Optional[dict] = None):
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": event_type,
        "actor_id": session.user_id,
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "at": now_iso_utc(),
        "payload": payload or {},
    })


def _content_hash(body: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# ── Taxonomy endpoints ───────────────────────────────────────────────────
@nextgen_r.get(V1 + "/taxonomy/building-systems")
async def get_taxonomy():
    return {
        "systems": BUILDING_SYSTEMS,
        "flat": flatten_taxonomy(),
        "severity": SEVERITY,
        "priority": PRIORITY,
        "risk_level": RISK_LEVEL,
        "risk_tier": RISK_TIER,
        "awe_categories": AWE_CATEGORIES,
        "timeline_kinds": TIMELINE_KINDS,
        "report_templates": REPORT_TEMPLATES,
        "visibility_scopes": VISIBILITY_SCOPES,
    }


# ── Create a Property Intelligence Object ────────────────────────────────
@nextgen_r.post(V1 + "/intelligence")
async def create_intelligence(
    body: IntelligenceCreate,
    session: NxSession = Depends(nx_session),
):
    mission = await _authorize_mission(session, body.mission_id)
    _validate_taxonomy(body.building_system, body.building_component)
    _validate_enums(body)

    # Verify evidence exists on this tenant + mission.
    if not body.evidence_ids:
        raise HTTPException(
            400,
            "Every intelligence object must cite at least one evidence item "
            "OR explicitly state why evidence is unavailable (Data Model §15 invariant 7).",
        )
    ev_docs = [d async for d in nx_collections.evidence_items.find({
        "canonical_id": {"$in": body.evidence_ids},
        "tenant_id": session.tenant_id,
        "mission_id": body.mission_id,
    })]
    if len(ev_docs) != len(set(body.evidence_ids)):
        raise HTTPException(400, "One or more evidence_ids not found on this mission")

    tier = tier_for_severity(body.severity)
    now = now_iso_utc()
    pio_id = nx_id()

    # Capture summary from first evidence item (best-effort provenance).
    first_ev = ev_docs[0]
    capture_ts = first_ev.get("captured_at")
    capture_loc = None
    meta = await nx_collections.evidence_metadata.find_one(
        {"evidence_item_id": first_ev["canonical_id"]}
    )
    if meta:
        gps = (meta.get("extracted") or {}).get("gps")
        if gps:
            capture_loc = gps

    pio_content = body.model_dump()
    pio = {
        "canonical_id": pio_id,
        "tenant_id": session.tenant_id,
        "mission_id": body.mission_id,
        "property_id": mission["property_id"],
        "evidence_ids": body.evidence_ids,
        "capture_timestamp": capture_ts,
        "capture_location": capture_loc,
        "inspector_user_id": session.user_id,
        "ai_confidence_pct": body.ai_confidence_pct,
        "human_qa_status": "candidate",
        "state": "candidate",
        "building_system": body.building_system,
        "building_component": body.building_component,
        "component_category": body.building_system,  # kept for downstream ergonomics
        "observation": body.observation,
        "classification": body.classification,
        "severity": body.severity,
        "priority": body.priority,
        "risk_level": body.risk_level,
        "risk_tier": tier,
        "recommended_action": body.recommended_action,
        "maintenance_recommendation": body.maintenance_recommendation,
        "repair_recommendation": body.repair_recommendation,
        "replacement_recommendation": body.replacement_recommendation,
        "estimated_remaining_life_years": body.estimated_remaining_life_years,
        "warranty_impact": body.warranty_impact,
        "insurance_relevance": body.insurance_relevance,
        "code_compliance_flag": body.code_compliance_flag,
        "awe_impact": body.awe_impact.model_dump(),
        "digital_twin_link": None,
        "passport_update_required": True,
        "habitat_visible": body.visibility.homeowner,
        "contractor_visible": body.visibility.contractor,
        "public_visible": body.visibility.public,
        "visibility": body.visibility.model_dump(),
        "historical_comparison": None,
        "previous_intelligence_id": None,
        "estimated_cost_placeholder_usd": body.estimated_cost_placeholder_usd,
        "notes": body.notes,
        "content_hash": _content_hash(pio_content),
        "created_by": session.user_id,
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }

    # Historical comparison: previous approved PIO on the same
    # property + system + component.
    prev = await nx_collections.intelligence_objects.find_one(
        {
            "tenant_id": session.tenant_id,
            "property_id": mission["property_id"],
            "building_system": body.building_system,
            "building_component": body.building_component,
            "state": {"$in": ["approved", "passport_committed"]},
        },
        sort=[("created_at", -1)],
    )
    if prev:
        pio["previous_intelligence_id"] = prev["canonical_id"]
        pio["historical_comparison"] = {
            "previous_id": prev["canonical_id"],
            "previous_severity": prev["severity"],
            "delta_severity": SEVERITY.index(body.severity) - SEVERITY.index(prev["severity"]),
        }

    await nx_collections.intelligence_objects.insert_one(dict(pio))
    await nx_collections.intelligence_versions.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "intelligence_id": pio_id,
        "version": 1,
        "content_hash": pio["content_hash"],
        "state": "candidate",
        "by": session.user_id,
        "at": now,
    })

    await _write_audit(session, "intelligence.created", "intelligence", pio_id, {
        "mission_id": body.mission_id, "system": body.building_system,
        "component": body.building_component, "severity": body.severity, "tier": tier,
    })
    return {"intelligence": strip_mongo_id(pio)}


# ── List / detail ────────────────────────────────────────────────────────
@nextgen_r.get(V1 + "/missions/{mission_id}/intelligence")
async def list_intelligence(
    mission_id: str,
    session: NxSession = Depends(nx_session),
):
    await _authorize_mission(session, mission_id)
    cursor = nx_collections.intelligence_objects.find({
        "tenant_id": session.tenant_id, "mission_id": mission_id,
    }).sort("created_at", -1)
    items = [strip_mongo_id(d) async for d in cursor]
    return {"items": items, "count": len(items)}


@nextgen_r.get(V1 + "/intelligence/{pio_id}")
async def get_intelligence(pio_id: str, session: NxSession = Depends(nx_session)):
    pio = await nx_collections.intelligence_objects.find_one({
        "canonical_id": pio_id, "tenant_id": session.tenant_id,
    })
    if not pio:
        raise HTTPException(404, "Intelligence object not found")
    versions = [strip_mongo_id(v) async for v in nx_collections.intelligence_versions.find(
        {"intelligence_id": pio_id}
    ).sort("version", 1)]
    reviews = [strip_mongo_id(r) async for r in nx_collections.intelligence_reviews.find(
        {"intelligence_id": pio_id}
    ).sort("at", 1)]
    return {
        "intelligence": strip_mongo_id(pio),
        "versions": versions,
        "reviews": reviews,
    }


# ── Review / approve ─────────────────────────────────────────────────────
@nextgen_r.post(V1 + "/intelligence/{pio_id}/review")
async def review_intelligence(
    pio_id: str,
    body: IntelligenceReviewBody,
    session: NxSession = Depends(nx_session),
):
    pio = await nx_collections.intelligence_objects.find_one({
        "canonical_id": pio_id, "tenant_id": session.tenant_id,
    })
    if not pio:
        raise HTTPException(404, "Intelligence object not found")

    if body.decision not in {"approve", "reject", "request_rework", "request_field_verification"}:
        raise HTTPException(400, "Unknown decision")

    if pio["state"] in {"passport_committed", "rejected"}:
        raise HTTPException(409, f"Cannot review — state is {pio['state']!r}")

    tier = pio["risk_tier"]
    now = now_iso_utc()
    passport_result = None

    if body.decision == "approve":
        await _write_audit(session, "SOURCE_APPROVAL_REQUESTED", "intelligence", pio_id, {
            "actor_role": session.role, "tier": tier,
        })
        head = await load_expected_state(
            tenant_id=session.tenant_id, property_id=pio["property_id"],
        )
        expected_revision = (
            body.expected_revision if body.expected_revision is not None
            else head["revision"]
        )
        expected_head_hash = (
            body.expected_head_hash if body.expected_head_hash is not None
            else head["head_hash"]
        )
        decision = evaluate_approval_policy(
            source_kind="intelligence",
            source=pio,
            actor_id=session.user_id,
            actor_role=session.role,
            tenant_id=session.tenant_id,
            property_id=pio["property_id"],
            require_evidence=True,
            expected_revision=expected_revision,
            expected_head_hash=expected_head_hash,
            require_expected_state=True,
            actor_attributes=(session.user.get("attributes") or {}),
        )
        if not decision.allowed:
            event = (
                "SOURCE_APPROVAL_BLOCKED_SOD"
                if decision.code == "SEPARATION_OF_DUTIES"
                else "SOURCE_APPROVAL_REJECTED"
            )
            await _write_audit(session, event, "intelligence", pio_id, decision.as_dict())
            status = 403 if decision.code in {
                "SEPARATION_OF_DUTIES", "ROLE_INELIGIBLE", "LICENSE_REQUIRED",
                "TENANT_MISMATCH", "PROPERTY_MISMATCH", "EVIDENCE_REQUIRED",
            } else 409
            raise HTTPException(status, decision.reason)

        review = {
            "canonical_id": nx_id(),
            "tenant_id": session.tenant_id,
            "intelligence_id": pio_id,
            "reviewer_user_id": session.user_id,
            "reviewer_role": session.role,
            "reviewer_tier": tier,
            "decision": body.decision,
            "notes": body.notes,
            "at": now,
            "signature": hashlib.sha256(
                (pio["content_hash"] + session.user_id + body.decision + now).encode()
            ).hexdigest(),
        }
        await nx_collections.intelligence_reviews.insert_one(dict(review))

        # Intermediate approved state BEFORE ledger commit — never passport_committed yet.
        await nx_collections.intelligence_objects.update_one(
            {"canonical_id": pio_id},
            {"$set": {
                "state": "approved",
                "human_qa_status": "approved",
                "updated_at": now,
            }, "$inc": {"version": 1}},
        )

        passport_payload = {
            "intelligence_id": pio_id,
            "content_hash": pio["content_hash"],
            "property_id": pio["property_id"],
            "mission_id": pio["mission_id"],
            "building_system": pio["building_system"],
            "building_component": pio["building_component"],
            "severity": pio["severity"],
            "risk_level": pio["risk_level"],
            "priority": pio["priority"],
            "awe_impact": pio["awe_impact"],
            "observation": pio["observation"],
            "recommended_action": pio["recommended_action"],
            "reviewer_signature": review["signature"],
            "visibility": pio["visibility"],
        }
        try:
            passport_result = await governed_publish(
                tenant_id=session.tenant_id,
                property_id=pio["property_id"],
                source_type="intelligence",
                source_id=pio_id,
                entry_type="INTELLIGENCE_APPROVED",
                payload=passport_payload,
                actor_id=session.user_id,
                actor_role=session.role,
                correlation_id=body.correlation_id,
                idempotency_key=f"intelligence.publish:{pio_id}",
                expected_revision=expected_revision,
                expected_head_hash=expected_head_hash,
            )
        except StaleExpectedStateError as exc:
            await _write_audit(session, "PUBLICATION_FAILED", "intelligence", pio_id, {
                "reason": "STALE_EXPECTED_STATE",
                "conflict_id": (exc.conflict or {}).get("conflict_id"),
            })
            # Leave state as approved (not passport_committed).
            raise HTTPException(409, {
                "error": "PASSPORT_APPEND_CONFLICT",
                "message": str(exc),
                "conflict": exc.conflict,
            })
        except MissingExpectedStateError as exc:
            raise HTTPException(400, str(exc))
        except IdempotencyConflictError as exc:
            raise HTTPException(409, str(exc))
        except TransactionUnavailableError as exc:
            raise HTTPException(503, str(exc))
        except PassportAppendError as exc:
            await _write_audit(session, "PUBLICATION_FAILED", "intelligence", pio_id, {
                "reason": getattr(exc, "code", "FAILED"),
            })
            raise HTTPException(
                500,
                "Passport append failed; intelligence not marked passport_committed",
            )

        await nx_collections.intelligence_objects.update_one(
            {"canonical_id": pio_id},
            {"$set": {
                "state": "passport_committed",
                "human_qa_status": "passport_committed",
                "passport_entry_id": passport_result["entry"]["canonical_id"],
                "passport_seq": passport_result["entry"]["seq"],
                "passport_content_hash": passport_result["entry"]["content_hash"],
                "passport_revision": passport_result["entry"].get("revision"),
                "passport_receipt_id": passport_result["receipt"]["canonical_id"],
                "updated_at": now,
            }},
        )
        await nx_collections.property_timeline.insert_one({
            "canonical_id": nx_id(),
            "tenant_id": session.tenant_id,
            "property_id": pio["property_id"],
            "kind": "INTELLIGENCE_APPROVED",
            "at": now,
            "actor_user_id": session.user_id,
            "reference_kind": "intelligence",
            "reference_id": pio_id,
            "summary": (
                f"{pio['severity']} · {pio['building_system']}/"
                f"{pio['building_component']} · {pio['observation'][:120]}"
            ),
            "passport_entry_id": passport_result["entry"]["canonical_id"],
            "awe_impact": pio["awe_impact"],
        })
        await emit_outbox_event(
            tenant_id=session.tenant_id,
            event_type="INTELLIGENCE_APPROVED",
            payload={
                "intelligence_id": pio_id,
                "property_id": pio["property_id"],
                "mission_id": pio["mission_id"],
                "passport_entry_id": passport_result["entry"]["canonical_id"],
                "passport_content_hash": passport_result["entry"]["content_hash"],
                "reviewer_user_id": session.user_id,
            },
            idempotency_key=f"intelligence.approved:{pio_id}",
            producer_resource_kind="intelligence",
            producer_resource_id=pio_id,
        )
        await _write_audit(session, "SOURCE_APPROVED", "intelligence", pio_id, {
            "passport_entry_id": passport_result["entry"]["canonical_id"],
            "seq": passport_result["entry"]["seq"],
        })
        await _write_audit(session, "passport.appended", "passport_entry",
                            passport_result["entry"]["canonical_id"], {
                                "intelligence_id": pio_id,
                                "seq": passport_result["entry"]["seq"],
                            })
        await _write_audit(session, "intelligence.reviewed", "intelligence", pio_id, {
            "decision": body.decision, "tier": tier, "new_state": "passport_committed",
        })
    else:
        # Non-approve decisions: role gate via policy without requiring expected state.
        decision = evaluate_approval_policy(
            source_kind="intelligence",
            source=pio,
            actor_id=session.user_id,
            actor_role=session.role,
            tenant_id=session.tenant_id,
            property_id=pio["property_id"],
            require_evidence=False,
            require_expected_state=False,
            actor_attributes=(session.user.get("attributes") or {}),
        )
        # For reject/rework, SoD and role still apply; ignore MISSING_EXPECTED_STATE.
        if not decision.allowed and decision.code != "MISSING_EXPECTED_STATE":
            # Allow reject by eligible reviewer even if SoD would block approve?
            # Uniform law: author may not approve; reject of own record also blocked
            # for SoD consistency on approve path only. Reject uses same SoD.
            if decision.code in {
                "SEPARATION_OF_DUTIES", "ROLE_INELIGIBLE", "LICENSE_REQUIRED",
                "TENANT_MISMATCH", "PROPERTY_MISMATCH",
            }:
                await _write_audit(
                    session, "SOURCE_APPROVAL_REJECTED", "intelligence", pio_id,
                    decision.as_dict(),
                )
                raise HTTPException(403, decision.reason)

        review = {
            "canonical_id": nx_id(),
            "tenant_id": session.tenant_id,
            "intelligence_id": pio_id,
            "reviewer_user_id": session.user_id,
            "reviewer_role": session.role,
            "reviewer_tier": tier,
            "decision": body.decision,
            "notes": body.notes,
            "at": now,
            "signature": None,
        }
        await nx_collections.intelligence_reviews.insert_one(dict(review))
        new_state = {
            "reject": "rejected",
            "request_rework": "candidate",
            "request_field_verification": "requires_field_verification",
        }[body.decision]
        await nx_collections.intelligence_objects.update_one(
            {"canonical_id": pio_id},
            {"$set": {
                "state": new_state,
                "human_qa_status": new_state,
                "updated_at": now,
            }, "$inc": {"version": 1}},
        )
        await _write_audit(session, "intelligence.reviewed", "intelligence", pio_id, {
            "decision": body.decision, "tier": tier, "new_state": new_state,
        })

    fresh = await nx_collections.intelligence_objects.find_one({"canonical_id": pio_id})
    return {
        "intelligence": strip_mongo_id(fresh),
        "review": strip_mongo_id(review),
        "passport": passport_result,
    }


# ── Property timeline ────────────────────────────────────────────────────
@nextgen_r.get(V1 + "/properties/{property_id}/timeline")
async def property_timeline(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id, "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found on your tenant")
    cursor = nx_collections.property_timeline.find({
        "property_id": property_id, "tenant_id": session.tenant_id,
    }).sort("at", -1)
    items = [strip_mongo_id(d) async for d in cursor]
    return {"items": items, "count": len(items)}


# ── Passport read (audience-scoped, read-only) ───────────────────────────
@nextgen_r.get(V1 + "/properties/{property_id}/passport")
async def read_passport(
    property_id: str,
    audience: str = "internal",
    session: NxSession = Depends(nx_session),
):
    if audience not in VISIBILITY_SCOPES:
        raise HTTPException(400, f"audience must be one of {VISIBILITY_SCOPES}")
    from ..passport_service import read_passport_projection
    return await read_passport_projection(
        tenant_id=session.tenant_id, property_id=property_id, audience=audience,
    )


# ── Report projections ───────────────────────────────────────────────────
def _project_intelligence_for_report(pios: List[Dict[str, Any]], template: str) -> Dict[str, Any]:
    """Report is a pure projection over approved intelligence.

    Templates change *which* fields are exposed, not *what* the underlying
    facts are.
    """
    common_public_fields = [
        "building_system", "building_component", "severity", "priority",
        "risk_level", "awe_impact", "observation",
        "recommended_action", "estimated_remaining_life_years",
        "warranty_impact", "insurance_relevance", "code_compliance_flag",
        "maintenance_recommendation", "repair_recommendation",
        "replacement_recommendation",
    ]
    audience_map = {
        "contractor_full": {"visibility": "contractor", "fields": common_public_fields
                             + ["estimated_cost_placeholder_usd", "notes", "capture_timestamp"]},
        "homeowner_summary": {"visibility": "homeowner", "fields":
                                ["building_system", "building_component", "severity",
                                 "priority", "recommended_action",
                                 "maintenance_recommendation", "awe_impact"]},
        "insurance_claim": {"visibility": "adjuster", "fields":
                              ["building_system", "building_component", "severity",
                               "risk_level", "awe_impact", "observation",
                               "insurance_relevance", "capture_timestamp"]},
        "hoa_summary": {"visibility": "public", "fields":
                          ["building_system", "severity", "priority",
                           "recommended_action"]},
        "energy_focused": {"visibility": "homeowner", "fields":
                             ["building_system", "building_component", "awe_impact",
                              "severity", "recommended_action",
                              "estimated_remaining_life_years"]},
        "executive_summary": {"visibility": "internal", "fields":
                                ["building_system", "severity", "risk_level",
                                 "priority", "awe_impact", "recommended_action"]},
        "property_health": {"visibility": "homeowner", "fields":
                              ["building_system", "building_component", "severity",
                               "priority", "risk_level", "awe_impact",
                               "recommended_action",
                               "estimated_remaining_life_years"]},
    }
    tmpl = audience_map[template]
    filtered = [p for p in pios if p.get("visibility", {}).get(tmpl["visibility"], False)
                 or tmpl["visibility"] == "internal"]

    # Aggregate metrics
    severity_counts = {s: sum(1 for p in filtered if p["severity"] == s) for s in SEVERITY}
    awe_counts = {c.lower(): sum(1 for p in filtered if p.get("awe_impact", {}).get(c.lower()))
                   for c in AWE_CATEGORIES}
    highest_severity = next(
        (s for s in reversed(SEVERITY) if severity_counts[s]), "INFORMATIONAL"
    )

    projected = [
        {k: p.get(k) for k in tmpl["fields"] if k in p}
        for p in filtered
    ]
    return {
        "template": template,
        "counts": {"total": len(filtered), "severity": severity_counts, "awe": awe_counts},
        "highest_severity": highest_severity,
        "items": projected,
    }


@nextgen_r.get(V1 + "/properties/{property_id}/report/{template}")
async def property_report(
    property_id: str,
    template: str,
    session: NxSession = Depends(nx_session),
):
    if template not in REPORT_TEMPLATES:
        raise HTTPException(404, f"Unknown template. Available: {REPORT_TEMPLATES}")
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id, "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found")
    pios = [d async for d in nx_collections.intelligence_objects.find({
        "tenant_id": session.tenant_id,
        "property_id": property_id,
        "state": {"$in": ["approved", "passport_committed"]},
    })]
    projection = _project_intelligence_for_report(
        [strip_mongo_id(p) for p in pios], template,
    )
    return {
        "property": strip_mongo_id(prop),
        "report": projection,
        "generated_at": now_iso_utc(),
        "source": "property_intelligence_engine",
        "note": "Reports are read-only projections of approved intelligence.",
    }


@nextgen_r.get(V1 + "/report-templates")
async def list_report_templates():
    return {"templates": REPORT_TEMPLATES}
