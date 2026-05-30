"""STRATEX Branch Manager Console — Master Price Index + Multi-Agent Quantify Pipeline.

The branch manager (supplier-side) owns:
  1. The MASTER PRICE INDEX with Tier 1/2/3 wholesale pricing per SKU.
  2. The QUANTIFY pipeline that takes raw drone telemetry → deterministic math →
     multi-agent AI cross-check → registers the verified payload onto a job.

NOTHING is committed to a job until the multi-AI panel reaches consensus.
"""
from __future__ import annotations

import asyncio
import json as _json
import math
import os
import uuid
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import admin_only, api, current_user, db, logger, now_iso

# ---------------------------------------------------------------------------
# Master Price Index (Branch Manager Override Repository)
# Canonical 10 SKUs per the v2.6 console spec.
# ---------------------------------------------------------------------------
MASTER_PRICE_INDEX = [
    {"id": "shingles_sq",    "sku": "SHINGLE-PREM-SQ",   "name": "Premium Architectural Shingles (Per Sq)",
     "category": "Shingles",    "unit_label": "Square",      "stock_units": 1420,
     "tier1_usd": 34.50,  "tier2_usd": 31.00,  "tier3_usd": 28.50},
    {"id": "felt_roll",      "sku": "FELT-SYN-15",       "name": "Synthetic Felt #15 Underlayment (Per Roll)",
     "category": "Underlayment", "unit_label": "Roll",       "stock_units": 340,
     "tier1_usd": 92.00,  "tier2_usd": 85.00,  "tier3_usd": 78.00},
    {"id": "ice_water_roll", "sku": "IWS-SELF-2SQ",      "name": "Self-Adhering Ice & Water Shield (Per Roll)",
     "category": "Underlayment", "unit_label": "Roll",       "stock_units": 180,
     "tier1_usd": 115.00, "tier2_usd": 104.00, "tier3_usd": 95.00},
    {"id": "drip_edge_ft",   "sku": "DRIP-ALU-LF",       "name": "Aluminum Drip Edge Trim (Per Linear Ft)",
     "category": "Accessories", "unit_label": "Linear Ft",   "stock_units": 8500,
     "tier1_usd": 2.10,   "tier2_usd": 1.85,   "tier3_usd": 1.60},
    {"id": "flashing_ft",    "sku": "FLASH-STEP-LF",     "name": "Wall Counter/Step Flashing Metal (Per Linear Ft)",
     "category": "Accessories", "unit_label": "Linear Ft",   "stock_units": 2100,
     "tier1_usd": 4.50,   "tier2_usd": 4.00,   "tier3_usd": 3.55},
    {"id": "chimney_kit",    "sku": "CHIMNEY-KIT",       "name": "Chimney Roll Flashing & Polyurethane Caulk Combo Pack",
     "category": "Accessories", "unit_label": "Kit",         "stock_units": 95,
     "tier1_usd": 85.00,  "tier2_usd": 75.00,  "tier3_usd": 68.00},
    {"id": "boot_2in",       "sku": "BOOT-2IN",          "name": "Roof Pipe Boot Cover (2-Inch Target Size)",
     "category": "Accessories", "unit_label": "Each",        "stock_units": 240,
     "tier1_usd": 18.00,  "tier2_usd": 16.00,  "tier3_usd": 14.50},
    {"id": "boot_3in",       "sku": "BOOT-3IN",          "name": "Roof Pipe Boot Cover (3-Inch Target Size)",
     "category": "Accessories", "unit_label": "Each",        "stock_units": 180,
     "tier1_usd": 22.00,  "tier2_usd": 19.50,  "tier3_usd": 17.00},
    {"id": "nails_box",      "sku": "FAST-COIL-7200",    "name": "1-1/4 Coil Roofing Fasteners Box (7200 ct)",
     "category": "Fasteners",   "unit_label": "Box",         "stock_units": 320,
     "tier1_usd": 75.00,  "tier2_usd": 70.00,  "tier3_usd": 65.00},
    {"id": "caps_box",       "sku": "FAST-CAP-BOX",      "name": "1\" Plastic Button Cap Mechanical Nails Box",
     "category": "Fasteners",   "unit_label": "Box",         "stock_units": 280,
     "tier1_usd": 48.00,  "tier2_usd": 44.00,  "tier3_usd": 40.00},
]

