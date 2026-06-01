"""STRATEX™ — Geofence Service & Tripwire Breach Pipeline.

Pure addition (preservation lock). Local geometry — no external API key
required, supports unbounded concurrent zones (one Mongo doc per zone).

Subsystems wired here:
  • Geofence zone init: 150-ft radius circle around a roof centroid.
  • Tripwire array:    contractor profile linked names + phone numbers
                       (Owner / Foreman / Sales Reps), indexed by phone.
  • Breach pipeline:   phone-ping → geofence point-in-circle test →
                       tripwire phone lookup → invoice gate check →
                       Yellow-Triangle alert payload + strike counter.
  • Blacklist engine:  Strike ≥ 2 ⇒ account_status RESTRICTED_PERIMETER_VIOLATION,
                       deliverable endpoints return 403 with that reason.

Collections introduced (additive only):
  • geofence_zones           — active zones per job_id
  • contractor_tripwires     — name+phone tuples per contractor user_id
  • geofence_breach_events   — append-only audit ledger
  • contractor_blacklist     — strike counter + status
"""
from __future__ import annotations

import math
import secrets
import uuid
from typing import Any, Dict, List, Optional

# WGS-84 mean Earth radius in feet.
_EARTH_RADIUS_FT = 20_902_231.0
DEFAULT_GEOFENCE_RADIUS_FT = 150.0


