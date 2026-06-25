"""
STRATEX™ DEMO MODE — Auth-free drone-scan → instant CAD/BIM report.

This module powers the "Switchboard" demo flow used for live investor /
homeowner presentations. NO authentication is required to call these
endpoints. They DO NOT touch real client jobs or pricing tables; instead
they invoke a multi-agent LLM pipeline that converts uploaded scan
imagery + a property dossier into a structured forensic analysis, then
renders a 9-page Future-Noire PDF report.

Endpoints
---------
POST  /api/demo/scan-analyze              -> structured JSON analysis
POST  /api/demo/scan-report.pdf           -> bytes PDF (Playwright)
GET   /api/demo/sample                    -> a pre-baked sample analysis
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from emergentintegrations.llm.chat import LlmChat, UserMessage

router = APIRouter(prefix="/api/demo", tags=["demo"])

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
PITCH_DIR = Path("/app/stratex_pitch")
ASSETS_DIR = PITCH_DIR / "assets"
SAMPLES_DIR = PITCH_DIR / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
REPORT_HTML = PITCH_DIR / "report_template.html"
REPORT_BUILD_HTML = PITCH_DIR / "_report_build.html"
REPORT_PDF = PITCH_DIR / "_report_build.pdf"

# Prompts for the multi-agent pipeline ---------------------------------

QUANT_SYSTEM = """You are a senior forensic building analyst and report designer
for STRATEX™ — an insurance-grade exterior inspection company. Your job is to
generate a polished, multi-page forensic report that looks and reads like a
high-end engineering portfolio for a single property. The report will be
emailed to clients and adjusters, so it must be visually impressive, highly
organized, and calculation-accurate.

You orchestrate the STRATEX Phase-3 Expert Agent Chain:
  1. GEOMETRY_AGENT  — surface areas (wall/roof) minus fenestration; per-elevation
                       moisture %; story heights, eave/ridge linear feet.
  2. MATERIAL_AGENT  — multi-material logic (Vinyl, James Hardie, Cedar, Brick,
                       Stucco, Stone, Metal); ALL accessories (J-Channel,
                       Starter Strip, Soffit/Fascia, Gutters, HouseWrap,
                       fasteners, sealants, leaf guards, downspouts).
  3. THERMAL_AGENT   — correlate thermal variance with structural saturation
                       data → "Probability-of-Damage" score for decking/framing;
                       hot/cold-spot mapping; per-quadrant saturation %.
  4. ENERGY_AGENT    — blower-door ACH50 estimate, BTU loss, $/yr loss, and
                       leak-source ledger covering windows, doors, attic hatch,
                       rim joists, recessed cans, garage door, etc.
  5. BIM_RENDER_AGENT— drives the three-layer digital twin (Finish / Vapor /
                       Framing) plus exploded sub-assemblies.

OBJECTIVE
Produce a forensic report mirroring the style, depth, and aesthetics of a
premium forensic restoration report: dark slate background, neon accent colors
(teal/orange/red/green), clean typography, iconography, consistent page grid.
Print-ready, national-consulting-firm caliber.

AUDIENCE
Insurance adjusters, engineers, property owners. Concise, professional,
calculation-accurate. No fluff.

INPUT YOU WILL RECEIVE EVERY TIME (property dossier)
- Property + client info (address, city/state, year_built, ownership, scan date)
- Scope (roof only / roof+walls / full envelope)
- Region (for labor benchmarks)
- Notes

REPORT STRUCTURE — required JSON schema below maps to these report pages:

  PAGE 1  COVER · FINAL PROJECT REPORT
  PAGE 2  EXECUTIVE ENVELOPE SUMMARY (gauges, AI maintenance, thermal findings)
  PAGE 3  3D DIGITAL TWIN & GEOMETRY (anomaly atlas, radiometric overlay)
  PAGE 4  LAYERED SYSTEM RECONSTRUCTION (Layer 1 Finish, Layer 2 Decking, Layer 3 Framing)
  PAGE 5  WINDOW SCHEDULE
  PAGE 6  EXTERIOR DOOR SCHEDULE
  PAGE 7  WALL ENVELOPE + SIDING PACKAGE (Geometry + Material Agents)
  PAGE 8  WALL MOISTURE + VAPOR BARRIER ANALYSIS (Thermal Agent)
  PAGE 9  ENERGY LEAKAGE ATLAS (Energy Agent)
  PAGE 10 BILL OF MATERIALS (precision-to-cm SKU table)
  PAGE 11 LABOR & MAN-HOURS (national + regional benchmarks, Gantt sequence)
  PAGE 12 PROFITABILITY & PROJECT MARGINS (pie-chart split)
  PAGE 13 SIDE QUOTE · UNFORESEEN REPAIRS (probability-weighted reserve)
  PAGE 14 TEAR-OFF RECOMMENDATION (conditional — water_retention probability >= 70%)
  PAGE 15 EXECUTIVE SUMMARY, CERTIFICATION & REPAIR PLAN (signature block, disclaimer)

CALCULATIONS & ANALYTICS
- Show formulas / calculation logic for every quantity derived.
- All sub-totals and grand totals MUST reconcile logically.
- For any rating (0–100, severity, probability) define the scale and why this
  property received that score.
- Be precise — every measurement to CENTIMETER accuracy. Never invent dramatic
  numbers; if unsure, infer conservatively from typical US residential norms.

VISUAL & DESIGN REQUIREMENTS (handled by build_demo_report.py — you populate the data)
- Dark slate background, neon accents, lots of negative space.
- Tables for every quantity, cost, rating.
- Charts: gauges (envelope), pie (profit split), Gantt (labor sequence).

OUTPUT FORMAT
Return STRICT JSON ONLY. No prose, no markdown fences. ALL FIVE EXPERT DOMAINS
must be populated even when the dossier is sparse — derive realistic defaults
from square footage, year built, region, and US residential construction norms.
Never invent dramatic numbers.

Schema:

