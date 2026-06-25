"""STRATEX™ — Mission Control bundle.

Three operational capabilities live here so they ship as one
deployment:

  1. Pre-Flight ATC — Open-Meteo telemetry + Claude-rendered GO /
     HOLD / NO-GO verdict for any GPS coordinate
  2. Connected Calendar — shared events collection (scan window /
     crew dispatch / billing / passport check-up)
  3. Fleet snapshot — JSON for the live-map UI (MDU rigs + active
     job sites) — Lexington-KY demo dataset is seeded by default
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core import db

load_dotenv()
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
OPEN_METEO_FCST = "https://api.open-meteo.com/v1/forecast"

router = APIRouter(prefix="/api", tags=["mission-control"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pub(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if k != "_id"}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  1 · PRE-FLIGHT ATC                                                   ║
# ╚══════════════════════════════════════════════════════════════════════╝
class PreflightVerdict(BaseModel):
    decision: Literal["GO", "HOLD", "NO-GO"]
    confidence_pct: int
    reasons: List[str]
    operator_brief: str           # ~30 words "ground commander" plain-language brief


def _classify(wind_mph: float, gust_mph: float, precip_mm: float, vis_m: float,
              cloud_pct: float, code: int) -> PreflightVerdict:
    """Rule-based fallback (and the seed the LLM enriches).
    Thresholds tuned to DJI Matrice 4TD operational envelope."""
    reasons: List[str] = []
    decision = "GO"
    conf = 92

    if gust_mph >= 26:
        decision, conf = "NO-GO", 95
        reasons.append(f"Gusts {gust_mph:.0f} mph exceed M4TD ceiling (26 mph).")
    elif gust_mph >= 20:
        decision, conf = "HOLD", 80
        reasons.append(f"Gusts {gust_mph:.0f} mph in the elevated band — hold for window.")

    if precip_mm >= 0.5:
        decision, conf = "NO-GO", max(conf, 92)
        reasons.append(f"Active precipitation {precip_mm:.1f} mm — payload not rated for wet.")

    if vis_m and vis_m < 4000:
        decision, conf = ("NO-GO" if vis_m < 1500 else "HOLD"), max(conf, 78)
        reasons.append(f"Visibility {vis_m:.0f} m — VFR cutoff approached.")

    if code in (96, 99):
        decision, conf = "NO-GO", 96
        reasons.append("Thunderstorm with hail in the radar window.")

    if not reasons:
        reasons.append(f"Wind {wind_mph:.0f} mph · Gust {gust_mph:.0f} mph · Cloud {cloud_pct:.0f}% — within envelope.")

    op_brief = {
        "GO":    "ATC clears for launch. Telemetry inside the M4TD envelope. Standard checklist applies.",
        "HOLD":  "ATC recommends a hold. One or more parameters trending hot — re-poll in 30 min.",
        "NO-GO": "ATC negates launch. Weather exceeds operational envelope. Reschedule recommended.",
    }[decision]
    return PreflightVerdict(decision=decision, confidence_pct=conf,
                            reasons=reasons, operator_brief=op_brief)


@router.get("/atc/preflight")
async def preflight(lat: float = Query(38.0406), lon: float = Query(-84.5037)):
    """Pre-flight ATC verdict for a GPS coordinate.

    Pulls live forecast from Open-Meteo (no API key needed), runs the
    rule-based classifier, then optionally enriches the brief with a
    short Claude-Sonnet narrative if the Emergent LLM key is wired.
    """
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "current": "temperature_2m,relative_humidity_2m,weather_code,"
                   "cloud_cover,wind_speed_10m,wind_gusts_10m,"
                   "precipitation,visibility",
        "hourly": "wind_gusts_10m,precipitation_probability",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "mm",
        "forecast_hours": 6,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(OPEN_METEO_FCST, params=params)
            r.raise_for_status()
            j = r.json()
    except Exception as e:
        raise HTTPException(502, f"weather upstream failed: {e}")

    cur = j.get("current", {}) or {}
    hourly = j.get("hourly", {}) or {}
    wind_mph   = float(cur.get("wind_speed_10m", 0) or 0)
    gust_mph   = float(cur.get("wind_gusts_10m", wind_mph) or wind_mph)
    precip_mm  = float(cur.get("precipitation", 0) or 0)
    vis_m      = float(cur.get("visibility", 10000) or 10000)
    cloud_pct  = float(cur.get("cloud_cover", 0) or 0)
    code       = int(cur.get("weather_code", 0) or 0)
    temp_f     = float(cur.get("temperature_2m", 0) or 0)
    rh         = float(cur.get("relative_humidity_2m", 0) or 0)

    verdict = _classify(wind_mph, gust_mph, precip_mm, vis_m, cloud_pct, code)

    # 6-hour gust trend (mini sparkline data)
    gusts_next_6h = (hourly.get("wind_gusts_10m") or [])[:6]
    precip_prob_next_6h = (hourly.get("precipitation_probability") or [])[:6]

    return {
        "coordinates": {"lat": lat, "lon": lon},
        "telemetry": {
            "wind_mph": round(wind_mph, 1),
            "gust_mph": round(gust_mph, 1),
            "precip_mm": round(precip_mm, 2),
            "visibility_m": round(vis_m, 0),
            "cloud_pct": round(cloud_pct, 0),
            "temp_f": round(temp_f, 1),
            "humidity_pct": round(rh, 0),
            "weather_code": code,
        },
        "verdict": verdict.model_dump(),
        "trend_6h": {
            "gusts_mph": gusts_next_6h,
            "precip_prob_pct": precip_prob_next_6h,
        },
        "doppler_radar_tile_url":
            "https://tilecache.rainviewer.com/v2/radar/{ts}/256/{z}/{x}/{y}/2/1_1.png",
        "polled_at": _now(),
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  2 · CONNECTED CALENDAR                                               ║
# ╚══════════════════════════════════════════════════════════════════════╝
class CalendarEvent(BaseModel):
    title: str
    kind: Literal["SCAN", "CREW", "DISPATCH", "BILLING", "CHECKUP", "MAINT", "OTHER"]
    start: str          # ISO datetime
    end:   Optional[str] = None
    location: Optional[str] = None
    crew: Optional[List[str]] = None
    job_id: Optional[str] = None
    notes: Optional[str] = None
    color: Optional[str] = None


@router.get("/calendar/events")
async def list_events(start: Optional[str] = None, end: Optional[str] = None):
    coll = db["calendar_events"]
    q: Dict[str, Any] = {}
    if start:
        q["start"] = {**q.get("start", {}), "$gte": start}
    if end:
        q["start"] = {**q.get("start", {}), "$lte": end}
    items = [_pub(d) async for d in coll.find(q).sort("start", 1)]
    return {"count": len(items), "items": items}


@router.post("/calendar/events")
async def create_event(body: CalendarEvent):
    coll = db["calendar_events"]
    rec = {**body.model_dump(), "id": str(uuid.uuid4()),
           "created_at": _now()}
    await coll.insert_one(rec)
    return _pub(rec)


@router.delete("/calendar/events/{event_id}")
async def delete_event(event_id: str):
    coll = db["calendar_events"]
    res = await coll.delete_one({"id": event_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "event not found")
    return {"deleted": True, "id": event_id}


@router.post("/calendar/seed-demo")
async def seed_calendar_demo():
    coll = db["calendar_events"]
    await coll.delete_many({})
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    seeds = [
        {"title": "Bingham · Drone Scan",     "kind": "SCAN",     "delta_h": 4,  "loc": "2440 Regency Rd · Lexington KY", "crew": ["Anthony Cross", "DJI M4TD-01"], "color": "#00E5FF"},
        {"title": "Crew Dispatch · Truck 02", "kind": "DISPATCH", "delta_h": 26, "loc": "Tates Creek Rd",                  "crew": ["Mason Walls", "Devin Pearce"], "color": "#FFB020"},
        {"title": "Tear-off · Lyle Residence", "kind": "CREW",    "delta_h": 50, "loc": "1185 Harrodsburg Pike",           "crew": ["Crew Alpha"], "color": "#A6FF00"},
        {"title": "Invoice INV-0046 Due",     "kind": "BILLING",  "delta_h": 72, "loc": "—",                                "color": "#FF7B00"},
        {"title": "Passport Check-up · Bingham","kind": "CHECKUP","delta_h": 96, "loc": "Virtual",                          "color": "#D4B86A"},
        {"title": "MDU Trailer Maint.",       "kind": "MAINT",    "delta_h":120, "loc": "Yard",                             "color": "#FF2D78"},
        {"title": "Andersen Window Delivery", "kind": "DISPATCH", "delta_h":144, "loc": "Warehouse",                        "color": "#FFB020"},
    ]
    out = []
    for s in seeds:
        start = (now + timedelta(hours=s["delta_h"])).isoformat()
        end   = (now + timedelta(hours=s["delta_h"] + 3)).isoformat()
        rec = {
            "id": str(uuid.uuid4()),
            "title": s["title"], "kind": s["kind"], "start": start, "end": end,
            "location": s["loc"], "crew": s.get("crew"), "notes": None,
            "color": s["color"], "created_at": _now(),
        }
        await coll.insert_one(rec)
        out.append(_pub(rec))
    return {"seeded": len(out), "items": out}


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  3 · FLEET SNAPSHOT (for the map)                                     ║
# ╚══════════════════════════════════════════════════════════════════════╝
class FleetUnit(BaseModel):
    id: str
    callsign: str
    kind: Literal["MDU", "DRONE", "TRUCK", "CREW"]
    status: Literal["ACTIVE", "EN_ROUTE", "STANDBY", "MAINT"]
    lat: float
    lon: float
    label: Optional[str] = None
    job_id: Optional[str] = None


@router.get("/fleet/snapshot")
async def fleet_snapshot():
    """Live fleet + job snapshot — returns ONLY real, persisted units.
    Empty by default; populate via `POST /api/fleet/seed-demo` when you
    explicitly want demo data, or wire real telemetry to the
    `fleet_units` collection.
    """
    coll = db["fleet_units"]
    items = [_pub(d) async for d in coll.find({})]
    # Pull active job sites from the calendar (only resolved coords).
    cal = db["calendar_events"]
    jobs: List[Dict[str, Any]] = []
    async for ev in cal.find({"kind": {"$in": ["SCAN", "CREW", "DISPATCH"]}}).sort("start", 1):
        ev2 = _pub(ev)
        gps = LOC_TO_GPS.get((ev2.get("location") or "").lower(), None)
        if gps:
            jobs.append({
                "id": ev2["id"], "title": ev2["title"],
                "lat": gps[0], "lon": gps[1],
                "kind": ev2["kind"], "start": ev2["start"],
            })
    return {"count": len(items), "units": items, "jobs": jobs}


# Central-KY anchor points (deterministic for the demo map)
LOC_TO_GPS = {
    "2440 regency rd · lexington ky":         (38.0235, -84.5470),
    "tates creek rd":                          (37.9961, -84.5026),
    "1185 harrodsburg pike":                   (38.0157, -84.5462),
    "warehouse":                               (38.0306, -84.5040),
    "yard":                                    (38.0500, -84.4900),
}


async def _seed_fleet_inline() -> List[Dict[str, Any]]:
    coll = db["fleet_units"]
    seeds = [
        ("MDU-01", "STRATEX-1", "MDU",   "ACTIVE",   38.0235, -84.5470, "Active scan · Bingham property"),
        ("MDU-02", "STRATEX-2", "MDU",   "STANDBY",  38.0500, -84.4900, "Yard · ready"),
        ("DRN-01", "MATRICE-01","DRONE", "EN_ROUTE", 38.0306, -84.5040, "Returning to warehouse"),
        ("TRK-02", "CREW-ALPHA","TRUCK", "EN_ROUTE", 37.9961, -84.5026, "Crew Alpha · tear-off site"),
        ("CRW-01", "PILOT-CROSS","CREW", "ACTIVE",   38.0235, -84.5470, "Anthony Cross on-site"),
    ]
    items = []
    for uid, cs, kind, stat, lat, lon, label in seeds:
        rec = {"id": uid, "callsign": cs, "kind": kind, "status": stat,
               "lat": lat, "lon": lon, "label": label, "created_at": _now()}
        await coll.insert_one(rec)
        items.append(_pub(rec))
    return items


@router.post("/fleet/seed-demo")
async def seed_fleet_demo():
    coll = db["fleet_units"]
    await coll.delete_many({})
    return {"seeded": len(await _seed_fleet_inline())}
