"""NextGen Passport Service — canonical hash-chained property ledger.

Only this module writes to `nextgen_passport_entries`. Callers submit
approved intelligence deltas and receive a signed receipt. The ledger is
append-only.

C-P-002 hardens append with:
  · optimistic concurrency (expected_revision / expected_head_hash)
  · deterministic idempotency
  · governed conflict records on stale writes
  · versioned HMAC sealing (prospective)
  · fail-closed multi-document transactions in strict/production mode

Corrections create new entries. Accepted history is never rewritten.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, Optional

from .db import now_iso_utc, nx_collections, nx_id, strip_mongo_id

# Serializes active-passport provisioning to prevent duplicate passports
# for the same tenant+property under concurrent first-touch appends.
_passport_provision_lock = asyncio.Lock()
from .passport_conflicts import create_conflict_record
from .passport_errors import (
    IdempotencyConflictError,
    MissingExpectedStateError,
    PassportAppendError,
    PropertyIsolationError,
    StaleExpectedStateError,
    TenantIsolationError,
    TransactionUnavailableError,
)
from .passport_seal import SealConfigurationError, seal_entry

logger = logging.getLogger("stratex.passport_service")

SCHEMA_VERSION_DEFAULT = "2"


def _canonical_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _request_fingerprint(
    *,
    entry_type: str,
    payload: Dict[str, Any],
    source_type: Optional[str],
    source_id: Optional[str],
    schema_version: str,
) -> str:
    body = {
        "entry_type": entry_type,
        "payload": payload,
        "source_type": source_type,
        "source_id": source_id,
        "schema_version": schema_version,
    }
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


def _strict_transactions_required() -> bool:
    env = (os.environ.get("APP_ENV") or "").strip().lower()
    if env in {"production", "prod", "live"}:
        return True
    return (os.environ.get("PASSPORT_REQUIRE_TRANSACTIONS") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _transactions_available_flag() -> bool:
    """Runtime override used by tests / disclosure.

    Default is False (standalone / unit-test hosts). Production must set
    PASSPORT_TRANSACTIONS_AVAILABLE=1 on a transaction-capable deployment;
    strict mode then fails closed when sessions cannot be opened.
    """
    raw = (os.environ.get("PASSPORT_TRANSACTIONS_AVAILABLE") or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return False


async def _audit_event(
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
    for banned in (
        "password", "secret", "authorization", "totp", "mfa",
        "hmac_key", "PASSPORT_SEAL_KEY", "entry_signature_key",
    ):
        safe.pop(banned, None)
    # Never log raw seal secrets or full confidential payloads.
    if "payload" in safe and isinstance(safe["payload"], dict):
        safe["payload"] = {"keys": sorted(safe["payload"].keys())}
    try:
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
    except Exception as exc:
        logger.error("passport audit write failed: %s", type(exc).__name__)


async def _ensure_passport(tenant_id: str, property_id: str) -> Dict[str, Any]:
    """Provision or return the active passport for a property."""
    async def _load() -> Optional[Dict[str, Any]]:
        p = await nx_collections.passports.find_one({
            "tenant_id": tenant_id, "property_id": property_id, "status": "active",
        })
        if not p:
            return None
        if "revision" not in p:
            await nx_collections.passports.update_one(
                {"canonical_id": p["canonical_id"]},
                {"$set": {"revision": 0, "head_hash": None, "head_entry_id": None}},
            )
            p = await nx_collections.passports.find_one({"canonical_id": p["canonical_id"]})
        return p

    existing = await _load()
    if existing:
        return existing

    async with _passport_provision_lock:
        existing = await _load()
        if existing:
            return existing
        now = now_iso_utc()
        p = {
            "canonical_id": nx_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "revision": 0,
            "head_hash": None,
            "head_entry_id": None,
        }
        await nx_collections.passports.insert_one(dict(p))
        await nx_collections.passport_sequences.insert_one({
            "canonical_id": nx_id(),
            "tenant_id": tenant_id,
            "passport_id": p["canonical_id"],
            "next_seq": 1,
            "created_at": now,
        })
        return p


async def get_passport_head(
    *, tenant_id: str, property_id: str,
) -> Dict[str, Any]:
    """Return current expected-state tokens for a property passport."""
    passport = await _ensure_passport(tenant_id, property_id)
    return {
        "passport_id": passport["canonical_id"],
        "property_id": property_id,
        "tenant_id": tenant_id,
        "revision": int(passport.get("revision") or 0),
        "head_hash": passport.get("head_hash"),
        "head_entry_id": passport.get("head_entry_id"),
    }


async def _next_seq(passport_id: str, *, session: Any = None) -> int:
    kwargs: Dict[str, Any] = {"return_document": True}
    if session is not None:
        kwargs["session"] = session
    doc = await nx_collections.passport_sequences.find_one_and_update(
        {"passport_id": passport_id},
        {"$inc": {"next_seq": 1}},
        **kwargs,
    )
    if not doc:
        raise PassportAppendError("Passport sequence document missing")
    return int(doc["next_seq"] - 1)


async def _load_idempotency(
    *, tenant_id: str, passport_id: str, idempotency_key: str,
) -> Optional[Dict[str, Any]]:
    return await nx_collections.passport_idempotency.find_one({
        "tenant_id": tenant_id,
        "passport_id": passport_id,
        "idempotency_key": idempotency_key,
    })


async def _begin_mongo_session():
    """Start a Motor client session when available.

    Returns (session, txn_cm_or_None). Caller must end the session.
    """
    if not _transactions_available_flag():
        return None, None
    try:
        from core import client  # AsyncIOMotorClient
        session = await client.start_session()
        return session, session
    except Exception as exc:
        logger.warning("passport session start failed: %s", type(exc).__name__)
        return None, None


async def append_entry(
    *,
    tenant_id: str,
    property_id: str,
    entry_type: str,
    payload: Dict[str, Any],
    authored_by: str,
    passport_id: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    expected_revision: Optional[int] = None,
    expected_head_hash: Optional[str] = None,
    schema_version: str = SCHEMA_VERSION_DEFAULT,
    publication_context: Optional[Dict[str, Any]] = None,
    require_expected_state: bool = False,
    actor_role: Optional[str] = None,
) -> Dict[str, Any]:
    """Append an entry to the passport ledger and return the signed receipt.

    Governed approval/publication paths must set require_expected_state=True
    and supply expected_revision and/or expected_head_hash.
    """
    if not tenant_id or not property_id:
        raise PassportAppendError("tenant_id and property_id are required")

    passport = await _ensure_passport(tenant_id, property_id)
    if passport.get("tenant_id") != tenant_id:
        raise TenantIsolationError("Passport tenant mismatch")
    if passport.get("property_id") != property_id:
        raise PropertyIsolationError("Passport property mismatch")
    if passport_id and passport["canonical_id"] != passport_id:
        raise PassportAppendError("passport_id does not match active property passport")

    pid = passport["canonical_id"]
    actual_revision = int(passport.get("revision") or 0)
    actual_head = passport.get("head_hash")
    fp = _request_fingerprint(
        entry_type=entry_type,
        payload=payload,
        source_type=source_type,
        source_id=source_id,
        schema_version=schema_version,
    )

    await _audit_event(
        tenant_id=tenant_id,
        event_type="PASSPORT_APPEND_REQUESTED",
        actor_id=authored_by,
        actor_role=actor_role,
        resource_kind="passport",
        resource_id=pid,
        payload={
            "property_id": property_id,
            "source_type": source_type,
            "source_id": source_id,
            "idempotency_key": idempotency_key,
            "expected_revision": expected_revision,
            "expected_head_hash": expected_head_hash,
            "actual_revision": actual_revision,
            "actual_head_hash": actual_head,
            "correlation_id": correlation_id,
            "request_fingerprint": fp,
        },
    )

    if require_expected_state and expected_revision is None and not expected_head_hash:
        await _audit_event(
            tenant_id=tenant_id,
            event_type="PASSPORT_APPEND_FAILED",
            actor_id=authored_by,
            actor_role=actor_role,
            resource_kind="passport",
            resource_id=pid,
            payload={"reason": "MISSING_EXPECTED_STATE"},
        )
        raise MissingExpectedStateError(
            "Controlled append requires expected_revision or expected_head_hash"
        )

    # Idempotency pre-check (committed duplicates return original result).
    if idempotency_key:
        existing = await _load_idempotency(
            tenant_id=tenant_id, passport_id=pid, idempotency_key=idempotency_key,
        )
        if existing:
            if existing.get("commit_status") == "COMMITTED":
                if existing.get("request_fingerprint") != fp:
                    await _audit_event(
                        tenant_id=tenant_id,
                        event_type="PASSPORT_APPEND_FAILED",
                        actor_id=authored_by,
                        actor_role=actor_role,
                        resource_kind="passport",
                        resource_id=pid,
                        payload={"reason": "IDEMPOTENCY_CONFLICT"},
                    )
                    raise IdempotencyConflictError(
                        "Idempotency key reused with different request content",
                        details={"idempotency_key": idempotency_key},
                    )
                entry = await nx_collections.passport_entries.find_one({
                    "canonical_id": existing["entry_id"],
                    "tenant_id": tenant_id,
                })
                receipt = await nx_collections.passport_receipts.find_one({
                    "canonical_id": existing.get("receipt_id"),
                    "tenant_id": tenant_id,
                })
                await _audit_event(
                    tenant_id=tenant_id,
                    event_type="PASSPORT_APPEND_DUPLICATE",
                    actor_id=authored_by,
                    actor_role=actor_role,
                    resource_kind="passport",
                    resource_id=pid,
                    payload={
                        "entry_id": existing.get("entry_id"),
                        "seq": existing.get("sequence"),
                        "revision": existing.get("revision"),
                    },
                )
                return {
                    "status": "DUPLICATE_SAME_REQUEST",
                    "passport": strip_mongo_id(passport),
                    "entry": strip_mongo_id(entry),
                    "receipt": strip_mongo_id(receipt),
                    "idempotency": strip_mongo_id(existing),
                }
            if existing.get("commit_status") == "FAILED":
                # Prior failure must not masquerade as committed; allow retry
                # only when fingerprint matches.
                if existing.get("request_fingerprint") != fp:
                    raise IdempotencyConflictError(
                        "Idempotency key reused with different request content",
                        details={"idempotency_key": idempotency_key},
                    )

    # Optimistic concurrency check (before allocating sequence).
    stale = False
    if expected_revision is not None and int(expected_revision) != actual_revision:
        stale = True
    if expected_head_hash is not None and expected_head_hash != actual_head:
        # Bootstrap: both None/empty is current.
        if not (expected_head_hash in (None, "") and actual_head in (None, "")):
            stale = True

    if stale:
        conflict = await create_conflict_record(
            tenant_id=tenant_id,
            passport_id=pid,
            property_id=property_id,
            source_type=source_type,
            source_id=source_id,
            attempted_idempotency_key=idempotency_key,
            attempted_expected_revision=expected_revision,
            attempted_expected_head_hash=expected_head_hash,
            actual_revision=actual_revision,
            actual_head_hash=actual_head,
            attempted_request_fingerprint=fp,
            actor=authored_by,
            actor_role=actor_role,
            correlation_id=correlation_id,
            conflict_reason="STALE_EXPECTED_STATE",
            attempted_payload_summary={
                "entry_type": entry_type,
                "payload_keys": sorted((payload or {}).keys()),
            },
        )
        await _audit_event(
            tenant_id=tenant_id,
            event_type="PASSPORT_APPEND_CONFLICT",
            actor_id=authored_by,
            actor_role=actor_role,
            resource_kind="passport_conflict",
            resource_id=conflict["conflict_id"],
            payload={
                "expected_revision": expected_revision,
                "actual_revision": actual_revision,
                "expected_head_hash": expected_head_hash,
                "actual_head_hash": actual_head,
            },
        )
        raise StaleExpectedStateError(
            "Stale expected Passport state; append refused",
            conflict=conflict,
        )

    # Transaction gate — fail closed in strict/production when unavailable.
    session = None
    use_txn = False
    if _strict_transactions_required():
        session, _ = await _begin_mongo_session()
        if session is None:
            await _audit_event(
                tenant_id=tenant_id,
                event_type="PASSPORT_APPEND_FAILED",
                actor_id=authored_by,
                actor_role=actor_role,
                resource_kind="passport",
                resource_id=pid,
                payload={"reason": "TRANSACTION_UNAVAILABLE"},
            )
            raise TransactionUnavailableError(
                "Multi-document transactions required but unavailable; "
                "failing closed. No partial append executed."
            )
        use_txn = True
    else:
        # Non-strict: prefer transactions when available; otherwise proceed
        # with CAS + unique indexes (NOT production-safe; disclosed).
        session, _ = await _begin_mongo_session()
        use_txn = session is not None

    now = now_iso_utc()
    new_revision = actual_revision + 1

    async def _commit_body(sess: Any = None) -> Dict[str, Any]:
        insert_kwargs: Dict[str, Any] = {}
        if sess is not None:
            insert_kwargs["session"] = sess

        # Claim revision slot BEFORE inserting an entry so losing racers
        # never leave orphan ledger rows in the non-transactional path.
        cas_filter: Dict[str, Any] = {
            "canonical_id": pid,
            "tenant_id": tenant_id,
            "revision": actual_revision,
        }
        if expected_head_hash is not None:
            cas_filter["head_hash"] = actual_head

        cas_result = await nx_collections.passports.update_one(
            cas_filter,
            {"$set": {
                "revision": new_revision,
                "updated_at": now,
                "head_claim_pending": True,
            }},
            **insert_kwargs,
        )
        matched = getattr(cas_result, "matched_count", None)
        if matched is None:
            matched = cas_result.get("matched_count", 1) if isinstance(cas_result, dict) else 1
        if matched == 0:
            raise StaleExpectedStateError(
                "CAS lost race on passport head",
                conflict={},
            )

        seq = await _next_seq(pid, session=sess)
        prior = actual_head
        entry_body = {
            "passport_id": pid,
            "seq": seq,
            "entry_type": entry_type,
            "payload": payload,
            "prior_hash": prior,
            "at": now,
            "authored_by": authored_by,
        }
        content_hash = hashlib.sha256(_canonical_bytes(entry_body)).hexdigest()
        seal_body = {
            **entry_body,
            "content_hash": content_hash,
            "revision": new_revision,
        }
        try:
            seal_meta = seal_entry(seal_body)
        except SealConfigurationError as exc:
            raise PassportAppendError(str(exc)) from exc

        entry_id = nx_id()
        entry = {
            "canonical_id": entry_id,
            "tenant_id": tenant_id,
            "property_id": property_id,
            **entry_body,
            "content_hash": content_hash,
            "revision": new_revision,
            "schema_version": schema_version,
            "source_type": source_type,
            "source_id": source_id,
            "correlation_id": correlation_id,
            "idempotency_key": idempotency_key,
            "publication_context": publication_context or {},
            "signature_algorithm": seal_meta.get("signature_algorithm"),
            "signature_key_version": seal_meta.get("signature_key_version"),
            "entry_signature": seal_meta.get("entry_signature"),
            "sealed_at": seal_meta.get("sealed_at"),
            "seal_status": seal_meta.get("seal_status"),
            # Compatibility field: HMAC digest when sealed; otherwise legacy
            # tenant-salt digest (NOT a production seal).
            "signature": seal_meta.get("entry_signature") or hashlib.sha256(
                (content_hash + tenant_id[:16]).encode()
            ).hexdigest(),
        }

        await nx_collections.passport_entries.insert_one(dict(entry), **insert_kwargs)

        await nx_collections.passports.update_one(
            {"canonical_id": pid, "tenant_id": tenant_id, "revision": new_revision},
            {"$set": {
                "head_hash": content_hash,
                "head_entry_id": entry_id,
                "head_claim_pending": False,
                "updated_at": now,
            }},
            **insert_kwargs,
        )

        receipt = {
            "canonical_id": nx_id(),
            "tenant_id": tenant_id,
            "passport_id": pid,
            "passport_entry_id": entry_id,
            "receipt_hash": content_hash,
            "signature": entry["signature"],
            "entry_signature": entry.get("entry_signature"),
            "signature_algorithm": entry.get("signature_algorithm"),
            "signature_key_version": entry.get("signature_key_version"),
            "sequence": seq,
            "revision": new_revision,
            "idempotency_key": idempotency_key,
            "request_fingerprint": fp,
            "issued_at": now,
            "commit_status": "COMMITTED",
        }
        await nx_collections.passport_receipts.insert_one(dict(receipt), **insert_kwargs)

        idem_doc = None
        if idempotency_key:
            idem_doc = {
                "canonical_id": nx_id(),
                "tenant_id": tenant_id,
                "passport_id": pid,
                "idempotency_key": idempotency_key,
                "request_fingerprint": fp,
                "entry_id": entry_id,
                "sequence": seq,
                "revision": new_revision,
                "entry_hash": content_hash,
                "receipt_id": receipt["canonical_id"],
                "commit_status": "COMMITTED",
                "created_at": now,
            }
            await nx_collections.passport_idempotency.insert_one(
                dict(idem_doc), **insert_kwargs,
            )

        fresh_passport = await nx_collections.passports.find_one(
            {"canonical_id": pid}, **({"session": sess} if sess else {}),
        )
        return {
            "status": "COMMITTED",
            "passport": strip_mongo_id(fresh_passport),
            "entry": strip_mongo_id(entry),
            "receipt": strip_mongo_id(receipt),
            "idempotency": strip_mongo_id(idem_doc) if idem_doc else None,
        }

    try:
        if use_txn and session is not None:
            try:
                async with session.start_transaction():
                    result = await _commit_body(session)
            except AttributeError:
                # Fake session without start_transaction context manager.
                result = await _commit_body(session)
        else:
            if _strict_transactions_required():
                raise TransactionUnavailableError(
                    "Transactions required but session inactive"
                )
            result = await _commit_body(None)
    except StaleExpectedStateError as exc:
        # CAS race after pre-check — create conflict, do not claim commit.
        conflict = await create_conflict_record(
            tenant_id=tenant_id,
            passport_id=pid,
            property_id=property_id,
            source_type=source_type,
            source_id=source_id,
            attempted_idempotency_key=idempotency_key,
            attempted_expected_revision=expected_revision,
            attempted_expected_head_hash=expected_head_hash,
            actual_revision=None,
            actual_head_hash=None,
            attempted_request_fingerprint=fp,
            actor=authored_by,
            actor_role=actor_role,
            correlation_id=correlation_id,
            conflict_reason="CAS_RACE_STALE",
        )
        await _audit_event(
            tenant_id=tenant_id,
            event_type="PASSPORT_APPEND_CONFLICT",
            actor_id=authored_by,
            actor_role=actor_role,
            resource_kind="passport_conflict",
            resource_id=conflict["conflict_id"],
            payload={"reason": "CAS_RACE_STALE"},
        )
        if idempotency_key:
            await nx_collections.passport_idempotency.update_one(
                {
                    "tenant_id": tenant_id,
                    "passport_id": pid,
                    "idempotency_key": idempotency_key,
                },
                {"$set": {
                    "commit_status": "FAILED",
                    "request_fingerprint": fp,
                    "updated_at": now_iso_utc(),
                }},
                upsert=True,
            )
        raise StaleExpectedStateError(
            "Stale expected Passport state; append refused",
            conflict=conflict,
        ) from exc
    except Exception as exc:
        # Roll back a claimed-but-unfinished revision so retries are possible
        # in non-transactional mode (NOT a substitute for multi-doc txn).
        try:
            await nx_collections.passports.update_one(
                {
                    "canonical_id": pid,
                    "tenant_id": tenant_id,
                    "revision": new_revision,
                    "head_claim_pending": True,
                },
                {"$set": {
                    "revision": actual_revision,
                    "head_claim_pending": False,
                    "updated_at": now_iso_utc(),
                }},
            )
        except Exception:
            logger.error("passport revision claim rollback failed for %s", pid)

        await _audit_event(
            tenant_id=tenant_id,
            event_type="PASSPORT_APPEND_FAILED",
            actor_id=authored_by,
            actor_role=actor_role,
            resource_kind="passport",
            resource_id=pid,
            payload={"reason": type(exc).__name__, "message": str(exc)[:200]},
        )
        if idempotency_key:
            try:
                await nx_collections.passport_idempotency.update_one(
                    {
                        "tenant_id": tenant_id,
                        "passport_id": pid,
                        "idempotency_key": idempotency_key,
                    },
                    {"$set": {
                        "commit_status": "FAILED",
                        "request_fingerprint": fp,
                        "updated_at": now_iso_utc(),
                    }},
                    upsert=True,
                )
            except Exception:
                pass
        if isinstance(exc, PassportAppendError):
            raise
        raise PassportAppendError(
            f"Append failed: {type(exc).__name__}",
            details={"message": str(exc)[:200]},
        ) from exc
    finally:
        if session is not None:
            try:
                await session.end_session()
            except Exception:
                pass

    await _audit_event(
        tenant_id=tenant_id,
        event_type="PASSPORT_APPEND_COMMITTED",
        actor_id=authored_by,
        actor_role=actor_role,
        resource_kind="passport_entry",
        resource_id=result["entry"]["canonical_id"],
        payload={
            "seq": result["entry"]["seq"],
            "revision": result["entry"].get("revision"),
            "content_hash": result["entry"].get("content_hash"),
            "idempotency_key": idempotency_key,
            "transactions_used": use_txn,
        },
    )
    return result


async def read_passport_projection(
    *,
    tenant_id: str,
    property_id: str,
    audience: str = "internal",
) -> Dict[str, Any]:
    """Compose a read-only projection for an audience.

    Audience filtering is metadata-only: entries flag their audience
    visibility on the payload; the projection includes an entry when its
    intersection with the audience is non-empty (or when the caller is
    internal).
    """
    passport = await nx_collections.passports.find_one({
        "tenant_id": tenant_id, "property_id": property_id, "status": "active",
    })
    if not passport:
        return {"passport": None, "entries": [], "audience": audience}
    entries_cursor = nx_collections.passport_entries.find({
        "passport_id": passport["canonical_id"], "tenant_id": tenant_id,
    }).sort("seq", 1)
    filtered = []
    async for e in entries_cursor:
        vis = (e.get("payload") or {}).get("visibility") or {}
        if audience == "internal" or audience in {"contractor", "adjuster", "insurer"} \
                or vis.get(audience, False):
            filtered.append(strip_mongo_id(e))
    return {"passport": strip_mongo_id(passport), "entries": filtered, "audience": audience}
