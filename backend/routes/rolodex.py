"""STRATEX™ GM Rolodex — lead conversion REST surface.

Pure addition (preservation lock). Wraps `GM_RolodexEngine` over MongoDB so
the demo state survives restarts. Pairs with `regional_switchboard.py` —
same 8 store territories.

Endpoints (mounted on shared /api router):
  GET  /api/rolodex                                  — all stores + funnel totals
  GET  /api/rolodex/{store_territory}                — single store
  POST /api/rolodex/discover                         — register a new target
  POST /api/rolodex/convert                          — promote target → active (first invoice)
  POST /api/rolodex/seed                             — admin/CEO idempotent demo seed
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from core import api, current_user, db, now_iso

ROLODEX_COLLECTION = "rolodex_accounts"


async def _ceo_or_admin(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"ceo", "admin"}:
        raise HTTPException(403, "Executive clearance required")
    return user


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DiscoverBody(BaseModel):
    store_territory: str
    company_name: str
    trade_scope: str
    city: str
    assigned_rep: Optional[str] = None


class ConvertBody(BaseModel):
    store_territory: str
    company_name: str
    initial_invoice_value: float


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api.get("/rolodex")
async def rolodex_all(user=Depends(_ceo_or_admin)):
    """Roll up every store's rolodex with national funnel totals."""
    await seed_rolodex_demo()
    cursor = db[ROLODEX_COLLECTION].find({}, {"_id": 0})
    accounts = await cursor.to_list(length=1000)

    by_store: Dict[str, Dict[str, Any]] = {}
    for a in accounts:
        terr = a["store_territory"]
        by_store.setdefault(terr, {
            "store_territory": terr, "default_rep": a.get("assigned_rep"),
            "targets": [], "active": [],
        })
        (by_store[terr]["active"] if a["conversion_invoiced"] else by_store[terr]["targets"]).append(a)

    stores = sorted(by_store.values(), key=lambda s: s["store_territory"])
    totals_targets = sum(len(s["targets"]) for s in stores)
    totals_active = sum(len(s["active"]) for s in stores)
    pipeline_value = sum(
        (a.get("estimated_pipeline_value") or 0)
        for s in stores for a in s["targets"]
    )
    recognized_ytd = sum(
        (a.get("initial_order_value") or 0)
        for s in stores for a in s["active"]
    )
    conv_rate = round(
        (totals_active / (totals_targets + totals_active)) * 100, 1
    ) if (totals_targets + totals_active) else 0.0

    return {
        "stores": stores,
        "totals": {
            "targets": totals_targets,
            "active": totals_active,
            "conversion_pct": conv_rate,
            "pipeline_value": pipeline_value,
            "recognized_ytd": recognized_ytd,
        },
    }


@api.get("/rolodex/{store_territory}")
async def rolodex_store(store_territory: str, user=Depends(_ceo_or_admin)):
    await seed_rolodex_demo()
    cursor = db[ROLODEX_COLLECTION].find(
        {"store_territory": store_territory}, {"_id": 0}
    )
    accounts = await cursor.to_list(length=500)
    if not accounts:
        raise HTTPException(404, f"No rolodex data for {store_territory}")
    targets = [a for a in accounts if not a["conversion_invoiced"]]
    active = [a for a in accounts if a["conversion_invoiced"]]
    return {
        "store_territory": store_territory,
        "targets": targets,
        "active": active,
    }


@api.post("/rolodex/discover")
async def rolodex_discover(body: DiscoverBody, user=Depends(_ceo_or_admin)):
    """Register a newly-discovered contractor (idempotent on company_name)."""
    existing = await db[ROLODEX_COLLECTION].find_one(
        {"store_territory": body.store_territory, "company_name": body.company_name},
    )
    if existing:
        existing.pop("_id", None)
        return {"already_present": True, **existing}

    rep = body.assigned_rep or _DEFAULT_REPS.get(body.store_territory, "James Johnson")
    doc = {
        "store_territory": body.store_territory,
        "company_name": body.company_name,
        "scope": body.trade_scope,
        "city": body.city,
        "assigned_rep": rep,
        "conversion_invoiced": False,
        "discovered_at": now_iso(),
        "estimated_pipeline_value": 0,
    }
    await db[ROLODEX_COLLECTION].insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.post("/rolodex/convert")
