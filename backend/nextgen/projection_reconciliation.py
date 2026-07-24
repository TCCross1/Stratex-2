"""C-P-003 projection and source-state reconciliation — derived state only.

Reconciliation compares *existing* projection/source markers against Passport
head metadata and publication results. It must NEVER fabricate property truth,
invent findings, write canonical Passport entries, or call append_entry /
governed_publish. Full Habitat sync remains out of scope for this checkpoint.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Protocol

from .db import now_iso_utc, nx_collections, nx_id

logger = logging.getLogger("stratex.projection_reconciliation")

MODULE_IDENTITY = "nextgen.projection_reconciliation"

# Explicit statuses — stubs prefer insufficient_data over invented equality.
STATUS_MATCHED = "matched"
STATUS_DRIFT_DETECTED = "drift_detected"
STATUS_INSUFFICIENT_DATA = "insufficient_data"
STATUS_STUB = "stub"
STATUS_REJECTED = "rejected"
STATUS_REPAIRED = "repaired"
STATUS_ALREADY_CURRENT = "already_current"


@dataclass
class ReconciliationResult:
    status: str
    tenant_id: str
    property_id: str
    checked_at: str
    notes: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProjectionReconciler(Protocol):
    """Port for projection vs Passport-head comparison."""

    async def reconcile_property(
        self,
        *,
        tenant_id: str,
        property_id: str,
    ) -> ReconciliationResult:
        ...


class StubProjectionReconciler:
    """Deterministic stub reconciler for FakeMongo / unit tests.

    Rules:
    - If no passport head and no projection marker → insufficient_data
    - If passport head exists but no projection marker → insufficient_data
      (does not invent a projection)
    - If both exist and head hashes match → matched
    - If both exist and head hashes differ → drift_detected
    - Never writes passport_entries / never calls append_entry
    """

    async def reconcile_property(
        self,
        *,
        tenant_id: str,
        property_id: str,
    ) -> ReconciliationResult:
        now = now_iso_utc()
        passport = await nx_collections.passports.find_one({
            "tenant_id": tenant_id,
            "property_id": property_id,
            "status": "active",
        })
        marker = await nx_collections.passport_projection_markers.find_one({
            "tenant_id": tenant_id,
            "property_id": property_id,
        })

        head_hash = (passport or {}).get("head_hash")
        marker_hash = (marker or {}).get("projected_head_hash")
        evidence = {
            "passport_present": passport is not None,
            "marker_present": marker is not None,
            "head_hash_present": bool(head_hash),
            "marker_hash_present": bool(marker_hash),
            # Hashes are content digests — not secrets; still truncate for logs.
            "head_hash_prefix": (head_hash or "")[:12] or None,
            "marker_hash_prefix": (marker_hash or "")[:12] or None,
            "reconciler": MODULE_IDENTITY,
            "mode": STATUS_STUB,
        }

        if not passport or not head_hash or not marker or not marker_hash:
            result = ReconciliationResult(
                status=STATUS_INSUFFICIENT_DATA,
                tenant_id=tenant_id,
                property_id=property_id,
                checked_at=now,
                notes=(
                    "Stub reconciler refuses to invent projection or property "
                    "truth when markers/head are incomplete."
                ),
                evidence=evidence,
            )
        elif head_hash == marker_hash:
            result = ReconciliationResult(
                status=STATUS_MATCHED,
                tenant_id=tenant_id,
                property_id=property_id,
                checked_at=now,
                notes="Projection marker matches active Passport head_hash.",
                evidence=evidence,
            )
        else:
            result = ReconciliationResult(
                status=STATUS_DRIFT_DETECTED,
                tenant_id=tenant_id,
                property_id=property_id,
                checked_at=now,
                notes="Projection marker head differs from Passport head_hash.",
                evidence=evidence,
            )

        logger.info(
            "projection_reconcile status=%s property_id=%s tenant_id=%s",
            result.status,
            property_id,
            tenant_id,
        )
        return result


async def reconcile_property_stub(
    *,
    tenant_id: str,
    property_id: str,
    reconciler: Optional[ProjectionReconciler] = None,
) -> Dict[str, Any]:
    """Convenience entrypoint returning a plain dict."""
    impl: ProjectionReconciler = reconciler or StubProjectionReconciler()
    result = await impl.reconcile_property(
        tenant_id=tenant_id, property_id=property_id
    )
    return result.to_dict()


async def _audit_reconciliation(
    *,
    tenant_id: str,
    property_id: str,
    event_type: str,
    actor_id: str,
    payload: Dict[str, Any],
) -> None:
    safe = dict(payload or {})
    for banned in ("password", "secret", "authorization", "token", "api_key"):
        safe.pop(banned, None)
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "event_type": event_type,
        "actor_id": actor_id,
        "actor_role": "service",
        "resource_kind": "property",
        "resource_id": property_id,
        "at": now_iso_utc(),
        "payload": safe,
    })


async def repair_projection_marker(
    *,
    tenant_id: str,
    property_id: str,
    actor_id: str = "reconciler",
) -> Dict[str, Any]:
    """Align projection marker to active Passport head — derived state only.

    Never writes passport_entries. Cross-tenant/property mismatches reject.
    Idempotent when already matched.
    """
    now = now_iso_utc()
    passport = await nx_collections.passports.find_one({
        "tenant_id": tenant_id,
        "property_id": property_id,
        "status": "active",
    })
    if not passport or not passport.get("head_hash"):
        return {
            "status": STATUS_INSUFFICIENT_DATA,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "checked_at": now,
            "notes": "No active Passport head available for projection repair.",
        }

    foreign = await nx_collections.passport_projection_markers.find_one({
        "property_id": property_id,
        "tenant_id": {"$ne": tenant_id},
    })
    if foreign:
        await _audit_reconciliation(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type="RECONCILE_REJECTED",
            actor_id=actor_id,
            payload={"reason": "cross_tenant_marker", "status": STATUS_REJECTED},
        )
        return {
            "status": STATUS_REJECTED,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "checked_at": now,
            "notes": "Cross-tenant projection marker rejected.",
        }

    head = passport["head_hash"]
    marker = await nx_collections.passport_projection_markers.find_one({
        "tenant_id": tenant_id,
        "property_id": property_id,
    })
    if marker and marker.get("projected_head_hash") == head:
        return {
            "status": STATUS_ALREADY_CURRENT,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "checked_at": now,
            "notes": "Projection marker already matches Passport head.",
        }

    if marker:
        await nx_collections.passport_projection_markers.update_one(
            {"tenant_id": tenant_id, "property_id": property_id},
            {"$set": {"projected_head_hash": head, "updated_at": now}},
        )
    else:
        await nx_collections.passport_projection_markers.insert_one({
            "canonical_id": nx_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "projected_head_hash": head,
            "updated_at": now,
        })

    await _audit_reconciliation(
        tenant_id=tenant_id,
        property_id=property_id,
        event_type="PROJECTION_RECONCILED",
        actor_id=actor_id,
        payload={
            "status": STATUS_REPAIRED,
            "head_hash_prefix": head[:12],
            "created_marker": marker is None,
        },
    )
    return {
        "status": STATUS_REPAIRED,
        "tenant_id": tenant_id,
        "property_id": property_id,
        "checked_at": now,
        "notes": "Projection marker aligned to Passport head (derived state only).",
        "passport_entries_written": 0,
    }


async def reconcile_source_publication_state(
    *,
    tenant_id: str,
    property_id: str,
    source_id: str,
    actor_id: str = "reconciler",
) -> Dict[str, Any]:
    """Source workflow alignment after a valid publication result exists.

    Law: source cannot become approved without a valid publication result.
    Never rewrites Passport history. Cross-tenant/property rejects.
    """
    now = now_iso_utc()
    source = await nx_collections.publication_sources.find_one({
        "canonical_id": source_id,
    })
    if not source:
        return {
            "status": STATUS_INSUFFICIENT_DATA,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "source_id": source_id,
            "checked_at": now,
            "notes": "Source record missing.",
        }

    if source.get("tenant_id") != tenant_id or source.get("property_id") != property_id:
        await _audit_reconciliation(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type="RECONCILE_REJECTED",
            actor_id=actor_id,
            payload={
                "reason": "cross_tenant_or_property_source",
                "source_id": source_id,
            },
        )
        return {
            "status": STATUS_REJECTED,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "source_id": source_id,
            "checked_at": now,
            "notes": "Cross-tenant/property source reconciliation rejected.",
        }

    pub = await nx_collections.publication_results.find_one({
        "tenant_id": tenant_id,
        "property_id": property_id,
        "source_id": source_id,
        "status": "published",
    })
    if not pub:
        return {
            "status": STATUS_INSUFFICIENT_DATA,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "source_id": source_id,
            "checked_at": now,
            "notes": (
                "No valid publication result — source cannot become approved "
                "via reconciliation alone."
            ),
            "source_status": source.get("status"),
        }

    if source.get("status") == "approved" and source.get("publication_result_id") == pub.get(
        "canonical_id"
    ):
        return {
            "status": STATUS_ALREADY_CURRENT,
            "tenant_id": tenant_id,
            "property_id": property_id,
            "source_id": source_id,
            "checked_at": now,
            "notes": "Source already aligned to publication result.",
        }

    await nx_collections.publication_sources.update_one(
        {
            "canonical_id": source_id,
            "tenant_id": tenant_id,
            "property_id": property_id,
        },
        {
            "$set": {
                "status": "approved",
                "publication_result_id": pub.get("canonical_id"),
                "reconciled_at": now,
            }
        },
    )
    await _audit_reconciliation(
        tenant_id=tenant_id,
        property_id=property_id,
        event_type="SOURCE_STATE_RECONCILED",
        actor_id=actor_id,
        payload={
            "source_id": source_id,
            "publication_result_id": pub.get("canonical_id"),
            "status": STATUS_REPAIRED,
        },
    )
    return {
        "status": STATUS_REPAIRED,
        "tenant_id": tenant_id,
        "property_id": property_id,
        "source_id": source_id,
        "checked_at": now,
        "notes": "Source workflow state aligned to existing publication result.",
        "passport_entries_written": 0,
    }
