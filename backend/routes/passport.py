"""STRATEX™ Property Passport — persistence + public portal + weather.

This module ships the three capabilities promised to American Roofing Co.:

  1. MongoDB-backed immutable passport archive.  Each passport is a record
     in `property_passports`; every mutating event appends a new entry to
     the passport's `ledger` array.  Each ledger entry carries a SHA-256
     `entry_hash` chained to the previous entry — tamper-evident.

  2. Public read-only portal.  `/api/passport/{hash}` is unauthenticated
     by design: it is the link the homeowner forwards to their insurance
     adjuster.

  3. Live weather correlation.  The Weather Shield ribbon is now sourced
     from Open-Meteo's archive API (free, no key) for the property's
     exact GPS coordinates over the last 30 days.

The legacy `/api/demo/property-passport.pdf` endpoint still works for
ad-hoc demo issuance; it now writes through this archive transparently.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from core import db
from stratex_auth import _extract_user

router = APIRouter(prefix="/api/passport", tags=["passport"])

# Legacy Passport mutation containment (C-P-001C): public portal must never
# author passport truth. Privileged operators only.
_PRIV_ROLES = {"admin", "ceo"}

OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

# Lexington KY (American Roofing Co. demo property)
DEFAULT_LAT = 38.0406
DEFAULT_LON = -84.5037

# ──────────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────────
class WeatherEvent(BaseModel):
    date: str                # ISO yyyy-mm-dd
    kind: str                # WIND · HAIL · RAIN
    value: str               # human-readable ("47 mph", "0.5 in")
    severity: str = "PASS"   # PASS · WATCH · BREACH
    wind_max_mph: Optional[float] = None
    gust_max_mph: Optional[float] = None
    precip_in: Optional[float] = None


class LedgerEntry(BaseModel):
    seq: int
    event: str                          # BASELINE / STORM / AUDIT / CLAIM / CHECKUP / TRANSFER
    note: Optional[str] = None
    status: str = "OK"                  # OK / ACTION / FAIL
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    prev_hash: Optional[str] = None
    entry_hash: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class PassportIssueBody(BaseModel):
    owner: str                          # Property Owner of Record
    address: str
    city_state: str
    year_built: Optional[int] = None
    lat: float = DEFAULT_LAT
    lon: float = DEFAULT_LON
    contractor: Optional[Dict[str, Any]] = None
    initial_status: str = "CERTIFIED HEALTHY"   # CERTIFIED HEALTHY / MONITOR · TIER B / ACTION REQUIRED
    envelope_score: int = 92
    moisture_pct: float = 12.0
    facets: Optional[int] = None
    squares: Optional[float] = None
    accuracy_cm: float = 0.78


# ──────────────────────────────────────────────────────────────────────────
# Hash chain
# ──────────────────────────────────────────────────────────────────────────
def _hash_entry(entry: Dict[str, Any]) -> str:
    """Deterministic SHA-256 of the entry's stable fields (excluding hash)."""
    payload = {k: v for k, v in entry.items() if k not in ("entry_hash",)}
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _append_ledger(passport: Dict[str, Any], event: str, note: str = "",
                   status: str = "OK", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ledger: List[Dict[str, Any]] = passport.get("ledger", [])
    prev_hash = ledger[-1]["entry_hash"] if ledger else None
    entry = {
        "seq": len(ledger) + 1,
        "event": event,
        "note": note,
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(),
        "prev_hash": prev_hash,
        "payload": payload or {},
    }
    entry["entry_hash"] = _hash_entry(entry)
    ledger.append(entry)
    passport["ledger"] = ledger
    passport["updated_at"] = entry["at"]
    return entry


def _passport_hash(owner: str, address: str, scan_date: str) -> str:
    """The 12-char public Passport short-hash (URL-friendly)."""
    seed = f"{owner}|{address}|{scan_date}"
    return hashlib.sha1(seed.encode()).hexdigest()[:12].upper()


# ──────────────────────────────────────────────────────────────────────────
# Weather Shield — Open-Meteo archive, no API key needed
# ──────────────────────────────────────────────────────────────────────────
async def _fetch_weather_shield(lat: float, lon: float, days: int = 30) -> List[WeatherEvent]:
    """Pull the last `days` of daily weather from the property's GPS.
    Returns ordered list of meaningful events (top-4 by wind gust + precip).
    """
    end = (datetime.now(timezone.utc) - timedelta(days=4)).date()
    start = end - timedelta(days=days - 1)
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "timezone": "auto",
        "daily": "weather_code,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as c:
            r = await c.get(OPEN_METEO_ARCHIVE, params=params)
            r.raise_for_status()
            j = r.json()
    except Exception:
        return []

    daily = j.get("daily", {}) or {}
    times: List[str]   = daily.get("time", []) or []
    gusts: List[float] = daily.get("wind_gusts_10m_max", []) or []
    winds: List[float] = daily.get("wind_speed_10m_max", []) or []
    precs: List[float] = daily.get("precipitation_sum", []) or []
    codes: List[int]   = daily.get("weather_code", []) or []

    events: List[WeatherEvent] = []
    for i, date in enumerate(times):
        g = gusts[i] if i < len(gusts) else None
        w = winds[i] if i < len(winds) else None
        p = precs[i] if i < len(precs) else None
        code = codes[i] if i < len(codes) else None

        kind, value, severity = None, None, "PASS"
        # Hail signature in WMO codes 96 / 99 (thunderstorm w/ hail)
        if code in (96, 99):
            kind = "HAIL"
            value = "≈0.5 in"
            severity = "WATCH"
        elif g and g >= 40:
            kind = "WIND"
            value = f"{g:.0f} mph"
            severity = "WATCH" if g >= 60 else "PASS"
        elif p and p >= 1.0:
            kind = "RAIN"
            value = f"{p:.1f} in"
            severity = "WATCH" if p >= 2.0 else "PASS"
        if not kind:
            continue
        events.append(WeatherEvent(
            date=date, kind=kind, value=value, severity=severity,
            wind_max_mph=w, gust_max_mph=g, precip_in=p,
        ))

    # Top 4 by storm strength
    events.sort(key=lambda e: (e.gust_max_mph or 0) + (e.precip_in or 0) * 20, reverse=True)
    return events[:4]


# ──────────────────────────────────────────────────────────────────────────
# Public DB helpers
# ──────────────────────────────────────────────────────────────────────────
async def _passport_collection():
    return db["property_passports"]


def _public_view(passport: Dict[str, Any]) -> Dict[str, Any]:
    """Strip ObjectId + return JSON-safe shape for public consumers."""
    out = {k: v for k, v in passport.items() if k != "_id"}
    return out


async def _log_blocked_write(request: Request, reason: str,
                             user: Optional[Dict[str, Any]] = None) -> None:
    """Safe audit of blocked Legacy Passport mutations (no secrets)."""
    try:
        await db["legacy_passport_blocked_writes"].insert_one({
            "id": str(uuid.uuid4()),
            "at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "path": request.url.path,
            "method": request.method,
            "ip": request.client.host if request.client else None,
            "user_id": (user or {}).get("id"),
            "user_email": (user or {}).get("email"),
            "actor": "authenticated" if user else "anonymous",
        })
    except Exception:
        # Best-effort audit: a logging failure must never grant access.
        pass


async def require_legacy_passport_writer(request: Request) -> Dict[str, Any]:
    """Gate Legacy Passport mutations to admin/ceo or an existing is_superadmin claim.

    Reads `is_superadmin` from the already-loaded user document when present.
    Does not expand global authorization helpers or invent new privilege paths.
    """
    try:
        user = await _extract_user(request, db)
    except HTTPException:
        await _log_blocked_write(request, "unauthenticated")
        raise HTTPException(
            403, "Legacy Passport writes require an authenticated privileged operator.")
    if user.get("role") not in _PRIV_ROLES and not bool(user.get("is_superadmin")):
        await _log_blocked_write(request, "insufficient_privilege", user)
        raise HTTPException(
            403, "Legacy Passport writes require admin/ceo/superadmin clearance.")
    return user


# ──────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────
async def _create_passport_record(body: PassportIssueBody):
    """Internal mint helper — HTTP surface is gated by require_legacy_passport_writer."""
    coll = await _passport_collection()
    scan_date = datetime.now(timezone.utc).date().isoformat()
    pid = _passport_hash(body.owner, body.address, scan_date)

    existing = await coll.find_one({"passport_id": pid})
    if existing:
        return JSONResponse({"passport_id": pid, "duplicate": True,
                             "view_url": f"/passport/{pid}"})

    # Weather Shield enrichment
    shield = await _fetch_weather_shield(body.lat, body.lon, days=30)

    passport: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "passport_id": pid,
        "owner": body.owner,
        "address": body.address,
        "city_state": body.city_state,
        "lat": body.lat,
        "lon": body.lon,
        "year_built": body.year_built,
        "facets": body.facets,
        "squares": body.squares,
        "accuracy_cm": body.accuracy_cm,
        "envelope_score": body.envelope_score,
        "moisture_pct": body.moisture_pct,
        "initial_status": body.initial_status,
        "contractor": body.contractor or {},
        "scan_date": scan_date,
        "weather_shield": [e.model_dump() for e in shield],
        "weather_source": "open-meteo-archive",
        "ledger": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _append_ledger(passport, "BASELINE",
                   note="Baseline scan recorded · Passport opened.",
                   status="OK", payload={"envelope_score": body.envelope_score})
    for ev in shield:
        if ev.severity != "PASS":
            _append_ledger(passport, "STORM",
                           note=f"{ev.kind} · {ev.value} on {ev.date}",
                           status="OK", payload=ev.model_dump())
    _append_ledger(passport, "AUDIT",
                   note="Forensic envelope audit issued.",
                   status="ACTION" if body.initial_status == "ACTION REQUIRED" else "OK")

    await coll.insert_one(passport)
    return JSONResponse({"passport_id": pid, "view_url": f"/passport/{pid}",
                         "weather_events": len(shield)})


@router.post("/issue")
async def issue_passport(body: PassportIssueBody,
                         _writer=Depends(require_legacy_passport_writer)):
    """Mint a Property Passport. Privileged operators only (C-P-001C)."""
    return await _create_passport_record(body)


@router.get("/{passport_id}")
async def get_passport(passport_id: str):
    """Public read-only fetch.  No auth — this is the carrier link."""
    coll = await _passport_collection()
    pid = passport_id.upper()
    rec = await coll.find_one({"passport_id": pid})
    if not rec:
        raise HTTPException(404, f"passport {pid} not found")
    return JSONResponse(_public_view(rec))


@router.get("/{passport_id}/verify")
async def verify_passport_chain(passport_id: str):
    """Re-hash every ledger entry and confirm the chain is intact."""
    coll = await _passport_collection()
    rec = await coll.find_one({"passport_id": passport_id.upper()})
    if not rec:
        raise HTTPException(404, f"passport {passport_id} not found")
    prev = None
    bad: List[int] = []
    for entry in rec.get("ledger", []):
        if entry.get("prev_hash") != prev:
            bad.append(entry.get("seq"))
        prev = entry.get("entry_hash")
        # Recompute hash and compare
        check = {k: v for k, v in entry.items() if k != "entry_hash"}
        if _hash_entry(check) != entry.get("entry_hash"):
            bad.append(entry.get("seq"))
    return {"passport_id": rec["passport_id"], "ledger_length": len(rec.get("ledger", [])),
            "tamper_evident": len(bad) == 0, "broken_seqs": bad}


@router.post("/{passport_id}/append")
async def append_event(passport_id: str, event: str = Query(...),
                       note: str = Query(""), status: str = Query("OK"),
                       _writer=Depends(require_legacy_passport_writer)):
    """Append a hash-chained event to the passport ledger.
    Allowed events: STORM · AUDIT · CLAIM · CHECKUP · TRANSFER · NOTE
    Privileged operators only (C-P-001C).
    """
    allowed = {"STORM", "AUDIT", "CLAIM", "CHECKUP", "TRANSFER", "NOTE"}
    ev = event.upper()
    if ev not in allowed:
        raise HTTPException(400, f"event must be one of {sorted(allowed)}")
    coll = await _passport_collection()
    pid = passport_id.upper()
    rec = await coll.find_one({"passport_id": pid})
    if not rec:
        raise HTTPException(404, f"passport {pid} not found")
    entry = _append_ledger(rec, ev, note=note, status=status)
    await coll.update_one({"passport_id": pid},
                          {"$set": {"ledger": rec["ledger"],
                                    "updated_at": rec["updated_at"]}})
    return {"passport_id": pid, "appended": entry,
            "ledger_length": len(rec["ledger"])}


@router.get("/{passport_id}/pdf")
async def passport_pdf(passport_id: str):
    """Re-render the stored passport as a tabloid-landscape PDF certificate."""
    coll = await _passport_collection()
    pid = passport_id.upper()
    rec = await coll.find_one({"passport_id": pid})
    if not rec:
        raise HTTPException(404, f"passport {pid} not found")

    # Build the analysis dict the report renderer expects.
    PITCH_DIR = Path(__file__).resolve().parent.parent.parent / "stratex_pitch"
    sys.path.insert(0, str(PITCH_DIR))
    from routes.demo_scan import _compute_totals, _sample_analysis, _render_report_pdf  # noqa: E402

    analysis = _compute_totals(_sample_analysis())
    analysis["_audience"] = "passport"
    analysis["project"]["ownership"] = rec.get("owner", "Property Owner of Record")
    analysis["project"]["address"] = rec.get("address", analysis["project"]["address"])
    analysis["project"]["city_state"] = rec.get("city_state", analysis["project"]["city_state"])
    analysis["project"]["year_built"] = rec.get("year_built", analysis["project"]["year_built"])
    analysis["project"]["scan_date"] = rec.get("scan_date", analysis["project"]["scan_date"])
    if rec.get("facets") is not None:
        analysis["quant"]["facet_count"] = rec["facets"]
    if rec.get("squares") is not None:
        analysis["quant"]["total_squares"] = rec["squares"]
    analysis["envelope_scores"] = analysis.get("envelope_scores", {}) | {
        "overall_envelope": rec.get("envelope_score", 92),
    }
    analysis["water_retention"] = analysis.get("water_retention", {}) | {
        "subsurface_moisture_pct": rec.get("moisture_pct", 12.0),
        "tear_off_recommended": rec.get("initial_status") == "ACTION REQUIRED",
    }
    # Hand the live weather shield to the renderer
    analysis["_weather_shield"] = rec.get("weather_shield", [])
    analysis["_passport_ledger"] = rec.get("ledger", [])
    analysis["_passport_id_override"] = rec["passport_id"]

    return _render_report_pdf(analysis, f"passport-{rec['passport_id'].lower()}")


@router.post("/seed/demo")
async def seed_demo_passport(_writer=Depends(require_legacy_passport_writer)):
    """One-shot demo seeder — creates the American Roofing × Bingham passport
    used in the live pitch.  Safe to re-run; existing record is preserved.
    Privileged operators only (C-P-001C)."""
    body = PassportIssueBody(
        owner="The Bingham Family Trust",
        address="2440 Regency Road",
        city_state="Lexington, KY 40503",
        year_built=1998,
        lat=DEFAULT_LAT,
        lon=DEFAULT_LON,
        facets=11,
        squares=24.31,
        envelope_score=92,
        moisture_pct=12.0,
        initial_status="CERTIFIED HEALTHY",
        contractor={
            "business_name": "American Roofing Company",
            "primary_contact": "Anthony Cross",
            "license_no": "BC-0043",
        },
    )
    return await _create_passport_record(body)
