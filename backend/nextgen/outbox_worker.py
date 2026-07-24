"""C-P-003 outbox delivery worker / replay / health — Blueprint §7.2 · SD-023.

Write-side remains `outbox.emit_outbox_event`. This module owns claim, delivery
attempts, backoff, dead-letter, inbox receipts, safe replay, and backlog health.

Does NOT write Passport ledger entries and is NOT a second publication authority.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from .db import now_iso_utc, nx_collections, nx_id

logger = logging.getLogger("stratex.outbox_worker")

MODULE_IDENTITY = "nextgen.outbox_worker"

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_LEASE_SECONDS = 30
BASE_BACKOFF_SECONDS = 2
MAX_BACKOFF_SECONDS = 300

DeliveryHandler = Callable[[Dict[str, Any]], Awaitable[None]]

_SECRET_KEYS = frozenset(
    {"password", "secret", "authorization", "totp", "mfa", "hmac_key", "token", "api_key"}
)


def _parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _add_seconds(iso_ts: str, seconds: float) -> str:
    return (_parse_iso(iso_ts) + timedelta(seconds=seconds)).isoformat()


def _backoff_seconds(attempts: int) -> int:
    exp = max(0, int(attempts) - 1)
    return int(min(MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2**exp)))


def payload_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _scrub(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    safe = dict(payload or {})
    for banned in _SECRET_KEYS:
        safe.pop(banned, None)
    return safe


async def _audit(
    *,
    tenant_id: str,
    event_type: str,
    actor_id: str,
    resource_kind: str,
    resource_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "event_type": event_type,
        "actor_id": actor_id,
        "actor_role": "service",
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "at": now_iso_utc(),
        "payload": _scrub(payload),
    })
    logger.info(
        "outbox_audit event_type=%s resource_kind=%s resource_id=%s actor_id=%s",
        event_type,
        resource_kind,
        resource_id,
        actor_id,
    )


def _claimable_filter(now: str) -> Dict[str, Any]:
    return {
        "delivered_at": None,
        "dead_lettered_at": None,
        "available_after": {"$lte": now},
        "$or": [
            {"lease_until": None},
            {"lease_until": {"$exists": False}},
            {"lease_until": {"$lte": now}},
        ],
    }


async def claim_next_event(
    *,
    worker_id: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Atomically claim the next available outbox row (idempotent lease).

    Two workers racing the same candidate: only one find_one_and_update wins.
    """
    now = now or now_iso_utc()
    filt = _claimable_filter(now)
    cursor = nx_collections.outbox_events.find(filt).sort("available_after", 1).limit(8)
    candidates = await cursor.to_list(8)
    for candidate in candidates:
        event_id = candidate["event_id"]
        lease_until = _add_seconds(now, lease_seconds)
        claimed = await nx_collections.outbox_events.find_one_and_update(
            {
                "event_id": event_id,
                **_claimable_filter(now),
            },
            {
                "$set": {
                    "leased_by": worker_id,
                    "lease_until": lease_until,
                    "claimed_at": now,
                    "last_claimed_by": worker_id,
                },
                "$inc": {"attempts": 1},
            },
            return_document=True,
        )
        if claimed is not None:
            logger.info(
                "outbox_claimed event_id=%s worker_id=%s attempts=%s",
                event_id,
                worker_id,
                claimed.get("attempts"),
            )
            return claimed
    return None


async def _write_inbox_receipt(
    *,
    event: Dict[str, Any],
    consumer_key: str,
    phash: str,
    now: str,
) -> Dict[str, Any]:
    """Idempotent delivery receipt keyed by (consumer_key, event_id, payload_hash)."""
    existing = await nx_collections.inbox_receipts.find_one({
        "consumer_key": consumer_key,
        "event_id": event["event_id"],
        "payload_hash": phash,
    })
    if existing:
        return {"receipt_id": existing.get("canonical_id"), "duplicate": True}

    receipt = {
        "canonical_id": nx_id(),
        "consumer_key": consumer_key,
        "event_id": event["event_id"],
        "payload_hash": phash,
        "tenant_id": event.get("tenant_id"),
        "event_type": event.get("event_type"),
        "applied_at": now,
    }
    await nx_collections.inbox_receipts.insert_one(dict(receipt))
    return {"receipt_id": receipt["canonical_id"], "duplicate": False}


