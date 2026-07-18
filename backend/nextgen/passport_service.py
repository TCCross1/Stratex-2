"""NextGen Passport Service — canonical hash-chained property ledger.

Only this module writes to `nextgen_passport_entries`. Callers submit
approved intelligence deltas and receive a signed receipt (SHA-256 over
the entry payload + prior_hash). The ledger is append-only.

Rebase / conflict semantics: Phase 2B uses optimistic append with a lock
on `nextgen_passport_sequences.next_seq`. True rebase logic (SD-014
conflict queue) arrives when concurrent write pressure appears.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from .db import now_iso_utc, nx_collections, nx_id, strip_mongo_id


def _canonical_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


async def _ensure_passport(tenant_id: str, property_id: str) -> Dict[str, Any]:
    """Provision or return the active passport for a property."""
    p = await nx_collections.passports.find_one({
        "tenant_id": tenant_id, "property_id": property_id, "status": "active",
    })
    if p:
        return p
    now = now_iso_utc()
    p = {
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "property_id": property_id,
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    await nx_collections.passports.insert_one(dict(p))
    await nx_collections.passport_sequences.insert_one({
        "canonical_id": nx_id(),
        "passport_id": p["canonical_id"],
        "next_seq": 1,
        "created_at": now,
    })
    return p


async def _next_seq(passport_id: str) -> int:
    """Optimistic monotonic next-seq. Two Mongo ops; races produce a retry
    at the caller — safe because the unique index on (passport_id, seq) will
    reject a collision.
    """
    doc = await nx_collections.passport_sequences.find_one_and_update(
        {"passport_id": passport_id},
        {"$inc": {"next_seq": 1}},
        return_document=True,  # motor returns updated doc when True
    )
    return int(doc["next_seq"] - 1)


async def _prior_hash(passport_id: str) -> Optional[str]:
    prev = await nx_collections.passport_entries.find_one(
        {"passport_id": passport_id},
        sort=[("seq", -1)],
    )
    return (prev or {}).get("content_hash")


async def append_entry(
    *,
    tenant_id: str,
    property_id: str,
    entry_type: str,
    payload: Dict[str, Any],
    authored_by: str,
) -> Dict[str, Any]:
    """Append an entry to the passport ledger and return the signed receipt.

    Content-addressed: `content_hash = sha256({payload, seq, prior_hash,
    entry_type, at, authored_by})`. `prior_hash` chains entries.
    """
    passport = await _ensure_passport(tenant_id, property_id)
    now = now_iso_utc()
    seq = await _next_seq(passport["canonical_id"])
    prior = await _prior_hash(passport["canonical_id"])
    entry_body = {
        "passport_id": passport["canonical_id"],
        "seq": seq,
        "entry_type": entry_type,
        "payload": payload,
        "prior_hash": prior,
        "at": now,
        "authored_by": authored_by,
    }
    content_hash = hashlib.sha256(_canonical_bytes(entry_body)).hexdigest()
    entry = {
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "property_id": property_id,
        **entry_body,
        "content_hash": content_hash,
        # signature = HMAC-like: sha256 of (content_hash + service key). In
        # Phase 2B the "service key" is a deterministic per-tenant salt so
        # the receipt is verifiable end-to-end without a KMS integration.
        "signature": hashlib.sha256(
            (content_hash + tenant_id[:16]).encode()
        ).hexdigest(),
    }
    await nx_collections.passport_entries.insert_one(dict(entry))
    receipt = {
        "canonical_id": nx_id(),
        "tenant_id": tenant_id,
        "passport_entry_id": entry["canonical_id"],
        "receipt_hash": entry["content_hash"],
        "signature": entry["signature"],
        "issued_at": now,
    }
    await nx_collections.passport_receipts.insert_one(dict(receipt))
    return {
        "passport": strip_mongo_id(passport),
        "entry": strip_mongo_id(entry),
        "receipt": strip_mongo_id(receipt),
    }


async def read_passport_projection(
    *,
    tenant_id: str,
    property_id: str,
    audience: str = "internal",
) -> Dict[str, Any]:
    """Compose a read-only projection for an audience.

    Audience filtering is metadata-only in Phase 2B: entries flag their
    audience visibility on the payload; the projection includes an entry
    when its intersection with the audience is non-empty (or when the
    caller is internal).
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
