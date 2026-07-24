"""Property Intelligence Engine — Findings API (Phase 3 · Directive 009).

Findings are the canonical, human-authored observations that flow through
the PIE lifecycle:

    DRAFT
      └─▶ PENDING_REVIEW
            ├─▶ APPROVED  ─┬─▶ RESOLVED
            │              └─▶ SUPERSEDED (by a newer approved finding)
            └─▶ REJECTED

Governing rules (Phase 3 mandate):
  · Only manual creation for Phase 3. AI-drafted findings are deferred to
    the Vision Grounding phase.
  · Findings must cite property_id. Missions, jobs and evidence are optional.
    A finding without evidence is a MANUAL OBSERVATION and is clearly
    labeled — it must never be represented as machine-verified.
  · Approval authority: CEO · Admin · GM only.
  · Separation of duties: the finding's author may NOT approve their own
    finding. There is no self-approval bypass.
  · Only APPROVED findings may append to the Passport ledger. Every
    Passport append is recorded on the finding with the resulting seq +
    content hash so downstream systems can prove provenance.
  · Habitat / homeowner projections strip reviewer identity, notes,
    confidence methodology, contractor pricing and audit internals.
  · Approved findings are immutable. Substantive changes require a new
    finding that supersedes the older one (server-side versioning +
    SUPERSEDE_FINDING passport append).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Query
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
    BUILDING_SYSTEMS,
    PRIORITY,
    SEVERITY,
    tier_for_severity,
)
from ._router import nextgen_r

V1 = "/v1"


# ── Role policy (Phase 3 mandate) ────────────────────────────────────────
APPROVER_ROLES = frozenset({"ceo", "admin", "gm"})
# Roles allowed to CREATE draft findings (contractor may only create for
# properties/jobs they can already see — tenant scoping handles that).
CREATOR_ROLES = frozenset({
    "ceo", "admin", "gm",
    "contractor", "operator", "pilot", "inspector",
})
# Read-only roles (findings visible per role policy).
VIEWER_ROLES = frozenset({
    "ceo", "admin", "gm",
    "contractor", "operator", "pilot", "inspector",
    "insurance", "adjuster",
})

TERMINAL_STATUSES = frozenset({"APPROVED", "REJECTED", "RESOLVED", "SUPERSEDED"})
STATUSES = ("DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED", "RESOLVED", "SUPERSEDED")


# ── Schemas ──────────────────────────────────────────────────────────────
class FindingCreate(BaseModel):
    property_id: str
    job_id: Optional[str] = None
    mission_id: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    taxonomy_category: str  # BUILDING_SYSTEMS key, e.g. "ROOF"
    taxonomy_component: Optional[str] = None  # component under the category
    severity: str = "MINOR"
    priority: str = "SCHEDULE"
    description: str
    confidence_pct: Optional[float] = None  # 0..100
    confidence_source: Optional[str] = None  # required if confidence_pct is set
    notes: Optional[str] = None
    habitat_visible: bool = False
    insurance_relevant: bool = False


class FindingUpdate(BaseModel):
    """Restricted field set — only DRAFT findings can be edited."""
    taxonomy_category: Optional[str] = None
    taxonomy_component: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None
    confidence_pct: Optional[float] = None
    confidence_source: Optional[str] = None
    notes: Optional[str] = None
    habitat_visible: Optional[bool] = None
    insurance_relevant: Optional[bool] = None
    evidence_ids: Optional[List[str]] = None
    mission_id: Optional[str] = None
    job_id: Optional[str] = None


class ReviewBody(BaseModel):
    notes: Optional[str] = None
    # C-P-002 optimistic concurrency tokens (optional; loaded from head if omitted).
    expected_revision: Optional[int] = None
    expected_head_hash: Optional[str] = None
    correlation_id: Optional[str] = None


class SupersedeBody(BaseModel):
    new_finding: FindingCreate
    reason: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────
def _validate_taxonomy(category: str, component: Optional[str]) -> None:
    if category not in BUILDING_SYSTEMS:
        raise HTTPException(400, f"Unknown taxonomy_category: {category!r}")
    if component and component not in BUILDING_SYSTEMS[category]:
        raise HTTPException(
            400,
            f"Component {component!r} not in category {category!r}. "
            f"Allowed: {BUILDING_SYSTEMS[category]}",
        )


def _validate_enums(severity: str, priority: str) -> None:
    if severity not in SEVERITY:
        raise HTTPException(400, f"severity must be one of {SEVERITY}")
    if priority not in PRIORITY:
        raise HTTPException(400, f"priority must be one of {PRIORITY}")


async def _authorize_property(session: NxSession, property_id: str) -> Dict[str, Any]:
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id, "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found on your tenant")
    return prop


async def _authorize_mission(session: NxSession, mission_id: str) -> Dict[str, Any]:
    m = await nx_collections.missions.find_one({
        "canonical_id": mission_id, "tenant_id": session.tenant_id,
    })
    if not m:
        raise HTTPException(404, "Mission not found on your tenant")
    return m


async def _validate_evidence(
    session: NxSession, mission_id: Optional[str], evidence_ids: List[str],
) -> None:
    if not evidence_ids:
        return
    q: Dict[str, Any] = {
        "canonical_id": {"$in": evidence_ids},
        "tenant_id": session.tenant_id,
    }
    if mission_id:
        q["mission_id"] = mission_id
    docs = [d async for d in nx_collections.evidence_items.find(q)]
    if len(docs) != len(set(evidence_ids)):
        raise HTTPException(400, "One or more evidence_ids not found on this tenant")


async def _write_audit(
    session: NxSession, event_type: str, resource_kind: str,
    resource_id: str, payload: Optional[dict] = None,
) -> None:
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


def _append_review(finding: Dict[str, Any], action: str, session: NxSession,
                    notes: Optional[str] = None,
                    extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    entry = {
        "action": action,
        "by": session.user_id,
        "role": session.role,
        "at": now_iso_utc(),
        "notes": notes,
    }
    if extra:
        entry.update(extra)
    finding.setdefault("review_history", []).append(entry)
    return entry


def _publicize(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Strip Mongo id and normalize for API response."""
    return strip_mongo_id(finding)


