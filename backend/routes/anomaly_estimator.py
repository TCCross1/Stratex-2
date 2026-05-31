"""STRATEX™ Structural Anomaly Estimator — REST surface.

Per v3.39 spec:
  POST /api/contractor/anomaly/evaluate              — compute + persist
  GET  /api/contractor/anomaly/tax-table             — state tax map for UI
  GET  /api/contractor/anomaly/scans                 — replay ledger (filterable)
  GET  /api/contractor/anomaly/scans/{scan_id}       — single-scan replay
  GET  /api/contractor/anomaly/delta                 — multi-temporal degradation delta

Auth: contractor + admin + ceo (combined GM-oversight scope).
Pricing: encrypted contractor MaterialsConfig (Fernet/AES-256) → spec defaults fallback.
Persistence: every evaluation is immutably snapshotted; financial values locked at
execution time so historical reports never drift on price/tax changes.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core import api, current_user, db, now_iso
from anomaly_estimator import (
    ANOMALY_ENGINE,
    DEFAULT_TAX_RATES_BY_STATE,
    ANOMALY_TIERS,
)
from materials_pricing import resolve_unit_price_book


# ---------------------------------------------------------------------------
# Auth gate — contractor + admin + ceo (parity with materials_brain routes).
# ---------------------------------------------------------------------------
async def _contractor_admin_or_ceo(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"contractor", "admin", "ceo"}:
        raise HTTPException(403, "Contractor, Admin, or CEO clearance required")
    return user


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class ThermalReading(BaseModel):
    """Single drone-thermal pixel/region reading. Coordinate fields are optional
    so the engine works for both ortho-pixel and georef'd scans."""
    thermal_signature_color: str = Field(..., description="YELLOW | ORANGE | RED | GREEN")
    pixel_damaged_area:      float = Field(..., ge=0, description="Square feet of damage in this region")
    centroid_x:    Optional[float] = None
    centroid_y:    Optional[float] = None
    centroid_lat:  Optional[float] = None
    centroid_lng:  Optional[float] = None
    altitude_ft:   Optional[float] = None
    frame_id:      Optional[str]   = None


class EvaluateAnomalyBody(BaseModel):
    project_id:         str               = Field(..., description="STRATEX job/project id")
    mission_id:         str               = Field(..., description="Drone reconnaissance flight identifier")
    capture_timestamp:  str               = Field(..., description="ISO-8601 of drone capture")
    home_state:         str               = Field(..., min_length=2, max_length=2)
    thermal_matrix:     List[ThermalReading] = Field(..., description="Full drone telemetry array")
    three_d_mesh_id:    Optional[str]     = Field(None, description="Optional reference to /api/jobs/{id}/mesh")


# ---------------------------------------------------------------------------
# Helper — derive a stable pricing_version_id from the active price book.
# Same encrypted-book contents → same version id. Any price change → new id.
# ---------------------------------------------------------------------------
def _pricing_version_id(price_book: Dict[str, Any]) -> str:
    # Pick only the price-bearing keys we use (stable subset).
    keys = (
        "osb_sheet_price",
        "labor_rate_per_hour",
        "labor_rate_per_square",
        "shingle_bundle_price",
        "underlayment_square_price",
    )
    snapshot = {k: price_book.get(k) for k in keys}
    blob = json.dumps(snapshot, sort_keys=True, default=str).encode("utf-8")
    return "pv_" + hashlib.sha256(blob).hexdigest()[:18]


