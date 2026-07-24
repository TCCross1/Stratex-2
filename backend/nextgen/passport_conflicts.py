"""Governed Passport append-conflict queue (C-P-002 / C-P-002A).

Conflicts never overwrite accepted history. Identical stale retries reuse one
active OPEN conflict via conflict_fingerprint deduplication.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Set

from .db import now_iso_utc, nx_collections, nx_id, strip_mongo_id

CONFLICT_STATUSES = (
    "OPEN",
    "UNDER_REVIEW",
    "REBASE_APPROVED",
    "REBASED",
    "REJECTED",
    "SUPERSEDED",
    "RESOLVED",
)

ACTIVE_CONFLICT_STATUSES = frozenset({"OPEN", "UNDER_REVIEW", "REBASE_APPROVED"})

CONFLICT_REVIEWER_ROLES: Set[str] = frozenset({
    "admin", "ceo", "passport_reviewer", "engineer_reviewer", "gm",
})


def _canonical_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def conflict_fingerprint(
    *,
    tenant_id: str,
    passport_id: str,
    property_id: str,
    source_type: Optional[str],
    source_id: Optional[str],
    request_fingerprint: str,
    attempted_expected_revision: Optional[int],
    attempted_expected_head_hash: Optional[str],
    actual_revision: Optional[int],
    actual_head_hash: Optional[str],
    conflict_reason: str,
) -> str:
    """Deterministic fingerprint for active-conflict deduplication (no timestamps)."""
    body = {
        "tenant_id": tenant_id,
        "passport_id": passport_id,
        "property_id": property_id,
        "source_type": source_type,
        "source_id": source_id,
        "request_fingerprint": request_fingerprint,
        "attempted_expected_revision": attempted_expected_revision,
        "attempted_expected_head_hash": attempted_expected_head_hash,
        "actual_revision": actual_revision,
        "actual_head_hash": actual_head_hash,
        "conflict_reason": conflict_reason,
    }
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


async def create_conflict_record(
    *,
    tenant_id: str,
    passport_id: str,
    property_id: str,
    source_type: Optional[str],
    source_id: Optional[str],
    attempted_idempotency_key: Optional[str],
    attempted_expected_revision: Optional[int],
    attempted_expected_head_hash: Optional[str],
    actual_revision: Optional[int],
    actual_head_hash: Optional[str],
    attempted_request_fingerprint: str,
    actor: str,
    actor_role: Optional[str],
    correlation_id: Optional[str],
    conflict_reason: str,
    audit_refs: Optional[list] = None,
    attempted_payload_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create or reuse an active OPEN conflict for an identical stale attempt."""
    fp = conflict_fingerprint(
        tenant_id=tenant_id,
        passport_id=passport_id,
        property_id=property_id,
        source_type=source_type,
        source_id=source_id,
        request_fingerprint=attempted_request_fingerprint,
        attempted_expected_revision=attempted_expected_revision,
        attempted_expected_head_hash=attempted_expected_head_hash,
        actual_revision=actual_revision,
        actual_head_hash=actual_head_hash,
        conflict_reason=conflict_reason,
    )

    existing = await nx_collections.passport_conflicts.find_one({
        "tenant_id": tenant_id,
        "passport_id": passport_id,
        "conflict_fingerprint": fp,
        "status": {"$in": list(ACTIVE_CONFLICT_STATUSES)},
    })
    if existing:
        # Touch updated_at / last_seen only — never rewrite original attempt fields.
        now = now_iso_utc()
        await nx_collections.passport_conflicts.update_one(
            {"canonical_id": existing["canonical_id"]},
            {"$set": {
                "updated_at": now,
                "last_seen_at": now,
                "duplicate_delivery_count": int(existing.get("duplicate_delivery_count") or 1) + 1,
            }},
        )
        fresh = await get_conflict(tenant_id=tenant_id, conflict_id=existing["conflict_id"])
        if fresh:
            fresh["deduplicated"] = True
            return fresh
        existing["deduplicated"] = True
        return strip_mongo_id(existing)

    now = now_iso_utc()
    doc = {
        "canonical_id": nx_id(),
        "conflict_id": nx_id(),
        "tenant_id": tenant_id,
        "passport_id": passport_id,
        "property_id": property_id,
        "source_type": source_type,
        "source_id": source_id,
        "attempted_idempotency_key": attempted_idempotency_key,
        "attempted_expected_revision": attempted_expected_revision,
        "attempted_expected_head_hash": attempted_expected_head_hash,
        "actual_revision": actual_revision,
        "actual_head_hash": actual_head_hash,
        "attempted_request_fingerprint": attempted_request_fingerprint,
        "conflict_fingerprint": fp,
        "attempted_payload_summary": attempted_payload_summary or {},
        "actor": actor,
        "actor_role": actor_role,
        "correlation_id": correlation_id,
        "conflict_reason": conflict_reason,
        "created_at": now,
        "updated_at": now,
        "last_seen_at": now,
        "duplicate_delivery_count": 1,
        "status": "OPEN",
        "reviewer": None,
        "resolution_reason": None,
        "replacement_append_id": None,
        "rebased_idempotency_key": None,
        "audit_refs": audit_refs or [],
        "original_attempt_immutable": True,
        "deduplicated": False,
    }
    try:
        await nx_collections.passport_conflicts.insert_one(dict(doc))
    except Exception as exc:
        # Concurrent identical insert — reclaim the winner.
        msg = str(exc)
        if "E11000" in msg or "duplicate" in msg.lower() or type(exc).__name__ == "DuplicateKeyError":
            raced = await nx_collections.passport_conflicts.find_one({
                "tenant_id": tenant_id,
                "passport_id": passport_id,
                "conflict_fingerprint": fp,
                "status": {"$in": list(ACTIVE_CONFLICT_STATUSES)},
            })
            if raced:
                raced = strip_mongo_id(raced)
                raced["deduplicated"] = True
                return raced
        raise
    return strip_mongo_id(doc)


async def get_conflict(*, tenant_id: str, conflict_id: str) -> Optional[Dict[str, Any]]:
    doc = await nx_collections.passport_conflicts.find_one({
        "tenant_id": tenant_id,
        "$or": [{"conflict_id": conflict_id}, {"canonical_id": conflict_id}],
    })
    return strip_mongo_id(doc)


async def mark_conflict_status(
    *,
    tenant_id: str,
    conflict_id: str,
    status: str,
    reviewer: str,
    resolution_reason: Optional[str] = None,
    replacement_append_id: Optional[str] = None,
    rebased_idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    if status not in CONFLICT_STATUSES:
        raise ValueError(f"Invalid conflict status: {status}")
    now = now_iso_utc()
    updates: Dict[str, Any] = {
        "status": status,
        "reviewer": reviewer,
        "updated_at": now,
    }
    if resolution_reason is not None:
        updates["resolution_reason"] = resolution_reason
    if replacement_append_id is not None:
        updates["replacement_append_id"] = replacement_append_id
    if rebased_idempotency_key is not None:
        updates["rebased_idempotency_key"] = rebased_idempotency_key

    await nx_collections.passport_conflicts.update_one(
        {
            "tenant_id": tenant_id,
            "$or": [{"conflict_id": conflict_id}, {"canonical_id": conflict_id}],
        },
        {"$set": updates},
    )
    fresh = await get_conflict(tenant_id=tenant_id, conflict_id=conflict_id)
    if not fresh:
        raise KeyError("conflict_not_found")
    return fresh


def role_may_review_conflicts(role: str) -> bool:
    return (role or "").strip().lower() in CONFLICT_REVIEWER_ROLES
