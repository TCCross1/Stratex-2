"""NextGen audit trail read endpoints — Domain 10."""
from __future__ import annotations

from fastapi import Depends, Query

from ..auth import NxSession, nx_session
from ..db import nx_collections, strip_mongo_id
from ._router import nextgen_r


@nextgen_r.get("/audit/events")
async def list_audit_events(
    session: NxSession = Depends(nx_session),
    limit: int = Query(100, ge=1, le=500),
):
    cursor = nx_collections.audit_events.find(
        {"tenant_id": session.tenant_id}
    ).sort("at", -1).limit(limit)
    items = [strip_mongo_id(d) async for d in cursor]
    return {"items": items, "count": len(items)}
