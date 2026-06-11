"""STRATEX™ Ops Dashboard KPI aggregator — Phase 2 v4.1.

Returns the IMG_2541-aligned 4-KPI tile data + fleet roster + week-ahead
calendar + sales goal + open jobs in ONE call so the cockpit page paints
in a single network round-trip.

Two views, same payload shape, different scopes:
  GET /api/ops/kpis           — CEO/Admin scope: every supplier, every region
  GET /api/ops/kpis/{sup_id}  — supplier-scoped (GM passes own supplier_id)
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from core import api, current_user, db, now_iso


# ---------------------------------------------------------------------------
# Mock fleet pins until WebSocket telemetry lands in Phase 9
# ---------------------------------------------------------------------------

_FLEET_CITY_PINS = [
    {"city": "Seattle, WA",     "lat": 47.61, "lng": -122.33, "units": 3, "phase": "In Flight"},
    {"city": "Portland, OR",    "lat": 45.51, "lng": -122.68, "units": 1, "phase": "Transit"},
    {"city": "Lexington, KY",   "lat": 38.04, "lng":  -84.50, "units": 2, "phase": "Assessment"},
    {"city": "Atlanta, GA",     "lat": 33.74, "lng":  -84.39, "units": 1, "phase": "Data Transfer"},
    {"city": "Dallas, TX",      "lat": 32.78, "lng":  -96.80, "units": 1, "phase": "Landing"},
    {"city": "Phoenix, AZ",     "lat": 33.45, "lng": -112.07, "units": 1, "phase": "Transit"},
    {"city": "Tampa, FL",       "lat": 27.95, "lng":  -82.46, "units": 1, "phase": "In Flight"},
]


async def _aggregate_kpis(supplier_id: Optional[str]) -> Dict[str, Any]:
    """Aggregates the 4 hero KPIs + supporting blocks for an Ops cockpit page."""

    # ---- scope filter for jobs/scans collections ----
    scope: Dict[str, Any] = {}
    if supplier_id:
        scope["supplier_id"] = supplier_id

    # ---- last month / this month boundaries ----
    now = datetime.now(timezone.utc)
    last_month_start = (now - timedelta(days=30)).isoformat()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    scans_completed = await db.scans.count_documents(
        {**scope, "status": "completed", "completed_at_iso": {"$gte": last_month_start}}
    )
    scans_scheduled = await db.scans.count_documents(
        {**scope, "status": "scheduled"}
    )
    # Prior-month baseline for the "+12%" badge
    prev_window_start = (now - timedelta(days=60)).isoformat()
    prev_scans = await db.scans.count_documents(
        {**scope, "status": "completed",
         "completed_at_iso": {"$gte": prev_window_start, "$lt": last_month_start}}
    )
    delta_pct = round(((scans_completed - prev_scans) / prev_scans) * 100, 1) if prev_scans else 12.0

    # ---- Sales Quotes (open job pipeline value) ----
    pipeline_cursor = db.jobs.find(
        {**scope, "status": {"$in": ["quote_sent", "under_review", "pending"]}}
    )
    sales_quotes_count = 0
    sales_quotes_value = 0.0
    async for j in pipeline_cursor:
        sales_quotes_count += 1
        sales_quotes_value += float(j.get("quote_total_usd") or 0)

    # ---- Closed Sales (won deals this month) ----
    closed_cursor = db.jobs.find(
        {**scope, "status": "closed_won", "closed_at_iso": {"$gte": this_month_start}}
    )
    closed_count = 0
    closed_value = 0.0
    async for j in closed_cursor:
        closed_count += 1
        closed_value += float(j.get("quote_total_usd") or 0)

    # ---- Mocked safety net so brand-new tenants still see a populated cockpit ----
    if scans_completed == 0:
        scans_completed = 2854
        scans_scheduled = 147
        sales_quotes_count = 312
        sales_quotes_value = 1_650_400.0
        closed_count = 104
        closed_value = 545_200.0
        delta_pct = 12.0

    # ---- Open Jobs table (latest 6) ----
    open_jobs: List[Dict[str, Any]] = []
    async for j in db.jobs.find({**scope, "status": {"$ne": "closed_won"}}).sort("created_at_iso", -1).limit(6):
        open_jobs.append({
            "job_id": j.get("id"),
            "client_address": j.get("property_address") or "—",
            "quote_usd": float(j.get("quote_total_usd") or 0),
            "date_quoted": (j.get("quoted_at_iso") or j.get("created_at_iso") or "")[:10],
            "status": j.get("status") or "pending",
        })
    if not open_jobs:
        # Cinematic demo seed
        open_jobs = [
            {"job_id": f"Job 10{12 + i}", "client_address": addr, "quote_usd": amt,
             "date_quoted": "2026-05-20", "status": st}
            for i, (addr, amt, st) in enumerate([
                ("742 Maple St, Seattle",   15200, "Pending Invoice"),
                ("120 Oak Rd, Portland",     9800, "Under Review"),
                ("742 Maple St, Seattle",   19300, "Under Review"),
                ("742 Maple St, Seattle",   15200, "Pending"),
                ("120 Oak Rd, Portland",     9800, "Pending"),
                ("742 Maple St, Seattle",   15200, "Pending"),
            ])
        ]

    # ---- 7-day calendar (current week) ----
    week_start = now - timedelta(days=now.weekday())
    week: List[Dict[str, Any]] = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        # Real scan count if present
        day_start = d.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        day_end   = (d.replace(hour=23, minute=59, second=59)).isoformat()
        cnt = await db.scans.count_documents(
            {**scope, "scheduled_at_iso": {"$gte": day_start, "$lte": day_end}}
        )
        if cnt == 0:
            # Demo-grade fallback variety
            cnt = random.choice([0, 1, 2, 3, 3, 4])
        week.append({
            "date_iso": d.date().isoformat(),
            "day_short": d.strftime("%a").upper(),
            "month_short": d.strftime("%b"),
            "day_num": d.day,
            "scan_count": cnt,
            "weather": random.choice(["clear", "cloud", "rain"]),
            "wind_mph": round(random.uniform(2, 14), 1),
            "rain_prob": random.choice([0, 5, 35, 65, 80]),
        })

    # ---- Sales goal for "Mobile Unit Addition" (cinematic) ----
    # Pulls revenue captured this month as fraction of NEXT_UNIT_COST
    NEXT_UNIT_COST_USD = 750_000
    captured = closed_value if closed_value > 0 else 545_200
    progress_pct = round(min(100, (captured / NEXT_UNIT_COST_USD) * 100), 1)

    # ---- Fleet pins ----
    fleet = []
    for pin in _FLEET_CITY_PINS:
        fleet.append({**pin, "active": True})

    return {
        "generated_at": now_iso(),
        "scope": "supplier" if supplier_id else "stratex",
        "supplier_id": supplier_id,
        "kpis": {
            "scans_completed":    {"value": scans_completed, "delta_pct": delta_pct,
                                   "subtitle": f"Last Month {'+' if delta_pct >= 0 else ''}{delta_pct}%"},
            "scans_scheduled":    {"value": scans_scheduled, "subtitle": "This Month"},
            "sales_quotes":       {"value": sales_quotes_count, "amount_usd": sales_quotes_value,
                                   "subtitle": f"Value: ${sales_quotes_value:,.0f}"},
            "closed_sales":       {"value": closed_count, "amount_usd": closed_value,
                                   "subtitle": f"Value: ${closed_value:,.0f}"},
        },
        "open_jobs": open_jobs,
        "calendar": week,
        "fleet": fleet,
        "sales_goal": {
            "label": "Mobile Unit Addition",
            "captured_usd": captured,
            "target_usd": NEXT_UNIT_COST_USD,
            "progress_pct": progress_pct,
            "footnote": f"+1 Unit Needed · {progress_pct}% to next MDU",
        },
        "fleet_summary": {
            "units_active": sum(p["units"] for p in _FLEET_CITY_PINS),
            "units_idle": 2,
            "total_assets": "2 Drones, 4 Units",
            "month_profit_usd": 125000,
        },
    }


@api.get("/ops/kpis")
async def ceo_ops_kpis(user=Depends(current_user)):
    """CEO/Admin view — global scope across all suppliers."""
    if user.get("role") not in ("ceo", "admin"):
        raise HTTPException(403, "CEO or Admin role required")
    return await _aggregate_kpis(supplier_id=None)


@api.get("/ops/kpis/supplier")
async def gm_ops_kpis(user=Depends(current_user)):
    """GM view — scoped to the GM's own supplier_id (read from JWT)."""
    if user.get("role") not in ("gm", "admin", "ceo"):
        raise HTTPException(403, "GM, Admin, or CEO role required")
    sup_id = user.get("supplier_id")
    if user["role"] == "gm" and not sup_id:
        raise HTTPException(409, "GM account has no supplier_id assigned")
    return await _aggregate_kpis(supplier_id=sup_id)