async def mark_delivered(
    *,
    event: Dict[str, Any],
    consumer_key: str,
    worker_id: str,
) -> Dict[str, Any]:
    now = now_iso_utc()
    phash = event.get("payload_hash") or payload_hash(event.get("payload") or {})
    receipt = await _write_inbox_receipt(
        event=event, consumer_key=consumer_key, phash=phash, now=now
    )
    await nx_collections.outbox_events.update_one(
        {"event_id": event["event_id"], "delivered_at": None},
        {
            "$set": {
                "delivered_at": now,
                "payload_hash": phash,
                "lease_until": None,
                "leased_by": None,
                "last_error": None,
            }
        },
    )
    await _audit(
        tenant_id=event.get("tenant_id") or "system",
        event_type="OUTBOX_DELIVERED",
        actor_id=worker_id,
        resource_kind="outbox_event",
        resource_id=event["event_id"],
        payload={
            "event_type": event.get("event_type"),
            "consumer_key": consumer_key,
            "receipt_duplicate": receipt["duplicate"],
            "attempts": event.get("attempts"),
        },
    )
    return {"status": "delivered", "receipt": receipt, "delivered_at": now}


async def _move_to_dead_letter(
    *,
    event: Dict[str, Any],
    worker_id: str,
    failure_class: str,
    error_message: str,
) -> Dict[str, Any]:
    now = now_iso_utc()
    dl = {
        "canonical_id": nx_id(),
        "event_id": event["event_id"],
        "tenant_id": event.get("tenant_id"),
        "event_type": event.get("event_type"),
        "payload": event.get("payload") or {},
        "failure_class": failure_class,
        "error_message": (error_message or "")[:500],
        "attempts": event.get("attempts"),
        "moved_at": now,
        "replayed_at": None,
        "replayed_by": None,
    }
    await nx_collections.dead_letter_events.insert_one(dict(dl))
    await nx_collections.outbox_events.update_one(
        {"event_id": event["event_id"]},
        {
            "$set": {
                "dead_lettered_at": now,
                "lease_until": None,
                "leased_by": None,
                "last_error": {
                    "failure_class": failure_class,
                    "message": (error_message or "")[:500],
                    "at": now,
                },
            }
        },
    )
    await _audit(
        tenant_id=event.get("tenant_id") or "system",
        event_type="OUTBOX_DEADLETTER",
        actor_id=worker_id,
        resource_kind="outbox_event",
        resource_id=event["event_id"],
        payload={
            "failure_class": failure_class,
            "attempts": event.get("attempts"),
            "event_type": event.get("event_type"),
        },
    )
    return {"status": "dead_lettered", "dead_letter_id": dl["canonical_id"], "at": now}


