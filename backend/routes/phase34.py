"""STRATEX™ — Phase 3/4 routes bundle.

Three new capability stacks live here so they can ship in one file:

  • storm-watcher manual trigger (admin demo button)
  • contractor_verify   – 3-contact verification wall for new contractors
  • gm_roster           – GM Brand Roster CRUD (Roofing · Gutters · Siding ·
                          Windows · Doors · Trim)
  • gm_inventory        – GM Pricing Inventory CRUD (SKU-level cost +
                          markup, optionally per-region)

All three collections live in MongoDB; ObjectIds are never returned —
records are always re-shaped through `_pub()` to a JSON-safe dict before
leaving the router.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

from core import db
from routes.storm_watcher import storm_watcher_sweep

router = APIRouter(prefix="/api", tags=["phase34"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pub(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Strip MongoDB ObjectId for safe JSON serialisation."""
    return {k: v for k, v in doc.items() if k != "_id"}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  STORM-WATCHER · MANUAL TRIGGER                                       ║
# ╚══════════════════════════════════════════════════════════════════════╝
@router.post("/passport/storm-tick")
async def storm_tick():
    """Force-run a storm-watcher sweep right now (useful for live demos)."""
    return await storm_watcher_sweep()


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PHASE 4 · CONTRACTOR 3-CONTACT VERIFICATION WALL                     ║
# ╚══════════════════════════════════════════════════════════════════════╝
class VerifyReference(BaseModel):
    name: str
    relationship: str = Field(..., description="Supplier / Past Client / GC / Inspector")
    phone: str
    email: Optional[EmailStr] = None
    years_known: Optional[int] = None
    notes: Optional[str] = None


class VerifyRefSubmit(BaseModel):
    contractor_email: EmailStr
    references: List[VerifyReference]


@router.get("/contractor/verify/status")
async def verify_status(contractor_email: str = Query(...)):
    coll = db["contractor_references"]
    rec = await coll.find_one({"contractor_email": contractor_email.lower()})
    if not rec:
        return {
            "contractor_email": contractor_email.lower(),
            "submitted": 0,
            "verified": 0,
            "required": 3,
            "unlocked": False,
            "references": [],
        }
    refs = rec.get("references", [])
    verified = sum(1 for r in refs if r.get("verified"))
    return {
        "contractor_email": rec["contractor_email"],
        "submitted": len(refs),
        "verified": verified,
        "required": 3,
        "unlocked": verified >= 3,
        "references": refs,
    }


@router.post("/contractor/verify/submit")
async def verify_submit(body: VerifyRefSubmit):
    """Submit the 3 references. They start `verified=false`; an admin
    (or the auto-verifier in this demo) flips them once outreach completes."""
    coll = db["contractor_references"]
    refs = [{
        **r.model_dump(),
        "verified":     False,
        "submitted_at": _now(),
        "verified_at":  None,
        "verifier":     None,
    } for r in body.references]
    rec = {
        "id": str(uuid.uuid4()),
        "contractor_email": body.contractor_email.lower(),
        "references": refs,
        "submitted_at": _now(),
        "unlocked": False,
    }
    await coll.replace_one(
        {"contractor_email": body.contractor_email.lower()},
        rec, upsert=True,
    )
    return _pub(rec)


@router.post("/contractor/verify/mark")
async def verify_mark(
    contractor_email: str = Query(...),
    reference_index: int = Query(..., ge=0, le=2),
    verifier: str = Query("STRATEX Verification Desk"),
):
    """Mark a single reference verified (admin/auto)."""
    coll = db["contractor_references"]
    rec = await coll.find_one({"contractor_email": contractor_email.lower()})
    if not rec:
        raise HTTPException(404, "no submission for this contractor")
    refs = rec.get("references", [])
    if reference_index >= len(refs):
        raise HTTPException(400, "reference_index out of range")
    refs[reference_index]["verified"] = True
    refs[reference_index]["verified_at"] = _now()
    refs[reference_index]["verifier"] = verifier
    unlocked = sum(1 for r in refs if r.get("verified")) >= 3
    await coll.update_one(
        {"contractor_email": contractor_email.lower()},
        {"$set": {"references": refs, "unlocked": unlocked}},
    )
    rec["references"] = refs
    rec["unlocked"] = unlocked
    return _pub(rec)


