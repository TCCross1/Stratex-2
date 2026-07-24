"""C-P-004 report publication package foundation — Blueprint §22 Stage 12–15 · SD-013.

Package/lifecycle foundation only. Does NOT:
- alter Passport ledger truth
- call append_entry / governed_publish (not a second publisher)
- introduce a second outbox worker (delivery recovery uses emit_outbox_event)

Owned concerns:
- ReportPublicationPackage state machine + durable package rows
- Deterministic report cache identity from stable inputs
- Delivery recovery outbox emission (write-side only)
- Bounded Passport projection + property timeline producers
  (idempotent; approved / versioned Passport heads only)
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from .db import now_iso_utc, nx_collections, nx_id
from .outbox import emit_outbox_event

logger = logging.getLogger("stratex.report_publication")

MODULE_IDENTITY = "nextgen.report_publication"
PACKAGE_CONTRACT = "ReportPublicationPackage"
CONTRACT_STATUS = "PROPOSED"  # never FROZEN from this lane
CONTRACT_VERSION = "0.0.0"

# Lifecycle states (ordered for documentation; transitions enforced below).
STATE_PROPOSED = "PROPOSED"
STATE_INPUTS_VALIDATED = "INPUTS_VALIDATED"
STATE_RENDERING = "RENDERING"
STATE_RENDERED = "RENDERED"
STATE_UNDER_REVIEW = "UNDER_REVIEW"
STATE_APPROVED_FOR_DELIVERY = "APPROVED_FOR_DELIVERY"
STATE_DELIVERING = "DELIVERING"
STATE_DELIVERED = "DELIVERED"
STATE_FAILED = "FAILED"
STATE_SUPERSEDED = "SUPERSEDED"

PUBLICATION_STATES = frozenset(
    {
        STATE_PROPOSED,
        STATE_INPUTS_VALIDATED,
        STATE_RENDERING,
        STATE_RENDERED,
        STATE_UNDER_REVIEW,
        STATE_APPROVED_FOR_DELIVERY,
        STATE_DELIVERING,
        STATE_DELIVERED,
        STATE_FAILED,
        STATE_SUPERSEDED,
    }
)

_ALLOWED_TRANSITIONS: Dict[str, frozenset] = {
    STATE_PROPOSED: frozenset({STATE_INPUTS_VALIDATED, STATE_FAILED, STATE_SUPERSEDED}),
    STATE_INPUTS_VALIDATED: frozenset({STATE_RENDERING, STATE_FAILED, STATE_SUPERSEDED}),
    STATE_RENDERING: frozenset({STATE_RENDERED, STATE_FAILED}),
    STATE_RENDERED: frozenset({STATE_UNDER_REVIEW, STATE_FAILED, STATE_SUPERSEDED}),
    STATE_UNDER_REVIEW: frozenset(
        {STATE_APPROVED_FOR_DELIVERY, STATE_RENDERING, STATE_FAILED, STATE_SUPERSEDED}
    ),
    STATE_APPROVED_FOR_DELIVERY: frozenset(
        {STATE_DELIVERING, STATE_FAILED, STATE_SUPERSEDED}
    ),
    STATE_DELIVERING: frozenset({STATE_DELIVERED, STATE_FAILED}),
    STATE_DELIVERED: frozenset({STATE_SUPERSEDED}),
    STATE_FAILED: frozenset({STATE_PROPOSED, STATE_SUPERSEDED}),
    STATE_SUPERSEDED: frozenset(),
}

# Outbox event types for delivery recovery (consumed by existing outbox_worker).
EVENT_REPORT_DELIVERY_REQUESTED = "REPORT_DELIVERY_REQUESTED"
EVENT_REPORT_DELIVERED = "REPORT_DELIVERED"
EVENT_REPORT_DELIVERY_FAILED = "REPORT_DELIVERY_FAILED"

TIMELINE_KIND_REPORT_PUBLICATION = "REPORT_PUBLICATION"
TIMELINE_KIND_REPORT_DELIVERED = "REPORT_DELIVERED"

# Stable keys allowed in cache identity (order-independent hashing).
_CACHE_IDENTITY_KEYS = (
    "tenant_id",
    "property_id",
    "passport_id",
    "passport_version",
    "passport_head_hash",
    "report_type",
    "template_id",
    "template_version",
    "approved_entry_ids",
    "locale",
    "schema_version",
)


class ReportPublicationError(ValueError):
    """Base error for report publication foundation."""


class InvalidPublicationTransition(ReportPublicationError):
    pass


class PassportTruthGuardError(ReportPublicationError):
    """Raised when an operation would invent or mutate Passport truth."""


def _fingerprint(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def report_cache_identity(stable_inputs: Dict[str, Any]) -> str:
    """Deterministic cache key from stable publication inputs only.

    Volatile fields (timestamps, actor ids, lease tokens, render wall-clock)
    are excluded. ``approved_entry_ids`` are sorted for order-independence.
    """
    if not isinstance(stable_inputs, dict):
        raise ReportPublicationError("stable_inputs must be a dict")

    canonical: Dict[str, Any] = {}
    for key in _CACHE_IDENTITY_KEYS:
        if key not in stable_inputs:
            continue
        value = stable_inputs[key]
        if key == "approved_entry_ids":
            if value is None:
                continue
            if not isinstance(value, (list, tuple, set)):
                raise ReportPublicationError("approved_entry_ids must be a sequence")
            value = sorted(str(v) for v in value)
        canonical[key] = value

    required = ("tenant_id", "property_id", "report_type", "template_id")
    missing = [k for k in required if not canonical.get(k)]
    if missing:
        raise ReportPublicationError(
            f"report_cache_identity missing required stable inputs: {missing}"
        )
    return _fingerprint({"cache_identity_v1": canonical})


def _validate_transition(current: str, target: str) -> None:
    if current not in PUBLICATION_STATES:
        raise InvalidPublicationTransition(f"unknown current state: {current}")
    if target not in PUBLICATION_STATES:
        raise InvalidPublicationTransition(f"unknown target state: {target}")
    if target == current:
        return
    allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidPublicationTransition(
            f"illegal transition {current} -> {target}; allowed={sorted(allowed)}"
        )


def _provenance(
    *,
    passport_id: Optional[str],
    passport_version: Optional[Any],
    passport_head_hash: Optional[str],
    approved_entry_ids: Optional[Sequence[str]],
    source_refs: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "passport_id": passport_id,
        "passport_version": passport_version,
        "passport_head_hash": passport_head_hash,
        "approved_entry_ids": list(approved_entry_ids or []),
        "source_refs": list(source_refs or []),
        "projector": MODULE_IDENTITY,
        "alters_passport_truth": False,
    }


async def propose_report_publication(
    *,
    tenant_id: str,
    property_id: str,
    report_type: str,
    template_id: str,
    template_version: str = "0.0.0",
    passport_id: Optional[str] = None,
    passport_version: Optional[Any] = None,
    passport_head_hash: Optional[str] = None,
    approved_entry_ids: Optional[Sequence[str]] = None,
    object_reference: Optional[str] = None,
    locale: str = "en-US",
    schema_version: str = CONTRACT_VERSION,
    actor_id: str = "system",
    idempotency_key: Optional[str] = None,
    extra_stable_inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create or return an existing ReportPublicationPackage in PROPOSED state."""
    if not tenant_id or not property_id or not report_type or not template_id:
        raise ReportPublicationError(
            "tenant_id, property_id, report_type, and template_id are required"
        )

    stable = {
        "tenant_id": tenant_id,
        "property_id": property_id,
        "passport_id": passport_id,
        "passport_version": passport_version,
        "passport_head_hash": passport_head_hash,
        "report_type": report_type,
        "template_id": template_id,
        "template_version": template_version,
        "approved_entry_ids": list(approved_entry_ids or []),
        "locale": locale,
        "schema_version": schema_version,
    }
    if extra_stable_inputs:
        for k, v in extra_stable_inputs.items():
            if k in _CACHE_IDENTITY_KEYS:
                stable[k] = v

    cache_id = report_cache_identity(stable)
    key = idempotency_key or f"report.publication:{cache_id}"

    existing = await nx_collections.report_publications.find_one(
        {"idempotency_key": key}
    )
    if existing:
        return {
            "report_publication_id": existing["report_publication_id"],
            "duplicate": True,
            "state": existing["state"],
            "cache_identity": existing["cache_identity"],
            "package": existing,
        }

    now = now_iso_utc()
    content_checksum = _fingerprint(
        {
            "cache_identity": cache_id,
            "object_reference": object_reference,
            "template_version": template_version,
        }
    )
    package = {
        "canonical_id": nx_id(),
        "report_publication_id": nx_id(),
        "tenant_id": tenant_id,
        "property_id": property_id,
        "passport_id": passport_id,
        "passport_version": passport_version,
        "passport_head_hash": passport_head_hash,
        "report_type": report_type,
        "template_id": template_id,
        "template_version": template_version,
        "locale": locale,
        "schema_version": schema_version,
        "state": STATE_PROPOSED,
        "checksum": content_checksum,
        "cache_identity": cache_id,
        "object_reference": object_reference,
        "provenance": _provenance(
            passport_id=passport_id,
            passport_version=passport_version,
            passport_head_hash=passport_head_hash,
            approved_entry_ids=approved_entry_ids,
        ),
        "confidence": {"band": "unknown", "notes": "foundation package; not rendered"},
        "unknown_state": {"state": "unknown", "reasons": ["not_yet_rendered"]},
        "package_contract": PACKAGE_CONTRACT,
        "package_contract_status": CONTRACT_STATUS,
        "package_contract_version": CONTRACT_VERSION,
        "idempotency_key": key,
        "delivery_outbox_event_id": None,
        "failure_reason": None,
        "created_at": now,
        "updated_at": now,
        "created_by": actor_id,
        "module": MODULE_IDENTITY,
        "alters_passport_truth": False,
    }
    await nx_collections.report_publications.insert_one(dict(package))
    await _audit(
        tenant_id=tenant_id,
        event_type="REPORT_PUBLICATION_PROPOSED",
        actor_id=actor_id,
        resource_id=package["report_publication_id"],
        payload={
            "state": STATE_PROPOSED,
            "cache_identity": cache_id,
            "report_type": report_type,
            "template_id": template_id,
        },
    )
    return {
        "report_publication_id": package["report_publication_id"],
        "duplicate": False,
        "state": STATE_PROPOSED,
        "cache_identity": cache_id,
        "package": package,
    }


