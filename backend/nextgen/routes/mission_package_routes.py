"""
Mission Package API Routes — Field Test v1
POST /api/nextgen/missions/packages/seal
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..mission_package_seal import seal_package, SealingError, create_empty_package
from ..mission_to_passport import prepare_for_governed_publish, HandoffError

router = APIRouter(prefix="/api/nextgen/missions/packages", tags=["mission-packages"])


class SealRequest(BaseModel):
    mission_id: str
    tenant_id: str
    property_id: str
    capture_type: str = "DAYTIME_PRECISION_MAPPING"
    package: Optional[Dict[str, Any]] = None  # full package if already assembled
    expected_revision: Optional[int] = None
    expected_head_hash: Optional[str] = None


@router.post("/seal")
async def seal_and_prepare(req: SealRequest):
    """
    Accept a mission package (or create a skeleton), seal it,
    and return a publication_request ready for the governed publisher.
    Does not write to Passport.
    """
    try:
        if req.package:
            raw = req.package
            # Ensure identity fields match
            raw["mission_id"] = req.mission_id
            raw["tenant_id"] = req.tenant_id
            raw["property_id"] = req.property_id
        else:
            raw = create_empty_package(
                mission_id=req.mission_id,
                tenant_id=req.tenant_id,
                property_id=req.property_id,
                capture_type=req.capture_type,
            )

        result = prepare_for_governed_publish(
            raw,
            expected_revision=req.expected_revision,
            expected_head_hash=req.expected_head_hash,
        )
        return result

    except (SealingError, HandoffError) as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": e.message})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
