"""Governed publication authority — sole path from approved sources to Passport.

Findings and Intelligence approve source records, then delegate canonical
ledger publication through this service, which calls
`passport_service.append_entry` (the only NextGen ledger writer).

Module identity: workflow.governed_publish_service (C-P-002).
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from .db import now_iso_utc, nx_collections, nx_id
from .passport_errors import (
    IdempotencyConflictError,
    MissingExpectedStateError,
    PassportAppendError,
    StaleExpectedStateError,
    TransactionUnavailableError,
)
from .passport_service import append_entry, get_passport_head

logger = logging.getLogger("stratex.governed_publish")

# Stable module path string for architecture assertions / documentation.
MODULE_IDENTITY = "workflow.governed_publish_service"


def _fingerprint(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


async def _audit(
    *,
    tenant_id: str,
    event_type: str,
    actor_id: str,
    actor_role: Optional[str],
    resource_kind: str,
    resource_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    safe = dict(payload or {})
    for banned in ("password", "secret", "authorization", "totp", "mfa", "hmac_key"):
        safe.pop(banned, None)
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "event_type": event_type,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "at": now_iso_utc(),
        "payload": safe,
    })


async def governed_publish(
    *,
    tenant_id: str,
    property_id: str,
    source_type: str,
    source_id: str,
    entry_type: str,
    payload: Dict[str, Any],
    actor_id: str,
    actor_role: Optional[str] = None,
    correlation_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    expected_revision: Optional[int] = None,
    expected_head_hash: Optional[str] = None,
    schema_version: str = "2",
    publication_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Publish an approved source into the canonical Passport ledger.

    Requires at least one expected-state token. On stale head, creates a
    governed conflict and does not mark the source committed.
    """
    if expected_revision is None and not expected_head_hash:
        await _audit(
            tenant_id=tenant_id,
            event_type="PUBLICATION_FAILED",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_kind=source_type,
            resource_id=source_id,
            payload={"reason": "MISSING_EXPECTED_STATE"},
        )
        raise MissingExpectedStateError(
            "Governed publication requires expected_revision or expected_head_hash"
        )

    key = idempotency_key or f"{source_type}.publish:{source_id}"
    await _audit(
        tenant_id=tenant_id,
        event_type="PUBLICATION_REQUESTED",
        actor_id=actor_id,
        actor_role=actor_role,
        resource_kind=source_type,
        resource_id=source_id,
        payload={
            "idempotency_key": key,
            "expected_revision": expected_revision,
            "expected_head_hash": expected_head_hash,
            "request_fingerprint": _fingerprint(payload),
            "correlation_id": correlation_id,
        },
    )

    try:
        result = await append_entry(
            tenant_id=tenant_id,
            property_id=property_id,
            entry_type=entry_type,
            payload=payload,
            authored_by=actor_id,
            source_type=source_type,
            source_id=source_id,
            correlation_id=correlation_id,
            idempotency_key=key,
            expected_revision=expected_revision,
            expected_head_hash=expected_head_hash,
            schema_version=schema_version,
            publication_context=publication_context or {
                "source_type": source_type,
                "source_id": source_id,
            },
            require_expected_state=True,
            actor_role=actor_role,
        )
    except StaleExpectedStateError as exc:
        await _audit(
            tenant_id=tenant_id,
            event_type="PUBLICATION_FAILED",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_kind=source_type,
            resource_id=source_id,
            payload={
                "reason": "STALE_EXPECTED_STATE",
                "conflict_id": (exc.conflict or {}).get("conflict_id"),
            },
        )
        raise
    except (IdempotencyConflictError, TransactionUnavailableError, PassportAppendError) as exc:
        await _audit(
            tenant_id=tenant_id,
            event_type="PUBLICATION_FAILED",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_kind=source_type,
            resource_id=source_id,
            payload={"reason": getattr(exc, "code", "FAILED"), "message": str(exc)[:200]},
        )
        raise

    status = result.get("status")
    if status in {"COMMITTED", "DUPLICATE_SAME_REQUEST"}:
        await _audit(
            tenant_id=tenant_id,
            event_type="PUBLICATION_COMMITTED",
            actor_id=actor_id,
            actor_role=actor_role,
            resource_kind=source_type,
            resource_id=source_id,
            payload={
                "status": status,
                "entry_id": result["entry"]["canonical_id"],
                "seq": result["entry"]["seq"],
                "revision": result["entry"].get("revision"),
                "receipt_id": result["receipt"]["canonical_id"],
            },
        )
    return result


async def load_expected_state(
    *, tenant_id: str, property_id: str,
) -> Dict[str, Any]:
    """Helper for approval endpoints: read current passport head tokens."""
    return await get_passport_head(tenant_id=tenant_id, property_id=property_id)
