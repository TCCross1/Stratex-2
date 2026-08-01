"""
Materials takeoff from verified / candidate geometry
Stratex Core — Field Test v1

Produces ESTIMATED materials quantities from roof plane measurements.
Never claims VERIFIED without explicit geometry authority.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _sum_area(planes: List[Dict[str, Any]]) -> float:
    total = 0.0
    for p in planes:
        if p.get("truth_classification") == "WITHHELD":
            continue
        a = p.get("area_sqft") or p.get("area") or 0
        try:
            total += float(a)
        except (TypeError, ValueError):
            pass
    return total


def takeoff_from_geometry(
    geometry_candidate: Dict[str, Any],
    *,
    waste_factor: float = 1.10,
    shingles_per_square: float = 3.0,
) -> Dict[str, Any]:
    """
    Build a materials list from geometry planes / measurements.
    All quantities are ESTIMATED unless caller upgrades truth class.
    """
    planes = geometry_candidate.get("planes") or []
    measurements = geometry_candidate.get("measurements") or {}

    area = measurements.get("total_roof_area_sqft")
    if area is None:
        area = _sum_area(planes)
    try:
        area = float(area or 0)
    except (TypeError, ValueError):
        area = 0.0

    squares = (area / 100.0) * waste_factor if area else 0.0
    ridge_lf = float(measurements.get("ridge_length_ft") or 0)
    eave_lf = float(measurements.get("eave_length_ft") or 0)
    hip_lf = float(measurements.get("hip_length_ft") or 0)

    items = [
        {
            "item": "Architectural Shingles",
            "qty": round(squares, 2) if squares else None,
            "unit": "SQ",
            "truth": "ESTIMATED" if squares else "UNKNOWN",
        },
        {
            "item": "Roof Underlayment",
            "qty": round(squares, 2) if squares else None,
            "unit": "SQ",
            "truth": "ESTIMATED" if squares else "UNKNOWN",
        },
        {
            "item": "Ridge Cap",
            "qty": round(ridge_lf, 1) if ridge_lf else None,
            "unit": "LF",
            "truth": "ESTIMATED" if ridge_lf else "UNKNOWN",
        },
        {
            "item": "Ridge Vent",
            "qty": round(ridge_lf * 0.9, 1) if ridge_lf else None,
            "unit": "LF",
            "truth": "PROJECTED" if ridge_lf else "UNKNOWN",
        },
        {
            "item": "Drip Edge",
            "qty": round(eave_lf, 1) if eave_lf else None,
            "unit": "LF",
            "truth": "ESTIMATED" if eave_lf else "UNKNOWN",
        },
        {
            "item": "Hip/Valley Metal",
            "qty": round(hip_lf, 1) if hip_lf else None,
            "unit": "LF",
            "truth": "ESTIMATED" if hip_lf else "UNKNOWN",
        },
        {
            "item": "Starter Strip",
            "qty": round(eave_lf, 1) if eave_lf else None,
            "unit": "LF",
            "truth": "ESTIMATED" if eave_lf else "UNKNOWN",
        },
        {
            "item": "Nails / Fasteners",
            "qty": None,
            "unit": "LOT",
            "truth": "PROJECTED",
        },
    ]

    return {
        "materials": items,
        "basis": {
            "roof_area_sqft": area,
            "squares_with_waste": round(squares, 2),
            "waste_factor": waste_factor,
            "plane_count_used": len([p for p in planes if p.get("truth_classification") != "WITHHELD"]),
        },
        "truth_policy": "All quantities ESTIMATED or PROJECTED from exterior geometry candidates.",
    }


def labor_estimate_from_squares(
    squares: float,
    *,
    hours_per_square: float = 4.0,
    labor_rate: float = 78.0,
) -> Dict[str, Any]:
    if not squares:
        return {"total_hours": None, "total_cost": None, "truth": "UNKNOWN"}
    hours = round(squares * hours_per_square, 1)
    cost = round(hours * labor_rate, 2)
    return {
        "total_hours": hours,
        "total_cost": cost,
        "labor_rate_per_hour": labor_rate,
        "hours_per_square": hours_per_square,
        "truth": "PROJECTED",
        "note": "Planning figures only until verified takeoff and local rates applied.",
    }
