"""STRATEX™ — Storm Watcher (background ledger ticker).

Iterates every Property Passport every N minutes, polls Open-Meteo for the
property's GPS, and appends a hash-chained STORM event to the ledger when
new high-impact weather (wind ≥ 60 mph gust · rain ≥ 2 in · hail) is
detected since the last poll.

This is the post-meeting "Property Guardian" promise the deck makes — the
homeowner never has to do anything; the system watches for them.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx

from core import db
from routes.passport import (
    OPEN_METEO_ARCHIVE, WeatherEvent, _append_ledger, _hash_entry,
)

logger = logging.getLogger("stratex.storm_watcher")

# Interval between sweeps.  In a production deploy you'd lean on a real
# scheduler (APScheduler, Celery beat); for the demo a coroutine is plenty.
DEFAULT_SWEEP_MINUTES = 30


async def _fetch_recent_storms(lat: float, lon: float, since: datetime) -> List[WeatherEvent]:
    """Pull storm-grade events since `since` for a given GPS coordinate."""
    end = (datetime.now(timezone.utc) - timedelta(days=4)).date()
    start = max(since.date(), end - timedelta(days=29))
    if start > end:
        return []
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": start.isoformat(),
        "end_date":   end.isoformat(),
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
    except Exception as e:
        logger.warning("open-meteo fetch failed: %s", e)
        return []

    daily   = j.get("daily", {}) or {}
    times   = daily.get("time", []) or []
    gusts   = daily.get("wind_gusts_10m_max", []) or []
    winds   = daily.get("wind_speed_10m_max",  []) or []
    precs   = daily.get("precipitation_sum",   []) or []
    codes   = daily.get("weather_code",        []) or []

    storms: List[WeatherEvent] = []
    for i, date in enumerate(times):
        g = gusts[i] if i < len(gusts) else None
        w = winds[i] if i < len(winds) else None
        p = precs[i] if i < len(precs) else None
        code = codes[i] if i < len(codes) else None

        # Only log "storm-grade" — these are the ones the homeowner cares about.
        kind = value = None
        if code in (96, 99):
            kind, value = "HAIL", "≥0.5 in"
        elif g and g >= 60:
            kind, value = "WIND", f"{g:.0f} mph"
        elif p and p >= 2.0:
            kind, value = "RAIN", f"{p:.1f} in"
        if not kind:
            continue
        storms.append(WeatherEvent(
            date=date, kind=kind, value=value, severity="WATCH",
            wind_max_mph=w, gust_max_mph=g, precip_in=p,
        ))
    return storms


async def _tick_one_passport(coll, passport: Dict[str, Any]) -> int:
    """Sweep a single passport.  Returns the number of events appended.

    For every newly-detected storm-grade event we also:
      • Append a STORM entry to the passport's hash-chained ledger
      • Insert a CHECKUP event in `calendar_events` so the operator's
        Mission Control calendar surfaces it automatically — and the
        Fleet/Jobs map can pin it via the passport's GPS.
    """
    last_checked_raw = passport.get("storm_watcher_last_checked")
    last_checked = (
        datetime.fromisoformat(last_checked_raw)
        if last_checked_raw else
        datetime.now(timezone.utc) - timedelta(days=30)
    )
    lat = passport.get("lat") or 38.0406
    lon = passport.get("lon") or -84.5037

    new_storms = await _fetch_recent_storms(lat, lon, since=last_checked)

    existing = {
        (e.get("payload") or {}).get("date") + "|" + (e.get("payload") or {}).get("kind", "")
        for e in passport.get("ledger", [])
        if e.get("event") == "STORM"
    }
    appended = 0
    new_payloads: List[Dict[str, Any]] = []
    for s in new_storms:
        key = f"{s.date}|{s.kind}"
        if key in existing:
            continue
        _append_ledger(
            passport, "STORM",
            note=f"{s.kind} · {s.value} on {s.date} · auto-detected via Open-Meteo",
            status="OK",
            payload=s.model_dump(),
        )
        existing.add(key)
        appended += 1
        new_payloads.append(s.model_dump())

    passport["storm_watcher_last_checked"] = datetime.now(timezone.utc).isoformat()
    await coll.update_one(
        {"passport_id": passport["passport_id"]},
        {"$set": {
            "ledger": passport["ledger"],
            "updated_at": passport.get("updated_at"),
            "storm_watcher_last_checked": passport["storm_watcher_last_checked"],
        }},
    )

    # ── Storm → Calendar bridge ────────────────────────────────────
    # Drop a CHECKUP event on the day after each new storm so the
    # contractor sees it in the shared schedule and the fleet map.
    if new_payloads:
        from uuid import uuid4 as _uuid4
        cal = db["calendar_events"]
        for s in new_payloads:
            try:
                storm_date = datetime.fromisoformat(s["date"])
            except Exception:
                storm_date = datetime.now(timezone.utc)
            checkup_start = (storm_date + timedelta(days=1)).replace(
                hour=14, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
            )
            rec = {
                "id": str(_uuid4()),
                "title": f"Post-storm Check-up · {passport.get('owner', 'Passport')}",
                "kind": "CHECKUP",
                "start": checkup_start.isoformat(),
                "end":   (checkup_start + timedelta(hours=2)).isoformat(),
                "location": passport.get("address", ""),
                "lat": lat, "lon": lon,
                "crew": None,
                "job_id": passport["passport_id"],
                "notes": f"Auto-scheduled after {s['kind']} {s['value']} crossed property GPS.",
                "color": "#D4B86A",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "storm_watcher",
                "storm_payload": s,
            }
            # Idempotent — never duplicate the same storm checkup
            await cal.update_one(
                {"job_id": passport["passport_id"], "kind": "CHECKUP",
                 "storm_payload.date": s["date"], "storm_payload.kind": s["kind"]},
                {"$setOnInsert": rec},
                upsert=True,
            )

        # ── WebSocket push — fan out to every Mission Control client ─
        try:
            from routes.live_ops import fan_out
            await fan_out({
                "type": "STORM_DETECTED",
                "passport_id": passport["passport_id"],
                "owner": passport.get("owner"),
                "address": passport.get("address"),
                "lat": lat, "lon": lon,
                "events": new_payloads,
                "at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as _e:
            logger.warning("live-ops fan-out failed: %s", _e)

    return appended


async def storm_watcher_sweep() -> Dict[str, Any]:
    """One full sweep across every passport."""
    coll = db["property_passports"]
    swept = appended_total = 0
    async for p in coll.find({}):
        swept += 1
        try:
            appended_total += await _tick_one_passport(coll, p)
        except Exception as e:
            logger.exception("sweep failed for %s: %s", p.get("passport_id"), e)
    logger.info("storm-watcher sweep · %d passports · %d events appended",
                swept, appended_total)
    return {"swept": swept, "appended": appended_total,
            "swept_at": datetime.now(timezone.utc).isoformat()}


async def storm_watcher_loop(interval_minutes: int = DEFAULT_SWEEP_MINUTES):
    """Long-running task — sleeps `interval_minutes` between sweeps."""
    while True:
        try:
            await storm_watcher_sweep()
        except Exception as e:
            logger.exception("storm-watcher loop sweep failed: %s", e)
        await asyncio.sleep(interval_minutes * 60)
