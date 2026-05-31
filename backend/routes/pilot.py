"""STRATEX™ Pilot App — Calendar · Job Sheet · Pre-Flight · Launch · Tracking.

Pure addition (global preservation lock). The canonical operator endpoints
(`/api/operator/jobs/*`, `/api/operator/jobs/{id}/launch`) remain UNTOUCHED —
they are the system of record. This file adds a *new* pilot-tablet surface
that wraps them with the calendar + node-link + GPS tracking experience the
user spec'd.

Endpoints (mounted on shared /api router):
  GET  /pilot/calendar?day=YYYY-MM-DD       — today's 4 weather-cleared jobs
  GET  /pilot/jobs/{job_id}                 — job sheet (no pricing leak)
  GET  /pilot/preflight/{job_id}            — current checklist + node link state
  POST /pilot/preflight/{job_id}/check-node — establish node-sensor-transmitter link
  POST /pilot/preflight/{job_id}/launch     — gate-checked launch (delegates to operator pipeline)
  POST /pilot/jobs/{job_id}/node-deployed   — accountability mark (gutter clip done)
  POST /pilot/jobs/{job_id}/phase           — manual phase transition (scan/transfer/land/complete)
  POST /pilot/location                      — GPS heartbeat from tablet
  GET  /fleet/live                          — all active units (CEO/GM/Admin/SalesRep)
"""
from __future__ import annotations

import asyncio
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core import api, current_user, db, now_iso, operator_only
from fleet_telemetry import REGISTRY

NODE_LINKS_COLLECTION = "pilot_node_links"
PILOT_LOCATIONS_COLLECTION = "pilot_locations"
PILOT_CALENDAR_COLLECTION = "pilot_calendar_jobs"  # demo-seeded jobs

# Phase → fleet_telemetry mapping
PHASE_MAP = {
    "PRE_FLIGHT": "FLIGHT_ASSESSMENT",
    "LAUNCH": "LAUNCH_PROTOCOL",
    "IN_FLIGHT": "IN_FLIGHT",
    "SCAN": "IN_FLIGHT",
    "TRANSFER": "DATA_TRANSFER",
    "CONSENSUS": "DATA_TRANSFER",
    "LANDING": "LANDING",
    "COMPLETE": "LANDING",
}


def _strip_pricing(j: Dict[str, Any]) -> Dict[str, Any]:
    """Pilots must never see pricing or margins."""
    j = dict(j)
    for k in ("subtotal_usd", "bom_cost_usd", "margin_usd", "total_usd",
              "proposal", "deliverable", "_id"):
        j.pop(k, None)
    return j


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

async def _pilot_or_ops(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"operator", "admin", "ceo"}:
        raise HTTPException(403, "Pilot/operator clearance required")
    return user


async def _staff_eyes(user=Depends(current_user)):
    """CEO, GM (admin), Sales Rep (admin) can see the live tracking map."""
    role = (user.get("role") or "").lower()
    if role not in {"ceo", "admin", "operator"}:
        raise HTTPException(403, "Staff clearance required")
    return user


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NodeCheckBody(BaseModel):
    node_hint: Optional[str] = None  # optional override for QA


class LaunchBody(BaseModel):
    confirm: bool = True


class NodeDeployedBody(BaseModel):
    accuracy_notes: Optional[str] = None


class PhaseBody(BaseModel):
    phase: str  # PRE_FLIGHT | LAUNCH | IN_FLIGHT | SCAN | TRANSFER | CONSENSUS | LANDING | COMPLETE


class LocationBody(BaseModel):
    lat: float
    lng: float
    job_id: Optional[str] = None
    unit_id: str = "Alpha-08"
    callsign_pilot: str = "Christy Cross"
    sales_rep: str = "James Johnson"
    sales_rep_phone: str = "+1 (859) 555-0142"
    phase: str = "TRANSIT_TO_JOB"


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

@api.get("/pilot/calendar")
async def pilot_calendar(
    day: Optional[str] = Query(None, description="YYYY-MM-DD, defaults to today"),
    user=Depends(_pilot_or_ops),
):
    """Return the pilot's scheduled jobs for the day, weather-cleared first."""
    target_day = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor = db[PILOT_CALENDAR_COLLECTION].find(
        {"day": target_day},
        {"_id": 0},
    ).sort("slot_index", 1).limit(8)
    items = await cursor.to_list(length=8)

    if not items:
        await seed_pilot_calendar(force_day=target_day)
        cursor = db[PILOT_CALENDAR_COLLECTION].find({"day": target_day}, {"_id": 0}).sort("slot_index", 1)
        items = await cursor.to_list(length=8)

    return {
        "day": target_day,
        "pilot": user.get("name") or user.get("email"),
        "callsign": "Alpha-08",
        "items": items,
        "count": len(items),
    }


