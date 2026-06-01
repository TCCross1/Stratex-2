"""STRATEX™ Supplier Registry — Phase 1.

CEO-only CRUD for building-material supplier brands (QXO, ABC Supply, future).
GM accounts MUST be associated with a `supplier_id` so their dashboard,
materials brand roster, and pricing inventory are correctly scoped.

Endpoints (mounted on shared /api router):

  POST   /api/admin/suppliers              — CEO creates a supplier brand
  GET    /api/admin/suppliers              — CEO/Admin lists all suppliers
  GET    /api/admin/suppliers/{id}         — fetch one
  PATCH  /api/admin/suppliers/{id}         — update name / colors / status
  DELETE /api/admin/suppliers/{id}         — archive (soft delete)
  POST   /api/admin/users/create           — CEO/GM creates downstream users
                                             enforcing the role pyramid

Role pyramid enforced at user-creation time:
    CEO     → can create: gm, stratex_staff (operator, sales)
    GM/Admin→ can create: branch_sales_rep, contractor
    Others  → 403
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import api, current_user, db, now_iso

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SupplierIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    short_code: str = Field(..., min_length=2, max_length=12)   # "QXO", "ABC"
    brand_color: str = "#00E5FF"                                  # hex
    secondary_color: str = "#FFB020"
    logo_text: Optional[str] = None
    headquarters_city: Optional[str] = None
    status: str = "active"                                        # active | archived


class SupplierPatch(BaseModel):
    name: Optional[str] = None
    brand_color: Optional[str] = None
    secondary_color: Optional[str] = None
    logo_text: Optional[str] = None
    headquarters_city: Optional[str] = None
    status: Optional[str] = None


class CreateUserBody(BaseModel):
    """Hardened account-creation gate. Replaces ad-hoc /signup for any
    non-self-serve creation (CEO creates GM, GM creates contractor, etc.)."""
    email: str
    legal_name: str
    role: str                                # gm | operator | sales | branch_sales_rep | contractor
    supplier_id: Optional[str] = None        # required for gm + branch_sales_rep + contractor
    company_name: Optional[str] = ""
    phone: Optional[str] = None
    initial_password: str = Field(..., min_length=8)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _public_supplier(doc: Dict[str, Any]) -> Dict[str, Any]:
    d = {k: v for k, v in doc.items() if k != "_id"}
    return d


async def _require_ceo(user: Dict[str, Any]) -> None:
    if user.get("role") not in ("ceo", "admin"):
        raise HTTPException(403, "CEO or Admin role required")


async def _require_ceo_or_gm(user: Dict[str, Any]) -> None:
    if user.get("role") not in ("ceo", "admin", "gm"):
        raise HTTPException(403, "CEO, Admin, or GM role required")


# ---------------------------------------------------------------------------
# Supplier CRUD
# ---------------------------------------------------------------------------

@api.post("/admin/suppliers")
async def create_supplier(body: SupplierIn, user=Depends(current_user)):
    await _require_ceo(user)
    short = body.short_code.upper().strip()
    if await db.suppliers.find_one({"short_code": short}):
        raise HTTPException(409, f"Supplier code {short} already exists")
    doc = {
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "short_code": short,
        "brand_color": body.brand_color,
        "secondary_color": body.secondary_color,
        "logo_text": body.logo_text or short,
        "headquarters_city": body.headquarters_city or "",
        "status": body.status,
        "created_at": now_iso(),
        "created_by": user.get("id"),
        "gm_count": 0,
        "contractor_count": 0,
    }
    await db.suppliers.insert_one(doc)
    return {"ok": True, "supplier": _public_supplier(doc)}


@api.get("/admin/suppliers")
async def list_suppliers(user=Depends(current_user)):
    await _require_ceo_or_gm(user)
    cursor = db.suppliers.find({}).sort("created_at", 1)
    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        # Live-recompute counts so the dashboard tile is always accurate.
        sid = doc["id"]
        doc["gm_count"] = await db.users.count_documents({"role": "gm", "supplier_id": sid})
        doc["contractor_count"] = await db.users.count_documents(
            {"role": "contractor", "supplier_id": sid}
        )
        items.append(_public_supplier(doc))
    return {"items": items, "count": len(items)}


@api.get("/admin/suppliers/{supplier_id}")
async def get_supplier(supplier_id: str, user=Depends(current_user)):
    await _require_ceo_or_gm(user)
    doc = await db.suppliers.find_one({"id": supplier_id})
    if not doc:
        raise HTTPException(404, "Supplier not found")
    return {"supplier": _public_supplier(doc)}


@api.patch("/admin/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, body: SupplierPatch, user=Depends(current_user)):
    await _require_ceo(user)
    patch = {k: v for k, v in body.dict().items() if v is not None}
    if not patch:
        raise HTTPException(400, "No fields to update")
    patch["updated_at"] = now_iso()
    result = await db.suppliers.update_one({"id": supplier_id}, {"$set": patch})
    if result.matched_count == 0:
        raise HTTPException(404, "Supplier not found")
    doc = await db.suppliers.find_one({"id": supplier_id})
    return {"ok": True, "supplier": _public_supplier(doc)}


@api.delete("/admin/suppliers/{supplier_id}")
async def archive_supplier(supplier_id: str, user=Depends(current_user)):
    await _require_ceo(user)
    result = await db.suppliers.update_one(
        {"id": supplier_id},
        {"$set": {"status": "archived", "archived_at": now_iso()}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Supplier not found")
    return {"ok": True, "archived": True}


# ---------------------------------------------------------------------------
# Role-pyramid user creation
# ---------------------------------------------------------------------------

# Who-can-create-whom matrix
_CREATION_RULES = {
    "ceo":   {"gm", "operator", "sales", "admin"},
    "admin": {"gm", "operator", "sales"},
    "gm":    {"branch_sales_rep", "contractor"},
}

# Roles that MUST be tied to a supplier_id
_SUPPLIER_BOUND_ROLES = {"gm", "branch_sales_rep", "contractor"}


@api.post("/admin/users/create")
async def create_user(body: CreateUserBody, user=Depends(current_user)):
    creator_role = user.get("role")
    if creator_role not in _CREATION_RULES:
        raise HTTPException(403, "Your role cannot create user accounts")

    target_role = body.role.lower().strip()
    if target_role not in _CREATION_RULES[creator_role]:
        raise HTTPException(
            403,
            f"As {creator_role} you cannot create role '{target_role}'. "
            f"Allowed: {sorted(_CREATION_RULES[creator_role])}",
        )

    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Email already registered")

    # Supplier scoping
    supplier_id = body.supplier_id
    if target_role in _SUPPLIER_BOUND_ROLES:
        if not supplier_id:
            raise HTTPException(400, f"supplier_id required for role '{target_role}'")
        supplier = await db.suppliers.find_one({"id": supplier_id, "status": "active"})
        if not supplier:
            raise HTTPException(404, "Active supplier not found for given supplier_id")
        # GM creating contractor/branch-rep must be inside that same supplier
        if creator_role == "gm" and user.get("supplier_id") != supplier_id:
            raise HTTPException(403, "GM may only create users inside own supplier branch")

    # Mint user (TOTP enrollment optional — admin-created accounts ship with a
    # forced-password-reset flag; TOTP setup happens at first real login).
    from stratex_auth import hash_password, new_totp_secret
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "legal_name": body.legal_name.strip(),
        "company_name": body.company_name or "",
        "role": target_role,
        "supplier_id": supplier_id,
        "phone": (body.phone or "").strip(),
        "password_hash": hash_password(body.initial_password),
        "totp_secret": new_totp_secret(),
        "totp_enrolled": False,
        "nda_accepted": False,
        "must_change_password": True,
        "created_at": now_iso(),
        "created_by": user.get("id"),
        "created_by_role": creator_role,
    }
    await db.users.insert_one(user_doc)
    return {
        "ok": True,
        "user": {
            "id": user_doc["id"],
            "email": email,
            "legal_name": user_doc["legal_name"],
            "role": target_role,
            "supplier_id": supplier_id,
            "must_change_password": True,
            "created_at": user_doc["created_at"],
        },
    }


# ---------------------------------------------------------------------------
# Idempotent seed of QXO + ABC Supply at startup
# ---------------------------------------------------------------------------

SEED_SUPPLIERS = [
    {
        "short_code": "QXO",
        "name": "QXO Building Products",
        "brand_color": "#00E5FF",
        "secondary_color": "#FFB020",
        "logo_text": "QXO",
        "headquarters_city": "Greenwich, CT",
    },
    {
        "short_code": "ABC",
        "name": "ABC Supply Co., Inc.",
        "brand_color": "#FF2D78",
        "secondary_color": "#00FF9C",
        "logo_text": "ABC",
        "headquarters_city": "Beloit, WI",
    },
]


async def seed_suppliers(db_) -> None:
    """Idempotent. Called from server.py startup."""
    for s in SEED_SUPPLIERS:
        existing = await db_.suppliers.find_one({"short_code": s["short_code"]})
        if existing:
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "name": s["name"],
            "short_code": s["short_code"],
            "brand_color": s["brand_color"],
            "secondary_color": s["secondary_color"],
            "logo_text": s["logo_text"],
            "headquarters_city": s["headquarters_city"],
            "status": "active",
            "created_at": now_iso(),
            "created_by": "seed",
            "gm_count": 0,
            "contractor_count": 0,
        }
        await db_.suppliers.insert_one(doc)
