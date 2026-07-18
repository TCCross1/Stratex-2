"""NextGen Passport endpoints (stub for Phase 1a).

Passport authority is the Passport Service (Blueprint §11). Phase 1a
exposes a read-only stub so downstream UI can wire against a real
endpoint before real ledger writes are enabled in Phase 1c.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException

from ..auth import NxSession, nx_session
from ..db import nx_collections, strip_mongo_id
from ._router import nextgen_r


@nextgen_r.get("/passports/by-property/{property_id}")
async def passport_by_property(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id,
        "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found")
    passport = await nx_collections.passports.find_one({"property_id": property_id})
    return {
        "property": strip_mongo_id(prop),
        "passport": strip_mongo_id(passport),
        "entries": [],  # ledger read arrives in Phase 1c
        "note": (
            "Passport ledger writes are gated to the Passport Service. "
            "Phase 1a exposes a read-only surface; ledger append lands in Phase 1c."
        ),
    }
