"""STRATEX™ Backend - Strategic Thermal Reconnaissance & Automated Topology Estimator."""
from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import random
import math
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from roof_topology import build_topology

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="STRATEX API", version="1.0.0")
api_router = APIRouter(prefix="/api")

logger = logging.getLogger("stratex")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectIntake(BaseModel):
    customer_name: str
    property_address: str
    insurance_carrier: Optional[str] = None
    project_type: str  # "Private Cash Pay" | "Insurance Claim"


class ScopeConfig(BaseModel):
    underlayment_brand: str  # Standard Felt | Synthetic Felt | Premium Synthetic Felt
    drip_edge_color: str
    disposal_strategy: str   # Automated Mobile Trailer Rig | Commercial Roll-off Dumpster
    fastener_type: str
    roof_style: str = "cross_hip"  # gable | hip | cross_hip | l_shape | dutch_gable


class CaliperReading(BaseModel):
    edge_thickness_in: float  # measured by the aero-caliper algorithm


class ProjectCreate(BaseModel):
    intake: ProjectIntake
    scope: ScopeConfig


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intake: ProjectIntake
    scope: ScopeConfig
    caliper: Optional[Dict[str, Any]] = None
    roof_telemetry: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    mission: Optional[Dict[str, Any]] = None
    agent_reports: Optional[Dict[str, Any]] = None
    status: str = "draft"   # draft | configured | scoped | priced | launched | complete
    created_at: str = Field(default_factory=now_iso)


# ---------------------------------------------------------------------------
# CORE ENGINEERING / ROOF TELEMETRY SIMULATION
# ---------------------------------------------------------------------------

XACTIMATE_TAGS = {
    "shingles": "RFG ASV",
    "decking": "RFG OSB",
    "labor": "RFG LAB",
    "drip_edge": "RFG DRIP",
    "underlayment": "RFG SYN" ,
    "ice_water": "RFG IWS",
    "ridge_cap": "RFG RIDGC",
    "disposal": "RFG DMPST",
    "starter": "RFG STARTER",
    "flashing": "RFG FLASHL",
}


def simulate_roof_telemetry(seed: str, style: str = "cross_hip") -> Dict[str, Any]:
    """Deterministic simulated drone photogrammetry → multi-facet topology.

    The full STRATEX™ Vision pipeline (SfM → MVS/NeRF → mesh extract → facet
    segmentation → RTK calibration → thermal fusion) is documented in
    `roof_topology.py`. For the demo we synthesise the FINAL output (facets +
    edges + anomalies + totals) deterministically from the project seed.
    """
    topo = build_topology(style=style, project_seed=seed)
    totals = topo["totals"]
    return {
        "style": topo["style"],
        "scale": topo["scale"],
        "facets": topo["facets"],
        "edges": topo["edges"],
        "totals": totals,
        "total_sf": totals["total_sf"],
        "squares": totals["squares"],
        "ridge_lf": totals["ridges_lf"],
        "valleys_lf": totals["valleys_lf"],
        "hips_lf": totals["hips_lf"],
        "eaves_lf": totals["eaves_lf"],
        "rakes_lf": totals["rakes_lf"],
        "pitch": f"{topo['primary_pitch']}/12",
        "pitch_num": int(round(topo["primary_pitch"])) or 8,
        "rtk_precision_cm": topo["rtk_precision_cm"],
        "mesh_status": topo["mesh_status"],
        "captured_at": now_iso(),
    }


