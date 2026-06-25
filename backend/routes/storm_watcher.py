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
    """Sweep a single passport.  Returns the number of events appended."""
    last_checked_raw = passport.get("storm_watcher_last_checked")
    last_checked = (
        datetime.fromisoformat(last_checked_raw)
        if last_checked_raw else
        datetime.now(timezone.utc) - timedelta(days=30)
    )
    lat = passport.get("lat") or 38.0406
    lon = passport.get("lon") or -84.5037

    new_storms = await _fetch_recent_storms(lat, lon, since=last_checked)

    # De-dupe vs storms already in the ledger (by date+kind+value)
    existing = {
        (e.get("payload") or {}).get("date") + "|" + (e.get("payload") or {}).get("kind", "")
        for e in passport.get("ledger", [])
        if e.get("event") == "STORM"
    }
    appended = 0
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

    # Always touch last_checked even if no events
    passport["storm_watcher_last_checked"] = datetime.now(timezone.utc).isoformat()
    await coll.update_one(
        {"passport_id": passport["passport_id"]},
        {"$set": {
            "ledger": passport["ledger"],
            "updated_at": passport.get("updated_at"),
            "storm_watcher_last_checked": passport["storm_watcher_last_checked"],
        }},
    )
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