@router.post("/contractor/verify/seed-demo")
async def verify_seed_demo():
    """Seed the demo contractor (American Roofing / Anthony Cross) with
    3 verified references so they walk straight through the wall."""
    coll = db["contractor_references"]
    refs = [
        {"name": "Brian Holloway",  "relationship": "GAF Regional Supplier",
         "phone": "(859) 555-0117", "email": "bholloway@gaf.com",
         "years_known": 6, "notes": "Master Elite tier preferred",
         "verified": True, "submitted_at": _now(), "verified_at": _now(),
         "verifier": "STRATEX Verification Desk"},
        {"name": "Catherine Lyle",  "relationship": "Past Client",
         "phone": "(859) 555-0142", "email": "catherine.lyle@example.com",
         "years_known": 3, "notes": "Lyle Residence · re-roof 2023",
         "verified": True, "submitted_at": _now(), "verified_at": _now(),
         "verifier": "STRATEX Verification Desk"},
        {"name": "James Mott",      "relationship": "General Contractor",
         "phone": "(859) 555-0188", "email": "jmott@mottconstruction.co",
         "years_known": 9, "notes": "Sub for 12 commercial roofs",
         "verified": True, "submitted_at": _now(), "verified_at": _now(),
         "verifier": "STRATEX Verification Desk"},
    ]
    rec = {
        "id": str(uuid.uuid4()),
        "contractor_email": "anthony@americanroofing.co",
        "references": refs,
        "submitted_at": _now(),
        "unlocked": True,
    }
    await coll.replace_one(
        {"contractor_email": "anthony@americanroofing.co"},
        rec, upsert=True,
    )
    return _pub(rec)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PHASE 3a · GM BRAND ROSTER CRUD                                      ║
# ╚══════════════════════════════════════════════════════════════════════╝
MATERIAL_CATEGORIES = ["Roofing", "Gutters", "Siding", "Windows", "Doors", "Trim"]


class BrandIn(BaseModel):
    name: str
    category: Literal["Roofing", "Gutters", "Siding", "Windows", "Doors", "Trim"]
    preferred: bool = True
    tier: Optional[str] = "STANDARD"      # MASTER / PREMIER / STANDARD
    rep_name: Optional[str] = None
    rep_phone: Optional[str] = None
    rep_email: Optional[str] = None
    territory: Optional[str] = "Central KY"
    notes: Optional[str] = None


@router.get("/gm/roster")
async def list_roster(category: Optional[str] = Query(None)):
    coll = db["gm_brand_roster"]
    q: Dict[str, Any] = {}
    if category:
        q["category"] = category
    items = [_pub(d) async for d in coll.find(q).sort([("category", 1), ("name", 1)])]
    return {"count": len(items), "items": items}


@router.post("/gm/roster")
async def create_brand(body: BrandIn):
    coll = db["gm_brand_roster"]
    rec = {**body.model_dump(), "id": str(uuid.uuid4()),
           "created_at": _now(), "updated_at": _now()}
    await coll.insert_one(rec)
    return _pub(rec)


@router.patch("/gm/roster/{brand_id}")
async def update_brand(brand_id: str, body: BrandIn):
    coll = db["gm_brand_roster"]
    patch = {**body.model_dump(), "updated_at": _now()}
    res = await coll.update_one({"id": brand_id}, {"$set": patch})
    if res.matched_count == 0:
        raise HTTPException(404, "brand not found")
    return _pub(await coll.find_one({"id": brand_id}))