async def record_delivery_failure(
    *,
    event: Dict[str, Any],
    worker_id: str,
    error: BaseException,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> Dict[str, Any]:
    attempts = int(event.get("attempts") or 0)
    failure_class = type(error).__name__
    message = str(error)
    if attempts >= max_attempts:
        return await _move_to_dead_letter(
            event=event,
            worker_id=worker_id,
            failure_class=failure_class,
            error_message=message,
        )

    now = now_iso_utc()
    delay = _backoff_seconds(attempts)
    available_after = _add_seconds(now, delay)
    await nx_collections.outbox_events.update_one(
        {"event_id": event["event_id"], "delivered_at": None, "dead_lettered_at": None},
        {
            "$set": {
                "available_after": available_after,
                "lease_until": None,
                "leased_by": None,
                "last_error": {
                    "failure_class": failure_class,
                    "message": message[:500],
                    "at": now,
                    "backoff_seconds": delay,
                },
            }
        },
    )
    await _audit(
        tenant_id=event.get("tenant_id") or "system",
        event_type="OUTBOX_DELIVERY_FAILED",
        actor_id=worker_id,
        resource_kind="outbox_event",
        resource_id=event["event_id"],
        payload={
            "failure_class": failure_class,
            "attempts": attempts,
            "backoff_seconds": delay,
            "available_after": available_after,
        },
    )
    return {
        "status": "retry_scheduled",
        "attempts": attempts,
        "available_after": available_after,
        "backoff_seconds": delay,
    }


async def process_one(
    *,
    worker_id: str,
    handler: DeliveryHandler,
    consumer_key: str = "default",
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> Optional[Dict[str, Any]]:
    """Claim one event, invoke handler, mark delivered or schedule retry/DLQ."""
    event = await claim_next_event(worker_id=worker_id, lease_seconds=lease_seconds)
    if event is None:
        return None
    try:
        await handler(event)
    except Exception as exc:  # noqa: BLE001 — delivery boundary; classify and continue
        result = await record_delivery_failure(
            event=event,
            worker_id=worker_id,
            error=exc,
            max_attempts=max_attempts,
        )
        return {"event_id": event["event_id"], **result}

    delivered = await mark_delivered(
        event=event, consumer_key=consumer_key, worker_id=worker_id
    )
    return {"event_id": event["event_id"], **delivered}


async def replay_dead_lettered_event(
    *,
    event_id: str,
    operator_id: str,
    reason: str = "operator_replay",
    reset_attempts: bool = True,
) -> Dict[str, Any]:
    """Safe operator replay: re-queue a dead-lettered/failed outbox row.

    Does not invent a new event_id (preserves idempotency). Clears dead-letter
    markers, releases lease, and makes the row immediately available.
    """
    event = await nx_collections.outbox_events.find_one({"event_id": event_id})
    if event is None:
        raise LookupError(f"outbox event not found: {event_id}")
    if event.get("delivered_at"):
        raise ValueError(f"event already delivered: {event_id}")
    if not event.get("dead_lettered_at") and not event.get("last_error"):
        raise ValueError(f"event is not dead-lettered or failed: {event_id}")

    now = now_iso_utc()
    update: Dict[str, Any] = {
        "dead_lettered_at": None,
        "available_after": now,
        "lease_until": None,
        "leased_by": None,
        "last_error": None,
        "replayed_at": now,
        "replayed_by": operator_id,
        "replay_reason": (reason or "")[:300],
    }
    if reset_attempts:
        update["attempts"] = 0

    await nx_collections.outbox_events.update_one(
        {"event_id": event_id},
        {"$set": update},
    )
    await nx_collections.dead_letter_events.update_one(
        {"event_id": event_id, "replayed_at": None},
        {"$set": {"replayed_at": now, "replayed_by": operator_id}},
    )
    await _audit(
        tenant_id=event.get("tenant_id") or "system",
        event_type="OUTBOX_REPLAYED",
        actor_id=operator_id,
        resource_kind="outbox_event",
        resource_id=event_id,
        payload={"reason": reason, "reset_attempts": reset_attempts},
    )
    return {
        "status": "requeued",
        "event_id": event_id,
        "available_after": now,
        "replayed_by": operator_id,
    }


async def outbox_backlog_status(
    *,
    now: Optional[str] = None,
    pending_warn_threshold: int = 100,
    dead_letter_critical_threshold: int = 1,
) -> Dict[str, Any]:
    """Health/readiness snapshot for outbox backlog (no secrets)."""
    now = now or now_iso_utc()
    pending = await nx_collections.outbox_events.count_documents({
        "delivered_at": None,
        "dead_lettered_at": None,
        "available_after": {"$lte": now},
        "$or": [
            {"lease_until": None},
            {"lease_until": {"$exists": False}},
            {"lease_until": {"$lte": now}},
        ],
    })
    leased = await nx_collections.outbox_events.count_documents({
        "delivered_at": None,
        "dead_lettered_at": None,
        "lease_until": {"$gt": now},
    })
    # FakeMongo supports $gt via the same operator path as $gte/$lte.
    deferred = await nx_collections.outbox_events.count_documents({
        "delivered_at": None,
        "dead_lettered_at": None,
        "available_after": {"$gt": now},
    })
    dead = await nx_collections.outbox_events.count_documents({
        "dead_lettered_at": {"$ne": None},
    })
    delivered = await nx_collections.outbox_events.count_documents({
        "delivered_at": {"$ne": None},
    })

    oldest = None
    cursor = (
        nx_collections.outbox_events.find({
            "delivered_at": None,
            "dead_lettered_at": None,
        })
        .sort("available_after", 1)
        .limit(1)
    )
    rows = await cursor.to_list(1)
    if rows:
        oldest = rows[0].get("available_after")

    if dead >= dead_letter_critical_threshold:
        status = "critical"
        ready = False
    elif pending >= pending_warn_threshold:
        status = "degraded"
        ready = True
    else:
        status = "ok"
        ready = True

    snapshot = {
        "module": MODULE_IDENTITY,
        "checked_at": now,
        "pending_count": pending,
        "leased_count": leased,
        "deferred_count": deferred,
        "dead_letter_count": dead,
        "delivered_count": delivered,
        "oldest_pending_available_after": oldest,
        "status": status,
        "ready": ready,
    }
    logger.info(
        "outbox_health status=%s pending=%s dead=%s leased=%s",
        status,
        pending,
        dead,
        leased,
    )
    return snapshot


async def outbox_readiness() -> Dict[str, Any]:
    """Thin readiness helper used by ops probes."""
    snap = await outbox_backlog_status()
    return {
        "ready": snap["ready"],
        "status": snap["status"],
        "pending_count": snap["pending_count"],
        "dead_letter_count": snap["dead_letter_count"],
        "checked_at": snap["checked_at"],
    }
