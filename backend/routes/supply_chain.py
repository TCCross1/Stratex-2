"""STRATEX™ CEO · Supply Chain Pipeline + Inventory rollup.

Powers the 5 bottom-dock destinations of the CEO Command Center:

  /ceo/leads             — NEW CLIENTS / SALES (status=lead)
  /ceo/orders/build      — ORDERS TO BUILD     (status=to_build)
  /ceo/orders/ready      — ORDERS READY         (status=ready)
  /ceo/orders/shipped    — ORDERS SHIPPED       (status=shipped)
  /ceo/inventory         — COMPLETE INVENTORY COST aggregate

A single Mongo collection (`supply_orders`) tracks the entire lifecycle:
   lead → to_build → ready → shipped

The pipeline is intentionally CEO-scope (no contractor / operator can see it).
Each `POST /api/ceo/orders/{order_id}/advance` moves the order to the next
status; the API never rolls back, never deletes.

Inventory aggregate composes the supplier material ledger × current
stock_units to produce a landed-cost rollup, broken down by category.
"""
from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import api, ceo_only, db, now_iso

ORDER_STATUSES = ("lead", "to_build", "ready", "shipped")
NEXT_STATUS = {"lead": "to_build", "to_build": "ready", "ready": "shipped"}

DEMO_CONTRACTORS = [
    {"company": "Apex Local Builders",   "contact": "Anthony Cross", "phone": "859-555-0142"},
    {"company": "Bluegrass Roofing Co.", "contact": "Marcus Lee",    "phone": "859-555-0167"},
    {"company": "Preciso Builders",      "contact": "Diana Ortiz",   "phone": "859-555-0173"},
    {"company": "Digital Builders",      "contact": "Sam Patel",     "phone": "859-555-0188"},
    {"company": "Crown Roofing",         "contact": "John Whitaker", "phone": "859-555-0199"},
]
DEMO_ADDRESSES = [
    "1247 Bluegrass Pkwy, Lexington, KY 40503",
    "885 Tates Creek Rd, Lexington, KY 40502",
    "2210 Versailles Rd, Lexington, KY 40504",
    "601 Limestone St, Lexington, KY 40508",
    "1990 Harrodsburg Rd, Lexington, KY 40503",
]
DEMO_SKUS = [
    ("SHINGLE-PREM-SQ", "Premium Architectural Shingles", 34.5, "Square"),
    ("FELT-SYN-15", "Synthetic Felt #15 Underlayment", 92.0, "Roll"),
    ("IWS-SELF-2SQ", "Self-Adhering Ice & Water Shield", 115.0, "Roll"),
    ("DRIP-ALU-LF", "Aluminum Drip Edge Trim", 2.1, "Linear Ft"),
    ("FLASH-STEP-LF", "Wall Step Flashing Metal", 4.5, "Linear Ft"),
    ("CHIMNEY-KIT", "Chimney Roll Flashing Kit", 85.0, "Kit"),
    ("BOOT-2IN", "Roof Pipe Boot 2-in", 18.0, "Each"),
    ("FAST-COIL-7200", "1-1/4 Coil Roofing Fasteners 7200 ct", 75.0, "Box"),
]


# ---------------------------------------------------------------------------
# Seed (idempotent)
# ---------------------------------------------------------------------------

async def seed_supply_orders() -> Dict[str, int]:
    """Seed ~15 orders distributed across the 4 statuses so the pipeline
    pages have content from a cold-boot. Idempotent — exits if any
    supply_order already exists."""
    existing = await db.supply_orders.count_documents({})
    if existing > 0:
        return {"existing": existing, "inserted": 0}

    rng = random.Random(20260531)
    docs: List[Dict[str, Any]] = []
    # 4 leads, 4 to_build, 3 ready, 4 shipped
    for status, count in [("lead", 4), ("to_build", 4), ("ready", 3), ("shipped", 4)]:
        for i in range(count):
            contractor = rng.choice(DEMO_CONTRACTORS)
            address = rng.choice(DEMO_ADDRESSES)
            line_count = rng.randint(2, 4)
            line_items: List[Dict[str, Any]] = []
            subtotal = 0.0
            for _ in range(line_count):
                sku, name, price, unit = rng.choice(DEMO_SKUS)
                qty = rng.randint(2, 12)
                line_total = round(qty * price, 2)
                subtotal += line_total
                line_items.append({
                    "sku": sku, "name": name, "unit_price_usd": price,
                    "unit_label": unit, "quantity": qty, "line_total_usd": line_total,
                })
            order_id = str(uuid.uuid4())
            stamp = (datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 18))).isoformat()
            docs.append({
                "id": order_id,
                "order_code": f"ORD-KY-{1000 + len(docs) + 1:04d}",
                "status": status,
                "contractor_company": contractor["company"],
                "contractor_contact": contractor["contact"],
                "contractor_phone": contractor["phone"],
                "site_address": address,
                "line_items": line_items,
                "subtotal_usd": round(subtotal, 2),
                "tax_usd": round(subtotal * 0.06, 2),
                "total_usd": round(subtotal * 1.06, 2),
                "estimated_ship_date": (datetime.now(timezone.utc) + timedelta(days=rng.randint(2, 9))).date().isoformat(),
                "created_at": stamp,
                "last_advanced_at": stamp,
                "history": [{"to_status": status, "at": stamp, "by": "seed"}],
            })

    if docs:
        await db.supply_orders.insert_many(docs)
    await db.supply_orders.create_index("status")
    await db.supply_orders.create_index("order_code", unique=True)
    return {"existing": 0, "inserted": len(docs)}