@router.delete("/gm/roster/{brand_id}")
async def delete_brand(brand_id: str):
    coll = db["gm_brand_roster"]
    res = await coll.delete_one({"id": brand_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "brand not found")
    return {"deleted": True, "id": brand_id}


@router.post("/gm/roster/seed-demo")
async def seed_roster_demo():
    """Pre-populate the roster with the same vendors visible on the Deck."""
    coll = db["gm_brand_roster"]
    await coll.delete_many({})
    seed_items = [
        ("GAF",          "Roofing",   "MASTER",   "Brian Holloway",  "(859) 555-0117"),
        ("Owens Corning","Roofing",   "PREMIER",  "Tomás Aguilar",   "(859) 555-0124"),
        ("CertainTeed",  "Roofing",   "STANDARD", "Karen Sutherland","(859) 555-0131"),
        ("LeafGuard",    "Gutters",   "PREMIER",  "Devon Lin",       "(859) 555-0146"),
        ("K-Style Pro",  "Gutters",   "STANDARD", "Maria Estrada",   "(859) 555-0151"),
        ("James Hardie", "Siding",    "MASTER",   "Cole Yeats",      "(859) 555-0163"),
        ("LP SmartSide", "Siding",    "PREMIER",  "Robin Hayes",     "(859) 555-0171"),
        ("Andersen",     "Windows",   "MASTER",   "Halima Khan",     "(859) 555-0185"),
        ("Pella",        "Windows",   "PREMIER",  "Mark Petros",     "(859) 555-0188"),
        ("Therma-Tru",   "Doors",     "PREMIER",  "Sasha Petrescu",  "(859) 555-0199"),
        ("Provia",       "Doors",     "STANDARD", "Bradley Niles",   "(859) 555-0202"),
        ("Royal Mldng.", "Trim",      "STANDARD", "Ines Castillo",   "(859) 555-0214"),
    ]
    for name, cat, tier, rep_name, phone in seed_items:
        await coll.insert_one({
            "id": str(uuid.uuid4()),
            "name": name, "category": cat, "preferred": True,
            "tier": tier, "rep_name": rep_name, "rep_phone": phone,
            "rep_email": f"{rep_name.lower().replace(' ','.')}@{name.lower().replace(' ','').replace('.','')}.com",
            "territory": "Central KY", "notes": "",
            "created_at": _now(), "updated_at": _now(),
        })
    return {"seeded": len(seed_items)}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  PHASE 3b · GM PRICING INVENTORY CRUD                                 ║
# ╚══════════════════════════════════════════════════════════════════════╝
class InventoryIn(BaseModel):
    brand: str
    category: Literal["Roofing", "Gutters", "Siding", "Windows", "Doors", "Trim"]
    sku: str
    description: str
    unit: str = "ea"                  # ea / sq / lf / pcs
    cost_usd: float
    markup_pct: float = 25.0          # default O&P band lower bound
    region: str = "Central KY"
    in_stock: bool = True


@router.get("/gm/inventory")
async def list_inventory(category: Optional[str] = None, brand: Optional[str] = None):
    coll = db["gm_pricing_inventory"]
    q: Dict[str, Any] = {}
    if category:
        q["category"] = category
    if brand:
        q["brand"] = brand
    items = []
    async for d in coll.find(q).sort([("category", 1), ("brand", 1), ("sku", 1)]):
        d2 = _pub(d)
        d2["sell_price_usd"] = round(d2["cost_usd"] * (1 + d2["markup_pct"] / 100), 2)
        items.append(d2)
    return {"count": len(items), "items": items}


@router.post("/gm/inventory")
async def create_inventory(body: InventoryIn):
    coll = db["gm_pricing_inventory"]
    rec = {**body.model_dump(), "id": str(uuid.uuid4()),
           "created_at": _now(), "updated_at": _now()}
    await coll.insert_one(rec)
    return _pub(rec)


@router.patch("/gm/inventory/{item_id}")
async def update_inventory(item_id: str, body: InventoryIn):
    coll = db["gm_pricing_inventory"]
    patch = {**body.model_dump(), "updated_at": _now()}
    res = await coll.update_one({"id": item_id}, {"$set": patch})
    if res.matched_count == 0:
        raise HTTPException(404, "inventory item not found")
    return _pub(await coll.find_one({"id": item_id}))


@router.delete("/gm/inventory/{item_id}")
async def delete_inventory(item_id: str):
    coll = db["gm_pricing_inventory"]
    res = await coll.delete_one({"id": item_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "inventory item not found")
    return {"deleted": True, "id": item_id}


@router.post("/gm/inventory/seed-demo")
async def seed_inventory_demo():
    coll = db["gm_pricing_inventory"]
    await coll.delete_many({})
    seed_items = [
        ("GAF",          "Roofing",  "GAF-TLR-CHR", "Timberline HDZ · Charcoal",            "sq",  118.50, 30),
        ("GAF",          "Roofing",  "GAF-STR-LCK", "Pro-Start Starter Strip · Lock-in",    "lf",    0.62, 35),
        ("Owens Corning","Roofing",  "OC-DUR-BLK",  "Duration · Onyx Black",                 "sq",  112.00, 28),
        ("CertainTeed",  "Roofing",  "CT-LMT-MOS",  "Landmark · Moire Black",                "sq",  108.75, 26),
        ("LeafGuard",    "Gutters",  "LG-K05-WHT",  "Seamless 5\" K-Style · White",          "lf",   12.40, 32),
        ("James Hardie", "Siding",   "JH-LAP-IRN",  "HardiePlank Lap · Iron Gray",            "sq",  385.00, 28),
        ("LP SmartSide", "Siding",   "LP-EXP-WAL",  "Expert Finish · Walnut",                 "sq",  342.00, 25),
        ("Andersen",     "Windows",  "AND-400-30",  "400 Series Tilt-Wash · 30×54 White",     "ea",  624.00, 22),
        ("Pella",        "Windows",  "PEL-RES-32",  "Reserve Trad · 32×60 Black",             "ea",  848.00, 24),
        ("Therma-Tru",   "Doors",    "TT-S206-OAK", "Smooth-Star S206 · Oak Stain",           "ea",  712.00, 26),
        ("Provia",       "Doors",    "PV-EMB-BLU",  "Embarq Fiberglass · Twilight Blue",      "ea",  945.00, 24),
        ("Royal Mldng.", "Trim",     "RM-J34",      "J-Channel 3/4\" · Vinyl",                "lf",    1.18, 35),
        ("Royal Mldng.", "Trim",     "RM-F50",      "F-Channel 1/2\" · Soffit Receiver",      "lf",    1.42, 35),
    ]
    for brand, cat, sku, desc, unit, cost, mk in seed_items:
        await coll.insert_one({
            "id": str(uuid.uuid4()),
            "brand": brand, "category": cat, "sku": sku, "description": desc,
            "unit": unit, "cost_usd": cost, "markup_pct": mk,
            "region": "Central KY", "in_stock": True,
            "created_at": _now(), "updated_at": _now(),
        })
    return {"seeded": len(seed_items)}