def haversine_distance_ft(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in feet. Pure local math — no API call."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_FT * c


def point_in_zone(point_lat: float, point_lng: float, zone: Dict[str, Any]) -> bool:
    """Return True if (lat,lng) is inside the zone's radius."""
    dist = haversine_distance_ft(point_lat, point_lng, zone["center_lat"], zone["center_lng"])
    return dist <= float(zone.get("radius_ft", DEFAULT_GEOFENCE_RADIUS_FT))


# ---------------------------------------------------------------------------
# Geofence zone CRUD (Mongo-bound; called by /api/geofence routes)
# ---------------------------------------------------------------------------
async def init_zone_for_job(
    db, job_id: str, center_lat: float, center_lng: float,
    initialized_by: str, radius_ft: float = DEFAULT_GEOFENCE_RADIUS_FT,
) -> Dict[str, Any]:
    """Drop a 150-ft radius circle around (lat,lng). One active zone per job."""
    zone_id = str(uuid.uuid4())
    sat_id = f"GFZ-{secrets.randbelow(9000) + 1000}-{secrets.token_hex(2).upper()}"
    doc = {
        "zone_id":         zone_id,
        "job_id":          job_id,
        "center_lat":      float(center_lat),
        "center_lng":      float(center_lng),
        "radius_ft":       float(radius_ft),
        "active":          True,
        "initialized_by":  initialized_by,
        "perimeter_tag":   sat_id,
    }
    # Deactivate any prior zone for this job (additive: history kept via flag flip, no delete).
    await db.geofence_zones.update_many({"job_id": job_id, "active": True}, {"$set": {"active": False}})
    await db.geofence_zones.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


async def get_active_zone(db, job_id: str) -> Optional[Dict[str, Any]]:
    return await db.geofence_zones.find_one({"job_id": job_id, "active": True}, {"_id": 0})


# ---------------------------------------------------------------------------
# Tripwire array CRUD
# ---------------------------------------------------------------------------
def _normalize_phone(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


async def save_contractor_tripwire(
    db, contractor_user_id: str, contacts: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Persist the tripwire array for a contractor. `contacts` is a list of
    {role, name, phone}. Roles required: 'owner', 'foreman', 'sales_rep' (≥1)."""
    norm: List[Dict[str, str]] = []
    for c in contacts:
        role  = (c.get("role") or "").strip().lower()
        name  = (c.get("name") or "").strip()
        phone = _normalize_phone(c.get("phone") or "")
        if role and name and phone:
            norm.append({"role": role, "name": name, "phone": phone, "phone_raw": c.get("phone") or ""})

    await db.contractor_tripwires.update_one(
        {"contractor_user_id": contractor_user_id},
        {"$set": {"contractor_user_id": contractor_user_id, "contacts": norm}},
        upsert=True,
    )
    return {"contractor_user_id": contractor_user_id, "contact_count": len(norm), "contacts": norm}


async def lookup_tripwire_by_phone(db, phone: str) -> Optional[Dict[str, Any]]:
    """Reverse-lookup a phone number across all contractor tripwire arrays."""
    norm = _normalize_phone(phone)
    if not norm:
        return None
    doc = await db.contractor_tripwires.find_one({"contacts.phone": norm}, {"_id": 0})
    if not doc:
        return None
    matched = next((c for c in doc.get("contacts") or [] if c.get("phone") == norm), None)
    if not matched:
        return None
    return {
        "contractor_user_id": doc["contractor_user_id"],
        "matched_contact":    matched,
    }


# ---------------------------------------------------------------------------
# Invoice gate (NO paid invoice on job ⇒ breach is unauthorized).
# Reuses existing `db.invoices` collection if present; falls back to a soft
# "no record" decision when the collection is empty (safer for demos).
# ---------------------------------------------------------------------------
async def job_has_cleared_invoice(db, job_id: str) -> bool:
    if "invoices" not in await db.list_collection_names():
        return False
    doc = await db.invoices.find_one(
        {"job_id": job_id, "status": {"$in": ["paid", "allocated", "paid_or_allocated"]}},
        {"_id": 0, "id": 1},
    )
    return doc is not None


# ---------------------------------------------------------------------------
# Breach event + blacklist engine
# ---------------------------------------------------------------------------
async def record_breach_event(
    db, *, zone: Dict[str, Any], phone_breacher: str,
    breach_lat: float, breach_lng: float, tripwire_match: Dict[str, Any],
    invoice_present: bool, triggered_by: Optional[str], now_iso: str,
) -> Dict[str, Any]:
    breach_id = str(uuid.uuid4())
    event = {
        "breach_id":          breach_id,
        "zone_id":            zone["zone_id"],
        "job_id":              zone["job_id"],
        "phone_breacher":      phone_breacher,
        "breach_lat":          float(breach_lat),
        "breach_lng":          float(breach_lng),
        "contractor_user_id":  tripwire_match["contractor_user_id"],
        "matched_contact":     tripwire_match["matched_contact"],
        "invoice_present":     bool(invoice_present),
        "unauthorized":        not invoice_present,
        "timestamp":           now_iso,
        "triggered_by":        triggered_by,
        "alert_type":          "UNAUTHORIZED_SITE_BREACH" if not invoice_present else "AUTHORIZED_TRIPWIRE_PING",
    }
    await db.geofence_breach_events.insert_one(event)
    return event


async def increment_strike(db, contractor_user_id: str, breach_id: str, now_iso: str) -> Dict[str, Any]:
    """Increment strike counter; flip to RESTRICTED_PERIMETER_VIOLATION at Strike ≥ 2."""
    existing = await db.contractor_blacklist.find_one({"contractor_user_id": contractor_user_id}, {"_id": 0})
    strikes_now = (existing or {}).get("strikes", 0) + 1
    status = "RESTRICTED_PERIMETER_VIOLATION" if strikes_now >= 2 else "WATCHLIST"
    doc = {
        "contractor_user_id": contractor_user_id,
        "strikes":            strikes_now,
        "account_status":     status,
        "last_breach_id":     breach_id,
        "last_updated":       now_iso,
    }
    await db.contractor_blacklist.update_one(
        {"contractor_user_id": contractor_user_id},
        {"$set": doc, "$push": {"breach_history": breach_id}},
        upsert=True,
    )
    return doc


async def is_contractor_restricted(db, contractor_user_id: str) -> Optional[Dict[str, Any]]:
    """Check if a contractor is in RESTRICTED_PERIMETER_VIOLATION. Returns None
    if clean, or the blacklist doc if restricted."""
    doc = await db.contractor_blacklist.find_one(
        {"contractor_user_id": contractor_user_id, "account_status": "RESTRICTED_PERIMETER_VIOLATION"},
        {"_id": 0},
    )
    return doc


async def recent_breach_alerts(db, limit: int = 25) -> List[Dict[str, Any]]:
    """Pull recent UNAUTHORIZED_SITE_BREACH events for the CEO/GM Yellow Triangle widget."""
    cursor = db.geofence_breach_events.find(
        {"alert_type": "UNAUTHORIZED_SITE_BREACH"}, {"_id": 0},
    ).sort("timestamp", -1).limit(int(limit))
    out: List[Dict[str, Any]] = []
    async for d in cursor:
        out.append(d)
    return out
