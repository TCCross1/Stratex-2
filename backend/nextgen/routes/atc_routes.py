"""
ATC Readiness + Evidence Ingest routes — Field Test v1
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import NxSession, nx_session
from ..atc.readiness import evaluate_readiness
from ..evidence_ingest import assemble_package_from_capture, ingest_media_item
from ..mission_package_seal import seal_package, SealingError
from ..mission_to_passport import prepare_for_governed_publish, HandoffError
from ._router import nextgen_r


class ReadinessRequest(BaseModel):
    mission_id: str
    weather_ok: bool = True
    airspace_clear: bool = True
    geofence_ok: bool = True
    battery_pct: float = 100.0
    sensor_status_ok: bool = True
    storage_ok: bool = True
    network_ok: bool = True
    calibration_ok: bool = True
    rtk_ready: bool = True
    pilot_authorized: bool = True
    equipment_health_ok: bool = True
    mission_plan_present: bool = True


class MediaItemIn(BaseModel):
    media_type: str
    capture_timestamp: str
    camera_model: str
    size_bytes: int
    content_hash: Optional[str] = None


class AssembleRequest(BaseModel):
    mission_id: str
    property_id: str
    capture_type: str = "DAYTIME_PRECISION_MAPPING"
    aircraft: str = "DJI Matrice 4E"
    pilot: Optional[str] = None
    weather: Optional[str] = None
    rtk_status: str = "UNKNOWN"
    media_items: List[MediaItemIn] = Field(default_factory=list)
    geometry_candidate: Optional[Dict[str, Any]] = None
    awe_candidate: Optional[Dict[str, Any]] = None
    seal: bool = True
    expected_revision: Optional[int] = None
    expected_head_hash: Optional[str] = None


@nextgen_r.post("/atc/readiness")
async def check_readiness(
    req: ReadinessRequest,
    session: NxSession = Depends(nx_session),
):
    """Evaluate ATC readiness for a mission. Blocking failures prevent capture."""
    report = evaluate_readiness(
        req.mission_id,
        weather_ok=req.weather_ok,
        airspace_clear=req.airspace_clear,
        geofence_ok=req.geofence_ok,
        battery_pct=req.battery_pct,
        sensor_status_ok=req.sensor_status_ok,
        storage_ok=req.storage_ok,
        network_ok=req.network_ok,
        calibration_ok=req.calibration_ok,
        rtk_ready=req.rtk_ready,
        pilot_authorized=req.pilot_authorized,
        equipment_health_ok=req.equipment_health_ok,
        mission_plan_present=req.mission_plan_present,
    )
    return report.to_dict()


@nextgen_r.post("/missions/packages/assemble")
async def assemble_and_optionally_seal(
    req: AssembleRequest,
    session: NxSession = Depends(nx_session),
):
    """
    Assemble a Canonical Mission Package from capture media.
    Optionally seal it and prepare the governed-publish payload.
    """
    try:
        items = [
            ingest_media_item(
                m.media_type,
                m.capture_timestamp,
                m.camera_model,
                m.size_bytes,
                content_hash=m.content_hash,
            )
            for m in req.media_items
        ]
        pkg = assemble_package_from_capture(
            mission_id=req.mission_id,
            tenant_id=session.tenant_id,
            property_id=req.property_id,
            capture_type=req.capture_type,
            media_items=items,
            aircraft=req.aircraft,
            pilot=req.pilot,
            weather=req.weather,
            rtk_status=req.rtk_status,
            geometry_candidate=req.geometry_candidate,
            awe_candidate=req.awe_candidate,
        )
        if not req.seal:
            return {"status": "ASSEMBLED", "package": pkg}

        result = prepare_for_governed_publish(
            pkg,
            expected_revision=req.expected_revision,
            expected_head_hash=req.expected_head_hash,
        )
        return result
    except (SealingError, HandoffError) as e:
        raise HTTPException(
            status_code=400,
            detail={"code": getattr(e, "code", "ERROR"), "message": str(e)},
        )