LABOR_RATE_PER_HOUR_USD = 200.0
WASTE_MULTIPLIER = 1.10                # mandatory 10% waste allocation
SQ_PER_FELT_ROLL = 4                    # 4 sq per roll → 400 sqft
LINEAR_FT_PER_IWS_ROLL = 75
LINEAR_FT_PER_DRIP_PIECE = 10
LABOR_HOURS_PER_SQ = 3.5
LABOR_HOURS_PER_VALLEY_FT = 0.15
DEFAULT_OVERHEAD_PCT = 0.10
DEFAULT_PROFIT_PCT = 0.08
DEFAULT_INSURANCE_MULTIPLIER = 1.04


async def seed_branch_materials() -> Dict[str, int]:
    """Idempotent: makes db.supplier_material_ledger EXACTLY the 10 SKUs above.
    Any other SKUs (legacy / orphaned) get removed so the catalog matches spec."""
    canonical_ids = {m["id"] for m in MASTER_PRICE_INDEX}
    for m in MASTER_PRICE_INDEX:
        await db.supplier_material_ledger.update_one(
            {"id": m["id"]},
            {"$set": {**m, "seeded_at": now_iso(), "seed_source": "MASTER_PRICE_INDEX_v2.6"}},
            upsert=True,
        )
    # Drop legacy SKUs (e.g., the older 6-SKU spec) so the ledger is the canonical 10
    purged = await db.supplier_material_ledger.delete_many({"id": {"$nin": list(canonical_ids)}})
    return {"upserted": len(MASTER_PRICE_INDEX), "purged_legacy": purged.deleted_count}


# ---------------------------------------------------------------------------
# Drone telemetry payload schema (input to /api/branch/quantify)
# ---------------------------------------------------------------------------
class Measurements(BaseModel):
    roofPerimeter_ft: float
    roofArea_sqft: float
    pitch: float = 6
    pitchMultiplier: float = 1.118
    hips_ft: float = 0
    ridges_ft: float = 0
    valleys_ft: float = 0
    overhang_in: float = 18
    housePerimeter_ft: float = 0
    wallAreaGross_sqft: float = 0
    wallHeight_ft: float = 10
    windowOpenings_sqft: float = 0
    doorOpenings_sqft: float = 0
    windowPerimeter_ft: float = 0
    doorPerimeter_ft: float = 0


class MoistureDetection(BaseModel):
    id: str
    level: float = Field(ge=0, le=1)
    placement: str
    target: str
    code: str


class ThermalSensors(BaseModel):
    moistureDetections: List[MoistureDetection] = []
    altitudinalExtensions_ft: float = 0


class PipeBoot(BaseModel):
    count: int = Field(ge=0)
    size_in: int  # 2 or 3


class DroneFinancials(BaseModel):
    overheadPercent: float = 10
    profitPercent: float = 8
    isInsuranceJob: bool = False
    insuranceMultiplier: float = 1.04


class QuantifyBody(BaseModel):
    projectId: str
    job_id: Optional[str] = None
    contractor_id: Optional[str] = None
    assigned_tier: str = "tier2"
    measurements: Measurements
    thermalSensors: ThermalSensors = ThermalSensors()
    pipeBootsData: List[PipeBoot] = []
    financials: DroneFinancials = DroneFinancials()
    register: bool = False  # if true & consensus reached, write to db.jobs


def _tier_key(tier: str) -> str:
    return {"tier1": "tier1_usd", "tier2": "tier2_usd", "tier3": "tier3_usd"}.get(tier, "tier2_usd")


def _format_feet_inches(total_ft: float) -> str:
    feet = int(total_ft)
    inches = round((total_ft - feet) * 12)
    return f"{feet}' {inches}\""