# ---------------------------------------------------------------------------
# Pipeline endpoints
# ---------------------------------------------------------------------------

@api.get("/ceo/orders")
async def list_orders(status: str = "lead", user=Depends(ceo_only)) -> Dict[str, Any]:
    """List orders filtered by pipeline status (lead | to_build | ready | shipped)."""
    if status not in ORDER_STATUSES:
        raise HTTPException(400, f"status must be one of {ORDER_STATUSES}")
    rows: List[Dict[str, Any]] = []
    async for o in db.supply_orders.find({"status": status}, {"_id": 0}).sort("created_at", -1):
        rows.append(o)
    # roll-up
    total_value = sum((float(o.get("total_usd") or 0) for o in rows), 0.0)
    total_units = sum(
        sum((li.get("quantity") or 0) for li in (o.get("line_items") or [])) for o in rows
    )
    counts_by_status: Dict[str, int] = {}
    for s in ORDER_STATUSES:
        counts_by_status[s] = await db.supply_orders.count_documents({"status": s})
    return {
        "status": status,
        "rows": rows,
        "totals": {"row_count": len(rows), "total_value_usd": total_value, "total_units": total_units},
        "counts_by_status": counts_by_status,
    }


class AdvanceOrderBody(BaseModel):
    note: Optional[str] = None


@api.post("/ceo/orders/{order_id}/advance")
async def advance_order(order_id: str, body: AdvanceOrderBody, user=Depends(ceo_only)) -> Dict[str, Any]:
    """Advance an order to the next pipeline status. No-op if already shipped."""
    o = await db.supply_orders.find_one({"id": order_id}, {"_id": 0})
    if not o:
        raise HTTPException(404, "Order not found")
    cur = o.get("status")
    nxt = NEXT_STATUS.get(cur)
    if not nxt:
        raise HTTPException(400, f"Order already at terminal status '{cur}'")
    entry = {"to_status": nxt, "at": now_iso(), "by": user["email"], "note": body.note or ""}
    await db.supply_orders.update_one(
        {"id": order_id},
        {"$set": {"status": nxt, "last_advanced_at": now_iso()}, "$push": {"history": entry}},
    )
    return {"order_id": order_id, "from": cur, "to": nxt, "history_entry": entry}


# ---------------------------------------------------------------------------
# Complete inventory cost rollup
# ---------------------------------------------------------------------------

@api.get("/ceo/inventory/cost-rollup")
async def inventory_cost_rollup(user=Depends(ceo_only)) -> Dict[str, Any]:
    """Aggregate landed cost of supplier inventory currently on hand. Groups by
    category. Uses tier_1 wholesale × stock_units as the landed-cost basis."""
    rows: List[Dict[str, Any]] = []
    by_category: Dict[str, Dict[str, Any]] = {}
    total_value = 0.0
    total_units = 0
    flagged = 0

    async for m in db.supplier_material_ledger.find({}, {"_id": 0}):
        stock = int(m.get("stock_units") or 0)
        unit_cost = float(m.get("tier_1_price_usd") or m.get("tier1_usd") or 0)
        landed = round(stock * unit_cost, 2)
        cat = m.get("category") or "Uncategorized"
        reorder = int(m.get("reorder_threshold") or 0)
        is_critical = reorder and stock <= reorder
        if is_critical:
            flagged += 1
        rows.append({
            "sku": m.get("sku"),
            "name": m.get("name"),
            "category": cat,
            "unit_label": m.get("unit_label"),
            "unit_cost_usd": unit_cost,
            "stock_units": stock,
            "landed_cost_usd": landed,
            "reorder_threshold": reorder,
            "is_critical": is_critical,
        })
        total_value += landed
        total_units += stock
        bucket = by_category.setdefault(cat, {"category": cat, "skus": 0, "units": 0, "landed_cost_usd": 0.0})
        bucket["skus"] += 1
        bucket["units"] += stock
        bucket["landed_cost_usd"] += landed

    cats = sorted(by_category.values(), key=lambda c: c["landed_cost_usd"], reverse=True)
    for c in cats:
        c["landed_cost_usd"] = round(c["landed_cost_usd"], 2)
        c["share_pct"] = round((c["landed_cost_usd"] / total_value * 100) if total_value > 0 else 0, 2)
    rows.sort(key=lambda r: r["landed_cost_usd"], reverse=True)

    return {
        "generated_at": now_iso(),
        "totals": {
            "sku_count": len(rows),
            "total_units": total_units,
            "total_landed_value_usd": round(total_value, 2),
            "critical_count": flagged,
        },
        "by_category": cats,
        "rows": rows,
    }
