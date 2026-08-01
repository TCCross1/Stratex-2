"""Publish bridge API — Field Test v1"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from ..auth import NxSession, nx_session
from ..publish_bridge import publish_sealed_package
from ._router import nextgen_r


class PublishRequest(BaseModel):
    publication_request: Dict[str, Any]
    correlation_id: Optional[str] = None


@nextgen_r.post("/field-test/publish")
async def publish_mission_package(
    req: PublishRequest,
    session: NxSession = Depends(nx_session),
):
    """
    Submit a prepared publication_request through governed_publish.
    Requires expected_revision or expected_head_hash on the request.
    """
    pr = dict(req.publication_request)
    # Enforce tenant isolation
    if pr.get("tenant_id") and pr["tenant_id"] != session.tenant_id:
        raise HTTPException(403, "Tenant mismatch")
    pr["tenant_id"] = session.tenant_id

    result = await publish_sealed_package(
        pr,
        actor_id=session.user_id,
        actor_role=getattr(session, "role", None),
        correlation_id=req.correlation_id,
    )
    status = result.get("status")
    if status == "REJECTED":
        raise HTTPException(400, result)
    if status == "CONFLICT":
        raise HTTPException(409, result)
    if status == "UNAVAILABLE":
        raise HTTPException(503, result)
    if status == "FAILED":
        raise HTTPException(500, result)
    return result