def _deterministic_quantify(body: QuantifyBody, prices: Dict[str, float]) -> Dict[str, Any]:
    """The 4-agent deterministic calculation pipeline.
    All math here is pure & reproducible; the AI agents below VERIFY it.
    """
    m = body.measurements
    # ─── Agent 1: Geometric Math Parser ───────────────────────────────────────
    net_wall_sqft = m.wallAreaGross_sqft - (m.windowOpenings_sqft + m.doorOpenings_sqft)
    adjusted_roof_sqft = m.roofArea_sqft * m.pitchMultiplier
    roof_squares_net = adjusted_roof_sqft / 100.0
    roof_squares_with_waste = roof_squares_net * WASTE_MULTIPLIER

    # ─── Agent 2: Precision Quantities + 10% Waste Allocator ──────────────────
    shingles_needed = math.ceil(roof_squares_with_waste)
    felt_needed     = math.ceil(adjusted_roof_sqft / (SQ_PER_FELT_ROLL * 100))
    iws_needed      = math.ceil(m.valleys_ft / LINEAR_FT_PER_IWS_ROLL) if m.valleys_ft > 0 else 0
    drip_edge_pieces = math.ceil(m.roofPerimeter_ft / LINEAR_FT_PER_DRIP_PIECE) if m.roofPerimeter_ft > 0 else 0

    # ─── Agent 3: Special Pricing + Cost Compilation ──────────────────────────
    lines: List[Dict[str, Any]] = []

    def add_line(item_id: str, qty: float, label_override: Optional[str] = None):
        unit = prices.get(item_id, 0.0)
        line_total = round(qty * unit, 2)
        lines.append({
            "material_id": item_id, "label": label_override or item_id,
            "quantity": qty, "unit_price_usd": unit, "line_total_usd": line_total,
        })
        return line_total

    materials_cost = 0.0
    materials_cost += add_line("shingles_sq",    shingles_needed,
                               f"Premium Architectural Shingles · {shingles_needed} sq (incl. 10% waste)")
    materials_cost += add_line("felt_roll",      felt_needed,
                               f"Synthetic Felt #15 · {felt_needed} roll(s)")
    if iws_needed > 0:
        materials_cost += add_line("ice_water_roll", iws_needed,
                                   f"Ice & Water Shield · {iws_needed} roll(s) for {_format_feet_inches(m.valleys_ft)} valleys")
    if drip_edge_pieces > 0:
        materials_cost += add_line("drip_edge_ft", drip_edge_pieces,
                                   f"Drip Edge · {drip_edge_pieces} × 10ft pieces ({_format_feet_inches(m.roofPerimeter_ft)} perimeter)")
    if body.thermalSensors.altitudinalExtensions_ft > 0:
        materials_cost += add_line("flashing_ft", body.thermalSensors.altitudinalExtensions_ft,
                                   f"Wall Counter/Step Flashing · {_format_feet_inches(body.thermalSensors.altitudinalExtensions_ft)}")
    materials_cost += add_line("chimney_kit", 1, "Chimney Flashing & Caulk Combo Pack")
    materials_cost += add_line("nails_box",   2, "Coil Roofing Fasteners · 2 boxes")
    materials_cost += add_line("caps_box",    1, "Plastic Button Cap Nails · 1 box")
    for boot in body.pipeBootsData:
        item_id = f"boot_{boot.size_in}in"
        if boot.count > 0 and item_id in prices:
            materials_cost += add_line(item_id, boot.count,
                                       f"Pipe Boot Cover · {boot.size_in}\" × {boot.count}")

    # ─── Agent 4: Labor + Insurance + Overhead/Profit ─────────────────────────
    est_man_hours = math.ceil((roof_squares_with_waste * LABOR_HOURS_PER_SQ) +
                              (m.valleys_ft * LABOR_HOURS_PER_VALLEY_FT))
    base_labor_cost = round(est_man_hours * LABOR_RATE_PER_HOUR_USD, 2)
    mechanical_subtotal = round(materials_cost + base_labor_cost, 2)

    insurance_markup = 0.0
    if body.financials.isInsuranceJob:
        insurance_markup = round(mechanical_subtotal * (body.financials.insuranceMultiplier - 1.0), 2)
    after_insurance = round(mechanical_subtotal + insurance_markup, 2)

    op_pct = (body.financials.overheadPercent + body.financials.profitPercent) / 100.0
    op_markup = round(after_insurance * op_pct, 2)
    gross_total = round(after_insurance + op_markup, 2)

    return {
        "geometry": {
            "net_wall_sqft": round(net_wall_sqft, 2),
            "roof_total_sqft_adjusted": round(adjusted_roof_sqft, 2),
            "roof_squares_net": round(roof_squares_net, 4),
            "roof_squares_with_waste": round(roof_squares_with_waste, 4),
            "valleys_fmt": _format_feet_inches(m.valleys_ft),
            "ridges_fmt": _format_feet_inches(m.ridges_ft),
            "hips_fmt":   _format_feet_inches(m.hips_ft),
            "roof_perimeter_fmt": _format_feet_inches(m.roofPerimeter_ft),
        },
        "quantities": {
            "shingles_squares": shingles_needed,
            "felt_rolls": felt_needed,
            "ice_water_rolls": iws_needed,
            "drip_edge_pieces": drip_edge_pieces,
            "altitudinal_flashing_ft": body.thermalSensors.altitudinalExtensions_ft,
            "pipe_boots": [boot.model_dump() for boot in body.pipeBootsData],
        },
        "line_items": lines,
        "labor": {
            "rate_per_hour_usd": LABOR_RATE_PER_HOUR_USD,
            "estimated_man_hours": est_man_hours,
            "base_labor_cost_usd": base_labor_cost,
        },
        "financial_summary": {
            "materials_cost_usd":    round(materials_cost, 2),
            "labor_cost_usd":        base_labor_cost,
            "mechanical_subtotal_usd": mechanical_subtotal,
            "insurance_multiplier":  body.financials.insuranceMultiplier if body.financials.isInsuranceJob else 1.0,
            "insurance_markup_usd":  insurance_markup,
            "overhead_pct":          body.financials.overheadPercent,
            "profit_pct":            body.financials.profitPercent,
            "overhead_profit_usd":   op_markup,
            "gross_total_usd":       gross_total,
        },
    }


