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


def simulate_roof_telemetry(seed: str) -> Dict[str, Any]:
    """Deterministic simulated drone photogrammetry output."""
    rnd = random.Random(seed)
    total_sf = round(rnd.uniform(2400, 3400), 0)
    eaves_lf = round(total_sf * rnd.uniform(0.038, 0.045), 0)
    rakes_lf = round(total_sf * rnd.uniform(0.034, 0.042), 0)
    ridge_lf = round(total_sf * rnd.uniform(0.025, 0.032), 0)
    valleys_lf = round(total_sf * rnd.uniform(0.008, 0.014), 0)
    hips_lf = round(total_sf * rnd.uniform(0.010, 0.018), 0)
    pitch = rnd.choice([6, 7, 8, 9, 10, 12])
    squares = round(total_sf / 100.0, 2)
    return {
        "total_sf": total_sf,
        "squares": squares,
        "eaves_lf": eaves_lf,
        "rakes_lf": rakes_lf,
        "ridge_lf": ridge_lf,
        "valleys_lf": valleys_lf,
        "hips_lf": hips_lf,
        "pitch": f"{pitch}/12",
        "pitch_num": pitch,
        "captured_at": now_iso(),
    }


def detect_anomalies(seed: str, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
    rnd = random.Random(seed + "anom")
    anomaly_types = [
        ("Wet Substrate", "subsurface_moisture", "+7.2°F"),
        ("Missing Shingle Field", "missing_shingle", "-3.1°F"),
        ("Loose Flashing", "flashing_defect", "+2.4°F"),
        ("Hail Bruising Cluster", "impact_bruising", "+1.8°F"),
        ("Compromised Decking", "rotted_decking", "+9.6°F"),
        ("Sealant Failure", "sealant_failure", "+1.1°F"),
    ]
    count = rnd.randint(4, 7)
    anomalies = []
    for i in range(count):
        kind, code, delta = rnd.choice(anomaly_types)
        anomalies.append({
            "id": f"ANOM-{i+1:02d}",
            "type": kind,
            "code": code,
            "thermal_delta": delta,
            "lat": round(38.0406 + rnd.uniform(-0.0005, 0.0005), 6),
            "lon": round(-84.5037 + rnd.uniform(-0.0005, 0.0005), 6),
            "severity": rnd.choice(["LOW", "MED", "HIGH", "CRITICAL"]),
            "confidence": round(rnd.uniform(0.86, 0.99), 3),
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
    # Pre-compute roof telemetry on create
    doc["roof_telemetry"] = simulate_roof_telemetry(project.id)
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
        p["roof_telemetry"] = simulate_roof_telemetry(project_id)
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
        and preflight.drone_battery_percentage >= 100
        and preflight.rtk_gps_signal == "Centimeter-Level Locked"
        and preflight.communication_uplink.startswith("Strong")
        and preflight.local_weather_clear
    )
    if not all_clear:
        raise HTTPException(400, "Preflight checks did not all return TRUE")

    if not p.get("pricing"):
        if not p.get("roof_telemetry"):
            p["roof_telemetry"] = simulate_roof_telemetry(project_id)
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
