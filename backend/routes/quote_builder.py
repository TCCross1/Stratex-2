"""STRATEX Contractor Quote Builder.

The contractor-facing surface of the supplier's Material Catalog. Each
contractor sees the supplier's full SKU list — but priced at THEIR assigned
tier only (the other two tiers are never returned over the wire).

Endpoints:
  GET  /api/contractor/quote-builder/catalog   — tier-priced material list
  POST /api/contractor/quote-builder/quotes    — create + persist a quote
  GET  /api/contractor/quote-builder/quotes    — list the contractor's quotes
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import api, contractor_only, db, now_iso

_DEFAULT_TIER = "tier2"
_VALID_TIERS = ("tier1", "tier2", "tier3")


class QuoteLineIn(BaseModel):
    material_id: str
    quantity: float = Field(gt=0)


class QuoteIn(BaseModel):
    title: str = "Untitled Quote"
    job_id: Optional[str] = None
    homeowner_name: Optional[str] = ""
    site_address: Optional[str] = ""
    markup_pct: float = Field(default=0.30, ge=0, le=2.0)
    lines: List[QuoteLineIn]
    notes: Optional[str] = ""


def _tier_price_field(tier: str) -> str:
    return {"tier1": "tier1_usd", "tier2": "tier2_usd", "tier3": "tier3_usd"}[tier]


async def _contractor_tier(contractor_id: str) -> str:
    u = await db.users.find_one({"id": contractor_id}, {"_id": 0, "assigned_tier": 1})
    t = (u or {}).get("assigned_tier")
    return t if t in _VALID_TIERS else _DEFAULT_TIER


def _public_material(m: Dict[str, Any], tier: str) -> Dict[str, Any]:
    """Strip the other two tiers so the contractor never sees them."""
    price_key = _tier_price_field(tier)
    return {
        "id": m["id"],
        "sku": m["sku"],
        "name": m["name"],
        "category": m.get("category", ""),
        "unit_label": m.get("unit_label", "Each"),
        "stock_units": m.get("stock_units", 0),
        "unit_price_usd": float(m.get(price_key, 0)),
        "tier": tier,
    }


@api.get("/contractor/quote-builder/catalog")
async def get_quote_builder_catalog(user=Depends(contractor_only)):
    tier = await _contractor_tier(user["id"])
    materials = await db.supplier_material_ledger.find({}, {"_id": 0}).sort("name", 1).to_list(length=500)
    return {
        "contractor_id": user["id"],
        "assigned_tier": tier,
        "tier_label": {"tier1": "Tier 1 · Builder", "tier2": "Tier 2 · Volume", "tier3": "Tier 3 · Enterprise"}[tier],
        "materials": [_public_material(m, tier) for m in materials],
        "as_of": now_iso(),
    }


@api.post("/contractor/quote-builder/quotes")
async def create_quote(body: QuoteIn, user=Depends(contractor_only)):
    if not body.lines:
        raise HTTPException(400, "Quote must include at least one line item.")
    tier = await _contractor_tier(user["id"])
    price_key = _tier_price_field(tier)

    # Validate optional job ownership
    if body.job_id:
        job = await db.jobs.find_one({"id": body.job_id, "contractor_id": user["id"]}, {"_id": 0, "id": 1})
        if not job:
            raise HTTPException(404, f"Job {body.job_id} not found in your portfolio.")

    # Resolve each line against the current catalog (defends against client tampering)
    material_ids = [ln.material_id for ln in body.lines]
    mats = await db.supplier_material_ledger.find(
        {"id": {"$in": material_ids}}, {"_id": 0},
    ).to_list(length=500)
    mats_by_id = {m["id"]: m for m in mats}

    resolved_lines: List[Dict[str, Any]] = []
    subtotal = 0.0
    for ln in body.lines:
        m = mats_by_id.get(ln.material_id)
        if not m:
            raise HTTPException(400, f"Unknown material {ln.material_id}")
        unit_price = float(m.get(price_key, 0))
        line_total = round(unit_price * float(ln.quantity), 2)
        subtotal += line_total
        resolved_lines.append({
            "material_id": m["id"],
            "sku": m["sku"],
            "name": m["name"],
            "category": m.get("category", ""),
            "unit_label": m.get("unit_label", "Each"),
            "quantity": float(ln.quantity),
            "unit_price_usd": unit_price,
            "line_total_usd": line_total,
        })

    subtotal = round(subtotal, 2)
    markup_usd = round(subtotal * float(body.markup_pct), 2)
    total = round(subtotal + markup_usd, 2)

    doc = {
        "id": f"quote-{uuid.uuid4().hex[:10]}",
        "contractor_id": user["id"],
        "contractor_email": user["email"],
        "title": body.title.strip() or "Untitled Quote",
        "job_id": body.job_id,
        "homeowner_name": (body.homeowner_name or "").strip(),
        "site_address": (body.site_address or "").strip(),
        "tier_used": tier,
        "lines": resolved_lines,
        "subtotal_usd": subtotal,
        "markup_pct": float(body.markup_pct),
        "markup_usd": markup_usd,
        "total_usd": total,
        "notes": (body.notes or "").strip(),
        "status": "draft",
        "created_at": now_iso(),
    }
    await db.contractor_quotes.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/contractor/quote-builder/quotes")
async def list_quotes(user=Depends(contractor_only)):
    docs = await db.contractor_quotes.find(
        {"contractor_id": user["id"]}, {"_id": 0},
    ).sort("created_at", -1).to_list(length=200)
    total_value = round(sum(float(d.get("total_usd", 0) or 0) for d in docs), 2)
    return {
        "count": len(docs),
        "total_value_usd": total_value,
        "quotes": docs,
    }
