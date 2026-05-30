"""STRATEX Weather Intelligence routes.

Open-Meteo (forecast + historical) + RainViewer (Doppler radar tiles) +
Claude Haiku 4.5 storm-watch / multi-year analyst. All upstream services
are public and free — no API keys required.
"""
from __future__ import annotations

import json as _json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

import httpx as _httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import Depends, HTTPException
from pydantic import BaseModel

from core import api, current_user, now_iso

OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
RAINVIEWER_MANIFEST = "https://api.rainviewer.com/public/weather-maps.json"

# Lexington, KY default
DEFAULT_LAT = 38.0406
DEFAULT_LON = -84.5037

_WX_CACHE: Dict[str, Tuple[datetime, Any]] = {}


def _wx_cache_get(key: str, ttl_s: int) -> Optional[Any]:
    rec = _WX_CACHE.get(key)
    if not rec:
        return None
    if (datetime.now(timezone.utc) - rec[0]).total_seconds() > ttl_s:
        _WX_CACHE.pop(key, None)
        return None
    return rec[1]


def _wx_cache_put(key: str, value: Any) -> None:
    _WX_CACHE[key] = (datetime.now(timezone.utc), value)


@api.get("/weather/forecast")
async def weather_forecast(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, user=Depends(current_user)):
    """7-day daily forecast from Open-Meteo (free, no API key)."""
    key = f"forecast::{round(lat,3)}::{round(lon,3)}"
    cached = _wx_cache_get(key, ttl_s=600)
    if cached is not None:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "auto",
        "current": "temperature_2m,wind_speed_10m,precipitation,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,sunrise,sunset",
        "forecast_days": 7,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
    }
    try:
        async with _httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(OPEN_METEO_FORECAST, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        raise HTTPException(502, f"forecast upstream failed: {type(e).__name__}")

    out = {"lat": lat, "lon": lon, "source": "open-meteo", **data}
    _wx_cache_put(key, out)
    return out


@api.get("/weather/radar")
async def weather_radar(user=Depends(current_user)):
    """RainViewer global Doppler-radar tile manifest (free, no API key)."""
    cached = _wx_cache_get("radar", ttl_s=120)
    if cached is not None:
        return cached
    try:
        async with _httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(RAINVIEWER_MANIFEST)
            r.raise_for_status()
            m = r.json()
    except Exception as e:
        raise HTTPException(502, f"radar upstream failed: {type(e).__name__}")

    host = m.get("host", "https://tilecache.rainviewer.com")
    past = m.get("radar", {}).get("past", []) or []
    nowcast = m.get("radar", {}).get("nowcast", []) or []
    out = {
        "host": host,
        "generated": m.get("generated"),
        "tile_template": "{host}{path}/256/{z}/{x}/{y}/2/1_1.png",
        "frames": [
            *[{"time": f["time"], "path": f["path"], "kind": "past"} for f in past],
            *[{"time": f["time"], "path": f["path"], "kind": "nowcast"} for f in nowcast],
        ],
    }
    _wx_cache_put("radar", out)
    return out


@api.get("/weather/historical-on-this-day")
async def weather_historical_on_this_day(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    years_back: int = 3,
    user=Depends(current_user),
):
    """Last N years of weather on today's calendar date at the given location."""
    years_back = max(1, min(years_back, 5))
    today = datetime.now(timezone.utc).date()
    rows: List[Dict[str, Any]] = []

    async with _httpx.AsyncClient(timeout=15.0) as c:
        for k in range(1, years_back + 1):
            target_year = today.year - k
            try:
                d = today.replace(year=target_year)
            except ValueError:
                d = today.replace(year=target_year, day=28)
            ds = d.isoformat()
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": ds,
                "end_date": ds,
                "timezone": "auto",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                         "wind_speed_10m_max,wind_gusts_10m_max",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
            }
            try:
                r = await c.get(OPEN_METEO_ARCHIVE, params=params)
                r.raise_for_status()
                j = r.json()
                daily = j.get("daily", {})
                rows.append({
                    "date": ds,
                    "year": target_year,
                    "tmax_f": (daily.get("temperature_2m_max") or [None])[0],
                    "tmin_f": (daily.get("temperature_2m_min") or [None])[0],
                    "precip_in": (daily.get("precipitation_sum") or [None])[0],
                    "wind_max_mph": (daily.get("wind_speed_10m_max") or [None])[0],
                    "gust_max_mph": (daily.get("wind_gusts_10m_max") or [None])[0],
                    "weather_code": (daily.get("weather_code") or [None])[0],
                })
            except Exception as e:
                rows.append({"date": ds, "year": target_year, "error": f"{type(e).__name__}"})

    return {"lat": lat, "lon": lon, "today": today.isoformat(), "rows": rows, "source": "open-meteo-archive"}


class StormWatchBody(BaseModel):
    lat: float = DEFAULT_LAT
    lon: float = DEFAULT_LON
    audience: Literal["admin", "contractor"] = "admin"


