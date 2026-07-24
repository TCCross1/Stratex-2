"""C-P-003 projection reconciliation stubs — interfaces only.

Reconciliation compares *existing* projection markers against Passport head
metadata. It must NEVER fabricate property truth, invent findings, or write
canonical Passport entries. Full Habitat sync remains out of scope for this
checkpoint.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Protocol

from .db import now_iso_utc, nx_collections

logger = logging.getLogger("stratex.projection_reconciliation")

MODULE_IDENTITY = "nextgen.projection_reconciliation"

# Explicit statuses — stubs prefer insufficient_data over invented equality.
STATUS_MATCHED = "matched"
STATUS_DRIFT_DETECTED = "drift_detected"
STATUS_INSUFFICIENT_DATA = "insufficient_data"
STATUS_STUB = "stub"


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