# ---------------------------------------------------------------------------
# Multi-Agent Consensus Verification (3 verifiers + 1 senior reviewer)
# ---------------------------------------------------------------------------
_VERIFIER_PROMPTS = {
    "geometry": (
        "You are STRATEX™ Verifier-G (Geometry). You will be given drone telemetry and the "
        "platform's deterministic geometry calculations. Independently re-compute net wall area "
        "(gross − windows − doors) and adjusted roof area (raw × pitch multiplier). "
        "Confirm or dispute the numbers. Reply STRICTLY as JSON: "
        "{verdict ('confirmed'|'flagged'|'rejected'), confidence_pct (0-100), "
        "narrative (≤2 sentences with the actual numbers you computed), discrepancies (array)}."
    ),
    "materials": (
        "You are STRATEX™ Verifier-M (Materials). Given the roof squares (with 10% waste), valley "
        "linear feet, perimeter, and material conversion rules (felt: 1 roll = 4 sq, IWS: 1 roll "
        "= 75 lf, drip edge: 1 piece = 10 lf), verify the quantity counts. Reply STRICTLY as JSON: "
        "{verdict, confidence_pct, narrative, discrepancies}."
    ),
    "financial": (
        "You are STRATEX™ Verifier-F (Financial). Given materials cost, labor (man-hours × "
        "$200/hr), insurance multiplier, and overhead+profit %, confirm the gross total math. "
        "Reply STRICTLY as JSON: {verdict, confidence_pct, narrative, discrepancies}."
    ),
}