@api.post("/weather/storm-watch")
async def weather_storm_watch(body: StormWatchBody, user=Depends(current_user)):
    """Claude Haiku 4.5 watches the 7-day forecast for developing storm systems."""
    key = f"stormwatch::{round(body.lat,3)}::{round(body.lon,3)}::{body.audience}"
    cached = _wx_cache_get(key, ttl_s=900)
    if cached is not None:
        return cached

    fc = await weather_forecast(lat=body.lat, lon=body.lon, user=user)
    daily = fc.get("daily", {})
    days = []
    for i, date in enumerate(daily.get("time", [])[:7]):
        days.append({
            "date": date,
            "tmax_f": (daily.get("temperature_2m_max") or [None])[i],
            "tmin_f": (daily.get("temperature_2m_min") or [None])[i],
            "precip_in": (daily.get("precipitation_sum") or [None])[i],
            "precip_prob_pct": (daily.get("precipitation_probability_max") or [None])[i],
            "wind_max_mph": (daily.get("wind_speed_10m_max") or [None])[i],
            "gust_max_mph": (daily.get("wind_gusts_10m_max") or [None])[i],
            "weather_code": (daily.get("weather_code") or [None])[i],
        })

    audience_brief = {
        "admin": "the STRATEX flight-operations admin (cares about fleet scheduling, no-fly windows, asset risk).",
        "contractor": "a roofing contractor (cares about job scheduling, customer expectations, storm-damage demand).",
    }[body.audience]

    sys_msg = (
        "You are the STRATEX™ storm-watch agent for Central Kentucky. "
        f"Your audience is {audience_brief} "
        "Reply STRICTLY as JSON with keys: risk_level (one of 'calm','watch','warning','severe'), "
        "headline (≤ 70 chars), narrative (2-4 sentences, concrete numbers, no fluff), "
        "developing_systems (array of 0-3 objects with keys: date, kind, confidence_pct, note). "
        "Use only the data provided. Never invent values."
    )
    user_msg = (
        "FORECAST_DATA (Lexington-area, next 7 days):\n"
        + _json.dumps(days, indent=2)
        + "\n\nReturn only the JSON object."
    )

    chat = LlmChat(
        api_key=os.environ.get("EMERGENT_LLM_KEY"),
        session_id=f"stormwatch::{uuid.uuid4()}",
        system_message=sys_msg,
    ).with_model("anthropic", "claude-haiku-4-5-20251001")
    try:
        raw = await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        raise HTTPException(502, f"storm-watch LLM failed: {type(e).__name__}")

    parsed: Dict[str, Any]
    try:
        parsed = _json.loads(raw)
    except Exception:
        s = raw.find("{")
        e = raw.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                parsed = _json.loads(raw[s:e + 1])
            except Exception:
                parsed = {"risk_level": "calm", "headline": "Unable to parse model output",
                          "narrative": raw[:400], "developing_systems": []}
        else:
            parsed = {"risk_level": "calm", "headline": "Unable to parse model output",
                      "narrative": raw[:400], "developing_systems": []}

    out = {
        "lat": body.lat, "lon": body.lon, "audience": body.audience,
        "model": "claude-haiku-4-5",
        "generated_at": now_iso(),
        "verdict": parsed,
        "input_days": days,
    }
    _wx_cache_put(key, out)
    return out


class HistoricalAnalysisBody(BaseModel):
    lat: float = DEFAULT_LAT
    lon: float = DEFAULT_LON
    audience: Literal["admin", "contractor"] = "admin"
    years_back: int = 3


@api.post("/weather/historical-analysis")
async def weather_historical_analysis(body: HistoricalAnalysisBody, user=Depends(current_user)):
    """Claude turns the last N years of on-this-day weather into a concise brief."""
    key = f"hist-analysis::{round(body.lat,3)}::{round(body.lon,3)}::{body.audience}::{body.years_back}"
    cached = _wx_cache_get(key, ttl_s=3600)
    if cached is not None:
        return cached

    hist = await weather_historical_on_this_day(
        lat=body.lat, lon=body.lon, years_back=body.years_back, user=user
    )
    audience_brief = {
        "admin": "the STRATEX flight-ops admin — focus on no-fly trends, wind/gust patterns, fleet readiness.",
        "contractor": "a roofing contractor — focus on storm-cycle demand patterns, scheduling windows, and what to tell customers.",
    }[body.audience]

    sys_msg = (
        "You are the STRATEX™ historical-weather analyst. "
        f"Your audience is {audience_brief} "
        "Reply STRICTLY as JSON: {summary_headline (≤80 chars), "
        "narrative (3-5 sentences, specific numbers from the data, no hedging), "
        "key_signals (array of 2-5 strings, each ≤100 chars), "
        "year_by_year (array same length as input, objects with keys: year, one_line_note)}. "
        "Use only the data provided."
    )
    user_msg = "HISTORICAL_DATA:\n" + _json.dumps(hist["rows"], indent=2) + "\n\nReturn only the JSON object."

    chat = LlmChat(
        api_key=os.environ.get("EMERGENT_LLM_KEY"),
        session_id=f"hist-analysis::{uuid.uuid4()}",
        system_message=sys_msg,
    ).with_model("anthropic", "claude-haiku-4-5-20251001")
    try:
        raw = await chat.send_message(UserMessage(text=user_msg))
    except Exception as e:
        raise HTTPException(502, f"historical-analysis LLM failed: {type(e).__name__}")

    try:
        parsed = _json.loads(raw)
    except Exception:
        s, e = raw.find("{"), raw.rfind("}")
        parsed = _json.loads(raw[s:e + 1]) if (s != -1 and e > s) else {
            "summary_headline": "Unable to parse model output",
            "narrative": raw[:400], "key_signals": [], "year_by_year": [],
        }

    out = {
        "lat": body.lat, "lon": body.lon, "audience": body.audience,
        "today": hist["today"], "rows": hist["rows"],
        "model": "claude-haiku-4-5",
        "generated_at": now_iso(),
        "verdict": parsed,
    }
    _wx_cache_put(key, out)
    return out
