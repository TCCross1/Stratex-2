"""NextGen mission endpoints — Domain 3 (Missions).

Phase 1a scope:
- POST /missions          → create a mission (SD-003)
- GET  /missions          → list tenant missions
- GET  /missions/{id}     → mission detail with the resolved product policy
- POST /missions/{id}/advance → advance workflow to the next stage (bounded)

Stage transitions are still deterministic and audited even when the
downstream capture/processing services are mocked or planned.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import NxSession, nx_session
from ..db import now_iso_utc, nx_collections, nx_id, strip_mongo_id
from ..models import MissionCreate
from ._router import nextgen_r
from .catalog import PRODUCTS, _product_by_key


STAGE_LABELS = [
    "Mission Control",
    "Mission Planning",
    "Mission Validation",
    "Flight",
    "Mission Assurance",
    "Capture Validation",
    "Digital Twin Generation",
    "AI Workforce Processing",
    "Property Intelligence",
    "AWE™ Intelligence",
    "Human QA",
    "Report Generation",
    "Property Passport Update",
    "Habitat Synchronization",
    "Customer Delivery",
]


class MissionAdvance(BaseModel):
    to_stage: int
    note: Optional[str] = None


@nextgen_r.post("/missions")
async def create_mission(
    body: MissionCreate,
    session: NxSession = Depends(nx_session),
):
    prop = await nx_collections.properties.find_one({
        "canonical_id": body.property_id,
        "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found on your tenant")

    product = _product_by_key(body.product)
    if not product:
        raise HTTPException(400, f"Unknown product: {body.product}")

    now = now_iso_utc()
    mission = {
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "property_id": body.property_id,
        "product": body.product,
        "state": "planned",
        "stage": 1,
        "dispatcher_user_id": session.user_id,
        "pilot_user_id": None,
        "scheduled_for": body.scheduled_for,
        "notes": body.notes,
        "price": {
            "amount_cents": product["contractor_price_cents"],
            "currency": "USD",
        },
        "estimated_cost": {
            "amount_cents": product["internal_cost_estimate_cents"],
            "currency": "USD",
        },
        "parent_failed_mission_id": None,
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    await nx_collections.missions.insert_one(dict(mission))
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "mission.created",
        "actor_id": session.user_id,
        "resource_kind": "mission",
        "resource_id": mission["canonical_id"],
        "at": now,
        "payload": {"product": body.product, "property_id": body.property_id},
    })
    return {"mission": strip_mongo_id(mission), "product": product}


@nextgen_r.get("/missions")
async def list_missions(
    session: NxSession = Depends(nx_session),
    property_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    q = {"tenant_id": session.tenant_id}
    if property_id:
        q["property_id"] = property_id
    cursor = nx_collections.missions.find(q).sort("created_at", -1).limit(limit)
    items = [strip_mongo_id(d) async for d in cursor]
    return {"items": items, "count": len(items)}


@nextgen_r.get("/missions/{mission_id}")
async def get_mission(
    mission_id: str,
    session: NxSession = Depends(nx_session),
):
    m = await nx_collections.missions.find_one({
        "canonical_id": mission_id,
        "tenant_id": session.tenant_id,
    })
    if not m:
        raise HTTPException(404, "Mission not found")
    prop = await nx_collections.properties.find_one({
        "canonical_id": m["property_id"],
    })
    product = _product_by_key(m["product"])
    return {
        "mission": strip_mongo_id(m),
        "property": strip_mongo_id(prop),
        "product": product,
        "stage_labels": STAGE_LABELS,
    }


@nextgen_r.post("/missions/{mission_id}/advance")
async def advance_mission(
    mission_id: str,
    body: MissionAdvance,
    session: NxSession = Depends(nx_session),
):
    m = await nx_collections.missions.find_one({
        "canonical_id": mission_id,
        "tenant_id": session.tenant_id,
    })
    if not m:
        raise HTTPException(404, "Mission not found")
    if body.to_stage < m["stage"]:
        raise HTTPException(400, "Cannot regress workflow stage; use SUPERSEDE")
    if body.to_stage > 15:
        raise HTTPException(400, "Max stage is 15")
    now = now_iso_utc()
    await nx_collections.missions.update_one(
        {"canonical_id": mission_id},
        {
            "$set": {"stage": body.to_stage, "updated_at": now},
            "$inc": {"version": 1},
        },
    )
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "mission.stage_advanced",
        "actor_id": session.user_id,
        "resource_kind": "mission",
        "resource_id": mission_id,
        "at": now,
        "payload": {
            "from_stage": m["stage"],
            "to_stage": body.to_stage,
            "note": body.note,
        },
    })
    return {"ok": True, "stage": body.to_stage,
            "stage_label": STAGE_LABELS[body.to_stage - 1]}
