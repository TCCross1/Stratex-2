"""NextGen Passport endpoints — read, verify-chain, conflict governance (C-P-002).

Canonical ledger writes remain exclusively in
`nextgen.passport_service.append_entry`. Habitat stays read-only.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import NxSession, nx_session
from ..db import now_iso_utc, nx_collections, nx_id, strip_mongo_id
from ..governed_publish_service import governed_publish, load_expected_state
from ..passport_conflicts import (
    CONFLICT_REVIEWER_ROLES,
    get_conflict,
    mark_conflict_status,
    role_may_review_conflicts,
)
from ..passport_errors import PassportAppendError, StaleExpectedStateError
from ..passport_verify import verify_passport_chain
from ._router import nextgen_r


@nextgen_r.get("/passports/by-property/{property_id}")
async def passport_by_property(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id,
        "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found")
    passport = await nx_collections.passports.find_one({
        "property_id": property_id,
        "tenant_id": session.tenant_id,
    })
    entries = []
    if passport:
        entries = [
            strip_mongo_id(e)
            async for e in nx_collections.passport_entries.find({
                "passport_id": passport["canonical_id"],
                "tenant_id": session.tenant_id,
            }).sort("seq", 1)
        ]
    return {
        "property": strip_mongo_id(prop),
        "passport": strip_mongo_id(passport),
        "entries": entries,
        "note": (
            "Passport ledger writes are gated to passport_service.append_entry. "
            "This endpoint is read-only."
        ),
    }


@nextgen_r.get("/passports/{passport_id}/verify-chain")
async def verify_chain(
    passport_id: str,
    session: NxSession = Depends(nx_session),
):
    """Authenticated, tenant-scoped chain verification (operator-safe)."""
    passport = await nx_collections.passports.find_one({
        "canonical_id": passport_id,
        "tenant_id": session.tenant_id,
    })
    if not passport:
        raise HTTPException(404, "Passport not found on your tenant")

    # Property authorization — passport must belong to a tenant property.
    prop = await nx_collections.properties.find_one({
        "canonical_id": passport.get("property_id"),
        "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found on your tenant")

    report = await verify_passport_chain(
        tenant_id=session.tenant_id,
        passport_id=passport_id,
    )
    # Audit without secrets / stack traces.
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": (
            "PASSPORT_CHAIN_VERIFIED"
            if report["result"] in {
                "VALID", "VALID_WITH_LEGACY_UNSEALED_ENTRIES",
            }
            else "PASSPORT_CHAIN_INVALID"
        ),
        "actor_id": session.user_id,
        "actor_role": session.role,
        "resource_kind": "passport",
        "resource_id": passport_id,
        "at": now_iso_utc(),
        "payload": {
            "result": report["result"],
            "entry_count": report.get("entry_count"),
            "issue_codes": [i.get("code") for i in report.get("issues") or []],
        },
    })
    # Strip any accidental sensitive fields — response is operator-safe.
    safe = {
        "result": report["result"],
        "passport_id": report["passport_id"],
        "tenant_id": report["tenant_id"],
        "property_id": report.get("property_id"),
        "entry_count": report.get("entry_count"),
        "passport_revision": report.get("passport_revision"),
        "passport_head_hash": report.get("passport_head_hash"),
        "has_legacy_unsealed_entries": report.get("has_legacy_unsealed_entries"),
        "issues": report.get("issues") or [],
    }
    return safe


class ConflictReviewBody(BaseModel):
    resolution_reason: Optional[str] = None


class ConflictRebaseBody(BaseModel):
    expected_revision: int
    expected_head_hash: Optional[str] = None
    resolution_reason: str
    # Caller must supply a fresh idempotency key for the rebased append.
    new_idempotency_key: str
    # Optional payload override — default reuses original summary only when
    # an explicit full payload is provided via publication_payload.
    publication_payload: Optional[Dict[str, Any]] = None
    entry_type: str = "INTELLIGENCE_APPROVED"
    source_type: Optional[str] = None
    source_id: Optional[str] = None


@nextgen_r.get("/passports/{passport_id}/conflicts")
async def list_conflicts(
    passport_id: str,
    status: Optional[str] = None,
    session: NxSession = Depends(nx_session),
):
    if not role_may_review_conflicts(session.role):
        raise HTTPException(403, "Not authorized to view Passport conflicts")
    q: Dict[str, Any] = {
        "tenant_id": session.tenant_id,
        "passport_id": passport_id,
    }
    if status:
        q["status"] = status
    items = [
        strip_mongo_id(d)
        async for d in nx_collections.passport_conflicts.find(q).sort("created_at", -1)
    ]
    return {"items": items, "count": len(items)}


@nextgen_r.post("/passports/conflicts/{conflict_id}/review")
async def review_conflict(
    conflict_id: str,
    body: ConflictReviewBody,
    session: NxSession = Depends(nx_session),
):
    if not role_may_review_conflicts(session.role):
        raise HTTPException(
            403,
            f"Role {session.role!r} may not review Passport conflicts. "
            f"Allowed: {sorted(CONFLICT_REVIEWER_ROLES)}",
        )
    conflict = await get_conflict(tenant_id=session.tenant_id, conflict_id=conflict_id)
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    if conflict["status"] not in {"OPEN", "UNDER_REVIEW"}:
        raise HTTPException(409, f"Conflict status is {conflict['status']!r}")
    updated = await mark_conflict_status(
        tenant_id=session.tenant_id,
        conflict_id=conflict_id,
        status="UNDER_REVIEW",
        reviewer=session.user_id,
        resolution_reason=body.resolution_reason,
    )
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "PASSPORT_CONFLICT_REVIEWED",
        "actor_id": session.user_id,
        "actor_role": session.role,
        "resource_kind": "passport_conflict",
        "resource_id": conflict_id,
        "at": now_iso_utc(),
        "payload": {"status": "UNDER_REVIEW"},
    })
    return {"conflict": updated}


@nextgen_r.post("/passports/conflicts/{conflict_id}/reject")
async def reject_conflict(
    conflict_id: str,
    body: ConflictReviewBody,
    session: NxSession = Depends(nx_session),
):
    if not role_may_review_conflicts(session.role):
        raise HTTPException(403, "Not authorized to reject Passport conflicts")
    conflict = await get_conflict(tenant_id=session.tenant_id, conflict_id=conflict_id)
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    if conflict["status"] in {"REBASED", "REJECTED", "RESOLVED", "SUPERSEDED"}:
        raise HTTPException(409, f"Conflict already terminal: {conflict['status']!r}")
    if not body.resolution_reason:
        raise HTTPException(400, "resolution_reason is required")
    updated = await mark_conflict_status(
        tenant_id=session.tenant_id,
        conflict_id=conflict_id,
        status="REJECTED",
        reviewer=session.user_id,
        resolution_reason=body.resolution_reason,
    )
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "PASSPORT_CONFLICT_REJECTED",
        "actor_id": session.user_id,
        "actor_role": session.role,
        "resource_kind": "passport_conflict",
        "resource_id": conflict_id,
        "at": now_iso_utc(),
        "payload": {"reason": body.resolution_reason},
    })
    return {"conflict": updated}


@nextgen_r.post("/passports/conflicts/{conflict_id}/approve-rebase")
async def approve_rebase(
    conflict_id: str,
    body: ConflictRebaseBody,
    session: NxSession = Depends(nx_session),
):
    """Approve a rebase: create a NEW append with fresh expected state.

    Never rewrites the original conflict record's attempt provenance.
    Never silently merges incompatible property facts.
    """
    if not role_may_review_conflicts(session.role):
        raise HTTPException(403, "Not authorized to rebase Passport conflicts")
    conflict = await get_conflict(tenant_id=session.tenant_id, conflict_id=conflict_id)
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    if conflict["status"] in {"REBASED", "REJECTED", "RESOLVED", "SUPERSEDED"}:
        raise HTTPException(409, f"Conflict terminal: {conflict['status']!r}")
    if not body.publication_payload:
        raise HTTPException(
            400,
            "publication_payload is required for rebase — automatic merge of "
            "incompatible payloads is forbidden",
        )
    if body.new_idempotency_key == conflict.get("attempted_idempotency_key"):
        raise HTTPException(
            400,
            "Rebase requires a new idempotency key; reusing the failed key is forbidden",
        )

    await mark_conflict_status(
        tenant_id=session.tenant_id,
        conflict_id=conflict_id,
        status="REBASE_APPROVED",
        reviewer=session.user_id,
        resolution_reason=body.resolution_reason,
        rebased_idempotency_key=body.new_idempotency_key,
    )
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "PASSPORT_REBASE_APPROVED",
        "actor_id": session.user_id,
        "actor_role": session.role,
        "resource_kind": "passport_conflict",
        "resource_id": conflict_id,
        "at": now_iso_utc(),
        "payload": {
            "expected_revision": body.expected_revision,
            "new_idempotency_key": body.new_idempotency_key,
        },
    })

    try:
        result = await governed_publish(
            tenant_id=session.tenant_id,
            property_id=conflict["property_id"],
            source_type=body.source_type or conflict.get("source_type") or "rebase",
            source_id=body.source_id or conflict.get("source_id") or conflict_id,
            entry_type=body.entry_type,
            payload=body.publication_payload,
            actor_id=session.user_id,
            actor_role=session.role,
            correlation_id=conflict.get("correlation_id"),
            idempotency_key=body.new_idempotency_key,
            expected_revision=body.expected_revision,
            expected_head_hash=body.expected_head_hash,
            publication_context={
                "rebase_of_conflict_id": conflict_id,
                "original_attempt_fingerprint": conflict.get(
                    "attempted_request_fingerprint"
                ),
            },
        )
    except StaleExpectedStateError as exc:
        raise HTTPException(409, {
            "error": "PASSPORT_APPEND_CONFLICT",
            "message": "Rebase append still stale against current head",
            "conflict": exc.conflict,
        })
    except PassportAppendError as exc:
        raise HTTPException(500, f"Rebase append failed: {exc}")

    updated = await mark_conflict_status(
        tenant_id=session.tenant_id,
        conflict_id=conflict_id,
        status="REBASED",
        reviewer=session.user_id,
        resolution_reason=body.resolution_reason,
        replacement_append_id=result["entry"]["canonical_id"],
        rebased_idempotency_key=body.new_idempotency_key,
    )
    # Preserve original attempt fields — re-read proves immutability of provenance.
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "PASSPORT_REBASE_COMMITTED",
        "actor_id": session.user_id,
        "actor_role": session.role,
        "resource_kind": "passport_conflict",
        "resource_id": conflict_id,
        "at": now_iso_utc(),
        "payload": {
            "replacement_append_id": result["entry"]["canonical_id"],
            "seq": result["entry"]["seq"],
            "revision": result["entry"].get("revision"),
        },
    })
    return {
        "conflict": updated,
        "passport": result,
        "note": "Original conflict attempt provenance remains immutable.",
    }


@nextgen_r.get("/passports/by-property/{property_id}/head")
async def passport_head(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id,
        "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found")
    return await load_expected_state(
        tenant_id=session.tenant_id, property_id=property_id,
    )