def detect_anomalies(seed: str, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The topology engine produces anomalies co-registered to facets; return them."""
    if telemetry and telemetry.get("facets"):
        topo = build_topology(style=telemetry.get("style", "cross_hip"), project_seed=seed)
        return topo["anomalies"]
    # Fallback to original generator
    rnd = random.Random(seed + "anom")
    anomaly_types = [
        ("Trapped Moisture", "subsurface_moisture", "+7.2°F", "CRITICAL"),
        ("Missing Shingle Field", "missing_shingle", "-3.1°F", "HIGH"),
        ("Loose Flashing", "flashing_defect", "+2.4°F", "MED"),
        ("Hail Bruising Cluster", "impact_bruising", "+1.8°F", "MED"),
        ("CDX Deck Rot", "rotted_decking", "+9.6°F", "CRITICAL"),
        ("Sealant Failure", "sealant_failure", "+1.1°F", "LOW"),
    ]
    count = rnd.randint(4, 7)
    anomalies = []
    for i in range(count):
        kind, code, delta, sev = rnd.choice(anomaly_types)
        anomalies.append({
            "id": f"AD-KY041-{i+1:03d}",
            "type": kind,
            "diagnosis": kind,
            "code": code,
            "thermal_delta": delta,
            "lat": round(38.0406 + rnd.uniform(-0.0005, 0.0005), 6),
            "lon": round(-84.5037 + rnd.uniform(-0.0005, 0.0005), 6),
            "severity": sev,
            "confidence": round(rnd.uniform(0.86, 0.99), 3),
            "facet_id": f"F{(i % 4) + 1}",
            "area_affected_sf": round(rnd.uniform(60, 280), 1),
        })
    return anomalies


# ---------------------------------------------------------------------------
# RECONCILIATION ENGINE (Quant™)
# ---------------------------------------------------------------------------

UNDERLAYMENT_PRICE = {
    "Standard Felt": 35.0,           # per square
    "Synthetic Felt": 55.0,
    "Premium Synthetic Felt": 78.0,
}

FASTENER_PRICE = {
    "Electro-Galvanized": 8.0,
    "Hot-Dipped Galvanized": 12.0,
    "Stainless Steel": 22.0,
}

PITCH_MULTIPLIER = {6: 1.0, 7: 1.05, 8: 1.15, 9: 1.25, 10: 1.4, 12: 1.6}

UNIT_PRICES = {
    "shingle_bundle": 42.50,        # architectural shingle bundle
    "osb_sheet": 38.75,             # 7/16 OSB 4x8
    "drip_edge_lf": 2.10,
    "ridge_cap_bundle": 58.00,
    "ice_water_roll": 92.00,        # ~200 sf roll
    "starter_bundle": 64.00,
    "flashing_lf": 6.75,
    "disposal_per_ton": 95.00,
    "labor_hour": 78.00,
}


def reconcile_estimate(project: Dict[str, Any]) -> Dict[str, Any]:
    tele = project["roof_telemetry"]
    scope = project["scope"]
    caliper = project.get("caliper") or {}
    intake = project["intake"]

    squares = tele["squares"]
    total_sf = tele["total_sf"]
    pitch = tele["pitch_num"]
    pitch_mult = PITCH_MULTIPLIER.get(pitch, 1.2)

    layers = caliper.get("layers_detected", 1)
    tearoff = caliper.get("scope_determined", "Overlay Permitted") == "Complete Tear-Off Required"
    layer_mult = 1.5 if tearoff else 1.0

    waste = 1.12 if pitch <= 8 else 1.15

    # Materials
    shingle_bundles = math.ceil(squares * 3 * waste)
    osb_sheets = math.ceil((total_sf / 32.0) * 0.20 * waste)  # ~20% decking replacement
    drip_edge_lf = math.ceil((tele["eaves_lf"] + tele["rakes_lf"]) * 1.05)
    ridge_cap_bundles = math.ceil(tele["ridge_lf"] / 20.0)
    ice_water_rolls = math.ceil((tele["eaves_lf"] * 3 + tele["valleys_lf"] * 3) / 200.0)
    starter_bundles = math.ceil((tele["eaves_lf"] + tele["rakes_lf"]) / 120.0)
    flashing_lf = math.ceil(tele["valleys_lf"] + tele["hips_lf"] * 0.5)
    underlayment_squares = math.ceil(squares * waste)

    # Labor
    labor_hours = round(squares * 4.2 * pitch_mult * layer_mult, 1)

    # Disposal
    disposal_tons = round((squares * 235 * layers) / 2000.0, 2)

    # Line items
    items = []

    def li(desc, qty, unit, unit_price, tag):
        total = round(qty * unit_price, 2)
        items.append({
            "description": desc,
            "qty": qty,
            "unit": unit,
            "unit_price": unit_price,
            "total": total,
            "xactimate_tag": tag,
        })
        return total

    li("Architectural Shingles (30-yr)", shingle_bundles, "BDL", UNIT_PRICES["shingle_bundle"], XACTIMATE_TAGS["shingles"])
    li(f"{scope['underlayment_brand']}", underlayment_squares, "SQ",
       UNDERLAYMENT_PRICE.get(scope["underlayment_brand"], 55.0), XACTIMATE_TAGS["underlayment"])
    li("OSB Decking 7/16\" Replacement", osb_sheets, "SHT", UNIT_PRICES["osb_sheet"], XACTIMATE_TAGS["decking"])
    li(f"Drip Edge — {scope['drip_edge_color']}", drip_edge_lf, "LF", UNIT_PRICES["drip_edge_lf"], XACTIMATE_TAGS["drip_edge"])
    li("Ice & Water Shield", ice_water_rolls, "RL", UNIT_PRICES["ice_water_roll"], XACTIMATE_TAGS["ice_water"])
    li("Ridge Cap Shingles", ridge_cap_bundles, "BDL", UNIT_PRICES["ridge_cap_bundle"], XACTIMATE_TAGS["ridge_cap"])
    li("Starter Course", starter_bundles, "BDL", UNIT_PRICES["starter_bundle"], XACTIMATE_TAGS["starter"])
    li("Valley / Step Flashing", flashing_lf, "LF", UNIT_PRICES["flashing_lf"], XACTIMATE_TAGS["flashing"])
    li(f"Fasteners — {scope['fastener_type']}", squares, "SQ",
       FASTENER_PRICE.get(scope["fastener_type"], 12.0), XACTIMATE_TAGS["shingles"])
    li("Labor — Tear-Off + Install" if tearoff else "Labor — Install",
       labor_hours, "HR", UNIT_PRICES["labor_hour"], XACTIMATE_TAGS["labor"])
    li(f"Disposal — {scope['disposal_strategy']}", disposal_tons, "TON",
       UNIT_PRICES["disposal_per_ton"], XACTIMATE_TAGS["disposal"])

    subtotal = round(sum(i["total"] for i in items), 2)

    insurance_claim = intake["project_type"] == "Insurance Claim"
    overhead_rate = 0.20 if insurance_claim else 0.10
    profit_rate = 0.25 if insurance_claim else 0.10

    overhead = round(subtotal * overhead_rate, 2)
    profit = round(subtotal * profit_rate, 2)
    final_total = round(subtotal + overhead + profit, 2)

    return {
        "computed_at": now_iso(),
        "line_items": items,
        "subtotal": subtotal,
        "overhead_rate": overhead_rate,
        "overhead": overhead,
        "profit_rate": profit_rate,
        "profit": profit,
        "final_total": final_total,
        "layers_detected": layers,
        "tear_off": tearoff,
        "pitch_multiplier": pitch_mult,
        "labor_hours": labor_hours,
        "disposal_tons": disposal_tons,
        "lock_mode": "INSURANCE 20/25 O&P" if insurance_claim else "RETAIL FLAT 10/10",
    }


# ---------------------------------------------------------------------------
# AI NARRATIVE (Claude Sonnet 4.6 via Emergent Universal Key)
# ---------------------------------------------------------------------------

async def generate_agent_reports(project: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Use Claude Sonnet 4.6 to produce forensic, validation, reconciliation, jurisprudential narratives."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:
        logger.warning("emergentintegrations not available: %s", e)
        return _fallback_reports(project, anomalies)

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return _fallback_reports(project, anomalies)

    intake = project["intake"]
    tele = project["roof_telemetry"]
    pricing = project.get("pricing") or {}

    system = (
        "You are STRATEX™ — a multi-agent roof-claims AI core composed of four sub-agents: "
        "(1) Forensic Diagnostic Agent, (2) Evidentiary Validation Agent, "
        "(3) Reconciliation Engine, and (4) Jurisprudential Code Agent. "
        "Return a single JSON object with keys: forensic, validation, reconciliation, jurisprudential. "
        "Each value is a 3-4 sentence professional report. Tone: clinical, military-grade, insurance-adjuster ready. "
        "Reference exact anomaly IDs, thermal deltas, line-item math and Xactimate tags where relevant. "
        "Do NOT include markdown, just raw JSON."
    )

    payload = {
        "project": {
            "customer": intake["customer_name"],
            "address": intake["property_address"],
            "carrier": intake.get("insurance_carrier"),
            "project_type": intake["project_type"],
        },
        "telemetry": tele,
        "anomalies": anomalies,
        "pricing_summary": {
            "final_total": pricing.get("final_total"),
            "lock_mode": pricing.get("lock_mode"),
            "tear_off": pricing.get("tear_off"),
            "layers_detected": pricing.get("layers_detected"),
        },
    }

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"stratex-{project['id']}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-6")

        msg = UserMessage(text=f"PROJECT DATA:\n{payload}\n\nReturn the JSON now.")
        resp = await chat.send_message(msg)
        import json
        import re
        raw = resp if isinstance(resp, str) else str(resp)
        # try to find first JSON object
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group(0))
        return {"forensic": raw, "validation": "", "reconciliation": "", "jurisprudential": ""}
    except Exception as e:
        logger.exception("LLM generation failed: %s", e)
        return _fallback_reports(project, anomalies)


def _fallback_reports(project: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
    intake = project["intake"]
    high = [a for a in anomalies if a["severity"] in ("HIGH", "CRITICAL")]
    return {
        "forensic": (
            f"Radiometric and RGB analysis of the structure at {intake['property_address']} flagged "
            f"{len(anomalies)} discrete anomalies — {len(high)} classified HIGH/CRITICAL. "
            f"Primary concerns include subsurface thermal retainment and compromised shingle adhesion."
        ),
        "validation": (
            "Each anomaly was cropped from the high-res orthomosaic, geo-stamped, and cross-overlaid with "
            "the radiometric layer. Evidence package complies with adjuster supplement standards."
        ),
        "reconciliation": (
            f"Material and labor were reconciled against the captured topology. Quant™ engine produced a "
            f"locked actuarial total under {project.get('pricing', {}).get('lock_mode', '20/25 O&P')} margin envelope."
        ),
        "jurisprudential": (
            "Local code overlays applied: mandatory drip edge installation and ice-and-water shield border "
            "along eaves and valleys per regional freeze-thaw jurisdiction."
        ),
    }


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@api_router.get("/")
async def root():
    return {"system": "STRATEX", "version": "1.0.0", "status": "online"}


@api_router.get("/health")
async def health():
    return {"ok": True, "ts": now_iso()}


@api_router.post("/projects")
async def create_project(body: ProjectCreate):
    project = Project(intake=body.intake, scope=body.scope, status="configured")
    doc = project.model_dump()
    # Pre-compute roof telemetry with the requested topology
    doc["roof_telemetry"] = simulate_roof_telemetry(project.id, style=body.scope.roof_style)
    await db.projects.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.get("/projects")
async def list_projects():
    projects = await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return projects


@api_router.get("/projects/{project_id}")
async def get_project(project_id: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@api_router.post("/projects/{project_id}/caliper")
async def submit_caliper(project_id: str, reading: CaliperReading):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")
    layers = 2 if reading.edge_thickness_in > 1.0 else 1
    scope_determined = "Complete Tear-Off Required" if layers >= 2 else "Overlay Permitted"
    labor_multiplier = 1.5 if layers >= 2 else 1.0
    dumping_allowance_multiplier = 1.5 if layers >= 2 else 1.0
    caliper = {
        "edge_thickness_in": reading.edge_thickness_in,
        "layers_detected": layers,
        "scope_determined": scope_determined,
        "labor_hour_multiplier": labor_multiplier,
        "dumping_weight_allowance_multiplier": dumping_allowance_multiplier,
        "measured_at": now_iso(),
    }
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"caliper": caliper, "status": "scoped"}},
    )
    return caliper


@api_router.post("/projects/{project_id}/pricing")
async def compute_pricing(project_id: str):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")
    if not p.get("roof_telemetry"):
        p["roof_telemetry"] = simulate_roof_telemetry(project_id, style=(p.get("scope") or {}).get("roof_style", "cross_hip"))
    if not p.get("caliper"):
        # default single-layer caliper
        p["caliper"] = {
            "layers_detected": 1,
            "scope_determined": "Overlay Permitted",
            "labor_hour_multiplier": 1.0,
            "dumping_weight_allowance_multiplier": 1.0,
        }
    pricing = reconcile_estimate(p)
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"pricing": pricing, "roof_telemetry": p["roof_telemetry"], "status": "priced"}},
    )
    return pricing


class PreflightStatus(BaseModel):
    trailer_hatch_secured: bool = True
    drone_battery_percentage: int = 100
    rtk_gps_signal: str = "Centimeter-Level Locked"
    communication_uplink: str = "Strong / Starlink Verified"
    local_weather_clear: bool = True


@api_router.post("/projects/{project_id}/launch")
async def launch_mission(project_id: str, preflight: PreflightStatus):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")

    all_clear = (
        preflight.trailer_hatch_secured
        and preflight.drone_battery_percentage >= 90
        and preflight.rtk_gps_signal == "Centimeter-Level Locked"
        and preflight.communication_uplink.startswith("Strong")
        and preflight.local_weather_clear
    )
    if not all_clear:
        raise HTTPException(400, "Preflight checks did not all return TRUE")

    if not p.get("pricing"):
        if not p.get("roof_telemetry"):
            p["roof_telemetry"] = simulate_roof_telemetry(project_id, style=(p.get("scope") or {}).get("roof_style", "cross_hip"))
        if not p.get("caliper"):
            p["caliper"] = {
                "layers_detected": 1,
                "scope_determined": "Overlay Permitted",
                "labor_hour_multiplier": 1.0,
                "dumping_weight_allowance_multiplier": 1.0,
            }
        p["pricing"] = reconcile_estimate(p)

    anomalies = detect_anomalies(project_id, p["roof_telemetry"])
    agent_reports = await generate_agent_reports(p, anomalies)

    mission = {
        "launched_at": now_iso(),
        "preflight": preflight.model_dump(),
        "hatch_command": "RELAY_OPEN_HATCH_ACK",
        "flight_path": "AUTONOMOUS_ORBIT_4_PASS",
        "anomalies": anomalies,
        "anomalies_count": len(anomalies),
        "critical_count": sum(1 for a in anomalies if a["severity"] == "CRITICAL"),
        "status": "COMPLETE",
    }

    await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "mission": mission,
            "agent_reports": agent_reports,
            "pricing": p["pricing"],
            "roof_telemetry": p["roof_telemetry"],
            "status": "complete",
        }},
    )

    out = await db.projects.find_one({"id": project_id}, {"_id": 0})
    return out


@api_router.post("/projects/{project_id}/scan")
async def run_vision_scan(project_id: str):
    """Simulate the autonomous drone scan: build the 3D mesh + detect anomalies."""
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")
    style = (p.get("scope") or {}).get("roof_style", "cross_hip")
    telemetry = p.get("roof_telemetry") or simulate_roof_telemetry(project_id, style=style)
    # ensure facets exist (in case an older project had only flat telemetry)
    if not telemetry.get("facets"):
        telemetry = simulate_roof_telemetry(project_id, style=style)
    anomalies = detect_anomalies(project_id, telemetry)
    scan = {
        "telemetry": telemetry,
        "anomalies": anomalies,
        "anomalies_count": len(anomalies),
        "critical_count": sum(1 for a in anomalies if a["severity"] == "CRITICAL"),
        "mesh_status": "STITCHED",
        "scanned_at": now_iso(),
    }
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {"roof_telemetry": telemetry, "scan": scan, "status": "scanned"}},
    )
    return scan


@api_router.get("/projects/{project_id}/report.pdf")
async def download_supplement_pdf(project_id: str):
    """Generate a forensic-supplement PDF for insurance adjusters."""
    from fastapi.responses import Response
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")
    pdf_bytes = _build_supplement_pdf(p)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=STRATEX_Supplement_{project_id[:8]}.pdf"
        },
    )


def _build_supplement_pdf(project: Dict[str, Any]) -> bytes:
    """Render an adjuster-ready supplement packet using reportlab."""
    from io import BytesIO
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )
    from reportlab.lib.units import inch

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.55 * inch, rightMargin=0.55 * inch,
        topMargin=0.6 * inch, bottomMargin=0.55 * inch,
    )
    OBS = colors.HexColor("#06080B")
    TEAL = colors.HexColor("#00F0FF")
    ORANGE = colors.HexColor("#FF5500")
    SILVER = colors.HexColor("#E2E8F0")
    MUTED = colors.HexColor("#94A3B8")

    base = getSampleStyleSheet()
    style_h1 = ParagraphStyle("h1", parent=base["Heading1"], textColor=TEAL,
                              fontName="Helvetica-Bold", fontSize=22, leading=26, spaceAfter=8)
    style_eyebrow = ParagraphStyle("eye", parent=base["Normal"], textColor=MUTED,
                                   fontName="Helvetica", fontSize=8, leading=10, spaceAfter=4)
    style_h2 = ParagraphStyle("h2", parent=base["Heading2"], textColor=ORANGE,
                              fontName="Helvetica-Bold", fontSize=12, leading=14, spaceBefore=12, spaceAfter=6)
    style_p = ParagraphStyle("p", parent=base["BodyText"], textColor=SILVER,
                             fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
    style_mono = ParagraphStyle("m", parent=base["BodyText"], textColor=MUTED,
                                fontName="Courier", fontSize=8, leading=10, spaceAfter=2)

    elements = []
    intake = project.get("intake", {})
    tele = project.get("roof_telemetry", {}) or {}
    pricing = project.get("pricing", {}) or {}
    mission = project.get("mission", {}) or {}
    agents = project.get("agent_reports", {}) or {}
    anomalies = mission.get("anomalies", []) or (project.get("scan", {}) or {}).get("anomalies", [])

    elements.append(Paragraph("STRATEX™ FORENSIC SUPPLEMENT PACKET", style_h1))
    elements.append(Paragraph(
        f"// Project {project.get('id', '')[:8]} • Generated {now_iso()}", style_eyebrow))

    # Project header card
    hdr = [
        ["CUSTOMER", intake.get("customer_name", ""), "CARRIER", intake.get("insurance_carrier", "") or "—"],
        ["PROPERTY", intake.get("property_address", ""), "TYPE", intake.get("project_type", "")],
        ["TOTAL SF", str(tele.get("total_sf", "—")), "SQUARES", str(tele.get("squares", "—"))],
        ["PITCH", str(tele.get("pitch", "—")), "RIDGE LF", str(tele.get("ridge_lf", "—"))],
        ["LAYERS", str((project.get("caliper") or {}).get("layers_detected", "—")),
         "SCOPE", str((project.get("caliper") or {}).get("scope_determined", "—"))],
    ]
    t = Table(hdr, colWidths=[1.0 * inch, 2.2 * inch, 1.0 * inch, 2.6 * inch])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 8),
        ("TEXTCOLOR", (0, 0), (0, -1), TEAL),
        ("TEXTCOLOR", (2, 0), (2, -1), TEAL),
        ("TEXTCOLOR", (1, 0), (1, -1), SILVER),
        ("TEXTCOLOR", (3, 0), (3, -1), SILVER),
        ("BACKGROUND", (0, 0), (-1, -1), OBS),
        ("BOX", (0, 0), (-1, -1), 0.7, TEAL),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#10141D")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Agent narratives
    for key, label in [
        ("forensic", "FORENSIC DIAGNOSTIC AGENT"),
        ("validation", "EVIDENTIARY VALIDATION AGENT"),
        ("reconciliation", "RECONCILIATION ENGINE"),
        ("jurisprudential", "JURISPRUDENTIAL CODE AGENT"),
    ]:
        elements.append(Paragraph(label, style_h2))
        elements.append(Paragraph(agents.get(key, "—"), style_p))

    # Anomalies
    if anomalies:
        elements.append(Paragraph("THERMAL ANOMALY FIELD", style_h2))
        rows = [["ID", "TYPE", "SEVERITY", "Δ°F", "LAT", "LON", "CONF"]]
        for a in anomalies:
            rows.append([
                a["id"], a["type"], a["severity"], a["thermal_delta"],
                f"{a['lat']:.4f}", f"{a['lon']:.4f}", f"{a['confidence']*100:.1f}%"
            ])
        at = Table(rows, colWidths=[0.8*inch, 1.7*inch, 0.7*inch, 0.6*inch, 0.7*inch, 0.7*inch, 0.6*inch])
        at.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Courier", 8),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 1), (-1, -1), SILVER),
            ("TEXTCOLOR", (2, 1), (2, -1), ORANGE),
            ("BACKGROUND", (0, 0), (-1, -1), OBS),
            ("BOX", (0, 0), (-1, -1), 0.5, TEAL),
            ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#10141D")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(at)

    elements.append(PageBreak())

    # Pricing line items
    elements.append(Paragraph("STRATEX QUANT™ — LOCKED LINE-ITEM ESTIMATE", style_h1))
    elements.append(Paragraph(
        f"Margin Lock: {pricing.get('lock_mode', '—')}  •  Pitch ×{pricing.get('pitch_multiplier', '—')}  •  "
        f"Labor Hrs {pricing.get('labor_hours', '—')}  •  Disposal {pricing.get('disposal_tons', '—')} TON",
        style_mono))
    elements.append(Spacer(1, 8))

    if pricing.get("line_items"):
        prows = [["DESCRIPTION", "QTY", "UNIT", "$ / UNIT", "TOTAL", "XACTIMATE"]]
        for li in pricing["line_items"]:
            prows.append([
                li["description"], str(li["qty"]), li["unit"],
                f"${li['unit_price']:.2f}",
                f"${li['total']:,.2f}",
                li["xactimate_tag"],
            ])
        pt = Table(prows, colWidths=[2.6*inch, 0.55*inch, 0.5*inch, 0.7*inch, 0.85*inch, 0.95*inch])
        pt.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 1), (-1, -1), SILVER),
            ("TEXTCOLOR", (4, 1), (4, -1), TEAL),
            ("TEXTCOLOR", (5, 1), (5, -1), ORANGE),
            ("BACKGROUND", (0, 0), (-1, -1), OBS),
            ("BOX", (0, 0), (-1, -1), 0.7, TEAL),
            ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#10141D")),
            ("ALIGN", (1, 1), (4, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(pt)

    # Summary
    elements.append(Spacer(1, 10))
    sub = pricing.get("subtotal", 0) or 0
    oh = pricing.get("overhead", 0) or 0
    pf = pricing.get("profit", 0) or 0
    ft = pricing.get("final_total", 0) or 0
    srows = [
        ["SUBTOTAL", f"${sub:,.2f}"],
        [f"OVERHEAD ({int((pricing.get('overhead_rate') or 0)*100)}%)", f"${oh:,.2f}"],
        [f"PROFIT ({int((pricing.get('profit_rate') or 0)*100)}%)", f"${pf:,.2f}"],
        ["FINAL TOTAL", f"${ft:,.2f}"],
    ]
    st = Table(srows, colWidths=[3.5 * inch, 2.5 * inch], hAlign="RIGHT")
    st.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica-Bold", 10),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -2), SILVER),
        ("TEXTCOLOR", (0, -1), (-1, -1), TEAL),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 13),
        ("BACKGROUND", (0, 0), (-1, -1), OBS),
        ("BOX", (0, 0), (-1, -1), 0.7, TEAL),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#10141D")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(st)

    elements.append(Spacer(1, 16))
    elements.append(Paragraph(
        "// Generated autonomously by the STRATEX™ multi-agent core. Supplement-ready for direct submission "
        "to the named insurance carrier. Xactimate codes are mapped per the carrier's billing convention.",
        style_mono))

    doc.build(elements)
    return buf.getvalue()


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
