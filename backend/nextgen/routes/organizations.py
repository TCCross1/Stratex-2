"""NextGen organization endpoints — Domain 1 (Tenants).

Phase 1a: read own organization + update basic contact info. Full user
management (invitations, roles, MFA) arrives in Phase 1b once RBAC lands.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..auth import NxSession, nx_session
from ..db import now_iso_utc, nx_collections, strip_mongo_id
from ._router import nextgen_r


class OrganizationPatch(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


@nextgen_r.get("/organizations/current")
async def get_current_org(session: NxSession = Depends(nx_session)):
    return {"organization": session.tenant}


@nextgen_r.patch("/organizations/current")
async def patch_current_org(
    body: OrganizationPatch,
    session: NxSession = Depends(nx_session),
):
    if session.role not in {"admin", "contractor", "ceo"}:
        raise HTTPException(403, "Only admin/contractor may update the org")
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not update:
        return {"organization": session.tenant}
    update["updated_at"] = now_iso_utc()
    await nx_collections.organizations.update_one(
        {"canonical_id": session.tenant_id},
        {"$set": update, "$inc": {"version": 1}},
    )
    org = await nx_collections.organizations.find_one(
        {"canonical_id": session.tenant_id}
    )
    return {"organization": strip_mongo_id(org)}
