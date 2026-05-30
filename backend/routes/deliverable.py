"""STRATEX Contractor Deliverable Packet — print-ready report contractor hands to homeowner.

Standard Central-KY market pricing (slate-replacement class job). The pricing
builder is shared with the simulation pipeline (routes/simulation.py).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import Depends, HTTPException

from core import api, current_user, db, now_iso

# Standard pricing (Central-KY market, slate replacement-class job).
_DELIVERABLE_PRICING = {
    "labor_per_square_usd": 175.0,
    "tearoff_per_square_usd": 95.0,
    "underlayment_per_square_usd": 28.0,
    "valley_per_lf_usd": 14.50,
    "material_per_square_usd": {
        "Finished Slate": 685.0,
        "Metal Standing Seam": 545.0,
        "Architectural Asphalt": 165.0,
    },
    "permits_fixed_usd": 285.0,
    "overhead_pct": 0.18,
    "margin_pct": 0.22,
}


def _build_pricing(job: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic pricing builder used by both /contractor/deliverable
    and /simulation/run. Single source of truth.
    """
    squares = float(job.get("roof_total_squares", 0) or 0)
    valleys_lf = float(job.get("valleys_lf_total", 0) or 0)
    material = job.get("primary_material", "Architectural Asphalt")
    mat_psq = _DELIVERABLE_PRICING["material_per_square_usd"].get(material, 165.0)
    line_items = [
        {"label": f"Material · {material} ({squares}sq × ${mat_psq:.2f}/sq)",
         "amount": round(squares * mat_psq, 2)},
        {"label": f"Labor · install ({squares}sq × ${_DELIVERABLE_PRICING['labor_per_square_usd']:.2f}/sq)",
         "amount": round(squares * _DELIVERABLE_PRICING["labor_per_square_usd"], 2)},
        {"label": f"Tear-off & disposal ({squares}sq × ${_DELIVERABLE_PRICING['tearoff_per_square_usd']:.2f}/sq)",
         "amount": round(squares * _DELIVERABLE_PRICING["tearoff_per_square_usd"], 2)},
        {"label": f"Underlayment · I&WS + synthetic ({squares}sq × ${_DELIVERABLE_PRICING['underlayment_per_square_usd']:.2f}/sq)",
         "amount": round(squares * _DELIVERABLE_PRICING["underlayment_per_square_usd"], 2)},
        {"label": f"Valley detail · custom step flash ({valleys_lf:.1f} lf × ${_DELIVERABLE_PRICING['valley_per_lf_usd']:.2f}/lf)",
         "amount": round(valleys_lf * _DELIVERABLE_PRICING["valley_per_lf_usd"], 2)},
        {"label": "Permits & dump fees", "amount": _DELIVERABLE_PRICING["permits_fixed_usd"]},
    ]
    anomaly_lines: List[Dict[str, Any]] = []
    for a in job.get("anomalies", []) or []:
        cost = float(a.get("remediation_cost_usd", 0) or 0)
        if cost > 0:
            anomaly_lines.append({
                "label": f"Anomaly {a.get('id')} · {a.get('kind')} · {a.get('remediation')}",
                "amount": cost,
            })
    subtotal = round(sum(li["amount"] for li in line_items) + sum(a["amount"] for a in anomaly_lines), 2)
    overhead = round(subtotal * _DELIVERABLE_PRICING["overhead_pct"], 2)
    margin = round((subtotal + overhead) * _DELIVERABLE_PRICING["margin_pct"], 2)
    total = round(subtotal + overhead + margin, 2)
    return {
        "currency": "USD",
        "line_items": line_items,
        "anomaly_remediations": anomaly_lines,
        "subtotal_usd": subtotal,
        "overhead_pct": _DELIVERABLE_PRICING["overhead_pct"],
        "overhead_usd": overhead,
        "margin_pct": _DELIVERABLE_PRICING["margin_pct"],
        "margin_usd": margin,
        "total_usd": total,
        "valid_for_days": 30,
        "valid_through_iso": (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(),
    }


@api.get("/contractor/deliverable/{job_id}")
async def contractor_deliverable(job_id: str, user=Depends(current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, f"job {job_id} not found")
    role = user.get("role")
    if role == "operator":
        raise HTTPException(403, "operators don't access pricing deliverables")
    # Canonical demo job is open to any authenticated non-operator (investor / showcase).
    is_demo = job_id in ("crown-demo", "AD-KY041") or job.get("is_public_demo") is True
    if role == "contractor" and not is_demo and job.get("contractor_id") != user["id"]:
        raise HTTPException(403, "not your job")

    pricing = _build_pricing(job)
    return {
        "deliverable_id": f"STRATEX-{job.get('project_code') or job_id}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "generated_at": now_iso(),
        "platform": {"name": "STRATEX™", "tagline": "Strategic Thermal Reconnaissance", "report_version": "1.2.0"},
        "contractor": {
            "company": job.get("contractor_company") or "—",
            "professional_name": job.get("professional_name") or "",
            "license_number": job.get("contractor_license") or "",
            "address": "Lexington, KY · Central Kentucky Service Region",
        },
        "client": {
            "name": job.get("client_name") or "—",
            "email": job.get("client_email") or "—",
            "phone": job.get("client_phone") or "—",
        },
        "site": {"address": job.get("site_address") or "—", "lat": job.get("site_lat"), "lng": job.get("site_lng")},
        "flight": {
            "project_code": job.get("project_code") or job_id,
            "pilot_name": job.get("pilot_name") or "—",
            "started_at": job.get("flight_started_at"),
            "completed_at": job.get("flight_completed_at"),
            "weather": job.get("weather_snapshot") or {},
            "telemetry": job.get("telemetry_summary") or {},
        },
        "roof": {
            "total_squares": job.get("roof_total_squares"),
            "total_sqft": job.get("roof_total_sqft"),
            "valleys_lf_total": job.get("valleys_lf_total"),
            "primary_material": job.get("primary_material"),
            "sub_layer_material": job.get("sub_layer_material"),
            "facets": job.get("facets") or [],
        },
        "anomalies": job.get("anomalies") or [],
        "moisture_diagnostics": job.get("moisture_diagnostics") or [],
        "geometrics_extended": job.get("geometrics_extended") or {},
        "financial_phases": job.get("financial_phases") or {},
        "disposal_logistics": job.get("disposal_logistics") or {},
        "twin_reference_url": job.get("twin_reference_url"),
        "frames_thumbs": job.get("frames_thumbs") or [],
        "pricing": pricing,
    }
