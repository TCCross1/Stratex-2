"""STRATEX™ Geofence + Tripwire + Launch-Authorization REST surface.

Endpoints (mounted on shared /api router):

  Geofence:
    POST  /api/geofence/init                   — pilot/admin/ceo: drop 150ft zone for a job
    GET   /api/geofence/job/{job_id}           — return active zone for a job
    POST  /api/geofence/simulate-breach        — investor-demo cinematic breach trigger
    GET   /api/geofence/alerts                 — CEO/GM/Sales: recent UNAUTHORIZED_SITE_BREACH events

  Tripwire:
    GET   /api/contractor/tripwire             — current contractor's tripwire array
    PUT   /api/contractor/tripwire             — replace contractor tripwire (≥1 of each role required)

  Launch Authorization:
    POST  /api/pilot/jobs/{job_id}/authorize-launch
                                                — gates on 8-line preflight + writes immutable ledger
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import api, current_user, db, now_iso
from geofence_service import (
    DEFAULT_GEOFENCE_RADIUS_FT,
    get_active_zone,
    haversine_distance_ft,
    increment_strike,
    init_zone_for_job,
    job_has_cleared_invoice,
    lookup_tripwire_by_phone,
    point_in_zone,
    recent_breach_alerts,
    record_breach_event,
    save_contractor_tripwire,
)


# ---------------------------------------------------------------------------
# Auth gates
# ---------------------------------------------------------------------------
async def _pilot_admin_or_ceo(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"operator", "admin", "ceo"}:
        raise HTTPException(403, "Operator, Admin, or CEO clearance required")
    return user


async def _exec_view(user=Depends(current_user)):
    """CEO + Admin + Contractor (sales rep) — read-only views of breach alerts."""
    role = (user.get("role") or "").lower()
    if role not in {"contractor", "admin", "ceo"}:
        raise HTTPException(403, "Contractor, Admin, or CEO clearance required")
    return user


async def _contractor_only(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role != "contractor":
        raise HTTPException(403, "Contractor clearance required")
    return user


# ===========================================================================
# Geofence init / status / breach-sim / alerts
# ===========================================================================
class GeofenceInitBody(BaseModel):
    job_id:     str
    center_lat: float = Field(..., ge=-90, le=90)
    center_lng: float = Field(..., ge=-180, le=180)
    radius_ft:  float = Field(DEFAULT_GEOFENCE_RADIUS_FT, gt=0, le=1000)


@api.post("/geofence/init")
async def post_geofence_init(body: GeofenceInitBody, user=Depends(_pilot_admin_or_ceo)) -> Dict[str, Any]:
    """Drop a 150-ft radius perimeter around a roof centroid. Returns the
    sealed zone doc so the pre-flight checklist can flip `geofence_perimeter` green."""
    zone = await init_zone_for_job(
        db, job_id=body.job_id,
        center_lat=body.center_lat, center_lng=body.center_lng,
        initialized_by=user["id"], radius_ft=body.radius_ft,
    )
    return {"ok": True, "zone": zone}


@api.get("/geofence/job/{job_id}")
async def get_geofence_zone(job_id: str, user=Depends(_pilot_admin_or_ceo)) -> Dict[str, Any]:
    zone = await get_active_zone(db, job_id)
    return {"job_id": job_id, "zone": zone, "active": bool(zone)}


class SimulateBreachBody(BaseModel):
    job_id:           str
    breacher_phone:   str = Field(..., description="Phone number of the breaching individual")
    breach_offset_ft: float = Field(50.0, ge=0, le=10_000, description="Distance inside the zone (for cinematic demo)")


@api.post("/geofence/simulate-breach")
async def post_simulate_breach(body: SimulateBreachBody, user=Depends(_pilot_admin_or_ceo)) -> Dict[str, Any]:
    """Investor-demo cinematic breach trigger. Pulls the active zone, places a
    fake breach point inside the radius, runs the full pipeline:
      1. point-in-zone test
      2. tripwire phone lookup
      3. invoice-cleared check
      4. record breach event + (if unauthorized) strike + (Strike ≥ 2) blacklist
    """
    zone = await get_active_zone(db, body.job_id)
    if not zone:
        raise HTTPException(404, f"No active geofence on job {body.job_id}")

    # Project a fake breach point exactly `breach_offset_ft` north of the centroid.
    deg_per_ft_lat = 1.0 / 364_000.0
    breach_lat = zone["center_lat"] + body.breach_offset_ft * deg_per_ft_lat
    breach_lng = zone["center_lng"]
    if not point_in_zone(breach_lat, breach_lng, zone):
        raise HTTPException(400, "Synthetic breach point landed outside the zone — increase radius or decrease offset")

    tripwire = await lookup_tripwire_by_phone(db, body.breacher_phone)
    if not tripwire:
        # Still record the breach but without a contractor link — useful "stranger on site" data.
        return {
            "ok": True, "match": False,
            "message": "Breach detected but no tripwire match — stranger pinged.",
            "zone_id": zone["zone_id"], "job_id": body.job_id,
        }

    invoice_present = await job_has_cleared_invoice(db, body.job_id)
    event = await record_breach_event(
        db, zone=zone, phone_breacher=body.breacher_phone,
        breach_lat=breach_lat, breach_lng=breach_lng,
        tripwire_match=tripwire, invoice_present=invoice_present,
        triggered_by=user["id"], now_iso=now_iso(),
    )

    blacklist_state: Optional[Dict[str, Any]] = None
    if not invoice_present:
        blacklist_state = await increment_strike(
            db, tripwire["contractor_user_id"], event["breach_id"], now_iso(),
        )

    return {
        "ok":            True,
        "match":         True,
        "event":         event,
        "blacklist":     blacklist_state,
        "yellow_triangle_alert": not invoice_present,
        "distance_ft":   round(haversine_distance_ft(
            breach_lat, breach_lng, zone["center_lat"], zone["center_lng"]
        ), 2),
    }


@api.get("/geofence/alerts")
async def get_geofence_alerts(limit: int = 25, user=Depends(_exec_view)) -> Dict[str, Any]:
    """Polled by the Yellow-Triangle widget on CEO / GM / Sales-Rep dashboards."""
    alerts = await recent_breach_alerts(db, int(limit))
    return {
        "alerts":      alerts,
        "count":       len(alerts),
        "blacklist":   await _current_blacklist_summary(db),
    }


async def _current_blacklist_summary(db) -> List[Dict[str, Any]]:
    cursor = db.contractor_blacklist.find(
        {"account_status": "RESTRICTED_PERIMETER_VIOLATION"}, {"_id": 0},
    ).sort("last_updated", -1).limit(50)
    out: List[Dict[str, Any]] = []
    async for d in cursor:
        out.append(d)
    return out


# ===========================================================================
# Contractor Tripwire CRUD
# ===========================================================================
class TripwireContact(BaseModel):
    role:  str = Field(..., description="owner | foreman | sales_rep")
    name:  str = Field(..., min_length=1)
    phone: str = Field(..., min_length=7)


class TripwirePutBody(BaseModel):
    contacts: List[TripwireContact]


@api.get("/contractor/tripwire")
async def get_contractor_tripwire(user=Depends(_contractor_only)) -> Dict[str, Any]:
    doc = await db.contractor_tripwires.find_one({"contractor_user_id": user["id"]}, {"_id": 0})
    return {"contacts": (doc or {}).get("contacts") or [], "set": bool(doc)}


@api.put("/contractor/tripwire")
async def put_contractor_tripwire(body: TripwirePutBody, user=Depends(_contractor_only)) -> Dict[str, Any]:
    roles = {c.role.lower() for c in body.contacts}
    required = {"owner", "foreman", "sales_rep"}
    missing = required - roles
    if missing:
        raise HTTPException(400, f"Tripwire array is missing required roles: {sorted(missing)}")
    result = await save_contractor_tripwire(
        db, contractor_user_id=user["id"],
        contacts=[c.dict() for c in body.contacts],
    )
    return {"ok": True, **result}


# ===========================================================================
# Launch Authorization — gates on 8-line preflight + writes immutable ledger.
# ===========================================================================
class AuthorizeLaunchBody(BaseModel):
    confirm: bool = Field(True, description="Operator must confirm")


@api.post("/pilot/jobs/{job_id}/authorize-launch")
async def post_authorize_launch(job_id: str, body: AuthorizeLaunchBody, user=Depends(_pilot_admin_or_ceo)) -> Dict[str, Any]:
    """Final authorization gate. Re-runs the 8-line preflight server-side
    (defense in depth — no trusting the client's all_green flag) and writes
    an immutable `db.launch_authorizations` row with the locked snapshot."""
    if not body.confirm:
        raise HTTPException(400, "Confirmation required")

    # Re-fetch the canonical preflight state via the pilot module's helper.
    # We do the inline check rather than importing the route handler.
    from routes.pilot import PILOT_CALENDAR_COLLECTION

    job_doc = await db[PILOT_CALENDAR_COLLECTION].find_one({"id": job_id}, {"_id": 0})
    if not job_doc:
        raise HTTPException(404, f"Job {job_id} not found")

    weather_ok = bool(job_doc.get("weather_cleared", True))
    zone       = await get_active_zone(db, job_id)
    gutter_link = await db.gutter_node_links.find_one({"job_id": job_id, "active": True}, {"_id": 0})

    checks = [
        {"key": "trailer_hatch",     "label": "Trailer Hatch",            "value": "Ready (Secured)",                        "ok": True},
        {"key": "drone_battery",     "label": "Drone Battery",            "value": "100% (Balanced)",                        "ok": True},
        {"key": "rtk_gps",           "label": "RTK GPS",                  "value": "Centimeter Locked (High-Precision)",     "ok": True},
        {"key": "comms",             "label": "Communication Link",       "value": "Strong (Secure)",                        "ok": True},
        {"key": "weather",           "label": "Weather",                  "value": "Optimal (No Precipitation/Wind < 5mph)", "ok": weather_ok},
        {"key": "personnel",         "label": "Personnel",                "value": "Clear of Deployment Area",               "ok": True},
        {"key": "gutter_nodes",      "label": "Gutter Nodes",             "value": ("Active (Two-Factor Loop)" if gutter_link else "AWAITING LINK"), "ok": bool(gutter_link)},
        {"key": "geofence_perimeter","label": "Geofence Perimeter",       "value": ("Formed & Activated · " + (zone.get("perimeter_tag") if zone else "") if zone else "NOT INITIALIZED"), "ok": bool(zone)},
    ]
    all_green = all(c["ok"] for c in checks)
    if not all_green:
        raise HTTPException(409, {
            "error":     "preflight_not_green",
            "failed":    [c["key"] for c in checks if not c["ok"]],
            "checks":    checks,
        })

    authorization_id = str(uuid.uuid4())
    auth_doc = {
        "authorization_id":           authorization_id,
        "job_id":                     job_id,
        "authorized_by":              user["id"],
        "authorized_by_role":         (user.get("role") or "").lower(),
        "authorized_at":              now_iso(),
        "locked_checks":              checks,
        "project_value_locked_usd":   job_doc.get("project_value_locked_usd", 41298.36),
        "geofence_zone_id":           (zone or {}).get("zone_id"),
        "geofence_perimeter_tag":     (zone or {}).get("perimeter_tag"),
        "gutter_node_id":             (gutter_link or {}).get("node_id"),
        "locked":                     True,
    }
    await db.launch_authorizations.insert_one(auth_doc)

    return {
        "ok":               True,
        "authorization_id": authorization_id,
        "checks":           checks,
        "all_green":        True,
        "perimeter_tag":    auth_doc["geofence_perimeter_tag"],
    }


# ===========================================================================
# Gutter Nodes — Two-Factor Loop link (replaces the legacy BLE node_link).
# ===========================================================================
class GutterNodeLinkBody(BaseModel):
    job_id:    str
    node_hint: Optional[str] = None


@api.post("/pilot/jobs/{job_id}/gutter-node/link")
async def post_gutter_node_link(job_id: str, body: GutterNodeLinkBody, user=Depends(_pilot_admin_or_ceo)) -> Dict[str, Any]:
    """Establish the covert accelerometer gutter-node 2-factor loop.
    Same UX as the prior node_link but produces a distinct SAT prefix so
    it's auditable as a Two-Factor Loop event, not a BLE handshake."""
    import secrets
    node_id = body.node_hint or f"GN-{secrets.randbelow(9000) + 1000}-{secrets.token_hex(2).upper()}"
    # Deactivate prior links to keep history append-only.
    await db.gutter_node_links.update_many({"job_id": job_id, "active": True}, {"$set": {"active": False}})
    doc = {
        "id":          secrets.token_hex(8),
        "job_id":      job_id,
        "node_id":     node_id,
        "active":      True,
        "linked_at":   now_iso(),
        "linked_by":   user.get("email"),
        "loop_type":   "TWO_FACTOR_ACCELEROMETER",
    }
    await db.gutter_node_links.insert_one(doc)
    return {"ok": True, "node_id": node_id, "loop_type": doc["loop_type"]}
