"""NextGen durable outbox writer — Blueprint v1.2 §7.2.

Phase 2A implements the write side only: an event row is committed alongside
the business row (best-effort in one Mongo write pattern). Worker/replay
mechanics arrive with the ledger append in Phase 1c per Directive 005 gates.
"""
from __future__ import annotations

from typing import Any, Dict

from .db import now_iso_utc, nx_collections, nx_id


async def emit_outbox_event(
    *,
    tenant_id: str,
    event_type: str,
    payload: Dict[str, Any],
    idempotency_key: str,
    producer_resource_kind: str,
    producer_resource_id: str,
) -> Dict[str, Any]:
    now = now_iso_utc()
    event = {
        "canonical_id": nx_id(),
        "event_id": nx_id(),
        "tenant_id": tenant_id,
        "event_type": event_type,
        "payload": payload,
        "idempotency_key": idempotency_key,
        "producer_resource_kind": producer_resource_kind,
        "producer_resource_id": producer_resource_id,
        "available_after": now,
        "attempts": 0,
        "delivered_at": None,
        "dead_lettered_at": None,
        "created_at": now,
    }
    # Idempotent insert: if a row with the same `idempotency_key` exists, skip.
    existing = await nx_collections.outbox_events.find_one(
        {"idempotency_key": idempotency_key}
    )
    if existing:
        return {"event_id": existing["event_id"], "duplicate": True}
    await nx_collections.outbox_events.insert_one(dict(event))
    return {"event_id": event["event_id"], "duplicate": False}