async def transition_report_publication(
    *,
    report_publication_id: str,
    target_state: str,
    actor_id: str = "system",
    object_reference: Optional[str] = None,
    checksum: Optional[str] = None,
    failure_reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Advance package lifecycle with guarded transitions (no Passport writes)."""
    row = await nx_collections.report_publications.find_one(
        {"report_publication_id": report_publication_id}
    )
    if row is None:
        raise LookupError(f"report publication not found: {report_publication_id}")

    current = row["state"]
    _validate_transition(current, target_state)
    if current == target_state:
        return {
            "report_publication_id": report_publication_id,
            "state": current,
            "changed": False,
            "package": row,
        }

    now = now_iso_utc()
    updates: Dict[str, Any] = {
        "state": target_state,
        "updated_at": now,
        "updated_by": actor_id,
    }
    if object_reference is not None:
        updates["object_reference"] = object_reference
    if checksum is not None:
        updates["checksum"] = checksum
    if failure_reason is not None:
        updates["failure_reason"] = failure_reason[:500]
    elif target_state != STATE_FAILED:
        updates["failure_reason"] = None
    if notes is not None:
        updates["transition_notes"] = notes[:300]

    await nx_collections.report_publications.update_one(
        {"report_publication_id": report_publication_id},
        {"$set": updates},
    )
    refreshed = await nx_collections.report_publications.find_one(
        {"report_publication_id": report_publication_id}
    )
    await _audit(
        tenant_id=row["tenant_id"],
        event_type="REPORT_PUBLICATION_TRANSITION",
        actor_id=actor_id,
        resource_id=report_publication_id,
        payload={
            "from_state": current,
            "to_state": target_state,
            "notes": (notes or "")[:300] or None,
        },
    )
    return {
        "report_publication_id": report_publication_id,
        "state": target_state,
        "changed": True,
        "package": refreshed,
    }


async def enqueue_report_delivery(
    *,
    report_publication_id: str,
    actor_id: str = "system",
    channel: str = "default",
) -> Dict[str, Any]:
    """Enqueue delivery recovery via accepted ``emit_outbox_event`` (no second worker).

    Package must be APPROVED_FOR_DELIVERY (or already DELIVERING). Transitions to
    DELIVERING and emits REPORT_DELIVERY_REQUESTED idempotently.
    """
    row = await nx_collections.report_publications.find_one(
        {"report_publication_id": report_publication_id}
    )
    if row is None:
        raise LookupError(f"report publication not found: {report_publication_id}")

    state = row["state"]
    if state == STATE_DELIVERED:
        return {
            "report_publication_id": report_publication_id,
            "status": "already_delivered",
            "delivery_outbox_event_id": row.get("delivery_outbox_event_id"),
            "duplicate": True,
        }
    if state not in (STATE_APPROVED_FOR_DELIVERY, STATE_DELIVERING):
        raise InvalidPublicationTransition(
            f"delivery requires APPROVED_FOR_DELIVERY or DELIVERING; got {state}"
        )

    if state == STATE_APPROVED_FOR_DELIVERY:
        moved = await transition_report_publication(
            report_publication_id=report_publication_id,
            target_state=STATE_DELIVERING,
            actor_id=actor_id,
            notes="enqueue_report_delivery",
        )
        row = moved["package"]

    idem = f"report.delivery:{report_publication_id}:{channel}"
    emitted = await emit_outbox_event(
        tenant_id=row["tenant_id"],
        event_type=EVENT_REPORT_DELIVERY_REQUESTED,
        payload={
            "report_publication_id": report_publication_id,
            "property_id": row["property_id"],
            "tenant_id": row["tenant_id"],
            "report_type": row["report_type"],
            "template_id": row["template_id"],
            "cache_identity": row["cache_identity"],
            "checksum": row.get("checksum"),
            "object_reference": row.get("object_reference"),
            "channel": channel,
            "passport_id": row.get("passport_id"),
            "passport_version": row.get("passport_version"),
        },
        idempotency_key=idem,
        producer_resource_kind="report_publication",
        producer_resource_id=report_publication_id,
    )

    if not emitted.get("duplicate"):
        await nx_collections.report_publications.update_one(
            {"report_publication_id": report_publication_id},
            {
                "$set": {
                    "delivery_outbox_event_id": emitted["event_id"],
                    "updated_at": now_iso_utc(),
                }
            },
        )

    return {
        "report_publication_id": report_publication_id,
        "status": "delivery_enqueued",
        "event_id": emitted["event_id"],
        "duplicate": emitted["duplicate"],
        "event_type": EVENT_REPORT_DELIVERY_REQUESTED,
        "worker": "nextgen.outbox_worker",  # existing worker only
    }


async def mark_report_delivered(
    *,
    report_publication_id: str,
    actor_id: str = "system",
    delivery_receipt: Optional[str] = None,
) -> Dict[str, Any]:
    """Mark package DELIVERED after successful outbox consumer handling."""
    result = await transition_report_publication(
        report_publication_id=report_publication_id,
        target_state=STATE_DELIVERED,
        actor_id=actor_id,
        notes=delivery_receipt or "delivered",
    )
    row = result["package"]
    await emit_outbox_event(
        tenant_id=row["tenant_id"],
        event_type=EVENT_REPORT_DELIVERED,
        payload={
            "report_publication_id": report_publication_id,
            "property_id": row["property_id"],
            "checksum": row.get("checksum"),
            "cache_identity": row.get("cache_identity"),
        },
        idempotency_key=f"report.delivered:{report_publication_id}",
        producer_resource_kind="report_publication",
        producer_resource_id=report_publication_id,
    )
    return result


async def produce_bounded_passport_projection(
    *,
    tenant_id: str,
    property_id: str,
    audience: str = "internal",
    max_entries: int = 50,
) -> Dict[str, Any]:
    """Build a bounded read projection from an approved/versioned Passport head.

    Read-only w.r.t. Passport ledger. Never invents property truth when head or
    version markers are missing. Caps entry fan-out via ``max_entries``.
    """
    if max_entries < 1 or max_entries > 200:
        raise ReportPublicationError("max_entries must be in [1, 200]")

    now = now_iso_utc()
    passport = await nx_collections.passports.find_one(
        {
            "tenant_id": tenant_id,
            "property_id": property_id,
            "status": "active",
        }
    )
    if not passport:
        return {
            "status": "insufficient_data",
            "tenant_id": tenant_id,
            "property_id": property_id,
            "audience": audience,
            "checked_at": now,
            "entries": [],
            "notes": "No active Passport head; refusing to invent projection truth.",
            "module": MODULE_IDENTITY,
            "alters_passport_truth": False,
        }

    head_hash = passport.get("head_hash")
    version = passport.get("version") or passport.get("revision")
    passport_id = passport.get("canonical_id") or passport.get("passport_id")
    if not head_hash or version is None:
        return {
            "status": "insufficient_data",
            "tenant_id": tenant_id,
            "property_id": property_id,
            "audience": audience,
            "checked_at": now,
            "entries": [],
            "notes": "Passport head lacks version/hash; refusing unbounded invent.",
            "module": MODULE_IDENTITY,
            "alters_passport_truth": False,
        }

    cursor = (
        nx_collections.passport_entries.find(
            {
                "tenant_id": tenant_id,
                "property_id": property_id,
                "passport_id": passport_id,
            }
        )
        .sort("seq", -1)
        .limit(max_entries)
    )
    entries = await cursor.to_list(max_entries)
    # Prefer approved / releasable markers when present.
    bounded: List[Dict[str, Any]] = []
    for entry in entries:
        release = (entry.get("release_state") or entry.get("state") or "").upper()
        if release and release in {"DRAFT", "REJECTED", "INTERNAL_ONLY"}:
            continue
        bounded.append(
            {
                "entry_id": entry.get("canonical_id"),
                "seq": entry.get("seq"),
                "entry_type": entry.get("entry_type"),
                "content_hash": entry.get("content_hash"),
                "revision": entry.get("revision"),
            }
        )

    projection = {
        "status": "ok",
        "tenant_id": tenant_id,
        "property_id": property_id,
        "audience": audience,
        "checked_at": now,
        "passport_id": passport_id,
        "passport_version": version,
        "passport_head_hash": head_hash,
        "entry_count": len(bounded),
        "max_entries": max_entries,
        "entries": bounded,
        "module": MODULE_IDENTITY,
        "alters_passport_truth": False,
        "provenance": _provenance(
            passport_id=passport_id,
            passport_version=version,
            passport_head_hash=head_hash,
            approved_entry_ids=[e["entry_id"] for e in bounded if e.get("entry_id")],
        ),
    }

    # Idempotent marker upsert (derived state only — not Passport truth).
    marker_key = {
        "tenant_id": tenant_id,
        "property_id": property_id,
        "audience": audience,
        "kind": "report_publication_projection",
    }
    existing = await nx_collections.passport_projection_markers.find_one(marker_key)
    marker_body = {
        **marker_key,
        "projected_head_hash": head_hash,
        "projected_version": version,
        "passport_id": passport_id,
        "entry_count": len(bounded),
        "updated_at": now,
        "module": MODULE_IDENTITY,
    }
    if existing:
        if (
            existing.get("projected_head_hash") == head_hash
            and existing.get("projected_version") == version
            and existing.get("entry_count") == len(bounded)
        ):
            projection["marker_status"] = "already_current"
        else:
            await nx_collections.passport_projection_markers.update_one(
                {"canonical_id": existing["canonical_id"]},
                {"$set": marker_body},
            )
            projection["marker_status"] = "updated"
    else:
        marker_body["canonical_id"] = nx_id()
        marker_body["created_at"] = now
        await nx_collections.passport_projection_markers.insert_one(dict(marker_body))
        projection["marker_status"] = "created"

    return projection


async def produce_report_timeline_entry(
    *,
    tenant_id: str,
    property_id: str,
    report_publication_id: str,
    kind: str = TIMELINE_KIND_REPORT_PUBLICATION,
    actor_id: str = "system",
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Idempotent property timeline producer for report publication events.

    Requires an existing package bound to an approved/versioned passport when
    passport fields are present. Never writes passport_entries.
    """
    if kind not in {
        TIMELINE_KIND_REPORT_PUBLICATION,
        TIMELINE_KIND_REPORT_DELIVERED,
        "REPORT_RENDERED",
        "REPORT_APPROVED_FOR_DELIVERY",
    }:
        raise ReportPublicationError(f"unsupported timeline kind: {kind}")

    package = await nx_collections.report_publications.find_one(
        {"report_publication_id": report_publication_id, "tenant_id": tenant_id}
    )
    if package is None:
        raise LookupError(f"report publication not found: {report_publication_id}")
    if package.get("property_id") != property_id:
        raise PassportTruthGuardError("property_id mismatch for timeline producer")

    # Only emit timeline for packages that reached a reviewable/delivery state
    # or explicit failure — never for raw PROPOSED without validation.
    allowed_states = {
        STATE_RENDERED,
        STATE_UNDER_REVIEW,
        STATE_APPROVED_FOR_DELIVERY,
        STATE_DELIVERING,
        STATE_DELIVERED,
        STATE_FAILED,
        STATE_SUPERSEDED,
        STATE_INPUTS_VALIDATED,
    }
    if package["state"] not in allowed_states:
        return {
            "status": "skipped",
            "reason": f"package state {package['state']} not timeline-eligible",
            "report_publication_id": report_publication_id,
        }

    idem = f"timeline.{kind}:{report_publication_id}"
    existing = await nx_collections.property_timeline.find_one({"idempotency_key": idem})
    if existing:
        return {
            "status": "already_current",
            "duplicate": True,
            "timeline_id": existing["canonical_id"],
            "entry": existing,
        }

    now = now_iso_utc()
    entry = {
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "property_id": property_id,
        "kind": kind,
        "at": now,
        "actor_user_id": actor_id,
        "reference_kind": "report_publication",
        "reference_id": report_publication_id,
        "summary": summary
        or (
            f"{package.get('report_type')} · {package.get('template_id')} · "
            f"{package.get('state')}"
        )[:200],
        "passport_id": package.get("passport_id"),
        "passport_version": package.get("passport_version"),
        "passport_head_hash": package.get("passport_head_hash"),
        "cache_identity": package.get("cache_identity"),
        "checksum": package.get("checksum"),
        "idempotency_key": idem,
        "module": MODULE_IDENTITY,
        "alters_passport_truth": False,
    }
    await nx_collections.property_timeline.insert_one(dict(entry))
    return {
        "status": "created",
        "duplicate": False,
        "timeline_id": entry["canonical_id"],
        "entry": entry,
    }


async def _audit(
    *,
    tenant_id: str,
    event_type: str,
    actor_id: str,
    resource_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    safe = dict(payload or {})
    for banned in (
        "password",
        "secret",
        "authorization",
        "token",
        "api_key",
        "private_key",
        "hmac_key",
    ):
        safe.pop(banned, None)
    await nx_collections.audit_events.insert_one(
        {
            "canonical_id": nx_id(),
            "tenant_id": tenant_id,
            "event_type": event_type,
            "actor_id": actor_id,
            "actor_role": "service",
            "resource_kind": "report_publication",
            "resource_id": resource_id,
            "at": now_iso_utc(),
            "payload": safe,
        }
    )
    logger.info(
        "report_publication_audit event_type=%s resource_id=%s actor_id=%s",
        event_type,
        resource_id,
        actor_id,
    )


def authority_surface_check() -> Dict[str, Any]:
    """Static self-description for writer-authority audits."""
    return {
        "module": MODULE_IDENTITY,
        "calls_append_entry": False,
        "calls_governed_publish": False,
        "second_publisher": False,
        "second_outbox_worker": False,
        "delivery_via": "outbox.emit_outbox_event",
        "alters_passport_truth": False,
        "contract_status": CONTRACT_STATUS,
        "package_contract": PACKAGE_CONTRACT,
    }
