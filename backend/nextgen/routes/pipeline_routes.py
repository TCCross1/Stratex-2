"""
Field Test Pipeline API — run single or dual path orchestration
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import NxSession, nx_session
from ..field_test_pipeline import run_single_path_pipeline, run_dual_path_pipeline
from ..evidence_ingest import ingest_media_item
from ._router import nextgen_r


class MediaItemIn(BaseModel):
    media_type: str
    capture_timestamp: str
    camera_model: str
    size_bytes: int
    content_hash: Optional[str] = None


class SinglePipelineRequest(BaseModel):
    mission_id: str
    property_id: str
    mission_type: str = "DAYTIME_PRECISION_MAPPING"
    aircraft_profile: str = "Matrice_4E"
    media_items: List[MediaItemIn] = Field(default_factory=list)
    geometry_candidate: Optional[Dict[str, Any]] = None
    awe_candidate: Optional[Dict[str, Any]] = None
    pilot: Optional[str] = None
    weather: Optional[str] = None
    rtk_status: str = "FIXED"
    skip_readiness: bool = False
    battery_pct: float = 90.0


class DualPipelineRequest(BaseModel):
    mapping_mission_id: str
    awe_mission_id: str
    property_id: str
    geometry_candidate: Optional[Dict[str, Any]] = None
    awe_candidate: Optional[Dict[str, Any]] = None
    battery_pct: float = 90.0


@nextgen_r.post("/field-test/pipeline/single")
async def pipeline_single(
    req: SinglePipelineRequest,
    session: NxSession = Depends(nx_session),
):
    items = [
        ingest_media_item(
            m.media_type, m.capture_timestamp, m.camera_model, m.size_bytes, m.content_hash
        )
        for m in req.media_items
    ] or None
    result = run_single_path_pipeline(
        mission_id=req.mission_id,
        tenant_id=session.tenant_id,
        property_id=req.property_id,
        mission_type=req.mission_type,
        aircraft_profile=req.aircraft_profile,
        media_items=items,
        geometry_candidate=req.geometry_candidate,
        awe_candidate=req.awe_candidate,
        pilot=req.pilot,
        weather=req.weather,
        rtk_status=req.rtk_status,
        readiness_kwargs={"battery_pct": req.battery_pct},
        skip_readiness=req.skip_readiness,
    )
    return result.to_dict()


@nextgen_r.post("/field-test/pipeline/dual")
async def pipeline_dual(
    req: DualPipelineRequest,
    session: NxSession = Depends(nx_session),
):
    result = run_dual_path_pipeline(
        mapping_mission_id=req.mapping_mission_id,
        awe_mission_id=req.awe_mission_id,
        tenant_id=session.tenant_id,
        property_id=req.property_id,
        geometry_candidate=req.geometry_candidate,
        awe_candidate=req.awe_candidate,
        readiness_kwargs={"battery_pct": req.battery_pct},
    )
    return result