# ---------------------------------------------------------------------------
# POST /evaluate — compute + persist (immutable)
# ---------------------------------------------------------------------------
@api.post("/contractor/anomaly/evaluate")
async def post_evaluate_anomaly(body: EvaluateAnomalyBody, user=Depends(_contractor_admin_or_ceo)) -> Dict[str, Any]:
    """Run the StructuralAnomalyEngine on the supplied thermal matrix, persist
    the full payload + result into `db.anomaly_scans`, and return the ledger."""
    if body.home_state.upper() not in DEFAULT_TAX_RATES_BY_STATE:
        # Allow it through with tax_rate=0.0 (engine handles missing state).
        pass

    # Resolve the caller's encrypted price book (or admin/ceo → defaults).
    # All three roles share the same pricing surface — admins/CEOs running
    # remediation previews see the same numbers contractors do.
    price_book = await resolve_unit_price_book(db, user["id"])

    raw_matrix: List[Dict[str, Any]] = [r.dict() for r in body.thermal_matrix]
    result = ANOMALY_ENGINE.evaluate_moisture_damage_anomalies(
        thermal_matrix_scan=raw_matrix,
        home_state=body.home_state.upper(),
        contractor_price_book=price_book,
    )

    scan_id = str(uuid.uuid4())
    pricing_version_id = _pricing_version_id(price_book)
    persisted_doc = {
        "scan_id":             scan_id,
        "project_id":          body.project_id,
        "mission_id":          body.mission_id,
        "capture_timestamp":   body.capture_timestamp,
        "processed_timestamp": now_iso(),
        "home_state":          body.home_state.upper(),
        "pricing_version_id":  pricing_version_id,
        "three_d_mesh_id":     body.three_d_mesh_id,
        "raw_thermal_matrix":  raw_matrix,
        "calculated_ledger":   result["anomaly_ledger"],
        "tier_counts":         result["tier_counts"],
        "financial_summary":   result["financial_summary"],
        "evaluated_by":        user["id"],
        "evaluated_by_role":   (user.get("role") or "").lower(),
        # Immutability marker — historical scans never re-price.
        "locked":              True,
    }
    await db.anomaly_scans.insert_one(persisted_doc)

    return {
        "ok":                  True,
        "scan_id":             scan_id,
        "pricing_version_id":  pricing_version_id,
        "anomaly_ledger":      result["anomaly_ledger"],
        "tier_counts":         result["tier_counts"],
        "financial_summary":   result["financial_summary"],
        "encryption_channel":  "Fernet/AES-256 (HKDF-SHA256 derived from AES_KEY)",
    }


# ---------------------------------------------------------------------------
# GET /tax-table — drives UI state dropdowns
# ---------------------------------------------------------------------------
@api.get("/contractor/anomaly/tax-table")
async def get_anomaly_tax_table(user=Depends(_contractor_admin_or_ceo)) -> Dict[str, Any]:
    return {
        "tax_rates_by_state": dict(DEFAULT_TAX_RATES_BY_STATE),
        "tiers": {
            color: {
                "severity_index":     t["severity_index"],
                "layer":              t["layer"],
                "item":               t["item"],
                "unit":               t["unit"],
                "coverage_sqft":      t["coverage_sqft"],
                "spec_unit_cost":     t["unit_cost_usd"],
                "spec_labor_per_unit": t["labor_per_unit_hrs"],
                "scaffold":           t["scaffold"],
                "encrypted_price_key": t.get("mc_price_key"),
            }
            for color, t in ANOMALY_TIERS.items()
        },
    }


# ---------------------------------------------------------------------------
# GET /scans — replay ledger (filterable)
# ---------------------------------------------------------------------------
@api.get("/contractor/anomaly/scans")
async def get_anomaly_scans(
    project_id: Optional[str] = None,
    mission_id: Optional[str] = None,
    limit: int = 50,
    user=Depends(_contractor_admin_or_ceo),
) -> Dict[str, Any]:
    """Return historical evaluations. Contractor scope is clamped to their own
    evaluations; admin/CEO see all."""
    limit = max(1, min(int(limit or 50), 200))
    role = (user.get("role") or "").lower()
    query: Dict[str, Any] = {}
    if role == "contractor":
        query["evaluated_by"] = user["id"]
    if project_id:
        query["project_id"] = project_id
    if mission_id:
        query["mission_id"] = mission_id

    cursor = db.anomaly_scans.find(query, {"_id": 0}).sort("processed_timestamp", -1).limit(limit)
    rows: List[Dict[str, Any]] = []
    async for doc in cursor:
        rows.append(doc)
    return {
        "scans": rows,
        "count": len(rows),
        "scope": "self" if role == "contractor" else "all",
    }