def _project_for_habitat(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Homeowner-safe projection.

    Only fields safe for the public/homeowner audience — internal reviewer
    identity, confidence methodology, notes, contractor pricing, ai
    reasoning and audit internals are stripped.
    """
    return {
        "canonical_id": finding["canonical_id"],
        "property_id": finding["property_id"],
        "taxonomy_category": finding["taxonomy_category"],
        "taxonomy_component": finding.get("taxonomy_component"),
        "severity": finding["severity"],
        "priority": finding["priority"],
        "description": finding["description"],
        "status": finding["status"],
        "approved_at": (finding.get("approval") or {}).get("at"),
        "manual_observation": finding.get("manual_observation", False),
        "resolved_at": finding.get("resolved_at"),
    }


# ── Create ───────────────────────────────────────────────────────────────
@nextgen_r.post(V1 + "/findings")
async def create_finding(
    body: FindingCreate,
    session: NxSession = Depends(nx_session),
):
    """Create a DRAFT finding.

    A finding is always tenant-scoped and property-scoped. Evidence and
    mission bindings are optional; missing evidence flags the finding as a
    MANUAL OBSERVATION so downstream projections do not represent it as
    machine-verified.
    """
    if session.role not in CREATOR_ROLES:
        raise HTTPException(403, f"Role {session.role!r} may not create findings")

    prop = await _authorize_property(session, body.property_id)
    _validate_taxonomy(body.taxonomy_category, body.taxonomy_component)
    _validate_enums(body.severity, body.priority)

    if body.mission_id:
        await _authorize_mission(session, body.mission_id)
    await _validate_evidence(session, body.mission_id, body.evidence_ids)

    if body.confidence_pct is not None and not body.confidence_source:
        raise HTTPException(
            400,
            "confidence_pct requires confidence_source (e.g. 'human_field_observation'). "
            "Phase 3 forbids AI-attributed confidence; enter the source explicitly.",
        )

    now = now_iso_utc()
    fid = nx_id()
    manual = not bool(body.evidence_ids)
    finding = {
        "canonical_id": fid,
        "tenant_id": session.tenant_id,
        "property_id": prop["canonical_id"],
        "job_id": body.job_id,
        "mission_id": body.mission_id,
        "evidence_ids": body.evidence_ids or [],
        "taxonomy_category": body.taxonomy_category,
        "taxonomy_component": body.taxonomy_component,
        "severity": body.severity,
        "priority": body.priority,
        "risk_tier": tier_for_severity(body.severity),
        "description": body.description,
        "confidence_pct": body.confidence_pct,
        "confidence_source": body.confidence_source,
        "notes": body.notes,
        "habitat_visible": bool(body.habitat_visible),
        "insurance_relevant": bool(body.insurance_relevant),
        "manual_observation": manual,
        "status": "DRAFT",
        "version": 1,
        "author_id": session.user_id,
        "author_role": session.role,
        "created_at": now,
        "updated_at": now,
        "approval": None,
        "rejected": None,
        "resolved_at": None,
        "passport_entry_id": None,
        "passport_seq": None,
        "passport_content_hash": None,
        "supersedes_finding_id": None,
        "superseded_by_finding_id": None,
        "review_history": [],
    }
    _append_review(finding, "create_draft", session,
                    extra={"manual_observation": manual})
    finding["content_hash"] = _content_hash({
        k: finding[k] for k in (
            "property_id", "taxonomy_category", "taxonomy_component",
            "severity", "priority", "description", "evidence_ids",
        )
    })
    await nx_collections.findings.insert_one(dict(finding))
    await _write_audit(session, "finding.created", "finding", fid, {
        "property_id": prop["canonical_id"],
        "manual_observation": manual,
        "severity": body.severity,
    })
    return {"finding": _publicize(finding)}


# ── Update DRAFT ─────────────────────────────────────────────────────────
@nextgen_r.patch(V1 + "/findings/{finding_id}")
async def update_finding(
    finding_id: str,
    body: FindingUpdate,
    session: NxSession = Depends(nx_session),
):
    finding = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not finding:
        raise HTTPException(404, "Finding not found")

    if finding["status"] != "DRAFT":
        raise HTTPException(409, "Only DRAFT findings can be edited. Approved findings must be superseded.")

    if session.user_id != finding["author_id"] and session.role not in APPROVER_ROLES:
        raise HTTPException(403, "Only the author or an authorized reviewer may edit a DRAFT")

    changes: Dict[str, Any] = {}
    d = body.model_dump(exclude_unset=True)

    if "taxonomy_category" in d or "taxonomy_component" in d:
        cat = d.get("taxonomy_category", finding["taxonomy_category"])
        comp = d.get("taxonomy_component", finding.get("taxonomy_component"))
        _validate_taxonomy(cat, comp)
    if "severity" in d or "priority" in d:
        sev = d.get("severity", finding["severity"])
        pri = d.get("priority", finding["priority"])
        _validate_enums(sev, pri)
    if "confidence_pct" in d and d["confidence_pct"] is not None:
        src = d.get("confidence_source", finding.get("confidence_source"))
        if not src:
            raise HTTPException(400, "confidence_pct requires confidence_source")
    if "mission_id" in d and d["mission_id"]:
        await _authorize_mission(session, d["mission_id"])
    if "evidence_ids" in d:
        await _validate_evidence(session, d.get("mission_id", finding.get("mission_id")),
                                  d["evidence_ids"] or [])
        changes["manual_observation"] = not bool(d["evidence_ids"])

    changes.update(d)
    if "severity" in changes:
        changes["risk_tier"] = tier_for_severity(changes["severity"])
    changes["updated_at"] = now_iso_utc()

    _append_review(finding, "edit_draft", session)
    changes["review_history"] = finding["review_history"]

    await nx_collections.findings.update_one(
        {"canonical_id": finding_id}, {"$set": changes},
    )
    fresh = await nx_collections.findings.find_one({"canonical_id": finding_id})
    return {"finding": _publicize(fresh)}


# ── Submit for review ────────────────────────────────────────────────────
@nextgen_r.post(V1 + "/findings/{finding_id}/submit")
async def submit_for_review(
    finding_id: str,
    body: ReviewBody,
    session: NxSession = Depends(nx_session),
):
    finding = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not finding:
        raise HTTPException(404, "Finding not found")
    if finding["status"] != "DRAFT":
        raise HTTPException(409, f"Cannot submit — current status is {finding['status']!r}")

    _append_review(finding, "submit_for_review", session, notes=body.notes)
    await nx_collections.findings.update_one(
        {"canonical_id": finding_id},
        {"$set": {
            "status": "PENDING_REVIEW",
            "updated_at": now_iso_utc(),
            "review_history": finding["review_history"],
        }},
    )
    await _write_audit(session, "finding.submitted", "finding", finding_id, {})
    fresh = await nx_collections.findings.find_one({"canonical_id": finding_id})
    return {"finding": _publicize(fresh)}


# ── Approve ──────────────────────────────────────────────────────────────
@nextgen_r.post(V1 + "/findings/{finding_id}/approve")
async def approve_finding(
    finding_id: str,
    body: ReviewBody,
    session: NxSession = Depends(nx_session),
):
    finding = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not finding:
        raise HTTPException(404, "Finding not found")

    await _write_audit(session, "SOURCE_APPROVAL_REQUESTED", "finding", finding_id, {
        "actor_role": session.role,
    })

    head = await load_expected_state(
        tenant_id=session.tenant_id, property_id=finding["property_id"],
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
        source_kind="finding",
        source=finding,
        actor_id=session.user_id,
        actor_role=session.role,
        tenant_id=session.tenant_id,
        property_id=finding["property_id"],
        expected_revision=expected_revision,
        expected_head_hash=expected_head_hash,
        require_expected_state=True,
    )
    if not decision.allowed:
        event = (
            "SOURCE_APPROVAL_BLOCKED_SOD"
            if decision.code == "SEPARATION_OF_DUTIES"
            else "SOURCE_APPROVAL_REJECTED"
        )
        await _write_audit(session, event, "finding", finding_id, decision.as_dict())
        status = 403 if decision.code in {
            "SEPARATION_OF_DUTIES", "ROLE_INELIGIBLE", "TENANT_MISMATCH",
            "PROPERTY_MISMATCH",
        } else 409
        raise HTTPException(status, decision.reason)

    # Idempotent re-approval: already published once.
    if finding.get("status") == "APPROVED" and finding.get("passport_entry_id"):
        return {
            "finding": _publicize(finding),
            "passport": {"status": "DUPLICATE_SAME_REQUEST", "entry": {
                "canonical_id": finding["passport_entry_id"],
                "seq": finding.get("passport_seq"),
                "content_hash": finding.get("passport_content_hash"),
            }},
            "note": "Finding already approved and published",
        }

    now = now_iso_utc()
    signature = hashlib.sha256(
        (finding["content_hash"] + session.user_id + now).encode()
    ).hexdigest()
    approval = {
        "reviewer_id": session.user_id,
        "reviewer_role": session.role,
        "at": now,
        "notes": body.notes,
        "signature": signature,
    }
    _append_review(finding, "approve", session, notes=body.notes,
                    extra={"signature": signature})

    passport_payload = {
        "finding_id": finding_id,
        "finding_version": finding["version"],
        "content_hash": finding["content_hash"],
        "property_id": finding["property_id"],
        "taxonomy_category": finding["taxonomy_category"],
        "taxonomy_component": finding.get("taxonomy_component"),
        "severity": finding["severity"],
        "priority": finding["priority"],
        "description": finding["description"],
        "manual_observation": finding.get("manual_observation", False),
        "approver_id": session.user_id,
        "approver_role": session.role,
        "approved_at": now,
        "reviewer_signature": signature,
        "visibility": {
            "contractor": True,
            "homeowner": bool(finding.get("habitat_visible")),
            "insurer": bool(finding.get("insurance_relevant")),
            "adjuster": bool(finding.get("insurance_relevant")),
            "internal": True,
            "public": False,
        },
    }

    try:
        passport_result = await governed_publish(
            tenant_id=session.tenant_id,
            property_id=finding["property_id"],
            source_type="finding",
            source_id=finding_id,
            entry_type="INTELLIGENCE_APPROVED",
            payload=passport_payload,
            actor_id=session.user_id,
            actor_role=session.role,
            correlation_id=body.correlation_id,
            idempotency_key=f"finding.publish:{finding_id}",
            expected_revision=expected_revision,
            expected_head_hash=expected_head_hash,
        )
    except StaleExpectedStateError as exc:
        await _write_audit(session, "PUBLICATION_FAILED", "finding", finding_id, {
            "reason": "STALE_EXPECTED_STATE",
            "conflict_id": (exc.conflict or {}).get("conflict_id"),
        })
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
        await _write_audit(session, "PUBLICATION_FAILED", "finding", finding_id, {
            "reason": getattr(exc, "code", "FAILED"),
        })
        raise HTTPException(500, "Passport append failed; finding not marked approved")

    # Only mark APPROVED after successful (or duplicate-same) commit.
    await nx_collections.findings.update_one(
        {"canonical_id": finding_id},
        {"$set": {
            "status": "APPROVED",
            "updated_at": now,
            "approval": approval,
            "passport_entry_id": passport_result["entry"]["canonical_id"],
            "passport_seq": passport_result["entry"]["seq"],
            "passport_content_hash": passport_result["entry"]["content_hash"],
            "passport_revision": passport_result["entry"].get("revision"),
            "passport_receipt_id": passport_result["receipt"]["canonical_id"],
            "review_history": finding["review_history"],
        }},
    )

    await nx_collections.property_timeline.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "property_id": finding["property_id"],
        "kind": "INTELLIGENCE_APPROVED",
        "at": now,
        "actor_user_id": session.user_id,
        "reference_kind": "finding",
        "reference_id": finding_id,
        "summary": (
            f"{finding['severity']} · {finding['taxonomy_category']}"
            f"{'/' + finding['taxonomy_component'] if finding.get('taxonomy_component') else ''}"
            f" · {finding['description'][:120]}"
        ),
        "passport_entry_id": passport_result["entry"]["canonical_id"],
    })

    await emit_outbox_event(
        tenant_id=session.tenant_id,
        event_type="FINDING_APPROVED",
        payload={
            "finding_id": finding_id,
            "property_id": finding["property_id"],
            "passport_entry_id": passport_result["entry"]["canonical_id"],
            "passport_content_hash": passport_result["entry"]["content_hash"],
            "approver_user_id": session.user_id,
        },
        idempotency_key=f"finding.approved:{finding_id}",
        producer_resource_kind="finding",
        producer_resource_id=finding_id,
    )
    await _write_audit(session, "SOURCE_APPROVED", "finding", finding_id, {
        "passport_entry_id": passport_result["entry"]["canonical_id"],
        "passport_seq": passport_result["entry"]["seq"],
    })
    await _write_audit(session, "finding.approved", "finding", finding_id, {
        "passport_entry_id": passport_result["entry"]["canonical_id"],
        "passport_seq": passport_result["entry"]["seq"],
    })

    if finding.get("supersedes_finding_id"):
        await _finalize_supersession(session, finding_id)

    fresh = await nx_collections.findings.find_one({"canonical_id": finding_id})
    return {
        "finding": _publicize(fresh),
        "passport": passport_result,
    }


# ── Reject ───────────────────────────────────────────────────────────────
@nextgen_r.post(V1 + "/findings/{finding_id}/reject")
async def reject_finding(
    finding_id: str,
    body: ReviewBody,
    session: NxSession = Depends(nx_session),
):
    if session.role not in APPROVER_ROLES:
        raise HTTPException(403, "Only CEO / Admin / GM may reject findings")

    finding = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not finding:
        raise HTTPException(404, "Finding not found")
    if finding["status"] != "PENDING_REVIEW":
        raise HTTPException(409, f"Cannot reject — status is {finding['status']!r}")
    if finding["author_id"] == session.user_id:
        raise HTTPException(403,
            "Separation of duties: the finding author may not reject their own finding.",
        )

    now = now_iso_utc()
    _append_review(finding, "reject", session, notes=body.notes)
    await nx_collections.findings.update_one(
        {"canonical_id": finding_id},
        {"$set": {
            "status": "REJECTED",
            "updated_at": now,
            "rejected": {
                "reviewer_id": session.user_id,
                "reviewer_role": session.role,
                "at": now, "notes": body.notes,
            },
            "review_history": finding["review_history"],
        }},
    )
    await _write_audit(session, "finding.rejected", "finding", finding_id, {})
    fresh = await nx_collections.findings.find_one({"canonical_id": finding_id})
    return {"finding": _publicize(fresh)}


# ── Resolve ──────────────────────────────────────────────────────────────
@nextgen_r.post(V1 + "/findings/{finding_id}/resolve")
async def resolve_finding(
    finding_id: str,
    body: ReviewBody,
    session: NxSession = Depends(nx_session),
):
    if session.role not in APPROVER_ROLES:
        raise HTTPException(403, "Only CEO / Admin / GM may mark findings RESOLVED")

    finding = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not finding:
        raise HTTPException(404, "Finding not found")
    if finding["status"] != "APPROVED":
        raise HTTPException(409, f"Only APPROVED findings can be RESOLVED (current: {finding['status']!r})")

    now = now_iso_utc()
    _append_review(finding, "resolve", session, notes=body.notes)
    await nx_collections.findings.update_one(
        {"canonical_id": finding_id},
        {"$set": {
            "status": "RESOLVED",
            "updated_at": now,
            "resolved_at": now,
            "review_history": finding["review_history"],
        }},
    )
    await _write_audit(session, "finding.resolved", "finding", finding_id, {})
    fresh = await nx_collections.findings.find_one({"canonical_id": finding_id})
    return {"finding": _publicize(fresh)}


# ── Supersede (approved finding replaced by new approved finding) ────────
@nextgen_r.post(V1 + "/findings/{finding_id}/supersede")
async def supersede_finding(
    finding_id: str,
    body: SupersedeBody,
    session: NxSession = Depends(nx_session),
):
    """Replace an APPROVED finding by a NEW finding.

    Creates the new finding (status = DRAFT) linked to the old one via
    `supersedes_finding_id`. Approval of the new finding must be performed
    independently through the normal submit → approve flow. Only when the
    new finding is APPROVED does the old finding transition to SUPERSEDED
    and a SUPERSEDE_FINDING passport entry is appended.
    """
    if session.role not in CREATOR_ROLES:
        raise HTTPException(403, f"Role {session.role!r} may not create findings")

    prior = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not prior:
        raise HTTPException(404, "Prior finding not found")
    if prior["status"] not in {"APPROVED", "RESOLVED"}:
        raise HTTPException(409, "Only APPROVED or RESOLVED findings can be superseded")

    # Force new finding to reference the same property.
    body.new_finding.property_id = prior["property_id"]

    # Reuse create logic by hand so we can wire supersedes link.
    prop = await _authorize_property(session, prior["property_id"])
    _validate_taxonomy(body.new_finding.taxonomy_category,
                        body.new_finding.taxonomy_component)
    _validate_enums(body.new_finding.severity, body.new_finding.priority)
    await _validate_evidence(session, body.new_finding.mission_id,
                              body.new_finding.evidence_ids or [])

    now = now_iso_utc()
    fid = nx_id()
    manual = not bool(body.new_finding.evidence_ids)
    finding = {
        "canonical_id": fid,
        "tenant_id": session.tenant_id,
        "property_id": prop["canonical_id"],
        "job_id": body.new_finding.job_id,
        "mission_id": body.new_finding.mission_id,
        "evidence_ids": body.new_finding.evidence_ids or [],
        "taxonomy_category": body.new_finding.taxonomy_category,
        "taxonomy_component": body.new_finding.taxonomy_component,
        "severity": body.new_finding.severity,
        "priority": body.new_finding.priority,
        "risk_tier": tier_for_severity(body.new_finding.severity),
        "description": body.new_finding.description,
        "confidence_pct": body.new_finding.confidence_pct,
        "confidence_source": body.new_finding.confidence_source,
        "notes": body.new_finding.notes,
        "habitat_visible": bool(body.new_finding.habitat_visible),
        "insurance_relevant": bool(body.new_finding.insurance_relevant),
        "manual_observation": manual,
        "status": "DRAFT",
        "version": prior["version"] + 1,
        "author_id": session.user_id,
        "author_role": session.role,
        "created_at": now,
        "updated_at": now,
        "approval": None,
        "rejected": None,
        "resolved_at": None,
        "passport_entry_id": None,
        "passport_seq": None,
        "passport_content_hash": None,
        "supersedes_finding_id": prior["canonical_id"],
        "superseded_by_finding_id": None,
        "review_history": [],
    }
    _append_review(finding, "create_supersede_draft", session,
                    notes=body.reason,
                    extra={"prior_finding_id": prior["canonical_id"]})
    finding["content_hash"] = _content_hash({
        k: finding[k] for k in (
            "property_id", "taxonomy_category", "taxonomy_component",
            "severity", "priority", "description", "evidence_ids",
        )
    })
    await nx_collections.findings.insert_one(dict(finding))
    await _write_audit(session, "finding.supersede_drafted", "finding", fid, {
        "prior_finding_id": prior["canonical_id"],
    })
    return {
        "finding": _publicize(finding),
        "supersedes": prior["canonical_id"],
        "note": "Supersedes chain established. Submit and approve the new finding "
                "to complete supersession. The prior finding remains APPROVED "
                "until the new one is approved.",
    }


async def _finalize_supersession(session: NxSession, new_finding_id: str) -> None:
    """Called after an approval where the new finding supersedes an older one.

    Flips the prior finding to SUPERSEDED and appends a SUPERSEDE_FINDING
    passport entry so the transition is on the ledger.
    """
    new_f = await nx_collections.findings.find_one({"canonical_id": new_finding_id})
    if not new_f or not new_f.get("supersedes_finding_id"):
        return
    prior_id = new_f["supersedes_finding_id"]
    prior = await nx_collections.findings.find_one({
        "canonical_id": prior_id, "tenant_id": session.tenant_id,
    })
    if not prior:
        return
    if prior["status"] == "SUPERSEDED":
        return  # idempotent

    now = now_iso_utc()
    head = await load_expected_state(
        tenant_id=session.tenant_id, property_id=prior["property_id"],
    )
    try:
        passport = await governed_publish(
            tenant_id=session.tenant_id,
            property_id=prior["property_id"],
            source_type="finding_supersede",
            source_id=f"{prior_id}->{new_finding_id}",
            entry_type="SUPERSEDE_FINDING",
            payload={
                "prior_finding_id": prior_id,
                "prior_content_hash": prior["content_hash"],
                "new_finding_id": new_finding_id,
                "new_content_hash": new_f["content_hash"],
                "approved_by": session.user_id,
            },
            actor_id=session.user_id,
            actor_role=session.role,
            idempotency_key=f"finding.supersede:{prior_id}:{new_finding_id}",
            expected_revision=head["revision"],
            expected_head_hash=head["head_hash"],
        )
    except (StaleExpectedStateError, PassportAppendError) as exc:
        # Do not flip prior to SUPERSEDED without a ledger receipt.
        await _write_audit(session, "PUBLICATION_FAILED", "finding", new_finding_id, {
            "reason": "SUPERSEDE_PUBLISH_FAILED",
            "error": type(exc).__name__,
        })
        return

    await nx_collections.findings.update_one(
        {"canonical_id": prior_id},
        {"$set": {
            "status": "SUPERSEDED",
            "superseded_by_finding_id": new_finding_id,
            "updated_at": now,
        }},
    )
    await nx_collections.property_timeline.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "property_id": prior["property_id"],
        "kind": "INTELLIGENCE_APPROVED",
        "at": now,
        "actor_user_id": session.user_id,
        "reference_kind": "finding",
        "reference_id": new_finding_id,
        "summary": (
            f"SUPERSEDES · {prior['taxonomy_category']} · "
            f"prior finding {prior_id[:8]} replaced"
        ),
        "passport_entry_id": passport["entry"]["canonical_id"],
    })


# Wrap approve to run supersession finalization when needed. We patch by
# post-processing rather than mutating the approve endpoint's return path.
@nextgen_r.post(V1 + "/findings/{finding_id}/finalize-supersession")
async def finalize_supersession_endpoint(
    finding_id: str,
    session: NxSession = Depends(nx_session),
):
    """Idempotent helper to flip prior→SUPERSEDED once the new finding is
    approved. Callers may run it explicitly; the approve endpoint also
    invokes the same helper internally when it detects a supersede link.
    """
    if session.role not in APPROVER_ROLES:
        raise HTTPException(403, "Only CEO / Admin / GM may finalize supersession")
    new_f = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not new_f:
        raise HTTPException(404, "Finding not found")
    if new_f["status"] != "APPROVED":
        raise HTTPException(409, "New finding must be APPROVED first")
    if not new_f.get("supersedes_finding_id"):
        return {"ok": True, "note": "No supersession link on this finding"}
    await _finalize_supersession(session, finding_id)
    return {"ok": True}


# ── List / detail ────────────────────────────────────────────────────────
@nextgen_r.get(V1 + "/properties/{property_id}/findings")
async def list_findings_for_property(
    property_id: str,
    status: Optional[str] = Query(None),
    session: NxSession = Depends(nx_session),
):
    if session.role not in VIEWER_ROLES:
        raise HTTPException(403, "Role not authorized to view findings")
    await _authorize_property(session, property_id)
    q: Dict[str, Any] = {
        "tenant_id": session.tenant_id,
        "property_id": property_id,
    }
    if status:
        if status not in STATUSES:
            raise HTTPException(400, f"status must be one of {STATUSES}")
        q["status"] = status
    cursor = nx_collections.findings.find(q).sort("created_at", -1)
    items = [_publicize(d) async for d in cursor]
    return {"items": items, "count": len(items)}


@nextgen_r.get(V1 + "/findings/{finding_id}")
async def get_finding(
    finding_id: str,
    session: NxSession = Depends(nx_session),
):
    if session.role not in VIEWER_ROLES:
        raise HTTPException(403, "Role not authorized to view findings")
    f = await nx_collections.findings.find_one({
        "canonical_id": finding_id, "tenant_id": session.tenant_id,
    })
    if not f:
        raise HTTPException(404, "Finding not found")
    return {"finding": _publicize(f)}


# ── Intelligence Summary (reusable aggregate) ────────────────────────────
@nextgen_r.get(V1 + "/properties/{property_id}/intelligence-summary")
async def intelligence_summary(
    property_id: str,
    audience: str = Query("internal"),
    session: NxSession = Depends(nx_session),
):
    """Aggregate for the reusable <PropertyIntelligenceSummary /> component.

    Fields:
      · counts by status (DRAFT / PENDING_REVIEW / APPROVED / REJECTED /
        RESOLVED / SUPERSEDED)
      · counts by severity (over APPROVED only)
      · completeness heuristic (approved / (approved + pending))
      · latest approved timestamp
      · manual observation count (approved & unlinked)
      · habitat-visible approved count (for the audience switcher)

    Homeowner / public audiences receive only APPROVED counts, no reviewer
    identity, and no draft/pending counts.
    """
    if session.role not in VIEWER_ROLES:
        raise HTTPException(403, "Role not authorized")
    await _authorize_property(session, property_id)

    docs = [d async for d in nx_collections.findings.find({
        "tenant_id": session.tenant_id, "property_id": property_id,
    })]

    by_status = {s: 0 for s in STATUSES}
    by_severity = {s: 0 for s in SEVERITY}
    approved_manual = 0
    habitat_visible_approved = 0
    latest_approved_at = None
    for d in docs:
        by_status[d.get("status", "DRAFT")] = by_status.get(d.get("status", "DRAFT"), 0) + 1
        if d.get("status") == "APPROVED":
            sev = d.get("severity")
            if sev in by_severity:
                by_severity[sev] += 1
            if d.get("manual_observation"):
                approved_manual += 1
            if d.get("habitat_visible"):
                habitat_visible_approved += 1
            appr = (d.get("approval") or {}).get("at")
            if appr and (latest_approved_at is None or appr > latest_approved_at):
                latest_approved_at = appr

    total = sum(by_status.values())
    approved = by_status["APPROVED"] + by_status["RESOLVED"] + by_status["SUPERSEDED"]
    pending = by_status["PENDING_REVIEW"] + by_status["DRAFT"]
    completeness = None
    if approved + pending > 0:
        completeness = int(round(100 * approved / max(1, approved + pending)))

    payload = {
        "property_id": property_id,
        "audience": audience,
        "total_findings": total,
        "counts_by_status": by_status,
        "approved_by_severity": by_severity,
        "approved_manual_observation_count": approved_manual,
        "habitat_visible_approved_count": habitat_visible_approved,
        "completeness_pct": completeness,
        "latest_approved_at": latest_approved_at,
        "any_findings": total > 0,
        "any_approved": (approved > 0),
        "generated_at": now_iso_utc(),
    }

    if audience in {"homeowner", "public"}:
        # Homeowner-safe subset — no draft/pending internals.
        payload = {
            "property_id": property_id,
            "audience": audience,
            "approved_count": by_status["APPROVED"] + by_status["RESOLVED"],
            "approved_by_severity": by_severity,
            "resolved_count": by_status["RESOLVED"],
            "latest_approved_at": latest_approved_at,
            "generated_at": payload["generated_at"],
        }

    return payload


# ── Habitat-safe projection of approved findings ─────────────────────────
@nextgen_r.get(V1 + "/properties/{property_id}/findings/habitat-projection")
async def habitat_projection(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    """Homeowner-safe projection over APPROVED findings only.

    Strips reviewer identity, confidence methodology, notes, insurance-only
    fields, contractor pricing, ai reasoning and audit internals.
    """
    if session.role not in VIEWER_ROLES:
        raise HTTPException(403, "Role not authorized")
    await _authorize_property(session, property_id)
    cursor = nx_collections.findings.find({
        "tenant_id": session.tenant_id,
        "property_id": property_id,
        "status": {"$in": ["APPROVED", "RESOLVED"]},
        "habitat_visible": True,
    })
    items = [_project_for_habitat(strip_mongo_id(d)) async for d in cursor]
    return {"items": items, "count": len(items), "audience": "homeowner"}