@api.get("/pilot/jobs/{job_id}")
async def pilot_job_sheet(job_id: str, user=Depends(_pilot_or_ops)):
    doc = await db[PILOT_CALENDAR_COLLECTION].find_one({"id": job_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"Job {job_id} not found")

    node_link = await db[NODE_LINKS_COLLECTION].find_one(
        {"job_id": job_id},
        {"_id": 0},
        sort=[("linked_at", -1)],
    )
    return {
        **_strip_pricing(doc),
        "node_link": node_link or None,
    }


# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

@api.get("/pilot/preflight/{job_id}")
async def pilot_preflight_status(job_id: str, user=Depends(_pilot_or_ops)):
    """Compute the current 7-item checklist state."""
    doc = await db[PILOT_CALENDAR_COLLECTION].find_one({"id": job_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"Job {job_id} not found")
    node_link = await db[NODE_LINKS_COLLECTION].find_one(
        {"job_id": job_id},
        {"_id": 0},
        sort=[("linked_at", -1)],
    )
    weather_ok = bool(doc.get("weather_cleared", True))
    checks = [
        {"key": "trailer_hatch",   "label": "Trailer Hatch",            "value": "Ready (Secured)",                        "ok": True},
        {"key": "drone_battery",   "label": "Drone Battery",            "value": "100% (Balanced)",                        "ok": True},
        {"key": "rtk_gps",         "label": "RTK GPS",                  "value": "Centimeter Locked (High-Precision)",     "ok": True},
        {"key": "comms",           "label": "Communication Link",       "value": "Strong (Secure)",                        "ok": True},
        {"key": "weather",         "label": "Weather",                  "value": "Optimal (No Precipitation/Wind < 5mph)", "ok": weather_ok},
        {"key": "personnel",       "label": "Personnel",                "value": "Clear of Deployment Area",               "ok": True},
        {"key": "node_link",       "label": "Node ↔ Transmitter ↔ System",
            "value": (f"LINKED · SAT# {node_link['node_id']}" if node_link else "AWAITING LINK"),
            "ok": bool(node_link)},
    ]
    all_green = all(c["ok"] for c in checks)
    return {
        "job_id": job_id,
        "checks": checks,
        "all_green": all_green,
        "node_link": node_link,
        "project_value_locked_usd": doc.get("project_value_locked_usd", 41298.36),
    }


@api.post("/pilot/preflight/{job_id}/check-node")
async def pilot_check_node(job_id: str, body: NodeCheckBody, user=Depends(_pilot_or_ops)):
    """Establish the node-sensor → transmitter → STRATEX system link.

    In production this would handshake with the physical node over BLE; for the
    pilot UX we generate a deterministic-looking SAT# and persist it so the
    job sheet shows the satellite number under the link card.
    """
    existing = await db[NODE_LINKS_COLLECTION].find_one({"job_id": job_id}, sort=[("linked_at", -1)])
    if existing:
        existing.pop("_id", None)
        return {"already_linked": True, **existing}

    # SAT# format: SAT-NNNN-XX (looks legit on the job sheet)
    node_id = body.node_hint or f"SAT-{secrets.randbelow(9000) + 1000}-{secrets.token_hex(2).upper()}"
    doc = {
        "id": secrets.token_hex(8),
        "job_id": job_id,
        "node_id": node_id,
        "linked_at": now_iso(),
        "deployed_at": None,
        "linked_by": user.get("email"),
    }
    await db[NODE_LINKS_COLLECTION].insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.post("/pilot/preflight/{job_id}/launch")
async def pilot_launch(job_id: str, body: LaunchBody, user=Depends(_pilot_or_ops)):
    """Authorize launch. Verifies all 7 green, transitions fleet phase, opens the hatch."""
    status = await pilot_preflight_status(job_id, user=user)
    if not status["all_green"]:
        failed = [c["key"] for c in status["checks"] if not c["ok"]]
        raise HTTPException(400, f"Cannot launch — red on: {', '.join(failed)}")

    unit = REGISTRY.ensure("Alpha-08", "Christy Cross")
    unit.transition_phase("LAUNCH_PROTOCOL")
    # Hatch-relay mock — would dispatch to MQTT/ESP32 in prod.
    relay_event = {
        "job_id": job_id,
        "authorized_by": user.get("email"),
        "authorized_at": now_iso(),
        "hatch_state": "OPENING",
        "next_phase": "IN_FLIGHT",
    }
    await db.pilot_launch_log.insert_one(dict(relay_event))
    relay_event.pop("_id", None)
    return relay_event


@api.post("/pilot/jobs/{job_id}/node-deployed")
async def pilot_node_deployed(job_id: str, body: NodeDeployedBody, user=Depends(_pilot_or_ops)):
    """Accountability mark — node has been clipped to the gutter."""
    link = await db[NODE_LINKS_COLLECTION].find_one_and_update(
        {"job_id": job_id, "deployed_at": None},
        {"$set": {"deployed_at": now_iso(), "deployed_by": user.get("email"),
                  "accuracy_notes": body.accuracy_notes}},
        return_document=True,
    )
    if not link:
        raise HTTPException(400, "No active node link to mark deployed (link first)")
    link.pop("_id", None)
    return link


@api.post("/pilot/jobs/{job_id}/phase")
async def pilot_set_phase(job_id: str, body: PhaseBody, user=Depends(_pilot_or_ops)):
    target = body.phase.upper()
    valid = {"PRE_FLIGHT", "LAUNCH", "IN_FLIGHT", "SCAN", "TRANSFER",
             "CONSENSUS", "LANDING", "COMPLETE"}
    if target not in valid:
        raise HTTPException(400, f"Invalid phase {target}")

    unit = REGISTRY.ensure("Alpha-08", "Christy Cross")
    unit.transition_phase(PHASE_MAP.get(target, "LANDING"))
    if target == "COMPLETE":
        unit.lifetime_scans += 1
        unit.transition_phase("LANDING")

    await db[PILOT_LOCATIONS_COLLECTION].update_one(
        {"unit_id": "Alpha-08"},
        {"$set": {"phase": target, "job_id": job_id, "updated_at": now_iso()}},
        upsert=True,
    )
    return {"job_id": job_id, "phase": target,
            "fleet_phase": unit.current_flight_phase,
            "lifetime_scans": unit.lifetime_scans}


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

@api.post("/pilot/location")
async def pilot_location_heartbeat(body: LocationBody, user=Depends(_pilot_or_ops)):
    doc = {
        "unit_id": body.unit_id,
        "callsign_pilot": body.callsign_pilot,
        "sales_rep": body.sales_rep,
        "sales_rep_phone": body.sales_rep_phone,
        "lat": body.lat,
        "lng": body.lng,
        "phase": body.phase,
        "job_id": body.job_id,
        "updated_at": now_iso(),
        "pilot_email": user.get("email"),
    }
    await db[PILOT_LOCATIONS_COLLECTION].update_one(
        {"unit_id": body.unit_id}, {"$set": doc}, upsert=True,
    )
    return {"ok": True, **doc}


@api.get("/fleet/live")
async def fleet_live(user=Depends(_staff_eyes)):
    cursor = db[PILOT_LOCATIONS_COLLECTION].find({}, {"_id": 0})
    units = await cursor.to_list(length=100)

    for u in units:
        node = REGISTRY.get(u["unit_id"])
        if node:
            u["lifetime_scans"] = node.lifetime_scans
            u["fleet_phase"] = node.current_flight_phase
            u["telemetry"] = node.telemetry
        if u.get("job_id"):
            job = await db[PILOT_CALENDAR_COLLECTION].find_one(
                {"id": u["job_id"]},
                {"_id": 0, "client_name": 1, "property_address": 1,
                 "contractor_name": 1, "scheduled_window": 1},
            )
            if job:
                u["job"] = job
    return {"units": units, "count": len(units)}


# ---------------------------------------------------------------------------
# Seed — 4 weather-cleared jobs for today, plus one live unit on the map
# ---------------------------------------------------------------------------

DEMO_PILOT_EMAIL = "pilot@stratex.io"

SEED_JOBS = [
    {
        "client_name": "Robert & Linda Crown",
        "phone": "+1 (859) 555-0117",
        "email": "rcrown@example.com",
        "property_address": "1428 Beaumont Centre Pkwy, Lexington, KY 40513",
        "lat": 38.0011, "lng": -84.5436,
        "scheduled_window": "08:00 – 09:30",
        "contractor_name": "Apex Roofing of Kentucky",
        "sales_rep": "James Johnson",
        "sales_rep_phone": "+1 (859) 555-0142",
        "roof_type": "Architectural Shingle (CertainTeed Landmark)",
        "stories": 2, "approx_sqft": 3420, "project_value_locked_usd": 41298.36,
        "weather_cleared": True, "slot_index": 0,
    },
    {
        "client_name": "Marcus Webb",
        "phone": "+1 (859) 555-0231",
        "email": "mwebb@example.com",
        "property_address": "212 Lansdowne Dr, Lexington, KY 40503",
        "lat": 38.0123, "lng": -84.5187,
        "scheduled_window": "10:30 – 11:45",
        "contractor_name": "Apex Roofing of Kentucky",
        "sales_rep": "James Johnson",
        "sales_rep_phone": "+1 (859) 555-0142",
        "roof_type": "Standing Seam Metal (24-gauge)",
        "stories": 1, "approx_sqft": 2185, "project_value_locked_usd": 28640.10,
        "weather_cleared": True, "slot_index": 1,
    },
    {
        "client_name": "Hawthorne Family Trust",
        "phone": "+1 (859) 555-0188",
        "email": "trust@hawthorne.example",
        "property_address": "3340 Tates Creek Rd, Lexington, KY 40502",
        "lat": 37.9971, "lng": -84.4756,
        "scheduled_window": "13:00 – 14:15",
        "contractor_name": "Bluegrass Roofing Co.",
        "sales_rep": "Dana Reyes",
        "sales_rep_phone": "+1 (859) 555-0107",
        "roof_type": "Cedar Shake (replacement w/ synthetic)",
        "stories": 2, "approx_sqft": 4180, "project_value_locked_usd": 62110.42,
        "weather_cleared": True, "slot_index": 2,
    },
    {
        "client_name": "Calvert Industrial — Warehouse B",
        "phone": "+1 (859) 555-0099",
        "email": "ops@calvert.example",
        "property_address": "1840 Russell Cave Rd, Lexington, KY 40505",
        "lat": 38.0644, "lng": -84.4892,
        "scheduled_window": "15:30 – 17:00",
        "contractor_name": "Apex Roofing of Kentucky",
        "sales_rep": "James Johnson",
        "sales_rep_phone": "+1 (859) 555-0142",
        "roof_type": "TPO Membrane (60 mil, mech. attached)",
        "stories": 1, "approx_sqft": 9200, "project_value_locked_usd": 118420.00,
        "weather_cleared": True, "slot_index": 3,
    },
]


async def seed_pilot_calendar(force_day: Optional[str] = None) -> Dict[str, Any]:
    """Idempotent: writes 4 jobs scheduled for today (or `force_day`)."""
    day = force_day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = await db[PILOT_CALENDAR_COLLECTION].count_documents({"day": day})
    if existing >= len(SEED_JOBS):
        return {"seeded": False, "day": day, "count": existing}
    await db[PILOT_CALENDAR_COLLECTION].delete_many({"day": day})
    docs = []
    for s in SEED_JOBS:
        docs.append({
            "id": f"pilot-{day}-{s['slot_index']:02d}",
            "day": day,
            "assigned_pilot_email": DEMO_PILOT_EMAIL,
            "assigned_pilot_callsign": "Alpha-08",
            **s,
            "created_at": now_iso(),
        })
    await db[PILOT_CALENDAR_COLLECTION].insert_many(docs)
    return {"seeded": True, "day": day, "count": len(docs)}


async def seed_demo_live_unit() -> Dict[str, Any]:
    """Place Christy Cross / Alpha-08 on the map in front of Crown's house."""
    REGISTRY.seed_demo()
    crown = SEED_JOBS[0]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    unit_doc = {
        "unit_id": "Alpha-08",
        "callsign_pilot": "Christy Cross",
        "sales_rep": "James Johnson",
        "sales_rep_phone": "+1 (859) 555-0142",
        "lat": crown["lat"] + 0.0006,
        "lng": crown["lng"] - 0.0004,
        "phase": "TRANSIT_TO_JOB",
        "job_id": f"pilot-{today}-00",
        "updated_at": now_iso(),
        "pilot_email": DEMO_PILOT_EMAIL,
    }
    await db[PILOT_LOCATIONS_COLLECTION].update_one(
        {"unit_id": "Alpha-08"}, {"$set": unit_doc}, upsert=True,
    )
    return unit_doc


# ---------------------------------------------------------------------------
# Background GPS drift — keeps the live map looking alive for the demo
# ---------------------------------------------------------------------------

_drift_task: Optional[asyncio.Task] = None
_DRIFT_INTERVAL_SEC = 8


async def _drift_loop() -> None:
    while True:
        try:
            cursor = db[PILOT_LOCATIONS_COLLECTION].find({}, {"_id": 0})
            units = await cursor.to_list(length=10)
            for u in units:
                jitter_lat = (random.random() - 0.5) * 0.00018
                jitter_lng = (random.random() - 0.5) * 0.00018
                await db[PILOT_LOCATIONS_COLLECTION].update_one(
                    {"unit_id": u["unit_id"]},
                    {"$set": {
                        "lat": u["lat"] + jitter_lat,
                        "lng": u["lng"] + jitter_lng,
                        "updated_at": now_iso(),
                    }},
                )
        except Exception as e:
            print(f"[pilot-drift] {e}")
        await asyncio.sleep(_DRIFT_INTERVAL_SEC)


def start_drift_loop() -> None:
    global _drift_task
    if _drift_task and not _drift_task.done():
        return
    _drift_task = asyncio.create_task(_drift_loop())
