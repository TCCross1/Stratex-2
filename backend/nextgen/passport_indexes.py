"""Idempotent NextGen Passport index definitions (C-P-002).

Never silently drops indexes. Never deletes conflicting historical records.
If unique-index creation fails due to duplicate data, that index is reported
NOT READY and production readiness remains blocked.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .db import nx_collections

logger = logging.getLogger("stratex.passport_indexes")

# Stable names — do not rename lightly (operators depend on them).
INDEX_SPECS: List[Dict[str, Any]] = [
    {
        "collection": "passport_entries",
        "name": "uniq_tenant_passport_seq",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("seq", 1)],
        "unique": True,
    },
    {
        "collection": "passport_entries",
        "name": "uniq_tenant_passport_entry_id",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("canonical_id", 1)],
        "unique": True,
    },
    {
        "collection": "passport_entries",
        "name": "idx_tenant_source_lookup",
        "keys": [("tenant_id", 1), ("source_type", 1), ("source_id", 1)],
        "unique": False,
    },
    {
        "collection": "passport_idempotency",
        "name": "uniq_tenant_passport_idempotency_key",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("idempotency_key", 1)],
        "unique": True,
    },
    {
        "collection": "passport_conflicts",
        "name": "idx_conflict_queue_lookup",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("status", 1), ("created_at", -1)],
        "unique": False,
    },
    {
        "collection": "passports",
        "name": "idx_passport_head_revision",
        "keys": [("tenant_id", 1), ("canonical_id", 1), ("revision", 1)],
        "unique": False,
    },
    {
        "collection": "passports",
        "name": "uniq_active_passport_property",
        "keys": [("tenant_id", 1), ("property_id", 1), ("status", 1)],
        "unique": False,
    },
    {
        "collection": "outbox_events",
        "name": "uniq_outbox_idempotency_key",
        "keys": [("idempotency_key", 1)],
        "unique": True,
    },
]


def index_definitions() -> List[Dict[str, Any]]:
    """Return the declared index catalog (for tests / documentation)."""
    return [dict(spec) for spec in INDEX_SPECS]


async def ensure_passport_indexes() -> Dict[str, Any]:
    """Create required indexes idempotently.

    Returns a structured report. Unique-index failures caused by existing
    duplicate data stop that index only — no data is mutated or deleted.
    """
    created: List[str] = []
    existed: List[str] = []
    failed: List[Dict[str, str]] = []
    not_ready_reasons: List[str] = []

    for spec in INDEX_SPECS:
        coll = getattr(nx_collections, spec["collection"])
        name = spec["name"]
        try:
            existing = await coll.index_information()
        except Exception as exc:  # collection may not exist yet
            existing = {}
            logger.info("passport_indexes: index_information unavailable for %s: %s",
                        spec["collection"], type(exc).__name__)

        if name in existing:
            existed.append(name)
            continue

        kwargs: Dict[str, Any] = {"name": name, "unique": bool(spec.get("unique"))}
        try:
            await coll.create_index(spec["keys"], **kwargs)
            created.append(name)
            logger.info("passport_indexes: created %s on %s", name, spec["collection"])
        except Exception as exc:
            msg = str(exc)
            redacted = {
                "index": name,
                "collection": f"nextgen_{spec['collection']}",
                "error_type": type(exc).__name__,
                "error": msg[:300],
            }
            failed.append(redacted)
            if spec.get("unique") and (
                "duplicate" in msg.lower()
                or "E11000" in msg
                or "already exists" in msg.lower()
            ):
                not_ready_reasons.append(
                    f"Unique index {name} blocked by existing duplicate data; "
                    "no automatic cleanup performed."
                )
            logger.error(
                "passport_indexes: FAILED creating %s on %s (%s)",
                name, spec["collection"], type(exc).__name__,
            )

    ready = len(failed) == 0
    return {
        "ready": ready,
        "created": created,
        "existed": existed,
        "failed": failed,
        "not_ready_reasons": not_ready_reasons,
        "production_readiness": "READY_FOR_INDEXES" if ready else "NOT READY",
    }


async def probe_duplicate_sequences(
    *, tenant_id: str, passport_id: str,
) -> List[Tuple[int, int]]:
    """Return [(seq, count), ...] for sequences with count > 1. Read-only."""
    pipeline = [
        {"$match": {"tenant_id": tenant_id, "passport_id": passport_id}},
        {"$group": {"_id": "$seq", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gt": 1}}},
    ]
    out: List[Tuple[int, int]] = []
    try:
        async for row in nx_collections.passport_entries.aggregate(pipeline):
            out.append((int(row["_id"]), int(row["n"])))
    except Exception:
        # Fake collections / limited drivers may not implement aggregate.
        pass
    return out
