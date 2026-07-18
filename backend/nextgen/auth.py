"""NextGen tenant/session bridge.

Legacy auth remains the source of truth for user identity. NextGen adds a
lightweight tenant binding: each authenticated user is bound to one
`nextgen_organization` row keyed by their `company_name` (auto-provisioned on
first request). This keeps Phase 1a compatible with the existing login flow
without touching legacy auth.

Requires `admin` or `contractor` role for now; expand to full RBAC in Phase 1b.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException

from core import current_user

from .db import now_iso_utc, nx_collections, nx_id, strip_mongo_id


async def _ensure_org_for_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Find or provision a NextGen organization tied to this user's company.

    Phase 1a shortcut: 1 org per legacy `company_name`. If the user has no
    company_name (e.g. admin), we fall back to a per-user personal tenant so
    they can still exercise the workflow end-to-end.
    """
    company = (user.get("company_name") or "").strip()
    tenant_key = company or f"__personal__::{user['id']}"

    org = await nx_collections.organizations.find_one({"tenant_key": tenant_key})
    if org:
        return strip_mongo_id(org)

    now = now_iso_utc()
    org = {
        "canonical_id": nx_id(),
        "tenant_key": tenant_key,
        "name": company or f"{user.get('legal_name', 'Personal')} — Personal",
        "legal_name": company or None,
        "jurisdiction": "US",
        "status": "active",
        "contact_email": user.get("email", ""),
        "contact_phone": None,
        "billing_status": "good",
        "owner_user_id": user["id"],
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    await nx_collections.organizations.insert_one(dict(org))
    return strip_mongo_id(org)


class NxSession:
    """Bundle of the legacy user + the derived NextGen tenant."""

    def __init__(self, user: Dict[str, Any], tenant: Dict[str, Any]):
        self.user = user
        self.tenant = tenant

    @property
    def tenant_id(self) -> str:
        return self.tenant["canonical_id"]

    @property
    def user_id(self) -> str:
        return self.user["id"]

    @property
    def role(self) -> str:
        return self.user.get("role", "contractor")


async def nx_session(user: Dict[str, Any] = Depends(current_user)) -> NxSession:
    if not user:
        raise HTTPException(401, "Not authenticated")
    tenant = await _ensure_org_for_user(user)
    return NxSession(user, tenant)
