"""NextGen workflow read endpoints — Blueprint §22 stage progression."""
from __future__ import annotations

from fastapi import Depends

from ..auth import NxSession, nx_session
from ..db import nx_collections, strip_mongo_id
from ._router import nextgen_r
from .missions import STAGE_LABELS


@nextgen_r.get("/workflow/stages")
async def list_stages():
    return {"stages": [
        {"index": i + 1, "label": STAGE_LABELS[i]} for i in range(15)
    ]}


@nextgen_r.get("/workflow/overview")
async def overview(session: NxSession = Depends(nx_session)):
    """Compact executive summary used by the Mission Control shell."""
    q = {"tenant_id": session.tenant_id}
    mission_count = await nx_collections.missions.count_documents(q)
    property_count = await nx_collections.properties.count_documents(
        {**q, "status": "active"}
    )
    by_stage = {}
    cursor = nx_collections.missions.find(q)
    async for m in cursor:
        stage = m.get("stage", 1)
        by_stage[stage] = by_stage.get(stage, 0) + 1
    return {
        "tenant_id": session.tenant_id,
        "counts": {
            "properties_active": property_count,
            "missions_total": mission_count,
        },
        "missions_by_stage": [
            {
                "stage": s,
                "label": STAGE_LABELS[s - 1],
                "count": by_stage.get(s, 0),
            }
            for s in range(1, 16)
        ],
    }
