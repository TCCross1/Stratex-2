"""STRATEX™ — Live Ops Bus.

Three capabilities ship together so the Mission Control front-end can stay
"truly live" without long-polling:

  1. /api/storms/active             — regional active-storm scan
                                       (100-mile radius default)
  2. WS /api/ws/live-ops            — push channel that streams:
                                         • STORM payloads as they land
                                         • ATC re-poll pings every 60s
                                         • CHECKUP calendar-event hints
  3. POST /api/live-ops/storm-tick  — internal helper that storm_watcher
                                       calls after each sweep so the WS
                                       fans out the freshly-detected
                                       events to every connected client.
"""
from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

import httpx
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from core import db

logger = logging.getLogger("stratex.live_ops")

router = APIRouter(prefix="/api", tags=["live-ops"])

OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

# ──────────────────────────────────────────────────────────────────────
# Geo helpers
# ──────────────────────────────────────────────────────────────────────
def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.7613  # earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ──────────────────────────────────────────────────────────────────────
# Regional active storms
# ──────────────────────────────────────────────────────────────────────
async def _fetch_recent_storms(lat: float, lon: float, days: int = 7) -> List[Dict[str, Any]]:
    end = (datetime.now(timezone.utc) - timedelta(days=4)).date()
    start = end - timedelta(days=days - 1)
    params = {
        "latitude": round(lat, 4), "longitude": round(lon, 4),
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "timezone": "auto",
        "daily": "weather_code,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
        "wind_speed_unit": "mph", "precipitation_unit": "inch",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(OPEN_METEO_ARCHIVE, params=params)
            r.raise_for_status()
            j = r.json()
    except Exception as e:
        logger.warning("regional storm fetch failed: %s", e)
        return []
    daily = j.get("daily", {}) or {}
    times = daily.get("time", []) or []
    gusts = daily.get("wind_gusts_10m_max", []) or []
    winds = daily.get("wind_speed_10m_max", []) or []
    precs = daily.get("precipitation_sum", []) or []
    codes = daily.get("weather_code", []) or []
    out: List[Dict[str, Any]] = []
    for i, dt in enumerate(times):
        g = gusts[i] if i < len(gusts) else None
        p = precs[i] if i < len(precs) else None
        code = codes[i] if i < len(codes) else None
        kind = value = severity = None
        if code in (96, 99):
            kind, value, severity = "HAIL", "≈0.5 in", "WATCH"
        elif g and g >= 50:
            kind, value, severity = "WIND", f"{g:.0f} mph", "WATCH" if g >= 60 else "PASS"
        elif p and p >= 1.5:
            kind, value, severity = "RAIN", f"{p:.1f} in", "WATCH" if p >= 2.0 else "PASS"
        if not kind:
            continue
        out.append({
            "date": dt, "kind": kind, "value": value, "severity": severity,
            "wind_max_mph": winds[i] if i < len(winds) else None,
            "gust_max_mph": g, "precip_in": p,
        })
    return out


@router.get("/storms/active")
async def storms_active(
    lat: float = Query(38.0406),
    lon: float = Query(-84.5037),
    radius_miles: int = Query(100, ge=10, le=500),
    days: int = Query(7, ge=1, le=30),
):
    """All passports inside `radius_miles` paired with their newest storm hits.
    The Mission Control map uses this to draw a 100-mile circle and pin storm
    callouts on properties inside it."""
    coll = db["property_passports"]
    in_range: List[Dict[str, Any]] = []
    async for p in coll.find({}):
        plat, plon = p.get("lat"), p.get("lon")
        if plat is None or plon is None:
            continue
        miles = _haversine_miles(lat, lon, plat, plon)
        if miles > radius_miles:
            continue
        storms = await _fetch_recent_storms(plat, plon, days=days)
        in_range.append({
            "passport_id": p["passport_id"],
            "owner": p.get("owner"),
            "address": p.get("address"),
            "lat": plat, "lon": plon,
            "distance_miles": round(miles, 1),
            "storm_count": len(storms),
            "storms": storms[:4],
            "envelope_score": p.get("envelope_score"),
        })

    # Region-level summary
    region_storms = await _fetch_recent_storms(lat, lon, days=days)
    return {
        "region_center": {"lat": lat, "lon": lon, "radius_miles": radius_miles},
        "polled_at": datetime.now(timezone.utc).isoformat(),
        "passport_count": len(in_range),
        "passports_in_range": in_range,
        "region_storms": region_storms,
    }


# ──────────────────────────────────────────────────────────────────────
# WebSocket — live ops bus
# ──────────────────────────────────────────────────────────────────────
_clients: Set[WebSocket] = set()


async def _safe_send(ws: WebSocket, payload: Dict[str, Any]) -> bool:
    try:
        await ws.send_json(payload)
        return True
    except Exception:
        return False


async def fan_out(payload: Dict[str, Any]) -> int:
    """Public broadcast helper — called by storm_watcher when new events land."""
    dead: List[WebSocket] = []
    for c in list(_clients):
        ok = await _safe_send(c, payload)
        if not ok:
            dead.append(c)
    for d in dead:
        _clients.discard(d)
    return len(_clients) - len(dead)


@router.websocket("/ws/live-ops")
async def live_ops_socket(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    try:
        # On connect, send the most recent sweep summary + an ATC ping
        await ws.send_json({
            "type": "WELCOME",
            "at": datetime.now(timezone.utc).isoformat(),
            "clients": len(_clients),
        })
        while True:
            # Keep the connection warm — clients can ping; we ack
            try:
                _ = await asyncio.wait_for(ws.receive_text(), timeout=120)
                await ws.send_json({"type": "PONG",
                                    "at": datetime.now(timezone.utc).isoformat()})
            except asyncio.TimeoutError:
                # No client message — emit a heartbeat so proxies don't drop us
                await ws.send_json({"type": "HEARTBEAT",
                                    "at": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("live-ops socket error: %s", e)
    finally:
        _clients.discard(ws)


@router.post("/live-ops/storm-tick")
async def storm_tick(payload: Dict[str, Any]):
    """Internal endpoint — storm-watcher calls this after each sweep so the
    WS layer immediately forwards new STORM events to connected clients."""
    payload = {**payload, "type": payload.get("type") or "STORM_TICK",
               "at": datetime.now(timezone.utc).isoformat()}
    n = await fan_out(payload)
    return {"broadcast_to": n}


# ──────────────────────────────────────────────────────────────────────
# Background broadcaster — ATC re-poll ping every 60 s
# ──────────────────────────────────────────────────────────────────────
async def broadcast_loop(interval_seconds: int = 60):
    """Lightweight loop: every minute push an ATC_REPOLL signal so all
    connected Mission Control panels know to refresh the live verdict.
    Self-respawning — if any tick raises, sleep briefly and resume so a
    single transient error never silences the channel until restart."""
    while True:
        try:
            await fan_out({
                "type": "ATC_REPOLL",
                "at": datetime.now(timezone.utc).isoformat(),
                "clients": len(_clients),
            })
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("broadcast loop tick failed: %s — resuming in 5s", e)
            await asyncio.sleep(5)