_SENIOR_REVIEWER_PROMPT = (
    "You are STRATEX™ Senior Reviewer (model: Claude Sonnet 4.5). You have read three independent "
    "verifier reports (geometry, materials, financial) and the underlying deterministic computation. "
    "Your job: issue the FINAL CONSENSUS RULING that determines whether the drone payload may be "
    "REGISTERED onto the job record. Reply STRICTLY as JSON: "
    "{ruling ('REGISTER'|'REGISTER_WITH_FLAGS'|'HALT'), consensus_score (0-100), "
    "reasoning (3-4 sentences citing specific numbers), agreements (array of short strings), "
    "dissents (array of short strings)}. "
    "Issue HALT if any verifier rejected or if confidence_pct < 80. "
    "Issue REGISTER_WITH_FLAGS if all verifiers confirmed but at least one flagged a discrepancy. "
    "Issue REGISTER only if all three verifiers confirmed with confidence_pct ≥ 90."
)


def _parse_json_lax(raw: str) -> Dict[str, Any]:
    try:
        return _json.loads(raw)
    except Exception:
        pass
    s, e = raw.find("{"), raw.rfind("}")
    if s != -1 and e > s:
        try:
            return _json.loads(raw[s:e + 1])
        except Exception:
            pass
    return {"verdict": "flagged", "confidence_pct": 0, "narrative": raw[:300], "discrepancies": []}


async def _run_verifier(name: str, brief: Dict[str, Any]) -> Dict[str, Any]:
    chat = LlmChat(
        api_key=os.environ.get("EMERGENT_LLM_KEY"),
        session_id=f"branch-verifier::{name}::{uuid.uuid4()}",
        system_message=_VERIFIER_PROMPTS[name],
    ).with_model("anthropic", "claude-haiku-4-5-20251001")
    try:
        raw = await chat.send_message(UserMessage(
            text=f"BRIEF (JSON):\n{_json.dumps(brief, indent=2)}\n\nReturn only the JSON verdict."
        ))
        return {"verifier": name, "ok": True, **_parse_json_lax(raw)}
    except Exception as e:
        logger.warning(f"verifier {name} error: {e!r}")
        return {"verifier": name, "ok": False, "verdict": "flagged",
                "confidence_pct": 0, "narrative": f"verifier unreachable: {type(e).__name__}",
                "discrepancies": []}