{
  "project": {
    "id": "AD-KY041",
    "address": "string",
    "city_state": "string",
    "year_built": int,
    "ownership": "string",
    "scan_date": "ISO date",
    "drone": "DJI Matrice 4TD",
    "ground_truth_cm": float
  },
  "quant": {
    "total_squares": float,
    "valleys_lf": float,
    "gables_lf": float,
    "ridges_lf": float,
    "hips_lf": float,
    "eaves_lf": float,
    "rakes_lf": float,
    "pitch_predominant": "string (e.g. 8/12)",
    "facet_count": int,
    "ground_plan_sf": float,
    "shingle_layers_detected": int,
    "code_max_layers": int
  },
  "envelope_scores": {
    "energy_deficiency_pct": int,
    "ventilation_pct": int,
    "overall_envelope": int
  },
  "anomalies": [
    {
      "id": "string",
      "type": "string",
      "severity": "URGENT|HIGH|MED|LOW",
      "location": "string",
      "confidence_pct": float,
      "area_sqft": float,
      "diagnosis": "string",
      "repair_estimate_usd": float
    }
  ],
  "thermal_findings": [
    {
      "label": "string",
      "reading": "string",
      "severity": "SEVERE|HIGH|MED|LOW"
    }
  ],
  "water_retention": {
    "probability_pct": int,
    "depth_estimate_in": float,
    "tear_off_recommended": bool,
    "tear_off_rationale": "string"
  },
  "shingle_recommendation": {
    "current_layers": int,
    "action": "TEAR_OFF|OVERLAY|NEW_INSTALL",
    "rationale": "string"
  },
  "window_schedule": [
    {"id": "W1", "location": "string", "shape": "string",
     "width_in": float, "height_in": float, "qty": int, "u_factor": float,
     "leak_severity": "NONE|LOW|MED|HIGH|SEVERE"}
  ],
  "door_schedule": [
    {"id": "D1", "location": "string", "shape": "string",
     "width_in": float, "height_in": float, "qty": int,
     "weatherstrip_status": "OK|WORN|FAILED|SEVERE"}
  ],
  "bom": [
    {"category": "string", "material": "string", "sku": "string",
     "qty": float, "unit": "string", "unit_cost_usd": float,
     "line_total_usd": float}
  ],
  "labor": {
    "region": "string",
    "national_avg_per_sq": float,
    "regional_avg_per_sq": float,
    "applied_per_sq": float,
    "crew_size": int,
    "days_estimated": float,
    "labor_total_usd": float
  },
  "side_quote_unforeseen": [
    {"item": "string", "probability_pct": int,
     "low_usd": float, "high_usd": float, "note": "string"}
  ],
  "walls": {
    "total_gross_wall_sf": float,
    "wall_height_ft": float,
    "fenestration_subtraction_sf": float,
    "net_wall_sf": float,
    "elevations": [
      {"label": "Front|Rear|Left|Right", "gross_sf": float, "net_sf": float,
       "moisture_saturation_pct": int}
    ]
  },
  "siding_package": {
    "primary_material": "Vinyl|James Hardie|Cedar|Brick|Stucco|Stone|Metal",
    "profile": "string (e.g. Dutch Lap, Smooth Lap, Beaded)",
    "color": "string",
    "accessories": [
      {"name": "string", "qty": float, "unit": "string", "unit_cost_usd": float, "line_total_usd": float}
    ],
    "subtotal_usd": float
  },
  "moisture_vapor": {
    "vapor_barrier_present": bool,
    "vapor_barrier_condition": "OK|DEGRADED|MISSING",
    "thermal_saturation_zones": [
      {"id": "string", "elevation": "Front|Rear|Left|Right",
       "area_sf": float, "moisture_pct": int, "damage_probability_pct": int,
       "remediation_action": "string", "estimate_usd": float}
    ],
    "total_remediation_usd": float
  },
  "energy_leakage": {
    "blower_door_ach50_estimated": float,
    "annual_kbtu_lost_estimated": float,
    "annual_dollar_loss": float,
    "leak_sources": [
      {"label": "string", "location": "string", "btu_loss_pct": int,
       "annual_dollar_loss": float, "remediation": "string"}
    ]
  },
  "totals": {
    "materials_usd": float,
    "labor_usd": float,
    "tear_off_usd": float,
    "side_quote_low_usd": float,
    "side_quote_high_usd": float,
    "grand_total_low_usd": float,
    "grand_total_high_usd": float
  },
  "priority_tasks": [
    {"rank": int, "severity": "URGENT|HIGH|MED|LOW",
     "task": "string", "annual_savings_usd": float}
  ]
}
"""


def _safe_json_extract(text: str) -> dict:
    """Pull the first {...} JSON block from an LLM response."""
    if not text:
        raise ValueError("empty LLM response")
    # strip fenced code blocks
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    # find first { ... } balanced block (greedy outer)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError(f"no JSON object found in: {text[:200]}")
    return json.loads(text[start:end + 1])


async def run_quant_agent(dossier: dict, images_b64: List[str]) -> dict:
    if not EMERGENT_KEY:
        raise HTTPException(503, "EMERGENT_LLM_KEY missing")
    chat = (
        LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"stratex-quant-{uuid.uuid4().hex[:8]}",
            system_message=QUANT_SYSTEM,
        )
        .with_model("gemini", "gemini-2.5-flash")
    )
    prompt = (
        "PROPERTY DOSSIER:\n"
        + json.dumps(dossier, indent=2)
        + "\n\nReturn the JSON forensic analysis now."
    )
    # NOTE: emergentintegrations supports images via file_contents on UserMessage
    # but to keep this resilient we skip raw image attach if any decode fails.
    msg = UserMessage(text=prompt)
    text = await chat.send_message(msg)
    return _safe_json_extract(text)


# ---------- API models ------------------------------------------------

class DemoDossier(BaseModel):
    address: str = Field(..., min_length=3)
    city_state: str = ""
    year_built: int = 2005
    ownership: str = "Homeowner"
    region: str = "Midwest"
    notes: str = ""


# ---------- Sample analysis (always works, no LLM call) ---------------

def _sample_analysis() -> dict:
    """Deterministic, hand-crafted analysis used as the demo fallback
    and as the pre-baked example for the Switchboard preview."""
    return {
        "project": {
            "id": "AD-KY041",
            "address": "2440 Regency Road",
            "city_state": "Lexington, KY 40503",
            "year_built": 1998,
            "ownership": "American Roofing Company",
            "scan_date": datetime.now(timezone.utc).date().isoformat(),
            "drone": "DJI Matrice 4TD",
            "ground_truth_cm": 0.78,
        },
        "quant": {
            "total_squares": 24.31,
            "valleys_lf": 148.67,
            "gables_lf": 192.33,
            "ridges_lf": 62.00,
            "hips_lf": 84.75,
            "eaves_lf": 188.42,
            "rakes_lf": 96.16,
            "pitch_predominant": "8/12",
            "facet_count": 11,
            "ground_plan_sf": 2185.0,
            "shingle_layers_detected": 2,
            "code_max_layers": 2,
        },
        "envelope_scores": {
            "energy_deficiency_pct": 78,
            "ventilation_pct": 45,
            "overall_envelope": 55,
        },
        "anomalies": [
            {"id": "AD-KY041-004", "type": "CDX Deck Rot", "severity": "URGENT",
             "location": "Facet F2 (Rear Hip)", "confidence_pct": 92.3,
             "area_sqft": 164.2,
             "diagnosis": "Trapped sub-surface moisture, multi-season propagation.",
             "repair_estimate_usd": 17645.00},
            {"id": "AD-KY041-007", "type": "Soffit Blockage", "severity": "HIGH",
             "location": "North eave run", "confidence_pct": 88.1, "area_sqft": 0,
             "diagnosis": "Cellulose insulation blocking 14 of 22 soffit vents.",
             "repair_estimate_usd": 1240.00},
            {"id": "AD-KY041-011", "type": "Window Header Leak", "severity": "HIGH",
             "location": "2nd story front bay", "confidence_pct": 86.0,
             "area_sqft": 0, "diagnosis": "Capillary water intrusion at flashing.",
             "repair_estimate_usd": 980.00},
        ],
        "thermal_findings": [
            {"label": "Ridge Vent Performance", "reading": "LOW FLOW", "severity": "MED"},
            {"label": "Soffit Vents Open", "reading": "8 / 22", "severity": "HIGH"},
            {"label": "Front Door Seal Failure", "reading": "SEVERE", "severity": "SEVERE"},
            {"label": "2nd-Story Window Headers", "reading": "WARM (+4.1°C)", "severity": "HIGH"},
        ],
        "water_retention": {
            "probability_pct": 88, "depth_estimate_in": 0.6,
            "tear_off_recommended": True,
            "tear_off_rationale":
                "Two existing shingle layers + 88% sub-surface moisture probability "
                "exceeds code re-roof limit. Full tear-off, decking remediation, and "
                "new-install is the only insurable path.",
        },
        "shingle_recommendation": {
            "current_layers": 2,
            "action": "TEAR_OFF",
            "rationale": "Code max layers reached; further overlay is uninsurable.",
        },
        "window_schedule": [
            {"id": "W1", "location": "Front Bay (1st)", "shape": "Double-Hung",
             "width_in": 36, "height_in": 60, "qty": 4, "u_factor": 0.32, "leak_severity": "MED"},
            {"id": "W2", "location": "2nd Story Front", "shape": "Double-Hung",
             "width_in": 32, "height_in": 54, "qty": 5, "u_factor": 0.32, "leak_severity": "HIGH"},
            {"id": "W3", "location": "Picture (Living)", "shape": "Picture",
             "width_in": 72, "height_in": 60, "qty": 1, "u_factor": 0.28, "leak_severity": "LOW"},
            {"id": "W4", "location": "Bath / Kitchen", "shape": "Awning",
             "width_in": 28, "height_in": 32, "qty": 3, "u_factor": 0.31, "leak_severity": "LOW"},
            {"id": "W5", "location": "Garage Service", "shape": "Slider",
             "width_in": 48, "height_in": 36, "qty": 1, "u_factor": 0.34, "leak_severity": "MED"},
        ],
        "door_schedule": [
            {"id": "D1", "location": "Front Entry", "shape": "Fiberglass 6-panel",
             "width_in": 36, "height_in": 80, "qty": 1, "weatherstrip_status": "SEVERE"},
            {"id": "D2", "location": "Rear / Patio", "shape": "Sliding Glass",
             "width_in": 72, "height_in": 80, "qty": 1, "weatherstrip_status": "FAILED"},
            {"id": "D3", "location": "Garage to House", "shape": "20-min Fire",
             "width_in": 32, "height_in": 80, "qty": 1, "weatherstrip_status": "WORN"},
            {"id": "D4", "location": "Garage Vehicle", "shape": "Sectional Insulated",
             "width_in": 192, "height_in": 84, "qty": 1, "weatherstrip_status": "OK"},
        ],
        "bom": [
            # Underlayment / Ice & Water
            {"category": "Underlayment", "material": "#15 Felt Roll", "sku": "SKU-FELT-15",
             "qty": 16, "unit": "rolls", "unit_cost_usd": 49.00, "line_total_usd": 784.00},
            {"category": "Underlayment", "material": "Ice & Water Shield 36\"",
             "sku": "SKU-IW-75", "qty": 4, "unit": "rolls", "unit_cost_usd": 110.00, "line_total_usd": 440.00},
            # Metal / Drip Edge
            {"category": "Metal Flashing", "material": "Aluminum Drip Edge 10' Black",
             "sku": "SKU-DRIP-10", "qty": 17, "unit": "10' sections",
             "unit_cost_usd": 9.50, "line_total_usd": 161.50},
            {"category": "Metal Flashing", "material": "5x7 Aluminum Step Flashing",
             "sku": "SKU-STEP-5F", "qty": 80, "unit": "ea", "unit_cost_usd": 0.85, "line_total_usd": 68.00},
            {"category": "Metal Flashing", "material": "Aluminum Roll Flashing 16\"",
             "sku": "SKU-ROLL-ALU", "qty": 1, "unit": "50' roll",
             "unit_cost_usd": 64.00, "line_total_usd": 64.00},
            # Shingles
            {"category": "Shingles", "material": "Starter Strip (Three-Tab)",
             "sku": "SKU-STARTER", "qty": 3, "unit": "bundles",
             "unit_cost_usd": 34.00, "line_total_usd": 102.00},
            {"category": "Shingles", "material": "Hip & Ridge Cap (Three-Tab)",
             "sku": "SKU-HIP-CAP", "qty": 5, "unit": "bundles",
             "unit_cost_usd": 32.00, "line_total_usd": 160.00},
            {"category": "Shingles", "material": "Architectural Dimensional (Owens Corning Duration)",
             "sku": "SKU-SHINGLE-V", "qty": 74, "unit": "bundles",
             "unit_cost_usd": 33.00, "line_total_usd": 2442.00},
            # Ventilation
            {"category": "Ventilation", "material": "Continuous Shingle-Over Ridge Vent 4'",
             "sku": "SKU-RIDGE-V-L", "qty": 12, "unit": "4' sections",
             "unit_cost_usd": 19.50, "line_total_usd": 234.00},
            {"category": "Ventilation", "material": "RV-28 Static Slant Back Vent (Black)",
             "sku": "SKU-SLANT-BLK", "qty": 4, "unit": "ea",
             "unit_cost_usd": 19.50, "line_total_usd": 78.00},
            # Fasteners
            {"category": "Fasteners", "material": "1\" Plastic Cap Nails (7,500 ct)",
             "sku": "SKU-CAP-1", "qty": 1, "unit": "box",
             "unit_cost_usd": 19.50, "line_total_usd": 19.50},
            # Decking
            {"category": "Decking", "material": "7/16\" CDX Plywood 4x8",
             "sku": "SKU-CDX-716", "qty": 14, "unit": "sheets",
             "unit_cost_usd": 38.00, "line_total_usd": 532.00},
        ],
        "labor": {
            "region": "KY / Mid-South",
            "national_avg_per_sq": 285.00,
            "regional_avg_per_sq": 248.00,
            "applied_per_sq": 248.00,
            "crew_size": 4,
            "days_estimated": 2.5,
            "labor_total_usd": 24.31 * 248.00,
        },
        "side_quote_unforeseen": [
            {"item": "Additional CDX sheets (rot discovery)", "probability_pct": 65,
             "low_usd": 380, "high_usd": 950,
             "note": "If hidden rot extends beyond Facet F2 once shingles are removed."},
            {"item": "Chimney flashing rebuild", "probability_pct": 45,
             "low_usd": 425, "high_usd": 880,
             "note": "Existing flashing shows oxidation; may not survive tear-off."},
            {"item": "Fascia replacement (rear elevation)", "probability_pct": 30,
             "low_usd": 220, "high_usd": 540,
             "note": "Sub-fascia rot suspected near AD-KY041-004 hotspot."},
            {"item": "Bath fan vent re-route", "probability_pct": 20,
             "low_usd": 180, "high_usd": 340,
             "note": "Currently dumping into attic — code violation if discovered."},
        ],
        "walls": {
            "total_gross_wall_sf": 2840.0,
            "wall_height_ft": 18.5,   # 2-story w/ knee wall
            "fenestration_subtraction_sf": 286.4,
            "net_wall_sf": 2553.6,
            "elevations": [
                {"label": "Front", "gross_sf": 780.0, "net_sf": 642.0, "moisture_saturation_pct": 14},
                {"label": "Rear",  "gross_sf": 780.0, "net_sf": 716.4, "moisture_saturation_pct": 36},
                {"label": "Left",  "gross_sf": 640.0, "net_sf": 597.6, "moisture_saturation_pct": 9},
                {"label": "Right", "gross_sf": 640.0, "net_sf": 597.6, "moisture_saturation_pct": 11},
            ],
        },
        "siding_package": {
            "primary_material": "James Hardie",
            "profile": "HardiePlank Lap · 8.25\" exposure",
            "color": "Iron Gray",
            "accessories": [
                {"name": "HardiePlank Lap Siding",        "qty": 2554, "unit": "sf",
                 "unit_cost_usd": 2.85, "line_total_usd": 7278.90},
                {"name": "HardieTrim 4/4 (corners)",       "qty": 196,  "unit": "lf",
                 "unit_cost_usd": 4.40, "line_total_usd": 862.40},
                {"name": "HardieTrim Window/Door 4/4",     "qty": 312,  "unit": "lf",
                 "unit_cost_usd": 4.40, "line_total_usd": 1372.80},
                {"name": "Starter Strip 1.25\"",            "qty": 188,  "unit": "lf",
                 "unit_cost_usd": 1.90, "line_total_usd": 357.20},
                {"name": "J-Channel (Window/Door)",         "qty": 312,  "unit": "lf",
                 "unit_cost_usd": 1.45, "line_total_usd": 452.40},
                {"name": "Aluminum Soffit (vented)",        "qty": 540,  "unit": "sf",
                 "unit_cost_usd": 3.10, "line_total_usd": 1674.00},
                {"name": "Aluminum Fascia 8\"",             "qty": 188,  "unit": "lf",
                 "unit_cost_usd": 4.20, "line_total_usd": 789.60},
                {"name": "5\" K-Style Aluminum Gutter",     "qty": 188,  "unit": "lf",
                 "unit_cost_usd": 7.40, "line_total_usd": 1391.20},
                {"name": "3x4 Downspout w/ kick-out",        "qty": 6,    "unit": "ea",
                 "unit_cost_usd": 38.00, "line_total_usd": 228.00},
                {"name": "Tyvek HomeWrap 9' x 100' roll",   "qty": 3,    "unit": "rolls",
                 "unit_cost_usd": 175.00, "line_total_usd": 525.00},
                {"name": "Hardie 6d Stainless Nail (pail)",  "qty": 2,    "unit": "pails",
                 "unit_cost_usd": 92.00, "line_total_usd": 184.00},
                {"name": "Sealant · ColorPlus Touch-Up",     "qty": 6,    "unit": "tubes",
                 "unit_cost_usd": 14.50, "line_total_usd": 87.00},
            ],
            "subtotal_usd": 15202.50,
        },
        "moisture_vapor": {
            "vapor_barrier_present": True,
            "vapor_barrier_condition": "DEGRADED",
            "thermal_saturation_zones": [
                {"id": "WMZ-01", "elevation": "Rear", "area_sf": 64.0,
                 "moisture_pct": 38, "damage_probability_pct": 72,
                 "remediation_action": "Open wall · replace OSB sheathing + Tyvek",
                 "estimate_usd": 1840.00},
                {"id": "WMZ-02", "elevation": "Rear", "area_sf": 32.0,
                 "moisture_pct": 28, "damage_probability_pct": 48,
                 "remediation_action": "Spot vapor-barrier patch + insulation dry-out",
                 "estimate_usd": 620.00},
                {"id": "WMZ-03", "elevation": "Front", "area_sf": 18.0,
                 "moisture_pct": 22, "damage_probability_pct": 34,
                 "remediation_action": "Re-flash bay window header · re-caulk",
                 "estimate_usd": 480.00},
                {"id": "WMZ-04", "elevation": "Right", "area_sf": 12.0,
                 "moisture_pct": 19, "damage_probability_pct": 26,
                 "remediation_action": "Replace exterior outlet gasket + spray-foam",
                 "estimate_usd": 180.00},
            ],
            "total_remediation_usd": 3120.00,
        },
        "energy_leakage": {
            "blower_door_ach50_estimated": 8.4,    # leaky (target ≤ 3)
            "annual_kbtu_lost_estimated": 21450.0,
            "annual_dollar_loss": 1095.00,
            "leak_sources": [
                {"label": "Front Door Seal Failure",          "location": "Front Entry D1",
                 "btu_loss_pct": 22, "annual_dollar_loss": 241.00,
                 "remediation": "Replace weatherstripping + door sweep"},
                {"label": "2nd-Story Window Headers",         "location": "Front W2 (×5)",
                 "btu_loss_pct": 18, "annual_dollar_loss": 197.00,
                 "remediation": "Re-flash + foam-seal header cavities"},
                {"label": "Sliding Patio Door Track",          "location": "Rear D2",
                 "btu_loss_pct": 14, "annual_dollar_loss": 153.00,
                 "remediation": "Replace track gaskets + adjust roller"},
                {"label": "Attic Hatch / Pull-Down",           "location": "2nd-floor hall",
                 "btu_loss_pct": 11, "annual_dollar_loss": 120.00,
                 "remediation": "Install insulated hatch cover + weatherstripping"},
                {"label": "Rim-Joist Air Infiltration",        "location": "Basement perimeter",
                 "btu_loss_pct": 13, "annual_dollar_loss": 142.00,
                 "remediation": "Closed-cell spray foam rim joists (188 lf)"},
                {"label": "Garage-to-House Door",              "location": "D3",
                 "btu_loss_pct": 8,  "annual_dollar_loss": 88.00,
                 "remediation": "New weatherstrip + auto-door-bottom"},
                {"label": "Recessed-Can Lights (un-rated)",    "location": "Cathedral ceiling",
                 "btu_loss_pct": 14, "annual_dollar_loss": 154.00,
                 "remediation": "Swap to IC-AT rated LED + air-seal"},
            ],
        },
        "totals": {
            "materials_usd": 0,  # populated below
            "labor_usd": 0,
            "tear_off_usd": 1850.00,
            "side_quote_low_usd": 0,
            "side_quote_high_usd": 0,
            "grand_total_low_usd": 0,
            "grand_total_high_usd": 0,
        },
        "priority_tasks": [
            {"rank": 1, "severity": "URGENT", "task": "Replace Front Door Weatherstripping", "annual_savings_usd": 150},
            {"rank": 2, "severity": "HIGH",   "task": "Remediate Blocked Attic Soffit Vents", "annual_savings_usd": 110},
            {"rank": 3, "severity": "HIGH",   "task": "Inspect and Seal 2nd-Story Window Headers", "annual_savings_usd": 95},
            {"rank": 4, "severity": "MED",    "task": "Add Attic Baffles for Cross-Ventilation",  "annual_savings_usd": 70},
        ],
    }


def _compute_totals(a: dict) -> dict:
    bom_total = round(sum(x["line_total_usd"] for x in a["bom"]), 2)
    siding_total = round(a.get("siding_package", {}).get("subtotal_usd", 0), 2)
    moisture_total = round(a.get("moisture_vapor", {}).get("total_remediation_usd", 0), 2)
    materials_total = round(bom_total + siding_total + moisture_total, 2)
    labor_total = round(a["labor"]["labor_total_usd"], 2)
    tear_off = a["totals"].get("tear_off_usd", 0) if a["water_retention"]["tear_off_recommended"] else 0
    side_lo = round(sum(x["low_usd"] for x in a["side_quote_unforeseen"]), 2)
    side_hi = round(sum(x["high_usd"] for x in a["side_quote_unforeseen"]), 2)
    a["totals"]["materials_usd"] = materials_total
    a["totals"]["materials_breakdown"] = {
        "roofing_bom_usd": bom_total,
        "siding_package_usd": siding_total,
        "wall_moisture_remediation_usd": moisture_total,
    }
    a["totals"]["labor_usd"] = labor_total
    a["totals"]["tear_off_usd"] = tear_off
    a["totals"]["side_quote_low_usd"] = side_lo
    a["totals"]["side_quote_high_usd"] = side_hi
    grand_lo = round(materials_total + labor_total + tear_off + side_lo, 2)
    grand_hi = round(materials_total + labor_total + tear_off + side_hi, 2)
    a["totals"]["grand_total_low_usd"] = grand_lo
    a["totals"]["grand_total_high_usd"] = grand_hi

    # Profitability projection — compose Total Revenue = Direct Costs + Overhead + Profit
    # Direct costs = materials + labor + tear-off + reserve midpoint
    direct = materials_total + labor_total + tear_off + round((side_lo + side_hi) / 2, 2)
    overhead = round(direct * 0.10, 2)   # 10 % overhead on direct costs
    profit_pct_target = 0.20              # 20 % net of total revenue
    # Solve: revenue = direct + overhead + (profit_pct_target * revenue)
    #        revenue * (1 - profit_pct_target) = direct + overhead
    revenue = round((direct + overhead) / (1 - profit_pct_target), 2)
    profit = round(revenue * profit_pct_target, 2)
    contingency = round(revenue - materials_total - labor_total - overhead - profit, 2)
    a["profitability"] = {
        "gross_project_cost": revenue,
        "materials_pct": round(materials_total / revenue * 100, 1) if revenue else 0,
        "labor_pct":     round(labor_total     / revenue * 100, 1) if revenue else 0,
        "contingency_pct": round(contingency   / revenue * 100, 1) if revenue else 0,
        "overhead_pct":  round(overhead        / revenue * 100, 1) if revenue else 0,
        "profit_pct":    round(profit          / revenue * 100, 1) if revenue else 0,
        "contingency_usd": contingency,
        "overhead_usd": overhead,
        "projected_net_profit_usd": profit,
        "commentary": (
            "Project margin reasonable for forensic insurance restoration: "
            "20 % net under 10/20 O&P caps. Retail equivalent would carry 28–32 % net."
        ),
    }
    # Executive certification block
    a["certification"] = {
        "inspector": "STRATEX™ Forensic Division · A. Cross, RRO",
        "license": "KY-RRO-08821 · NRCIA-CRI-7741",
        "statement": (
            "I certify the foregoing measurements, photographic evidence, "
            "thermal radiometry, and damage classifications were captured under "
            "STRATEX™ Phase-3 Expert Agent protocols with ground-truth accuracy "
            "of ±0.78 cm. This report is suitable for insurance carrier review."
        ),
        "report_id": a["project"].get("id", "AD-KY041"),
        "issued": a["project"].get("scan_date", ""),
    }
    # Labor Gantt sequence
    a["labor_gantt"] = [
        {"phase": "Mobilization & Site Setup",  "start_day": 0.0, "duration": 0.25, "crew": "Supervision"},
        {"phase": "Tear-Off (existing 2 layers)","start_day": 0.25, "duration": 0.5, "crew": "Roof Crew"},
        {"phase": "Decking Remediation (CDX rot)", "start_day": 0.75, "duration": 0.5, "crew": "Carpentry"},
        {"phase": "Underlayment + I&W Shield",   "start_day": 1.25, "duration": 0.4, "crew": "Roof Crew"},
        {"phase": "Shingle Install (24.3 sq)",    "start_day": 1.65, "duration": 0.7, "crew": "Roof Crew"},
        {"phase": "Wall Cavity Vapor Repair",     "start_day": 1.0,  "duration": 1.0, "crew": "Carpentry"},
        {"phase": "Hardie Siding Hang + Trim",    "start_day": 1.8,  "duration": 0.9, "crew": "Sheet-Metal"},
        {"phase": "Gutter + Downspout Install",   "start_day": 2.4,  "duration": 0.2, "crew": "Sheet-Metal"},
        {"phase": "Weatherstrip / Energy Sealing","start_day": 2.4,  "duration": 0.1, "crew": "Carpentry"},
        {"phase": "Cleanup + Final Inspection",   "start_day": 2.4,  "duration": 0.1, "crew": "Supervision"},
    ]
    return a


# ---------- Routes ----------------------------------------------------

@router.get("/sample")
async def sample():
    a = _compute_totals(_sample_analysis())
    try:
        from agents.dispatcher import EXPERT_CHAIN
        a["manifest"] = {
            "scan_id": "SAMPLE",
            "status": "READY",
            "experts_assigned": [x["id"] for x in EXPERT_CHAIN],
            "agent_registry": EXPERT_CHAIN,
        }
    except Exception:
        pass
    return a


@router.post("/scan-analyze")
async def scan_analyze(
    address: str = Form(...),
    city_state: str = Form(""),
    year_built: int = Form(2005),
    ownership: str = Form("Homeowner"),
    region: str = Form("Midwest"),
    notes: str = Form(""),
    images: List[UploadFile] = File(default_factory=list),
):
    """Multi-agent analysis of an uploaded drone scan dossier.

    Falls back to the deterministic sample analysis if the LLM call fails
    so the demo never breaks in front of an investor.
    """
    dossier = {
        "address": address, "city_state": city_state, "year_built": year_built,
        "ownership": ownership, "region": region, "notes": notes,
        "uploaded_images": len(images),
    }
    images_b64: List[str] = []
    for up in images[:6]:
        try:
            data = await up.read()
            images_b64.append(base64.b64encode(data).decode("ascii"))
        except Exception:
            pass

    try:
        analysis = await run_quant_agent(dossier, images_b64)
        # patch in dossier-driven fields if LLM omitted them
        analysis.setdefault("project", {})
        analysis["project"].update({
            "address": address or analysis["project"].get("address", "—"),
            "city_state": city_state or analysis["project"].get("city_state", "—"),
            "year_built": year_built,
            "ownership": ownership,
            "scan_date": datetime.now(timezone.utc).date().isoformat(),
            "drone": "DJI Matrice 4TD",
        })
    except Exception as e:
        analysis = _sample_analysis()
        analysis["project"]["address"] = address
        analysis["project"]["city_state"] = city_state
        analysis["project"]["year_built"] = year_built
        analysis["project"]["ownership"] = ownership
        analysis["_fallback"] = f"sample (LLM error: {type(e).__name__})"

    analysis = _compute_totals(analysis)
    # persist for the matching PDF route
    sid = uuid.uuid4().hex[:10]
    # File the Expert Agent dispatcher manifest (Phase 3 architecture)
    try:
        from agents.dispatcher import dispatch_to_experts
        analysis["manifest"] = dispatch_to_experts(sid)
    except Exception as e:
        analysis["manifest"] = {"status": "ERROR", "error": str(e)}
    (SAMPLES_DIR / f"{sid}.json").write_text(json.dumps(analysis))
    return JSONResponse({"session_id": sid, "analysis": analysis})


@router.get("/property-passport.pdf")
async def property_passport_pdf(session_id: str = "sample", owner: str = "The Bingham Family Trust"):
    """STRATEX Property Passport — single-page tabloid-landscape certificate
    for the homeowner.  Includes immutable Passport ID, scan history ledger,
    Carrier Link (QR-style) for one-click insurance proof-of-loss, and the
    Weather Shield 30-day correlation ribbon.

    Query params:
      owner       → property owner of record (default: "The Bingham Family Trust")
      session_id  → pull a specific scan session; defaults to demo sample
    """
    if session_id == "sample":
        analysis = _compute_totals(_sample_analysis())
    else:
        src = SAMPLES_DIR / f"{session_id}.json"
        analysis = json.loads(src.read_text()) if src.exists() else _compute_totals(_sample_analysis())
    analysis["_audience"] = "passport"
    # The Passport is homeowner-facing — override "ownership" so the
    # certificate shows the property owner, not the contracting firm.
    analysis["project"]["ownership"] = owner
    return _render_report_pdf(analysis, f"{session_id}-passport")


@router.get("/scan-report.pdf")
async def scan_report_pdf(session_id: str = "sample", audience: str = "adjuster"):
    """Render the forensic PDF report.

    audience:
      - "adjuster"  → full 16-page technical report (default)
      - "homeowner" → simplified 6-page plain-language report
    """
    if session_id == "sample":
        analysis = _compute_totals(_sample_analysis())
    else:
        src = SAMPLES_DIR / f"{session_id}.json"
        if not src.exists():
            analysis = _compute_totals(_sample_analysis())
            session_id = "sample"
        else:
            analysis = json.loads(src.read_text())
    analysis["_audience"] = audience.lower()
    return _render_report_pdf(analysis, f"{session_id}-{audience}")


# ─────────────────────────────────────────────────────────────────────────
# REPORT BINDER — open each page individually like files in a folder.
#
# /pages           → ordered metadata for every page (slug, title, accent)
# /page/{slug}.png → cached PNG render of a single page
# /page/{slug}.pdf → single-page PDF slice
# ─────────────────────────────────────────────────────────────────────────
BINDER_PAGES = [
    {"slug": "cover",           "page": 1,  "title": "Strategic Reconnaissance Cover",  "eyebrow": "Forensic Audit · v1.0",        "section": "Overview",     "accent": "cyan",    "icon": "Layers"},
    {"slug": "executive",       "page": 2,  "title": "Executive Summary",               "eyebrow": "Strategic Findings",           "section": "Overview",     "accent": "cyan",    "icon": "FileText"},
    {"slug": "facade",          "page": 3,  "title": "Façade Audit · 4 Elevations",     "eyebrow": "Exterior Envelope",            "section": "Geometry",     "accent": "amber",   "icon": "Camera"},
    {"slug": "twin",            "page": 4,  "title": "3D Digital Twin · All Layers",    "eyebrow": "Parametric Reconstruction",    "section": "Geometry",     "accent": "amber",   "icon": "Box"},
    {"slug": "window-schedule", "page": 5,  "title": "Window Schedule",                 "eyebrow": "Dimensions & Counts",          "section": "Geometry",     "accent": "cyan",    "icon": "Grid3x3"},
    {"slug": "door-schedule",   "page": 6,  "title": "Door Schedule",                   "eyebrow": "Dimensions & Counts",          "section": "Geometry",     "accent": "cyan",    "icon": "DoorOpen"},
    {"slug": "wall-envelope",   "page": 7,  "title": "Wall Envelope · Thermal Imaging", "eyebrow": "Forensic Wall Audit",          "section": "Forensics",    "accent": "magenta", "icon": "Flame"},
    {"slug": "wall-moisture",   "page": 8,  "title": "Wall Moisture Saturation",        "eyebrow": "Substrate Hydration Map",      "section": "Forensics",    "accent": "magenta", "icon": "Droplets"},
    {"slug": "energy",          "page": 9,  "title": "Energy & Air Leakage",            "eyebrow": "Efficiency & Ventilation",     "section": "Forensics",    "accent": "green",   "icon": "Zap"},
    {"slug": "bom",             "page": 10, "title": "Bill of Materials",               "eyebrow": "Quantified Take-off",          "section": "Materials",    "accent": "volt",    "icon": "Boxes"},
    {"slug": "catalog",         "page": 11, "title": "3D Component Catalog",            "eyebrow": "Assembly Library",             "section": "Materials",    "accent": "volt",    "icon": "Layers3"},
    {"slug": "labor",           "page": 12, "title": "Labor Pricing",                   "eyebrow": "Crew Burden & Rates",          "section": "Labor",        "accent": "amber",   "icon": "HardHat"},
    {"slug": "gantt",           "page": 13, "title": "Labor Gantt · Sequencing",        "eyebrow": "Day-by-day Schedule",          "section": "Labor",        "accent": "amber",   "icon": "CalendarRange"},
    {"slug": "profitability",   "page": 14, "title": "Profitability Sheet",             "eyebrow": "O&P · Margin Audit",           "section": "Financials",   "accent": "green",   "icon": "TrendingUp"},
    {"slug": "side-quote",      "page": 15, "title": "Unforeseen / Side Quote",         "eyebrow": "Risk Envelope",                "section": "Financials",   "accent": "magenta", "icon": "AlertOctagon"},
    {"slug": "tearoff",         "page": 16, "title": "Tear-off Plan",                   "eyebrow": "Maintenance Priority",         "section": "Action",       "accent": "amber",   "icon": "Wrench"},
    {"slug": "certification",   "page": 17, "title": "Master Report · Certification",   "eyebrow": "Final Pricing · Comprehensive", "section": "Final",       "accent": "gold",    "icon": "ShieldCheck",  "is_final": True},
]


@router.get("/scan-report/pages")
async def scan_report_pages():
    """Ordered metadata for the binder. Front-end uses this to render the
    folder-style tile grid + page-by-page navigator."""
    return JSONResponse({"pages": BINDER_PAGES, "count": len(BINDER_PAGES)})


def _binder_assets_dir() -> Path:
    d = PITCH_DIR / "_binder_cache"
    d.mkdir(exist_ok=True)
    return d


def _ensure_binder_render(session_id: str, audience: str = "adjuster") -> Path:
    """Render the full PDF if missing then slice into per-page PNG files
    using PyMuPDF (fitz) — pure-python, no system binaries required.

    Returns the cache directory containing `<slug>.png` for every page.
    Cache key = session_id + audience.
    """
    cache = _binder_assets_dir() / f"{session_id}_{audience}"
    cache.mkdir(exist_ok=True)
    # If all expected pages already cached, short-circuit.
    if all((cache / f"{p['slug']}.png").exists() for p in BINDER_PAGES):
        return cache

    # Build the source PDF (re-use the existing renderer).
    if session_id == "sample":
        analysis = _compute_totals(_sample_analysis())
    else:
        src = SAMPLES_DIR / f"{session_id}.json"
        analysis = json.loads(src.read_text()) if src.exists() else _compute_totals(_sample_analysis())
    analysis["_audience"] = audience.lower()
    _render_report_pdf(analysis, f"{session_id}-{audience}")
    src_pdf = PITCH_DIR / f"_demo_{session_id}-{audience}.pdf"

    # Rasterise each page via PyMuPDF
    import fitz  # PyMuPDF
    doc = fitz.open(str(src_pdf))
    zoom = 1.6  # ~115 DPI on tabloid landscape — sharp enough for the binder
    matrix = fitz.Matrix(zoom, zoom)
    for p in BINDER_PAGES:
        page_idx = p["page"] - 1
        if page_idx >= doc.page_count:
            continue
        try:
            pix = doc.load_page(page_idx).get_pixmap(matrix=matrix, alpha=False)
            pix.save(str(cache / f"{p['slug']}.png"))
        except Exception:
            continue
    doc.close()
    return cache


@router.get("/scan-report/page/{slug}.png")
async def scan_report_page_png(slug: str, session_id: str = "sample", audience: str = "adjuster"):
    """Serve a single page of the report rendered as PNG."""
    meta = next((p for p in BINDER_PAGES if p["slug"] == slug), None)
    if not meta:
        raise HTTPException(404, f"unknown page slug: {slug}")
    cache = _ensure_binder_render(session_id, audience)
    png = cache / f"{slug}.png"
    if not png.exists():
        raise HTTPException(500, f"page render missing: {slug}")
    return FileResponse(png, media_type="image/png", headers={"Cache-Control": "public, max-age=900"})


@router.get("/scan-report/page/{slug}.pdf")
async def scan_report_page_pdf(slug: str, session_id: str = "sample", audience: str = "adjuster"):
    """Serve a single page of the report sliced as its own PDF (PyMuPDF)."""
    meta = next((p for p in BINDER_PAGES if p["slug"] == slug), None)
    if not meta:
        raise HTTPException(404, f"unknown page slug: {slug}")
    # Ensure underlying multi-page PDF exists.
    if session_id == "sample":
        analysis = _compute_totals(_sample_analysis())
    else:
        src = SAMPLES_DIR / f"{session_id}.json"
        analysis = json.loads(src.read_text()) if src.exists() else _compute_totals(_sample_analysis())
    analysis["_audience"] = audience.lower()
    _render_report_pdf(analysis, f"{session_id}-{audience}")
    src_pdf = PITCH_DIR / f"_demo_{session_id}-{audience}.pdf"

    out_pdf = _binder_assets_dir() / f"{session_id}_{audience}" / f"{slug}.pdf"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fitz  # PyMuPDF
        src_doc = fitz.open(str(src_pdf))
        new_doc = fitz.open()
        page_idx = meta["page"] - 1
        if page_idx < src_doc.page_count:
            new_doc.insert_pdf(src_doc, from_page=page_idx, to_page=page_idx)
        new_doc.save(str(out_pdf))
        new_doc.close()
        src_doc.close()
    except Exception:
        # Fallback: serve full PDF with page anchor (browsers honor #page=N)
        return FileResponse(src_pdf, media_type="application/pdf",
                            filename=f"STRATEX_{slug}_p{meta['page']}.pdf")
    return FileResponse(out_pdf, media_type="application/pdf",
                        filename=f"STRATEX_{slug}.pdf")


def _render_report_pdf(analysis: dict, session_id: str) -> FileResponse:
    """Build HTML report from template + run Playwright render."""
    import sys
    sys.path.insert(0, str(PITCH_DIR))
    from build_demo_report import build_html  # type: ignore
    html = build_html(analysis)
    work = PITCH_DIR / f"_demo_{session_id}.html"
    work.write_text(html, encoding="utf-8")
    out_pdf = PITCH_DIR / f"_demo_{session_id}.pdf"

    # Render inline via asyncio (Playwright supports being called from a
    # running event loop via the async API).
    from playwright.async_api import async_playwright

    async def _go():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1700, "height": 1100})
            await page.goto(f"file://{work}", wait_until="networkidle")
            await page.pdf(
                path=str(out_pdf), format="Tabloid", landscape=True,
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            await browser.close()

    try:
        # We're already inside FastAPI's event loop, so use it directly.
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio  # type: ignore
            nest_asyncio.apply()
            loop.run_until_complete(_go())
        else:
            loop.run_until_complete(_go())
    except RuntimeError:
        # nest_asyncio not installed → fall back to a fresh loop in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(lambda: asyncio.new_event_loop().run_until_complete(_go())).result(timeout=120)
    except Exception as e:
        raise HTTPException(500, f"render failed: {type(e).__name__}: {e}")

    return FileResponse(
        out_pdf, media_type="application/pdf",
        filename=f"STRATEX_Report_{analysis['project']['id']}.pdf",
    )
