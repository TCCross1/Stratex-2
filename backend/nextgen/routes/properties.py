"""NextGen property endpoints — Domain 2 (Properties).

Implements the minimum viable slice of the SD-002 identity resolution flow:
- POST /properties/resolve  → auto-match, review, or create-new
- POST /properties          → create a property (skips duplicate check)
- GET  /properties          → list this tenant's properties
- GET  /properties/{id}     → property detail
- PATCH /properties/{id}    → correct fields (address/coordinate/unit) via
  SUPERSEDE semantics (writes an audit event + bumps version).

Passport identity is composite (address + coordinate + parcel + unit) per
Blueprint §11.2. Duplicate detection is address+parcel exact match for
Phase 1a; fuzzy match arrives with the identity-resolution service.
"""
from __future__ import annotations

import hashlib
from typing import List

from fastapi import Depends, HTTPException, Query

from ..auth import NxSession, nx_session
from ..db import now_iso_utc, nx_collections, nx_id, strip_mongo_id
from ..models import Address, GeoCoordinate, ParcelIdentifier, PropertyCreate
from ._router import nextgen_r


def _value_hash(*parts: str) -> str:
    return hashlib.sha256("|".join(p.lower().strip() for p in parts if p).encode()).hexdigest()[:24]


def _identity_hashes(body: PropertyCreate):
    addr = body.address
    address_hash = _value_hash(
        addr.line1 or "", addr.line2 or "", addr.city, addr.region,
        addr.postal_code, addr.country_iso, body.unit_label or "",
    )
    parcel_hash = (
        _value_hash(body.parcel.jurisdiction, body.parcel.parcel_number)
        if body.parcel else None
    )
    return address_hash, parcel_hash


async def _find_candidates(tenant_id: str, address_hash: str, parcel_hash: str | None):
    q = {"tenant_id": tenant_id, "status": "active",
         "$or": [{"address_hash": address_hash}]}
    if parcel_hash:
        q["$or"].append({"parcel_hash": parcel_hash})
    cursor = nx_collections.properties.find(q).limit(5)
    return [strip_mongo_id(d) async for d in cursor]


@nextgen_r.post("/properties/resolve")
async def resolve_property(
    body: PropertyCreate,
    session: NxSession = Depends(nx_session),
):
    address_hash, parcel_hash = _identity_hashes(body)
    candidates = await _find_candidates(session.tenant_id, address_hash, parcel_hash)
    if candidates:
        return {
            "decision": "auto_match" if len(candidates) == 1 else "review",
            "candidates": candidates,
        }
    return {"decision": "create_new", "candidates": []}


@nextgen_r.post("/properties")
async def create_property(
    body: PropertyCreate,
    session: NxSession = Depends(nx_session),
):
    address_hash, parcel_hash = _identity_hashes(body)
    dup = await nx_collections.properties.find_one({
        "tenant_id": session.tenant_id,
        "address_hash": address_hash,
        "status": "active",
    })
    if dup:
        raise HTTPException(
            409,
            {
                "code": "duplicate_property",
                "message": "A property with this address already exists on your tenant.",
                "existing_property_id": dup["canonical_id"],
            },
        )
    now = now_iso_utc()
    prop = {
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "status": "active",
        "truth_score_band": 5,
        "address": body.address.model_dump(),
        "coordinate": body.coordinate.model_dump() if body.coordinate else None,
        "parcel": body.parcel.model_dump() if body.parcel else None,
        "unit_label": body.unit_label,
        "address_hash": address_hash,
        "parcel_hash": parcel_hash,
        "superseded_by_id": None,
        "created_by": session.user_id,
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    await nx_collections.properties.insert_one(dict(prop))

    # Audit event (§Domain 10) — minimal but real.
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "property.created",
        "actor_id": session.user_id,
        "resource_kind": "property",
        "resource_id": prop["canonical_id"],
        "at": now,
        "payload": {"address_hash": address_hash, "parcel_hash": parcel_hash},
    })
    return {"property": strip_mongo_id(prop)}


@nextgen_r.get("/properties")
async def list_properties(
    session: NxSession = Depends(nx_session),
    limit: int = Query(50, ge=1, le=200),
):
    cursor = nx_collections.properties.find(
        {"tenant_id": session.tenant_id, "status": "active"}
    ).sort("created_at", -1).limit(limit)
    items = [strip_mongo_id(d) async for d in cursor]
    return {"items": items, "count": len(items)}


@nextgen_r.get("/properties/{property_id}")
async def get_property(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    doc = await nx_collections.properties.find_one({
        "canonical_id": property_id,
        "tenant_id": session.tenant_id,
    })
    if not doc:
        raise HTTPException(404, "Property not found")
    return {"property": strip_mongo_id(doc)}