@api.get("/contractor/anomaly/scans/{scan_id}")
async def get_anomaly_scan(scan_id: str, user=Depends(_contractor_admin_or_ceo)) -> Dict[str, Any]:
    doc = await db.anomaly_scans.find_one({"scan_id": scan_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"Scan '{scan_id}' not found")
    role = (user.get("role") or "").lower()
    if role == "contractor" and doc.get("evaluated_by") != user["id"]:
        raise HTTPException(403, "Cross-contractor read not permitted")
    return doc


# ---------------------------------------------------------------------------
# GET /delta — multi-temporal degradation comparison.
# Compares two scans on the same project to measure anomaly expansion.
# ---------------------------------------------------------------------------
@api.get("/contractor/anomaly/delta")
async def get_anomaly_delta(
    project_id: str = Query(..., description="STRATEX project/job id"),
    scan_a:     str = Query(..., description="Older scan_id (baseline)"),
    scan_b:     str = Query(..., description="Newer scan_id (current)"),
    user=Depends(_contractor_admin_or_ceo),
) -> Dict[str, Any]:
    """Surface structural degradation expansion between two timestamped scans
    on the same project — e.g., how much the RED rot footprint grew between
    a baseline and follow-up drone mission. Powers the GM's Multi-Temporal
    Replay view."""
    docs = {}
    async for doc in db.anomaly_scans.find({"project_id": project_id, "scan_id": {"$in": [scan_a, scan_b]}}, {"_id": 0}):
        docs[doc["scan_id"]] = doc
    if scan_a not in docs:
        raise HTTPException(404, f"scan_a '{scan_a}' not found in project")
    if scan_b not in docs:
        raise HTTPException(404, f"scan_b '{scan_b}' not found in project")

    role = (user.get("role") or "").lower()
    if role == "contractor":
        if docs[scan_a].get("evaluated_by") != user["id"] or docs[scan_b].get("evaluated_by") != user["id"]:
            raise HTTPException(403, "Cross-contractor delta not permitted")

    def _tier_sqft(scan: Dict[str, Any]) -> Dict[str, float]:
        out = {"YELLOW": 0.0, "ORANGE": 0.0, "RED": 0.0}
        for entry in scan.get("calculated_ledger") or []:
            tc = (entry.get("thermal_color") or "").upper()
            if tc in out:
                out[tc] = round(out[tc] + float(entry.get("damage_extent_sqft", 0.0) or 0.0), 2)
        return out

    sqft_a = _tier_sqft(docs[scan_a])
    sqft_b = _tier_sqft(docs[scan_b])
    delta_sqft = {
        k: round(sqft_b[k] - sqft_a[k], 2) for k in ("YELLOW", "ORANGE", "RED")
    }
    cost_a = float(docs[scan_a].get("financial_summary", {}).get("gross_combined_phase_cost", 0.0) or 0.0)
    cost_b = float(docs[scan_b].get("financial_summary", {}).get("gross_combined_phase_cost", 0.0) or 0.0)

    return {
        "project_id": project_id,
        "scan_a": {
            "scan_id":     scan_a,
            "captured":    docs[scan_a].get("capture_timestamp"),
            "tier_sqft":   sqft_a,
            "gross_cost":  round(cost_a, 2),
            "pricing_version_id": docs[scan_a].get("pricing_version_id"),
        },
        "scan_b": {
            "scan_id":     scan_b,
            "captured":    docs[scan_b].get("capture_timestamp"),
            "tier_sqft":   sqft_b,
            "gross_cost":  round(cost_b, 2),
            "pricing_version_id": docs[scan_b].get("pricing_version_id"),
        },
        "delta": {
            "tier_sqft_growth":           delta_sqft,
            "total_sqft_growth":          round(sum(delta_sqft.values()), 2),
            "critical_rot_growth_sqft":   delta_sqft["RED"],
            "gross_cost_delta_usd":       round(cost_b - cost_a, 2),
            "pricing_drift_detected":     docs[scan_a].get("pricing_version_id") != docs[scan_b].get("pricing_version_id"),
        },
    }
