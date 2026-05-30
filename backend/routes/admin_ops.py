"""STRATEX Admin Ops Command — supplier-side control room.

Three operational surfaces for the roofing-material supplier (platform tenant)
who offers STRATEX to their contractor customers:

  1. Fleet Allocation       — assign hardware drone nodes (NODE-ALPHA, NODE-GAMMA…)
                              to contractor leads (pending jobs awaiting capture).
  2. Supplier Material Catalog — global SKU ledger with Tier-1/2/3 wholesale pricing.
                              Each contractor account is assigned a tier; the
                              supplier controls the matrix, contractors see only
                              their tier.
  3. Account Coverage       — supplier sales reps, monthly quotas vs. realized
                              volume, and the contractor accounts each rep owns.

All three persist to Mongo. Seeded idempotently on startup via `seed_admin_ops`.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import admin_only, api, db, now_iso

# ---------------------------------------------------------------------------
# Seed data — Central-KY supplier launch portfolio
# ---------------------------------------------------------------------------
SEED_HARDWARE_NODES = [
    {"id": "node-alpha",   "label": "NODE-ALPHA",   "status": "available", "dock_address": "Trailer Rig 01 · Lexington Depot"},
    {"id": "node-beta",    "label": "NODE-BETA",    "status": "available", "dock_address": "Trailer Rig 02 · Lexington Depot"},
    {"id": "node-gamma",   "label": "NODE-GAMMA",   "status": "available", "dock_address": "Trailer Rig 03 · Versailles Sub-Depot"},
    {"id": "node-delta",   "label": "NODE-DELTA",   "status": "available", "dock_address": "Trailer Rig 04 · Nicholasville Sub-Depot"},
    {"id": "node-epsilon", "label": "NODE-EPSILON", "status": "maintenance", "dock_address": "Trailer Rig 05 · Service Bay"},
]

SEED_MATERIAL_LEDGER = [
    {"id": "mat-arch-shingle",      "sku": "ARCH-LAM-30YR", "name": "Architectural Laminate Shingles",
     "category": "Shingles", "unit_label": "Bundle", "stock_units": 1420,
     "tier1_usd": 34.50, "tier2_usd": 31.00, "tier3_usd": 28.50},
    {"id": "mat-synth-underlayment","sku": "SYNTH-UND-10SQ","name": "High-Performance Synthetic Underlayment",
     "category": "Underlayment", "unit_label": "Roll (10 sq)", "stock_units": 340,
     "tier1_usd": 92.00, "tier2_usd": 85.00, "tier3_usd": 78.00},
    {"id": "mat-ice-water-shield",  "sku": "IWS-SELF-2SQ", "name": "Self-Adhering Ice & Water Shield",
     "category": "Underlayment", "unit_label": "Roll (2 sq)", "stock_units": 180,
     "tier1_usd": 115.00, "tier2_usd": 104.00, "tier3_usd": 95.00},
    {"id": "mat-eave-starter",      "sku": "STARTER-EAVE", "name": "Pro-Series Eave Starter Strips",
     "category": "Accessories", "unit_label": "Linear Ft", "stock_units": 8500,
     "tier1_usd": 2.10, "tier2_usd": 1.85, "tier3_usd": 1.60},
    {"id": "mat-ridge-cap",         "sku": "RIDGE-CAP-25", "name": "Hip & Ridge Cap Shingles",
     "category": "Shingles", "unit_label": "Bundle (25 lf)", "stock_units": 620,
     "tier1_usd": 58.00, "tier2_usd": 52.00, "tier3_usd": 47.50},
    {"id": "mat-drip-edge",         "sku": "DRIP-ALU-10", "name": "Aluminum Drip Edge",
     "category": "Accessories", "unit_label": "10 ft section", "stock_units": 2100,
     "tier1_usd": 12.40, "tier2_usd": 11.10, "tier3_usd": 9.95},
]

SEED_SALES_REPS = [
    {"id": "rep-mvance",   "name": "Marcus Vance",   "email": "mvance@stratex.io",
     "monthly_quota_usd": 250_000, "current_volume_usd": 142_000,
     "territory": "Fayette · Jessamine · Woodford"},
    {"id": "rep-erostova", "name": "Elena Rostova",  "email": "erostova@stratex.io",
     "monthly_quota_usd": 250_000, "current_volume_usd": 198_000,
     "territory": "Bourbon · Scott · Clark"},
    {"id": "rep-tharper",  "name": "Tobias Harper",  "email": "tharper@stratex.io",
     "monthly_quota_usd": 200_000, "current_volume_usd": 87_500,
     "territory": "Madison · Garrard · Lincoln"},
]

# Contractor → (tier, rep) initial mapping. The contractor accounts themselves
# already exist in db.users (seeded by stratex_auth seed). We layer the
# supplier-side metadata onto them via this map.
SEED_CONTRACTOR_OPS = {
    "anthony@apexroofing.com": {"assigned_tier": "tier2", "assigned_rep_id": "rep-mvance"},
    "john@crownroofing.com":   {"assigned_tier": "tier3", "assigned_rep_id": "rep-erostova"},
}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
TierLiteral = Literal["tier1", "tier2", "tier3"]


class MaterialIn(BaseModel):
    sku: str
    name: str
    category: str = "Shingles"
    unit_label: str = "Each"
    stock_units: int = 0
    tier1_usd: float
    tier2_usd: float
    tier3_usd: float


class SalesRepIn(BaseModel):
    name: str
    email: Optional[str] = ""
    monthly_quota_usd: float = 250_000
    territory: Optional[str] = ""


class NodeAssignBody(BaseModel):
    node_id: str
    job_id: str


class TierAssignBody(BaseModel):
    tier: TierLiteral


class RepAssignBody(BaseModel):
    rep_id: str


# ---------------------------------------------------------------------------
# Seed function — called once on app startup
# ---------------------------------------------------------------------------
async def seed_admin_ops() -> Dict[str, int]:
    """Idempotent seed of hardware_nodes + supplier_material_ledger + sales_reps
    + per-contractor tier/rep assignment. Safe to call repeatedly.
    """
    for n in SEED_HARDWARE_NODES:
        await db.hardware_nodes.update_one(
            {"id": n["id"]},
            {"$set": {**n, "seeded_at": now_iso()}, "$setOnInsert": {"assigned_job_id": None}},
            upsert=True,
        )
    for m in SEED_MATERIAL_LEDGER:
        await db.supplier_material_ledger.update_one(
            {"id": m["id"]},
            {"$set": {**m, "seeded_at": now_iso()}},
            upsert=True,
        )
    for r in SEED_SALES_REPS:
        await db.sales_reps.update_one(
            {"id": r["id"]},
            {"$set": {**r, "seeded_at": now_iso()}},
            upsert=True,
        )
    for email, ops in SEED_CONTRACTOR_OPS.items():
        await db.users.update_one(
            {"email": email},
            {"$set": ops},
        )
    return {
        "nodes": len(SEED_HARDWARE_NODES),
        "materials": len(SEED_MATERIAL_LEDGER),
        "reps": len(SEED_SALES_REPS),
        "contractor_ops": len(SEED_CONTRACTOR_OPS),
    }


# ---------------------------------------------------------------------------
# Dashboard — single call, full payload (fast paint)
# ---------------------------------------------------------------------------
@api.get("/admin/ops/dashboard")
async def admin_ops_dashboard(user=Depends(admin_only)):
    """One call returns everything the /admin/ops page needs."""
    nodes = await db.hardware_nodes.find({}, {"_id": 0}).sort("label", 1).to_list(length=200)
    materials = await db.supplier_material_ledger.find({}, {"_id": 0}).sort("name", 1).to_list(length=500)
    reps = await db.sales_reps.find({}, {"_id": 0}).sort("name", 1).to_list(length=200)

    contractors = await db.users.find(
        {"role": "contractor"},
        {"_id": 0, "id": 1, "email": 1, "company_name": 1, "legal_name": 1,
         "assigned_tier": 1, "assigned_rep_id": 1, "subscription_tier": 1, "subscription_status": 1},
    ).sort("company_name", 1).to_list(length=500)

    # Pull pending jobs (the "lead vectors") with optional already-assigned node.
    pending_jobs = await db.jobs.find(
        {"status": {"$in": ["PENDING_FIELD_CAPTURE", "DRAFT"]}},
        {"_id": 0, "id": 1, "contractor_id": 1, "site_address": 1, "client_name": 1,
         "assigned_node_id": 1, "status": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(length=500)

    # Bucket pending jobs by contractor for the table
    jobs_by_contractor: Dict[str, List[Dict[str, Any]]] = {}
    for j in pending_jobs:
        jobs_by_contractor.setdefault(j.get("contractor_id"), []).append({
            "job_id": j.get("id"),
            "address": j.get("site_address") or "—",
            "client_name": j.get("client_name") or "—",
            "assigned_node_id": j.get("assigned_node_id"),
            "status": j.get("status"),
        })

    contractor_rows = []
    for c in contractors:
        cid = c.get("id")
        contractor_rows.append({
            **c,
            "leads": jobs_by_contractor.get(cid, []),
            "lead_count": len(jobs_by_contractor.get(cid, [])),
        })

    available_nodes = [n for n in nodes if n.get("status") == "available" and not n.get("assigned_job_id")]

    return {
        "generated_at": now_iso(),
        "hardware_nodes": nodes,
        "available_node_count": len(available_nodes),
        "materials": materials,
        "sales_reps": reps,
        "contractors": contractor_rows,
        "summary": {
            "contractor_count": len(contractors),
            "lead_count": len(pending_jobs),
            "node_total": len(nodes),
            "node_available": len(available_nodes),
            "material_skus": len(materials),
            "rep_count": len(reps),
        },
    }


# ---------------------------------------------------------------------------
# Material Ledger — full CRUD
# ---------------------------------------------------------------------------
@api.post("/admin/ops/materials")
async def create_material(body: MaterialIn, user=Depends(admin_only)):
    doc = {
        "id": f"mat-{uuid.uuid4().hex[:10]}",
        **body.model_dump(),
        "created_at": now_iso(),
        "created_by": user["email"],
    }
    await db.supplier_material_ledger.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/admin/ops/materials/{material_id}")
async def update_material(material_id: str, body: MaterialIn, user=Depends(admin_only)):
    res = await db.supplier_material_ledger.update_one(
        {"id": material_id},
        {"$set": {**body.model_dump(), "updated_at": now_iso(), "updated_by": user["email"]}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, f"material {material_id} not found")
    return {"ok": True, "material_id": material_id}


@api.delete("/admin/ops/materials/{material_id}")
async def delete_material(material_id: str, user=Depends(admin_only)):
    res = await db.supplier_material_ledger.delete_one({"id": material_id})
    if res.deleted_count == 0:
        raise HTTPException(404, f"material {material_id} not found")
    return {"ok": True, "material_id": material_id, "purged_at": now_iso()}


# ---------------------------------------------------------------------------
# Sales Reps
# ---------------------------------------------------------------------------
@api.post("/admin/ops/sales-reps")
async def create_sales_rep(body: SalesRepIn, user=Depends(admin_only)):
    doc = {
        "id": f"rep-{uuid.uuid4().hex[:10]}",
        **body.model_dump(),
        "current_volume_usd": 0.0,
        "created_at": now_iso(),
        "created_by": user["email"],
    }
    await db.sales_reps.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------------------------------------------------------------------------
# Hardware Node assignment to a contractor lead (pending job)
# ---------------------------------------------------------------------------
@api.post("/admin/ops/hardware-nodes/assign")
async def assign_hardware_node(body: NodeAssignBody, user=Depends(admin_only)):
    node = await db.hardware_nodes.find_one({"id": body.node_id}, {"_id": 0})
    if not node:
        raise HTTPException(404, f"node {body.node_id} not found")
    if node.get("status") != "available":
        raise HTTPException(409, f"node {body.node_id} is {node.get('status')}")
    if node.get("assigned_job_id"):
        raise HTTPException(409, f"node {body.node_id} already assigned to {node['assigned_job_id']}")

    job = await db.jobs.find_one({"id": body.job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, f"job {body.job_id} not found")
    if job.get("assigned_node_id"):
        raise HTTPException(409, f"job {body.job_id} already has node {job['assigned_node_id']}")

    now = now_iso()
    await db.hardware_nodes.update_one(
        {"id": body.node_id},
        {"$set": {"status": "assigned", "assigned_job_id": body.job_id, "assigned_at": now,
                  "assigned_by": user["email"]}},
    )
    await db.jobs.update_one(
        {"id": body.job_id},
        {"$set": {"assigned_node_id": body.node_id, "node_assigned_at": now,
                  "node_assigned_by": user["email"]}},
    )
    return {"ok": True, "node_id": body.node_id, "job_id": body.job_id, "assigned_at": now}


@api.post("/admin/ops/hardware-nodes/{node_id}/release")
async def release_hardware_node(node_id: str, user=Depends(admin_only)):
    node = await db.hardware_nodes.find_one({"id": node_id}, {"_id": 0})
    if not node:
        raise HTTPException(404, f"node {node_id} not found")
    job_id = node.get("assigned_job_id")
    await db.hardware_nodes.update_one(
        {"id": node_id},
        {"$set": {"status": "available", "assigned_job_id": None,
                  "released_at": now_iso(), "released_by": user["email"]}},
    )
    if job_id:
        await db.jobs.update_one(
            {"id": job_id},
            {"$set": {"assigned_node_id": None, "node_released_at": now_iso()}},
        )
    return {"ok": True, "node_id": node_id, "previous_job_id": job_id}


# ---------------------------------------------------------------------------
# Contractor metadata mutations
# ---------------------------------------------------------------------------
@api.put("/admin/ops/contractors/{contractor_id}/tier")
async def update_contractor_tier(contractor_id: str, body: TierAssignBody, user=Depends(admin_only)):
    res = await db.users.update_one(
        {"id": contractor_id, "role": "contractor"},
        {"$set": {"assigned_tier": body.tier, "tier_assigned_at": now_iso(),
                  "tier_assigned_by": user["email"]}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, f"contractor {contractor_id} not found")
    return {"ok": True, "contractor_id": contractor_id, "assigned_tier": body.tier}


@api.put("/admin/ops/contractors/{contractor_id}/rep")
async def update_contractor_rep(contractor_id: str, body: RepAssignBody, user=Depends(admin_only)):
    rep = await db.sales_reps.find_one({"id": body.rep_id}, {"_id": 0, "id": 1, "name": 1})
    if not rep:
        raise HTTPException(404, f"rep {body.rep_id} not found")
    res = await db.users.update_one(
        {"id": contractor_id, "role": "contractor"},
        {"$set": {"assigned_rep_id": body.rep_id, "rep_assigned_at": now_iso(),
                  "rep_assigned_by": user["email"]}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, f"contractor {contractor_id} not found")
    return {"ok": True, "contractor_id": contractor_id, "assigned_rep_id": body.rep_id,
            "rep_name": rep["name"]}


# ---------------------------------------------------------------------------
# Sales Strategy Playbook — softened, professional, supplier-safe copy
# ---------------------------------------------------------------------------
SALES_STRATEGY_PLAYBOOK = [
    {
        "code": "PHASE 1.0",
        "title": "Free First-Scan Anchoring",
        "body": "Open every new contractor relationship with a complimentary STRATEX scan on their first pipeline property. This removes adoption friction and positions the rep as a technical consultant rather than a vendor, accelerating trust and shortening the next quote cycle.",
    },
    {
        "code": "PHASE 2.0",
        "title": "Estimation Quality Differentiation",
        "body": "Walk decision-makers through the structural twin and the 100-point validation report. Quantify the labor hours and callback risk eliminated by sub-surface moisture detection — frame the value as crew safety and proposal accuracy, not as a cost-cut.",
    },
    {
        "code": "PHASE 2.1",
        "title": "Material Verification & Lot Discipline",
        "body": "Use the deliverable's material-section as a lot-and-batch verification anchor. Reinforce shingle profile, underlayment match, and batch consistency at delivery to protect the contractor from architectural mismatch claims and shorten dispute cycles with manufacturers.",
    },
    {
        "code": "PHASE 3.0",
        "title": "Tier Alignment & Margin Expansion",
        "body": "Once the contractor has run 2-3 scanned jobs, walk them through the tier-pricing matrix. Show how faster proposal velocity and lower callback rates expand their net margin even at our standard wholesale tier — making the upgrade conversation a margin discussion, not a price discussion.",
    },
]


@api.get("/admin/ops/playbook")
async def get_sales_playbook(user=Depends(admin_only)):
    return {"playbook": SALES_STRATEGY_PLAYBOOK, "version": "1.0.0"}
