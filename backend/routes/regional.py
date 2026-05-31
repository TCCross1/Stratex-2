"""STRATEX™ Regional Switchboard — REST surface.

Pure addition (preservation lock). Wraps `RegionalSwitchboard` for the CEO's
national-rollup dashboard.

Endpoints (mounted on shared /api router):
  GET  /api/regional/switchboard?local_state=KY — sorted jurisdictions + per-store metrics + national totals
  GET  /api/regional/state/{state}              — drilldown to one state
  POST /api/regional/seed                       — admin/CEO idempotent seed
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Query

from core import api, current_user
from regional_switchboard import SWITCHBOARD, seed_regional_demo


async def _ceo_or_admin(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"ceo", "admin"}:
        raise HTTPException(403, "Executive clearance required")
    return user


def _parse_store_key(store_key: str) -> Dict[str, str]:
    """'Lexington_KY-FLAGSHIP' → {'city': 'Lexington', 'store_id': 'KY-FLAGSHIP'}"""
    if "_" not in store_key:
        return {"city": store_key, "store_id": ""}
    city, store_id = store_key.split("_", 1)
    return {"city": city, "store_id": store_id}


def _build_store_card(state: str, store_key: str) -> Dict[str, Any]:
    parsed = _parse_store_key(store_key)
    metrics = SWITCHBOARD.aggregate_store_metrics(state, parsed["city"], parsed["store_id"])
    nodes = SWITCHBOARD.regional_mesh.get(state, {}).get(store_key, [])
    return {
        "state": state,
        "city": parsed["city"],
        "store_id": parsed["store_id"],
        "callsigns": [n.unit_id for n in nodes],
        "pilots": [n.pilot for n in nodes],
        **metrics,
    }


def _national_totals(state_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    units = 0
    scans = 0
    gross = 0
    opex = 0
    saturated = 0
    total_stores = 0
    for s in state_cards:
        for store in s["stores"]:
            total_stores += 1
            units += store["combined_units"]
            scans += store["accumulated_scans"]
            gross += store["gross_pipeline_sales"]
            opex += store["operational_expense_cost"]
            if store["roi_target_saturation_met"]:
                saturated += 1
    return {
        "units": units,
        "scans": scans,
        "gross_pipeline_sales": gross,
        "operational_expense_cost": opex,
        "projected_mrr": opex,  # license + scan revenue = projected MRR for STRATEX
        "stores_total": total_stores,
        "stores_at_roi": saturated,
        "roi_saturation_pct": round((saturated / total_stores) * 100, 1) if total_stores else 0.0,
    }


@api.get("/regional/switchboard")
async def regional_switchboard(
    local_state: str = Query("KY", description="Pinned-first state"),
    user=Depends(_ceo_or_admin),
):
    if not SWITCHBOARD.regional_mesh:
        seed_regional_demo()

    jurisdictions = SWITCHBOARD.get_sorted_jurisdictions(local_state)
    state_cards: List[Dict[str, Any]] = []
    for state in jurisdictions:
        stores = []
        for store_key in sorted(SWITCHBOARD.regional_mesh.get(state, {}).keys()):
            stores.append(_build_store_card(state, store_key))
        # state-level rollup
        s_units = sum(s["combined_units"] for s in stores)
        s_scans = sum(s["accumulated_scans"] for s in stores)
        s_gross = sum(s["gross_pipeline_sales"] for s in stores)
        s_opex = sum(s["operational_expense_cost"] for s in stores)
        s_sat = sum(1 for s in stores if s["roi_target_saturation_met"])
        state_cards.append({
            "state": state,
            "is_local": state == local_state,
            "store_count": len(stores),
            "stores_at_roi": s_sat,
            "units": s_units,
            "scans": s_scans,
            "gross_pipeline_sales": s_gross,
            "operational_expense_cost": s_opex,
            "stores": stores,
        })
    return {
        "local_state": local_state,
        "states": state_cards,
        "totals": _national_totals(state_cards),
    }


@api.get("/regional/state/{state}")
async def regional_state(state: str, user=Depends(_ceo_or_admin)):
    if not SWITCHBOARD.regional_mesh:
        seed_regional_demo()
    state = state.upper()
    if state not in SWITCHBOARD.regional_mesh:
        raise HTTPException(404, f"State {state} not present in switchboard")
    stores = [_build_store_card(state, k) for k in sorted(SWITCHBOARD.regional_mesh[state].keys())]
    return {"state": state, "stores": stores}


@api.post("/regional/seed")
async def regional_seed(user=Depends(_ceo_or_admin)):
    return seed_regional_demo()
