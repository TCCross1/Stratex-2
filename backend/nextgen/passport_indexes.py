"""Idempotent NextGen Passport index definitions and readiness (C-P-002A).

Never silently drops indexes. Never deletes conflicting historical records.
Critical unique-index failures mark readiness FAILED and block strict/production
governed publication.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from .db import now_iso_utc, nx_collections

logger = logging.getLogger("stratex.passport_indexes")

# Passport document statuses observed / reserved in NextGen.
# Only "active" is provisioned by passport_service today; other values are
# reserved for historical / replacement records and must NOT collide on the
# active unique index.
PASSPORT_ACTIVE_STATUS = "active"
PASSPORT_NON_ACTIVE_STATUSES = frozenset({
    "superseded", "merged_into", "split_from", "archived", "suspended", "closed",
})

# Readiness state machine
STATE_NOT_INITIALIZED = "NOT_INITIALIZED"
STATE_INITIALIZING = "INITIALIZING"
STATE_READY = "READY"
STATE_FAILED = "FAILED"

# Critical unique indexes — failure blocks strict/production publication.
CRITICAL_INDEX_NAMES = frozenset({
    "uniq_tenant_passport_seq",
    "uniq_tenant_passport_entry_id",
    "uniq_tenant_passport_idempotency_key",
    "uniq_active_passport_per_tenant_property",
    "uniq_active_conflict_fingerprint",
})

# Stable index catalog.
INDEX_SPECS: List[Dict[str, Any]] = [
    {
        "collection": "passport_entries",
        "name": "uniq_tenant_passport_seq",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("seq", 1)],
        "unique": True,
        "critical": True,
    },
    {
        "collection": "passport_entries",
        "name": "uniq_tenant_passport_entry_id",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("canonical_id", 1)],
        "unique": True,
        "critical": True,
    },
    {
        "collection": "passport_entries",
        "name": "idx_tenant_source_lookup",
        "keys": [("tenant_id", 1), ("source_type", 1), ("source_id", 1)],
        "unique": False,
        "critical": False,
    },
    {
        "collection": "passport_idempotency",
        "name": "uniq_tenant_passport_idempotency_key",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("idempotency_key", 1)],
        "unique": True,
        "critical": True,
    },
    {
        "collection": "passport_conflicts",
        "name": "idx_conflict_queue_lookup",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("status", 1), ("created_at", -1)],
        "unique": False,
        "critical": False,
    },
    {
        "collection": "passport_conflicts",
        "name": "uniq_active_conflict_fingerprint",
        "keys": [("tenant_id", 1), ("passport_id", 1), ("conflict_fingerprint", 1)],
        "unique": True,
        "critical": True,
        # Active queue only — resolved/rejected/superseded history may reuse
        # the same material fingerprint for a later legitimate conflict cycle
        # after the prior row leaves the active set.
        "partialFilterExpression": {
            "status": {"$in": ["OPEN", "UNDER_REVIEW", "REBASE_APPROVED"]},
            "conflict_fingerprint": {"$type": "string"},
        },
    },
    {
        "collection": "passports",
        "name": "idx_passport_head_revision",
        "keys": [("tenant_id", 1), ("canonical_id", 1), ("revision", 1)],
        "unique": False,
        "critical": False,
    },
    {
        "collection": "passports",
        "name": "uniq_active_passport_per_tenant_property",
        "keys": [("tenant_id", 1), ("property_id", 1)],
        "unique": True,
        "critical": True,
        "partialFilterExpression": {"status": PASSPORT_ACTIVE_STATUS},
    },
    {
        "collection": "outbox_events",
        "name": "uniq_outbox_idempotency_key",
        "keys": [("idempotency_key", 1)],
        "unique": True,
        "critical": False,
    },
]

# Process-local readiness (safe metadata only).
_readiness: Dict[str, Any] = {
    "state": STATE_NOT_INITIALIZED,
    "checked_at": None,
    "failed_index": None,
    "error_classification": None,
    "critical_failed": False,
    "created": [],
    "existed": [],
    "failed": [],
    "not_ready_reasons": [],
}


def index_definitions() -> List[Dict[str, Any]]:
    return [dict(spec) for spec in INDEX_SPECS]


def get_index_readiness() -> Dict[str, Any]:
    """Return safe Passport index readiness metadata (no secrets/URLs)."""
    return dict(_readiness)


def set_index_readiness_for_tests(**kwargs: Any) -> None:
    """Test-only readiness override. Not used by production routes."""
    _readiness.update(kwargs)


def indexes_are_ready() -> bool:
    return _readiness.get("state") == STATE_READY


def _strict_index_enforcement() -> bool:
    env = (os.environ.get("APP_ENV") or "").strip().lower()
    if env in {"production", "prod", "live"}:
        return True
    return (os.environ.get("PASSPORT_REQUIRE_INDEXES") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def require_indexes_ready_for_publication() -> None:
    """Fail closed in strict/production when critical indexes are not READY."""
    from .passport_errors import IndexReadinessError

    if indexes_are_ready():
        return
    if not _strict_index_enforcement():
        # Local/test: allow controlled testing but readiness remains non-READY.
        return
    raise IndexReadinessError(
        "Passport critical indexes are not READY; governed publication blocked",
        details={
            "state": _readiness.get("state"),
            "failed_index": _readiness.get("failed_index"),
            "error_classification": _readiness.get("error_classification"),
        },
    )


async def ensure_passport_indexes() -> Dict[str, Any]:
    """Create required indexes idempotently and update readiness state."""
    global _readiness
    _readiness = {
        "state": STATE_INITIALIZING,
        "checked_at": now_iso_utc(),
        "failed_index": None,
        "error_classification": None,
        "critical_failed": False,
        "created": [],
        "existed": [],
        "failed": [],
        "not_ready_reasons": [],
    }

    created: List[str] = []
    existed: List[str] = []
    failed: List[Dict[str, str]] = []
    not_ready_reasons: List[str] = []
    critical_failed = False
    first_critical_name: Optional[str] = None
    first_critical_class: Optional[str] = None

    # Drop the prior misleading non-unique name if present (never drops data).
    try:
        passports = nx_collections.passports
        info = await passports.index_information()
        if "uniq_active_passport_property" in info:
            # Motor/pymongo: drop_index. FakeMongo may no-op via AttributeError.
            drop = getattr(passports, "drop_index", None)
            if callable(drop):
                try:
                    await drop("uniq_active_passport_property")
                    logger.info(
                        "passport_indexes: dropped obsolete non-unique "
                        "uniq_active_passport_property (no data deleted)"
                    )
                except Exception as exc:
                    logger.warning(
                        "passport_indexes: could not drop obsolete index name (%s)",
                        type(exc).__name__,
                    )
    except Exception:
        pass

    for spec in INDEX_SPECS:
        coll = getattr(nx_collections, spec["collection"])
        name = spec["name"]
        try:
            existing = await coll.index_information()
        except Exception as exc:
            existing = {}
            logger.info(
                "passport_indexes: index_information unavailable for %s: %s",
                spec["collection"], type(exc).__name__,
            )

        if name in existing:
            existed.append(name)
            continue

        kwargs: Dict[str, Any] = {"name": name, "unique": bool(spec.get("unique"))}
        if spec.get("partialFilterExpression"):
            kwargs["partialFilterExpression"] = spec["partialFilterExpression"]
        try:
            await coll.create_index(spec["keys"], **kwargs)
            created.append(name)
            logger.info("passport_indexes: created %s on %s", name, spec["collection"])
        except Exception as exc:
            msg = str(exc)
            classification = type(exc).__name__
            if "duplicate" in msg.lower() or "E11000" in msg:
                classification = "DUPLICATE_DATA_BLOCKS_UNIQUE_INDEX"
            redacted = {
                "index": name,
                "collection": f"nextgen_{spec['collection']}",
                "error_type": classification,
                "error": msg[:300],
                "critical": bool(spec.get("critical")),
            }
            failed.append(redacted)
            if spec.get("critical"):
                critical_failed = True
                if first_critical_name is None:
                    first_critical_name = name
                    first_critical_class = classification
                not_ready_reasons.append(
                    f"Critical index {name} unavailable ({classification}); "
                    "no automatic cleanup performed."
                )
            logger.error(
                "passport_indexes: FAILED creating %s on %s (%s)",
                name, spec["collection"], classification,
            )

    ready = len(failed) == 0 and not critical_failed
    state = STATE_READY if ready else STATE_FAILED
    _readiness = {
        "state": state,
        "checked_at": now_iso_utc(),
        "failed_index": first_critical_name,
        "error_classification": first_critical_class,
        "critical_failed": critical_failed,
        "created": created,
        "existed": existed,
        "failed": failed,
        "not_ready_reasons": not_ready_reasons,
    }

    if not ready:
        logger.error(
            "passport_indexes readiness FAILED critical=%s failed=%s",
            critical_failed, [f.get("index") for f in failed],
        )
        if _strict_index_enforcement() and critical_failed:
            # Production/strict: raise so startup can fail closed when desired.
            raise RuntimeError(
                "Critical Passport index initialization failed; "
                f"index={first_critical_name} class={first_critical_class}"
            )
    else:
        logger.info(
            "passport_indexes READY created=%s existed=%s", created, existed,
        )

    return {
        "ready": ready,
        "state": state,
        "created": created,
        "existed": existed,
        "failed": failed,
        "not_ready_reasons": not_ready_reasons,
        "critical_failed": critical_failed,
        "production_readiness": "READY" if ready else "NOT READY",
        "readiness": get_index_readiness(),
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
        pass
    return out


async def probe_duplicate_active_passports() -> List[Dict[str, str]]:
    """Read-only redacted report of tenant/property pairs with >1 active passport."""
    pipeline = [
        {"$match": {"status": PASSPORT_ACTIVE_STATUS}},
        {"$group": {
            "_id": {"tenant_id": "$tenant_id", "property_id": "$property_id"},
            "n": {"$sum": 1},
        }},
        {"$match": {"n": {"$gt": 1}}},
    ]
    out: List[Dict[str, str]] = []
    try:
        async for row in nx_collections.passports.aggregate(pipeline):
            tid = (row.get("_id") or {}).get("tenant_id") or ""
            pid = (row.get("_id") or {}).get("property_id") or ""
            out.append({
                "tenant_id_prefix": tid[:8],
                "property_id_prefix": pid[:8],
                "count": str(row.get("n")),
            })
    except Exception:
        pass
    return out