async def _run_senior_reviewer(verifier_reports: List[Dict[str, Any]],
                                deterministic: Dict[str, Any]) -> Dict[str, Any]:
    chat = LlmChat(
        api_key=os.environ.get("EMERGENT_LLM_KEY"),
        session_id=f"branch-senior::{uuid.uuid4()}",
        system_message=_SENIOR_REVIEWER_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        raw = await chat.send_message(UserMessage(text=_json.dumps({
            "verifier_reports": verifier_reports,
            "deterministic_summary": {
                "geometry": deterministic["geometry"],
                "quantities": deterministic["quantities"],
                "financial_summary": deterministic["financial_summary"],
            },
        }, indent=2)))
        return {"ok": True, **_parse_json_lax(raw)}
    except Exception as e:
        logger.warning(f"senior reviewer error: {e!r}")
        return {"ok": False, "ruling": "HALT", "consensus_score": 0,
                "reasoning": f"Senior reviewer unreachable: {type(e).__name__}. Halting by default for safety.",
                "agreements": [], "dissents": [f"reviewer unreachable: {type(e).__name__}"]}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@api.get("/branch/master-price-index")
async def get_master_price_index(user=Depends(admin_only)):
    docs = await db.supplier_material_ledger.find({}, {"_id": 0}).sort("name", 1).to_list(length=200)
    return {"as_of": now_iso(), "count": len(docs), "items": docs}


@api.post("/branch/quantify")
async def branch_quantify(body: QuantifyBody, user=Depends(current_user)):
    """Drone telemetry → deterministic math → 3-verifier swarm → senior consensus.

    Only writes to db.jobs if `register=true` AND senior ruling is REGISTER or
    REGISTER_WITH_FLAGS. HALT rulings post to db.telemetry_halts and never touch
    the job record.
    """
    if body.assigned_tier not in ("tier1", "tier2", "tier3"):
        raise HTTPException(400, "assigned_tier must be tier1, tier2, or tier3")
    materials = await db.supplier_material_ledger.find({}, {"_id": 0}).to_list(length=200)
    price_key = _tier_key(body.assigned_tier)
    prices = {m["id"]: float(m.get(price_key, 0)) for m in materials}

    deterministic = _deterministic_quantify(body, prices)

    geom_brief = {
        "raw_input": body.measurements.model_dump(),
        "platform_computed": deterministic["geometry"],
    }
    materials_brief = {
        "roof_squares_with_waste": deterministic["geometry"]["roof_squares_with_waste"],
        "valleys_ft": body.measurements.valleys_ft,
        "perimeter_ft": body.measurements.roofPerimeter_ft,
        "platform_computed_quantities": deterministic["quantities"],
    }
    financial_brief = {
        "tier": body.assigned_tier,
        "platform_computed": deterministic["financial_summary"],
        "labor_rate_per_hour": LABOR_RATE_PER_HOUR_USD,
        "estimated_man_hours": deterministic["labor"]["estimated_man_hours"],
    }

    verifier_reports = await asyncio.gather(
        _run_verifier("geometry",  geom_brief),
        _run_verifier("materials", materials_brief),
        _run_verifier("financial", financial_brief),
    )
    senior = await _run_senior_reviewer(verifier_reports, deterministic)

    ruling = senior.get("ruling", "HALT")
    consensus_passed = ruling in ("REGISTER", "REGISTER_WITH_FLAGS")
    consensus_id = f"consensus-{uuid.uuid4().hex[:12]}"

    consensus_record = {
        "id": consensus_id,
        "project_id": body.projectId,
        "job_id": body.job_id,
        "contractor_id": body.contractor_id or user["id"],
        "submitted_by": user["id"],
        "submitted_email": user["email"],
        "assigned_tier": body.assigned_tier,
        "telemetry_payload": body.model_dump(),
        "deterministic": deterministic,
        "verifier_reports": verifier_reports,
        "senior_ruling": senior,
        "consensus_passed": consensus_passed,
        "ruling": ruling,
        "consensus_score": senior.get("consensus_score", 0),
        "registered": False,
        "created_at": now_iso(),
    }

    if body.register and consensus_passed and body.job_id:
        job = await db.jobs.find_one({"id": body.job_id}, {"_id": 0, "id": 1})
        if job:
            await db.jobs.update_one(
                {"id": body.job_id},
                {"$set": {
                    "branch_quantify_payload": deterministic,
                    "branch_quantify_consensus_id": consensus_id,
                    "branch_quantify_registered_at": now_iso(),
                    "branch_quantify_ruling": ruling,
                    "branch_quantify_score": senior.get("consensus_score", 0),
                }},
            )
            consensus_record["registered"] = True

    if not consensus_passed:
        await db.telemetry_halts.insert_one({
            "id": f"halt-{uuid.uuid4().hex[:10]}",
            "source": "branch_quantify_consensus",
            "consensus_id": consensus_id,
            "project_id": body.projectId,
            "job_id": body.job_id,
            "ruling": ruling,
            "consensus_score": senior.get("consensus_score", 0),
            "reasoning": senior.get("reasoning", ""),
            "verifier_reports": verifier_reports,
            "created_at": now_iso(),
            "status": "open",
        })

    await db.branch_consensus_runs.insert_one(consensus_record)
    consensus_record.pop("_id", None)
    return consensus_record


@api.get("/branch/consensus-runs")
async def list_consensus_runs(limit: int = 25, user=Depends(admin_only)):
    docs = await db.branch_consensus_runs.find(
        {}, {"_id": 0, "telemetry_payload": 0}  # heavy field — load on demand
    ).sort("created_at", -1).to_list(length=max(1, min(limit, 100)))
    return {"count": len(docs), "runs": docs}
