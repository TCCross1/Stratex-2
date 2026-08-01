"""
Mission Package Sealing endpoints — Field Test v1

POST /api/nextgen/missions/packages/seal
  Accepts a mission package (or creates a skeleton), seals it with
  geometry withholding rules, and returns a publication_request ready
  for the existing governed publisher. Does NOT write to Passport.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import NxSession, nx_session
from ..mission_package_seal import seal_package, SealingError, create_empty_package
from ..mission_to_passport import prepare_for_governed_publish, HandoffError
from ._router import nextgen_r


class SealRequest(BaseModel):
    mission_id: str
    property_id: str
    capture_type: str = "DAYTIME_PRECISION_MAPPING"
    package: Optional[Dict[str, Any]] = None
    expected_revision: Optional[int] = None
    expected_head_hash: Optional[str] = None


@nextgen_r.post("/missions/packages/seal")
async def seal_and_prepare(
    req: SealRequest,
    session: NxSession = Depends(nx_session),
):
    """
    Seal a Canonical Mission Package and prepare it for governed publication.
    Returns status READY_FOR_GOVERNED_PUBLISH + the publication_request payload.
    """
    try:
        if req.package:
            raw = dict(req.package)
            raw["mission_id"] = req.mission_id
            raw["tenant_id"] = session.tenant_id
            raw["property_id"] = req.property_id
        else:
            raw = create_empty_package(
                mission_id=req.mission_id,
                tenant_id=session.tenant_id,
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
        raise HTTPException(
            status_code=400,
            detail={"code": getattr(e, "code", "SEAL_ERROR"), "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