async def rolodex_convert(body: ConvertBody, user=Depends(_ceo_or_admin)):
    """Promote a target → active customer by recording the first invoice."""
    res = await db[ROLODEX_COLLECTION].find_one_and_update(
        {"store_territory": body.store_territory, "company_name": body.company_name,
         "conversion_invoiced": False},
        {"$set": {
            "conversion_invoiced": True,
            "initial_order_value": body.initial_invoice_value,
            "converted_at": now_iso(),
            "converted_by": user.get("email"),
        }},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(404, f"No open target {body.company_name} in {body.store_territory}")
    return res


@api.post("/rolodex/seed")
async def rolodex_seed(user=Depends(_ceo_or_admin)):
    return await seed_rolodex_demo(force=True)


# ---------------------------------------------------------------------------
# Seed data — pairs with the 8 Regional Switchboard stores
# ---------------------------------------------------------------------------

_DEFAULT_REPS = {
    "Lexington_KY-FLAGSHIP": "James Johnson",
    "Louisville_KY-002": "Dana Reyes",
    "BowlingGreen_KY-003": "Avery Crane",
    "Cincinnati_OH-101": "Marcus Webb",
    "Columbus_OH-102": "Lena Park",
    "Nashville_TN-201": "Wendy Cho",
    "Knoxville_TN-202": "Tessa Quinn",
    "Indianapolis_IN-301": "Casey Lin",
}

SCOPES = [
    "Residential Re-Roof", "Commercial TPO", "Storm Restoration",
    "Multi-Family", "Solar Integration", "Insurance Restoration",
    "Standing Seam Metal",
]

# 4 targets + 1 active per store = 32 targets + 8 actives across the network.
_SEED_TARGETS = {
    "Lexington_KY-FLAGSHIP": [
        ("Apex Roofing of Kentucky",   "Residential Re-Roof",   "Lexington",     185000, True,  42180.10),
        ("Bluegrass Roofing Co.",      "Multi-Family",          "Lexington",     412000, False, None),
        ("Stonepath Builders",         "Insurance Restoration", "Versailles",    96000,  False, None),
        ("Cardinal Hill Exteriors",    "Storm Restoration",     "Lexington",     145000, False, None),
        ("Beaumont Trade Group",       "Commercial TPO",        "Lexington",     228000, False, None),
    ],
    "Louisville_KY-002": [
        ("Derby City Roofworks",       "Residential Re-Roof",   "Louisville",    140000, True,  31420.50),
        ("Highlands Premier Builders", "Multi-Family",          "St. Matthews",  310000, False, None),
        ("Falls Cities Exteriors",     "Storm Restoration",     "Jeffersontown", 92000,  False, None),
        ("Bardstown Solar+Roof",       "Solar Integration",     "Bardstown",     208000, False, None),
    ],
    "BowlingGreen_KY-003": [
        ("Warren County Builders",     "Insurance Restoration", "Bowling Green", 88000,  True,  19250.00),
        ("Plano Ridge Roofing",        "Residential Re-Roof",   "Plano",         71000,  False, None),
        ("Greenwood Trade Group",      "Commercial TPO",        "Bowling Green", 160000, False, None),
    ],
    "Cincinnati_OH-101": [
        ("Queen City Roof+Solar",      "Solar Integration",     "Cincinnati",    245000, True,  58910.00),
        ("Eastgate Property Services", "Multi-Family",          "Eastgate",      298000, False, None),
        ("Mt. Adams Restorations",     "Insurance Restoration", "Cincinnati",    132000, False, None),
        ("Anderson Storm Crew",        "Storm Restoration",     "Anderson",      118000, False, None),
    ],
    "Columbus_OH-102": [
        ("Arch City Roofing",          "Standing Seam Metal",   "Columbus",      176000, True,  44800.20),
        ("Dublin Premier Exteriors",   "Residential Re-Roof",   "Dublin",        201000, False, None),
        ("Polaris Trade Group",        "Commercial TPO",        "Polaris",       310000, False, None),
    ],
    "Nashville_TN-201": [
        ("Music City Roofing",         "Residential Re-Roof",   "Nashville",     162000, True,  38670.00),
        ("Brentwood Storm Restore",    "Storm Restoration",     "Brentwood",     142000, False, None),
        ("Bellevue Solar+Roof",        "Solar Integration",     "Bellevue",      218000, False, None),
        ("Tennessee Trade Co.",        "Commercial TPO",        "Nashville",     265000, False, None),
    ],
    "Knoxville_TN-202": [
        ("Smoky Mountain Roof Co.",    "Residential Re-Roof",   "Knoxville",     104000, True,  22980.00),
        ("Sequoyah Hills Builders",    "Multi-Family",          "Knoxville",     188000, False, None),
        ("West Hills Insurance Roof",  "Insurance Restoration", "Knoxville",     95000,  False, None),
    ],
    "Indianapolis_IN-301": [
        ("Circle City Roofworks",      "Residential Re-Roof",   "Indianapolis",  198000, True,  47620.80),
        ("Carmel Storm Restoration",   "Storm Restoration",     "Carmel",        152000, False, None),
        ("Fishers Premier Exteriors",  "Multi-Family",          "Fishers",       272000, False, None),
        ("Speedway Solar+Roof",        "Solar Integration",     "Speedway",      189000, False, None),
    ],
}


async def seed_rolodex_demo(force: bool = False) -> Dict[str, Any]:
    """Idempotent: hydrate `rolodex_accounts` with ~32 targets + 8 active customers."""
    if force:
        await db[ROLODEX_COLLECTION].delete_many({})

    existing = await db[ROLODEX_COLLECTION].count_documents({})
    if existing > 0 and not force:
        return {"seeded": False, "count": existing}

    docs = []
    for territory, rows in _SEED_TARGETS.items():
        rep = _DEFAULT_REPS.get(territory, "James Johnson")
        for company, scope, city, pipeline, active, initial in rows:
            d = {
                "store_territory": territory,
                "company_name": company,
                "scope": scope,
                "city": city,
                "assigned_rep": rep,
                "conversion_invoiced": active,
                "estimated_pipeline_value": pipeline,
                "discovered_at": now_iso(),
            }
            if active:
                d["initial_order_value"] = initial
                d["converted_at"] = now_iso()
            docs.append(d)

    if docs:
        await db[ROLODEX_COLLECTION].insert_many(docs)
    return {"seeded": True, "count": len(docs)}
