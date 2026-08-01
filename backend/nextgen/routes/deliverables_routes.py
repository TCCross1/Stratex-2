"""Contractor deliverables API — Field Test v1"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends
from pydantic import BaseModel, Field

from ..auth import NxSession, nx_session
from ..deliverables_package import (
    build_contractor_deliverables,
    build_dual_path_deliverables,
)
from ..evidence_ingest import ingest_media_item
from ._router import nextgen_r


class MediaItemIn(BaseModel):
    media_type: str
    capture_timestamp: str
    camera_model: str
    size_bytes: int
    content_hash: Optional[str] = None


class DeliverablesRequest(BaseModel):
    mission_id: str
    property_id: str
    mission_type: str = "DAYTIME_PRECISION_MAPPING"
    aircraft_profile: str = "Matrice_4E"
    media_items: List[MediaItemIn] = Field(default_factory=list)
    geometry_candidate: Optional[Dict[str, Any]] = None
    awe_candidate: Optional[Dict[str, Any]] = None
    battery_pct: float = 90.0
    include_homeowner_html: bool = True


class DualDeliverablesRequest(BaseModel):
    mapping_mission_id: str
    awe_mission_id: str
    property_id: str
    geometry_candidate: Optional[Dict[str, Any]] = None
    awe_candidate: Optional[Dict[str, Any]] = None


@nextgen_r.post("/field-test/deliverables")
async def contractor_deliverables(
    req: DeliverablesRequest,
    session: NxSession = Depends(nx_session),
):
    items = [
        ingest_media_item(
            m.media_type, m.capture_timestamp, m.camera_model, m.size_bytes, m.content_hash
        )
        for m in req.media_items
    ] or None
    return build_contractor_deliverables(
        mission_id=req.mission_id,
        tenant_id=session.tenant_id,
        property_id=req.property_id,
        mission_type=req.mission_type,
        aircraft_profile=req.aircraft_profile,
        media_items=items,
        geometry_candidate=req.geometry_candidate,
        awe_candidate=req.awe_candidate,
        readiness_kwargs={"battery_pct": req.battery_pct},
        include_homeowner_html=req.include_homeowner_html,
    )


@nextgen_r.post("/field-test/deliverables/dual")
async def dual_deliverables(
    req: DualDeliverablesRequest,
    session: NxSession = Depends(nx_session),
):
    return build_dual_path_deliverables(
        mapping_mission_id=req.mapping_mission_id,
        awe_mission_id=req.awe_mission_id,
        tenant_id=session.tenant_id,
        property_id=req.property_id,
        geometry_candidate=req.geometry_candidate,
        awe_candidate=req.awe_candidate,
    )
