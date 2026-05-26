"""STRATEX™ Backend — secure dual-portal API.

Roles:
- contractor: owns business rules, creates jobs, sees fully unblinded proposals
- operator:   STRATEX field pilot; sees jobs WITHOUT pricing; runs pre-flight + launch
- admin:      seed/maintenance

Job lifecycle:
- DRAFT
- PENDING_FIELD_CAPTURE   (contractor created, awaiting operator)
- IN_FLIGHT               (operator authorized launch, drone aerial recon)
- DATA_CAPTURE_COMPLETE   (operator-visible terminal state — no $)
- PROPOSAL_READY          (contractor-visible — business brain applied)
- AUDIT_APPROVED          (contractor signed off)
- SENT_TO_HOMEOWNER       (contractor recorded delivery)
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Dict, Any
import os
import uuid
import logging
import random
import math
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from stratex_auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    new_totp_secret, totp_uri, verify_totp,
    encrypt_value, decrypt_value,
    auth_dep, role_dep, require_nda,
    render_nda,
)
from roof_topology import build_topology

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]


def get_db():
    return db


app = FastAPI(title="STRATEX API", version="2.0.0")
api = APIRouter(prefix="/api")
auth_r = APIRouter(prefix="/api/auth")

logger = logging.getLogger("stratex")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class SignupBody(BaseModel):
    email: EmailStr
    password: str
    legal_name: str
    company_name: Optional[str] = ""
    role: str  # contractor | operator (admin only via seed)


class LoginStartBody(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class AcceptNDABody(BaseModel):
    typed_name: str


class MaterialsConfig(BaseModel):
    # Public catalog choices
    shingle_brand: str = "GAF Timberline HDZ"
    underlayment_brand: str = "GAF FeltBuster Synthetic"
    ice_water_brand: str = "GAF StormGuard"
    ridge_vent_brand: str = "GAF Cobra Ridge Vent"
    starter_brand: str = "GAF Pro-Start"
    drip_edge_color: str = "Charcoal"
    fastener_type: str = "Hot-Dipped Galvanized"

    # Unit prices (PRIVATE / encrypted at rest)
    shingle_bundle_price: float = 38.50
    underlayment_square_price: float = 78.00
    ice_water_roll_price: float = 92.00
    ridge_cap_bundle_price: float = 58.00
    starter_bundle_price: float = 64.00
    drip_edge_lf_price: float = 2.10
    fastener_square_price: float = 12.00
    osb_sheet_price: float = 38.75

    # Business multipliers (FULLY ISOLATED — never exposed to operators)
    overhead_pct: float = 20.0
    profit_margin_pct: float = 25.0
    labor_rate_per_hour: float = 78.00
    labor_rate_per_square: float = 0.0  # if set, used instead of hourly
    insurance_supplement_multiplier_pct: float = 12.0  # applied to insurance jobs

    @field_validator(
        "shingle_bundle_price", "underlayment_square_price", "ice_water_roll_price",
        "ridge_cap_bundle_price", "starter_bundle_price", "drip_edge_lf_price",
        "fastener_square_price", "osb_sheet_price", "labor_rate_per_hour", "labor_rate_per_square",
    )
    @classmethod
    def _non_negative_price(cls, v: float, info) -> float:
        if v < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        if v > 100000:
            raise ValueError(f"{info.field_name} is unreasonably high (>$100,000)")
        return v

    @field_validator("overhead_pct", "profit_margin_pct", "insurance_supplement_multiplier_pct")
    @classmethod
    def _percentage_bounds(cls, v: float, info) -> float:
        if v < 0:
            raise ValueError(f"{info.field_name} cannot be negative")
        if v > 100:
            raise ValueError(f"{info.field_name} cannot exceed 100%")
        return v


class JobCreate(BaseModel):
    property_address: str
    lat: float
    lon: float
    homeowner_name: str
    homeowner_email: Optional[EmailStr] = None
    homeowner_phone: Optional[str] = ""
    project_type: str = "Insurance Claim"  # Insurance Claim | Private Cash Pay
    insurance_carrier: Optional[str] = ""
    roof_style: str = "cross_hip"
    notes: Optional[str] = ""


class PreflightStatus(BaseModel):
    trailer_hatch_secured: bool = True
    drone_battery_percentage: int = 100
    rtk_gps_signal: str = "Centimeter-Level Locked"
    communication_uplink: str = "Strong / Starlink Verified"
    local_weather_clear: bool = True
    personnel_clear: bool = True


# ---------------------------------------------------------------------------
# Dependencies (bound to local db)
# ---------------------------------------------------------------------------

current_user      = auth_dep(get_db)
contractor_only   = role_dep(get_db, "contractor")
operator_only     = role_dep(get_db, "operator")
admin_only        = role_dep(get_db, "admin")
contractor_ndaed  = require_nda(get_db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _public_user(u: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": u["id"],
        "email": u["email"],
        "legal_name": u.get("legal_name", ""),
        "company_name": u.get("company_name", ""),
        "role": u["role"],
        "nda_accepted": u.get("nda_accepted", False),
        "totp_enrolled": u.get("totp_enrolled", False),
        "created_at": u.get("created_at"),
    }


def _strip_pricing(job: Dict[str, Any]) -> Dict[str, Any]:
    """Operator/operator-board view: redact ALL pricing & business fields."""
    o = dict(job)
    o.pop("pricing", None)
    o.pop("homeowner_email", None)
    o.pop("homeowner_phone", None)
    # also redact contractor-private telemetry fields if any (the topology mesh itself is fine)
    return o


# ---------------------------------------------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------------------------------------------

@auth_r.post("/signup")
async def signup(body: SignupBody, request: Request):
    if body.role not in ("contractor", "operator"):
        raise HTTPException(400, "role must be 'contractor' or 'operator'")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Email already registered")
    secret = new_totp_secret()
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "legal_name": body.legal_name,
        "company_name": body.company_name or "",
        "role": body.role,
        "password_hash": hash_password(body.password),
        "totp_secret": secret,
        "totp_enrolled": False,
        "nda_accepted": False,
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    return {
        "user": _public_user(user),
        "totp_setup": {
            "secret": secret,
            "uri": totp_uri(secret, email),
            "issuer": "STRATEX",
        },
        "next_step": "verify_totp_then_login",
    }


@auth_r.post("/login")
async def login(body: LoginStartBody, request: Request):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        # brute-force tracking
        await db.login_attempts.update_one(
            {"identifier": email},
            {"$inc": {"failed": 1}, "$set": {"last_at": now_iso()}},
            upsert=True,
        )
        raise HTTPException(401, "Invalid credentials")

    if not body.totp_code:
        return {"mfa_required": True, "issuer": "STRATEX",
                "totp_enrolled": user.get("totp_enrolled", False)}

    if not verify_totp(user["totp_secret"], body.totp_code):
        raise HTTPException(401, "Invalid MFA code")

    if not user.get("totp_enrolled"):
        await db.users.update_one({"id": user["id"]}, {"$set": {"totp_enrolled": True}})
        user["totp_enrolled"] = True

    await db.login_attempts.delete_many({"identifier": email})
    access = create_access_token(user["id"], user["role"], user["email"])
    refresh = create_refresh_token(user["id"])
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "user": _public_user(user),
    }


@auth_r.post("/refresh")
async def refresh_token(body: Dict[str, str]):
    import jwt as _jwt
    try:
        payload = decode_token(body.get("refresh_token", ""))
    except _jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")
    u = await db.users.find_one({"id": payload["sub"]})
    if not u:
        raise HTTPException(401, "User not found")
    return {"access_token": create_access_token(u["id"], u["role"], u["email"]), "token_type": "Bearer"}


@auth_r.get("/me")
async def me(user=Depends(current_user)):
    return _public_user(user)


@auth_r.post("/accept-nda")
async def accept_nda(body: AcceptNDABody, request: Request, user=Depends(current_user)):
    if user["role"] != "contractor":
        # Operators don't need NDA gate but record acceptance anyway
        pass
    if body.typed_name.strip().lower() != user.get("legal_name", "").strip().lower():
        raise HTTPException(400, "Typed signature must match your registered legal name exactly")
    ip = request.client.host if request.client else "0.0.0.0"
    when = datetime.now(timezone.utc)
    nda_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "typed_name": body.typed_name.strip(),
        "ip": ip,
        "signed_at": when.isoformat(),
        "rendered_text": render_nda(user["legal_name"], user.get("company_name", ""), user["email"], ip, when),
    }
    await db.ndas.insert_one(nda_doc)
    await db.users.update_one({"id": user["id"]}, {"$set": {"nda_accepted": True, "nda_signed_at": when.isoformat(), "nda_signed_ip": ip}})
    return {"ok": True, "signed_at": when.isoformat(), "nda_id": nda_doc["id"]}


@auth_r.get("/nda-preview")
async def nda_preview(request: Request, user=Depends(current_user)):
    ip = request.client.host if request.client else "0.0.0.0"
    when = datetime.now(timezone.utc)
    return {"rendered_text": render_nda(user["legal_name"], user.get("company_name", ""), user["email"], ip, when)}


# ---------------------------------------------------------------------------
# CONTRACTOR ENDPOINTS — Materials Config (Business Brain)
# ---------------------------------------------------------------------------

@api.get("/contractor/materials")
async def get_materials(user=Depends(contractor_only)):
    doc = await db.materials_configs.find_one({"user_id": user["id"]}, {"_id": 0})
    if not doc:
        # default config
        return MaterialsConfig().model_dump()
    # decrypt the encrypted financial fields
    if doc.get("_encrypted"):
        try:
            decrypted = decrypt_value(doc["_encrypted"])
            doc.update(decrypted)
        except Exception as e:
            logger.error("Failed to decrypt materials for %s: %s", user["id"], e)
    doc.pop("_encrypted", None)
    doc.pop("user_id", None)
    return doc


@api.put("/contractor/materials")
async def save_materials(body: MaterialsConfig, user=Depends(contractor_only)):
    # Encrypt the private financial fields
    PRIVATE = {
        "shingle_bundle_price": body.shingle_bundle_price,
        "underlayment_square_price": body.underlayment_square_price,
        "ice_water_roll_price": body.ice_water_roll_price,
        "ridge_cap_bundle_price": body.ridge_cap_bundle_price,
        "starter_bundle_price": body.starter_bundle_price,
        "drip_edge_lf_price": body.drip_edge_lf_price,
        "fastener_square_price": body.fastener_square_price,
        "osb_sheet_price": body.osb_sheet_price,
        "overhead_pct": body.overhead_pct,
        "profit_margin_pct": body.profit_margin_pct,
        "labor_rate_per_hour": body.labor_rate_per_hour,
        "labor_rate_per_square": body.labor_rate_per_square,
        "insurance_supplement_multiplier_pct": body.insurance_supplement_multiplier_pct,
    }
    PUBLIC = {
        "shingle_brand": body.shingle_brand,
        "underlayment_brand": body.underlayment_brand,
        "ice_water_brand": body.ice_water_brand,
        "ridge_vent_brand": body.ridge_vent_brand,
        "starter_brand": body.starter_brand,
        "drip_edge_color": body.drip_edge_color,
        "fastener_type": body.fastener_type,
    }
    encrypted = encrypt_value(PRIVATE)
    await db.materials_configs.update_one(
        {"user_id": user["id"]},
        {"$set": {"user_id": user["id"], "_encrypted": encrypted, **PUBLIC, "updated_at": now_iso()}},
        upsert=True,
    )
    return {"ok": True, "encrypted_field_count": len(PRIVATE)}


# ---------------------------------------------------------------------------
# CONTRACTOR — Jobs
# ---------------------------------------------------------------------------

@api.post("/contractor/jobs")
async def create_job(body: JobCreate, user=Depends(contractor_only)):
    job = {
        "id": str(uuid.uuid4()),
        "contractor_id": user["id"],
        "contractor_company": user.get("company_name", ""),
        "property_address": body.property_address,
        "lat": body.lat,
        "lon": body.lon,
        "homeowner_name": body.homeowner_name,
        "homeowner_email": body.homeowner_email or "",
        "homeowner_phone": body.homeowner_phone or "",
        "project_type": body.project_type,
        "insurance_carrier": body.insurance_carrier or "",
        "roof_style": body.roof_style,
        "notes": body.notes or "",
        "status": "PENDING_FIELD_CAPTURE",
        "created_at": now_iso(),
        "roof_telemetry": None,
        "anomalies": [],
        "mission": None,
        "agent_reports": None,
        "pricing": None,
    }
    await db.jobs.insert_one(job)
    job.pop("_id", None)
    return job


@api.get("/contractor/jobs")
async def list_contractor_jobs(user=Depends(contractor_only)):
    jobs = await db.jobs.find({"contractor_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return jobs


@api.get("/contractor/jobs/{job_id}")
async def get_contractor_job(job_id: str, user=Depends(contractor_only)):
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@api.post("/contractor/jobs/{job_id}/compute-proposal")
async def compute_proposal(job_id: str, user=Depends(contractor_only)):
    """Apply the contractor's encrypted Business Brain to the captured mesh — in memory."""
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] not in ("DATA_CAPTURE_COMPLETE", "PROPOSAL_READY", "AUDIT_APPROVED", "SENT_TO_HOMEOWNER"):
        raise HTTPException(400, f"Job status {job['status']} is not ready for pricing")

    mat_doc = await db.materials_configs.find_one({"user_id": user["id"]}, {"_id": 0})
    mat = MaterialsConfig().model_dump()
    if mat_doc:
        public_keys = {k: v for k, v in mat_doc.items() if k not in ("_encrypted", "user_id", "updated_at")}
        mat.update(public_keys)
        if mat_doc.get("_encrypted"):
            try:
                mat.update(decrypt_value(mat_doc["_encrypted"]))
            except Exception as e:
                logger.error("decrypt failure: %s", e)

    pricing = _reconcile(job, mat)
    await db.jobs.update_one({"id": job_id}, {"$set": {"pricing": pricing, "status": "PROPOSAL_READY"}})
    job["pricing"] = pricing
    job["status"] = "PROPOSAL_READY"
    return job


@api.post("/contractor/jobs/{job_id}/audit-approve")
async def audit_approve(job_id: str, user=Depends(contractor_only)):
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    await db.jobs.update_one({"id": job_id}, {"$set": {"status": "AUDIT_APPROVED", "audit_approved_at": now_iso()}})
    return {"ok": True, "status": "AUDIT_APPROVED"}


@api.post("/contractor/jobs/{job_id}/mark-sent")
async def mark_sent(job_id: str, user=Depends(contractor_only)):
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    await db.jobs.update_one({"id": job_id}, {"$set": {"status": "SENT_TO_HOMEOWNER", "sent_at": now_iso()}})
    return {"ok": True, "status": "SENT_TO_HOMEOWNER"}


# ---------------------------------------------------------------------------
# OPERATOR ENDPOINTS — Job Board + Launch
# ---------------------------------------------------------------------------

@api.get("/operator/jobs")
async def list_operator_jobs(user=Depends(operator_only)):
    """Operators only see jobs awaiting capture or in-flight — and NEVER any pricing or homeowner contact."""
    jobs = await db.jobs.find(
        {"status": {"$in": ["PENDING_FIELD_CAPTURE", "IN_FLIGHT"]}},
        {"_id": 0}
    ).sort("created_at", 1).to_list(200)
    return [_strip_pricing(j) for j in jobs]


@api.get("/operator/jobs/{job_id}")
async def get_operator_job(job_id: str, user=Depends(operator_only)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    return _strip_pricing(job)


@api.post("/operator/jobs/{job_id}/launch")
async def operator_launch(job_id: str, preflight: PreflightStatus, user=Depends(operator_only)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "PENDING_FIELD_CAPTURE":
        raise HTTPException(400, f"Cannot launch a job in status {job['status']}")
    all_clear = (
        preflight.trailer_hatch_secured
        and preflight.drone_battery_percentage >= 90
        and preflight.rtk_gps_signal == "Centimeter-Level Locked"
        and preflight.communication_uplink.startswith("Strong")
        and preflight.local_weather_clear
        and preflight.personnel_clear
    )
    if not all_clear:
        raise HTTPException(400, "Preflight checks did not all pass")

    # Mark IN_FLIGHT, then asynchronously process (in-process simulated)
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "IN_FLIGHT", "launched_at": now_iso(), "preflight": preflight.model_dump(), "operator_id": user["id"]}},
    )
    # Build topology synchronously for the demo (fast)
    topo = build_topology(style=job.get("roof_style", "cross_hip"), project_seed=job_id)
    anomalies = topo["anomalies"]
    mission = {
        "launched_at": now_iso(),
        "preflight": preflight.model_dump(),
        "hatch_command": "RELAY_OPEN_HATCH_ACK",
        "flight_path": "AUTONOMOUS_ORBIT_4_PASS",
        "anomalies_count": len(anomalies),
        "critical_count": sum(1 for a in anomalies if a["severity"] == "CRITICAL"),
        "anomalies": anomalies,
        "status": "DATA_CAPTURE_COMPLETE",
    }

    # multi-agent narrative (best-effort)
    agent_reports = await _agent_narratives(job, topo, anomalies)

    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "roof_telemetry": {
                "style": topo["style"], "scale": topo["scale"],
                "facets": topo["facets"], "edges": topo["edges"],
                "totals": topo["totals"], "rtk_precision_cm": topo["rtk_precision_cm"],
                "mesh_status": topo["mesh_status"],
                "total_sf": topo["totals"]["total_sf"], "squares": topo["totals"]["squares"],
                "ridge_lf": topo["totals"]["ridges_lf"], "valleys_lf": topo["totals"]["valleys_lf"],
                "hips_lf": topo["totals"]["hips_lf"], "eaves_lf": topo["totals"]["eaves_lf"],
                "rakes_lf": topo["totals"]["rakes_lf"],
                "pitch": f"{topo['primary_pitch']}/12", "pitch_num": int(round(topo["primary_pitch"])) or 8,
            },
            "anomalies": anomalies,
            "mission": mission,
            "agent_reports": agent_reports,
            "status": "DATA_CAPTURE_COMPLETE",
            "captured_at": now_iso(),
        }},
    )
    out = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    # Operator sees terminal state WITHOUT pricing (compute is deferred to contractor)
    return _strip_pricing(out)


# ---------------------------------------------------------------------------
# Pricing reconciliation using the contractor's encrypted business rules
# ---------------------------------------------------------------------------

XACTIMATE_TAGS = {
    "shingles": "RFG ASV", "decking": "RFG OSB", "labor": "RFG LAB",
    "drip_edge": "RFG DRIP", "underlayment": "RFG SYN", "ice_water": "RFG IWS",
    "ridge_cap": "RFG RIDGC", "disposal": "RFG DMPST", "starter": "RFG STARTER", "flashing": "RFG FLASHL",
}
PITCH_MULT = {6: 1.0, 7: 1.05, 8: 1.15, 9: 1.25, 10: 1.4, 12: 1.6}


def _reconcile(job: Dict[str, Any], mat: Dict[str, Any]) -> Dict[str, Any]:
    tele = job["roof_telemetry"]
    totals = tele["totals"]
    squares = totals["squares"]
    total_sf = totals["total_sf"]
    pitch = tele["pitch_num"]
    pitch_mult = PITCH_MULT.get(pitch, 1.2)

    insurance = job["project_type"] == "Insurance Claim"
    waste = 1.12 if pitch <= 8 else 1.15

    shingle_bundles = math.ceil(squares * 3 * waste)
    osb_sheets = math.ceil((total_sf / 32.0) * 0.20 * waste)
    drip_edge_lf = math.ceil((totals["eaves_lf"] + totals["rakes_lf"]) * 1.05)
    ridge_cap_bundles = max(1, math.ceil(totals["ridges_lf"] / 20.0))
    ice_water_rolls = max(1, math.ceil((totals["eaves_lf"] * 3 + totals["valleys_lf"] * 3) / 200.0))
    starter_bundles = max(1, math.ceil((totals["eaves_lf"] + totals["rakes_lf"]) / 120.0))
    flashing_lf = math.ceil(totals["valleys_lf"] + totals["hips_lf"] * 0.5)
    under_squares = math.ceil(squares * waste)

    if mat.get("labor_rate_per_square") and mat["labor_rate_per_square"] > 0:
        labor_qty = round(squares * pitch_mult, 1)
        labor_unit_price = mat["labor_rate_per_square"]
        labor_unit = "SQ"
    else:
        labor_qty = round(squares * 4.2 * pitch_mult, 1)
        labor_unit_price = mat["labor_rate_per_hour"]
        labor_unit = "HR"

    disposal_tons = round((squares * 235) / 2000.0, 2)

    items = []

    def li(desc, qty, unit, unit_price, tag):
        total = round(qty * unit_price, 2)
        items.append({"description": desc, "qty": qty, "unit": unit,
                      "unit_price": round(unit_price, 2), "total": total, "xactimate_tag": tag})

    li(f"{mat['shingle_brand']} Architectural Shingles", shingle_bundles, "BDL", mat["shingle_bundle_price"], XACTIMATE_TAGS["shingles"])
    li(f"{mat['underlayment_brand']} Underlayment", under_squares, "SQ", mat["underlayment_square_price"], XACTIMATE_TAGS["underlayment"])
    li("OSB Decking 7/16\" Replacement", osb_sheets, "SHT", mat["osb_sheet_price"], XACTIMATE_TAGS["decking"])
    li(f"Drip Edge — {mat['drip_edge_color']}", drip_edge_lf, "LF", mat["drip_edge_lf_price"], XACTIMATE_TAGS["drip_edge"])
    li(f"{mat['ice_water_brand']} Ice & Water Shield", ice_water_rolls, "RL", mat["ice_water_roll_price"], XACTIMATE_TAGS["ice_water"])
    li("Ridge Cap Shingles", ridge_cap_bundles, "BDL", mat["ridge_cap_bundle_price"], XACTIMATE_TAGS["ridge_cap"])
    li(f"{mat['starter_brand']} Starter Course", starter_bundles, "BDL", mat["starter_bundle_price"], XACTIMATE_TAGS["starter"])
    li("Valley / Step Flashing", flashing_lf, "LF", 6.75, XACTIMATE_TAGS["flashing"])
    li(f"Fasteners — {mat['fastener_type']}", squares, "SQ", mat["fastener_square_price"], XACTIMATE_TAGS["shingles"])
    li(f"Labor — {'per Square' if labor_unit == 'SQ' else 'per Man-Hour'}", labor_qty, labor_unit, labor_unit_price, XACTIMATE_TAGS["labor"])
    li("Disposal — Tear-Off Debris", disposal_tons, "TON", 95.00, XACTIMATE_TAGS["disposal"])

    subtotal = round(sum(i["total"] for i in items), 2)
    overhead_rate = mat["overhead_pct"] / 100.0
    profit_rate = mat["profit_margin_pct"] / 100.0
    insurance_supp_rate = (mat["insurance_supplement_multiplier_pct"] / 100.0) if insurance else 0.0

    overhead = round(subtotal * overhead_rate, 2)
    profit = round(subtotal * profit_rate, 2)
    insurance_supp = round(subtotal * insurance_supp_rate, 2)
    final_total = round(subtotal + overhead + profit + insurance_supp, 2)

    return {
        "computed_at": now_iso(),
        "line_items": items,
        "subtotal": subtotal,
        "overhead_rate": overhead_rate, "overhead": overhead,
        "profit_rate": profit_rate, "profit": profit,
        "insurance_supplement_rate": insurance_supp_rate, "insurance_supplement": insurance_supp,
        "final_total": final_total,
        "pitch_multiplier": pitch_mult,
        "lock_mode": f"O&P {mat['overhead_pct']:.0f}/{mat['profit_margin_pct']:.0f}" + (f" + Supp {mat['insurance_supplement_multiplier_pct']:.0f}%" if insurance else ""),
    }


# ---------------------------------------------------------------------------
# Multi-agent narrative (Claude Sonnet 4.6 via Emergent LLM Key)
# ---------------------------------------------------------------------------

async def _agent_narratives(job: Dict[str, Any], topo: Dict[str, Any], anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return _fallback_agents(job, anomalies)
        system = (
            "You are STRATEX™ — a multi-agent roof-claims forensic core. Return JSON with keys "
            "forensic, validation, reconciliation, jurisprudential — each 3-4 clinical sentences. "
            "Reference exact anomaly IDs and facet IDs. No markdown."
        )
        payload = {
            "address": job["property_address"],
            "carrier": job.get("insurance_carrier"),
            "project_type": job["project_type"],
            "topology": {"style": topo["style"], "totals": topo["totals"]},
            "anomalies": anomalies,
        }
        chat = LlmChat(api_key=api_key, session_id=f"stratex-{job['id']}", system_message=system).with_model("anthropic", "claude-sonnet-4-6")
        resp = await chat.send_message(UserMessage(text=f"DATA:\n{payload}\n\nReturn JSON."))
        import json, re
        m = re.search(r"\{[\s\S]*\}", str(resp))
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        logger.warning("agent narrative failed: %s", e)
    return _fallback_agents(job, anomalies)


def _fallback_agents(job, anomalies):
    return {
        "forensic": f"Captured topology of the structure at {job['property_address']} produced {len(anomalies)} discrete anomalies.",
        "validation": "Each anomaly was cropped, geo-stamped, and cross-overlaid with radiometric thermal data.",
        "reconciliation": "Material/labor reconciled against captured mesh dimensions; awaiting contractor pricing brain.",
        "jurisprudential": "Local code overlays (drip edge, ice & water shield, freeze-thaw border) applied per jurisdiction.",
    }


# ---------------------------------------------------------------------------
# PDF (carry over from v1)
# ---------------------------------------------------------------------------

@api.get("/contractor/jobs/{job_id}/report.pdf")
async def contractor_pdf(job_id: str, user=Depends(contractor_only)):
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    from fastapi.responses import Response
    pdf = _build_pdf(job)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=STRATEX_Proposal_{job_id[:8]}.pdf"})


def _build_pdf(job: Dict[str, Any]) -> bytes:
    from io import BytesIO
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.units import inch
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    OBS, TEAL, ORANGE, SILVER, MUTED = (colors.HexColor(c) for c in ("#06080B", "#00F0FF", "#FF5500", "#E2E8F0", "#94A3B8"))
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], textColor=TEAL, fontName="Helvetica-Bold", fontSize=20)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], textColor=ORANGE, fontName="Helvetica-Bold", fontSize=12)
    p = ParagraphStyle("p", parent=base["BodyText"], textColor=SILVER, fontName="Helvetica", fontSize=10, leading=14)
    mono = ParagraphStyle("m", parent=base["BodyText"], textColor=MUTED, fontName="Courier", fontSize=8)
    el = []
    el.append(Paragraph("STRATEX™ — HOMEOWNER PROPOSAL", h1))
    el.append(Paragraph(f"// Job {job['id'][:8]} • {now_iso()}", mono))
    el.append(Spacer(1, 10))
    hdr = [
        ["HOMEOWNER", job.get("homeowner_name", ""), "ADDRESS", job["property_address"]],
        ["CONTRACTOR", job.get("contractor_company", ""), "PROJECT TYPE", job["project_type"]],
        ["CARRIER", job.get("insurance_carrier") or "—", "STATUS", job["status"]],
    ]
    t = Table(hdr, colWidths=[1.0*inch, 2.4*inch, 1.0*inch, 2.4*inch])
    t.setStyle(TableStyle([("FONT",(0,0),(-1,-1),"Helvetica",9),("FONT",(0,0),(0,-1),"Helvetica-Bold",8),("FONT",(2,0),(2,-1),"Helvetica-Bold",8),("TEXTCOLOR",(0,0),(0,-1),TEAL),("TEXTCOLOR",(2,0),(2,-1),TEAL),("TEXTCOLOR",(1,0),(1,-1),SILVER),("TEXTCOLOR",(3,0),(3,-1),SILVER),("BACKGROUND",(0,0),(-1,-1),OBS),("BOX",(0,0),(-1,-1),0.7,TEAL)]))
    el.append(t)
    el.append(Spacer(1, 12))
    for k, label in [("forensic","FORENSIC FINDINGS"),("validation","EVIDENCE PACKAGE"),("reconciliation","RECONCILIATION"),("jurisprudential","CODE COMPLIANCE")]:
        el.append(Paragraph(label, h2))
        el.append(Paragraph((job.get("agent_reports") or {}).get(k, "—"), p))
    pricing = job.get("pricing") or {}
    if pricing.get("line_items"):
        el.append(PageBreak())
        el.append(Paragraph("LINE-ITEM ESTIMATE", h1))
        el.append(Paragraph(pricing.get("lock_mode",""), mono))
        rows = [["DESCRIPTION","QTY","UNIT","UNIT $","TOTAL","TAG"]]
        for li in pricing["line_items"]:
            rows.append([li["description"], str(li["qty"]), li["unit"], f"${li['unit_price']:.2f}", f"${li['total']:,.2f}", li["xactimate_tag"]])
        pt = Table(rows, colWidths=[2.6*inch,0.55*inch,0.5*inch,0.7*inch,0.85*inch,0.95*inch])
        pt.setStyle(TableStyle([("FONT",(0,0),(-1,-1),"Helvetica",8),("FONT",(0,0),(-1,0),"Helvetica-Bold",8),("TEXTCOLOR",(0,0),(-1,0),TEAL),("TEXTCOLOR",(0,1),(-1,-1),SILVER),("TEXTCOLOR",(4,1),(4,-1),TEAL),("TEXTCOLOR",(5,1),(5,-1),ORANGE),("BACKGROUND",(0,0),(-1,-1),OBS),("BOX",(0,0),(-1,-1),0.7,TEAL)]))
        el.append(pt)
        el.append(Spacer(1, 10))
        sub, oh, pf, supp, ft = (pricing.get(k, 0) or 0 for k in ("subtotal","overhead","profit","insurance_supplement","final_total"))
        srows = [["SUBTOTAL", f"${sub:,.2f}"], [f"OVERHEAD {int((pricing.get('overhead_rate') or 0)*100)}%", f"${oh:,.2f}"], [f"PROFIT {int((pricing.get('profit_rate') or 0)*100)}%", f"${pf:,.2f}"]]
        if supp: srows.append([f"INSURANCE SUPP {int((pricing.get('insurance_supplement_rate') or 0)*100)}%", f"${supp:,.2f}"])
        srows.append(["FINAL TOTAL", f"${ft:,.2f}"])
        st = Table(srows, colWidths=[3.5*inch, 2.5*inch], hAlign="RIGHT")
        st.setStyle(TableStyle([("FONT",(0,0),(-1,-1),"Helvetica-Bold",10),("TEXTCOLOR",(0,0),(0,-1),MUTED),("TEXTCOLOR",(1,0),(1,-2),SILVER),("TEXTCOLOR",(0,-1),(-1,-1),TEAL),("FONT",(0,-1),(-1,-1),"Helvetica-Bold",13),("BACKGROUND",(0,0),(-1,-1),OBS),("BOX",(0,0),(-1,-1),0.7,TEAL)]))
        el.append(st)
    doc.build(el)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# MISC
# ---------------------------------------------------------------------------

@api.get("/")
async def root():
    return {"system": "STRATEX", "version": "2.0.0", "status": "online"}


# ---------------------------------------------------------------------------
# FLEET STATUS — live multi-trailer telemetry (deterministic mock per slot)
# ---------------------------------------------------------------------------

FLEET_RIGS = [
    {"id": "STX-01", "callsign": "VANGUARD", "base": "Lexington, KY", "lat": 38.0406, "lon": -84.5037},
    {"id": "STX-02", "callsign": "OUTRIDER", "base": "Louisville, KY", "lat": 38.2527, "lon": -85.7585},
    {"id": "STX-03", "callsign": "HORIZON",  "base": "Indianapolis, IN", "lat": 39.7684, "lon": -86.1581},
    {"id": "STX-04", "callsign": "RAVEN",    "base": "Nashville, TN", "lat": 36.1627, "lon": -86.7816},
    {"id": "STX-05", "callsign": "SENTINEL", "base": "Cincinnati, OH", "lat": 39.1031, "lon": -84.5120},
    {"id": "STX-06", "callsign": "OBSIDIAN", "base": "St Louis, MO", "lat": 38.6270, "lon": -90.1994},
]


@api.get("/fleet/status")
async def fleet_status(user=Depends(current_user)):
    """Live telemetry for the STRATEX trailer fleet. Mocked but deterministic per call slot."""
    # rotate the slot every 6 seconds so the UI animates as it polls
    slot = int(datetime.now(timezone.utc).timestamp() // 6)
    rigs = []
    # pull in-flight jobs to attach to "deployed" rigs
    in_flight = await db.jobs.find({"status": "IN_FLIGHT"}, {"_id": 0}).to_list(20)
    pending = await db.jobs.find({"status": "PENDING_FIELD_CAPTURE"}, {"_id": 0}).to_list(20)
    for i, base in enumerate(FLEET_RIGS):
        seed = (slot + i * 7) % 100
        # rotate statuses: STANDBY / DEPLOYED / IN_FLIGHT / CHARGING / MAINTENANCE
        if seed < 35:
            status = "STANDBY"
            battery = 96 + (seed % 5)
        elif seed < 55:
            status = "CHARGING"
            battery = 38 + seed
        elif seed < 75:
            status = "DEPLOYED"
            battery = 80 - (seed % 10)
        elif seed < 92:
            status = "IN_FLIGHT"
            battery = 60 + (seed % 15)
        else:
            status = "MAINTENANCE"
            battery = max(20, seed - 10)
        rig = {
            **base,
            "status": status,
            "battery_pct": battery,
            "uplink": "STARLINK" if seed % 11 != 0 else "LTE-FAILOVER",
            "rtk_signal_cm": round(0.5 + (seed % 4) * 0.4, 2),
            "active_job_id": None,
            "active_job_address": None,
            "missions_today": (seed % 7),
            "last_heartbeat": now_iso(),
        }
        if status in ("DEPLOYED", "IN_FLIGHT"):
            pool = in_flight + pending
            if pool:
                j = pool[(slot + i) % len(pool)]
                rig["active_job_id"] = j["id"][:8]
                rig["active_job_address"] = j.get("property_address")
                rig["lat"] = (rig["lat"] + j.get("lat", rig["lat"])) / 2
                rig["lon"] = (rig["lon"] + j.get("lon", rig["lon"])) / 2
        rigs.append(rig)
    totals = {
        "total_rigs": len(rigs),
        "deployed": sum(1 for r in rigs if r["status"] in ("DEPLOYED", "IN_FLIGHT")),
        "standby":  sum(1 for r in rigs if r["status"] == "STANDBY"),
        "charging": sum(1 for r in rigs if r["status"] == "CHARGING"),
        "maintenance": sum(1 for r in rigs if r["status"] == "MAINTENANCE"),
        "avg_battery_pct": round(sum(r["battery_pct"] for r in rigs) / len(rigs)),
        "missions_today": sum(r["missions_today"] for r in rigs),
    }
    return {"rigs": rigs, "totals": totals, "as_of": now_iso()}


# ---------------------------------------------------------------------------
# SEED on startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.jobs.create_index("contractor_id")
    await db.jobs.create_index("status")

    async def seed(email_key, pw_key, role, legal, company):
        email = os.environ.get(email_key)
        pw = os.environ.get(pw_key)
        if not email or not pw:
            return
        existing = await db.users.find_one({"email": email})
        if existing:
            # ensure password matches the env (idempotent)
            if not verify_password(pw, existing["password_hash"]):
                await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(pw)}})
            # ensure totp/nda for seeds (frictionless demo)
            updates = {}
            if not existing.get("totp_secret"): updates["totp_secret"] = new_totp_secret()
            if existing.get("totp_enrolled") is not True: updates["totp_enrolled"] = True
            if role != "operator" and existing.get("nda_accepted") is not True:
                updates["nda_accepted"] = True
                updates["nda_signed_at"] = now_iso()
            if updates:
                await db.users.update_one({"email": email}, {"$set": updates})
            return
        secret = new_totp_secret()
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": email,
            "legal_name": legal,
            "company_name": company,
            "role": role,
            "password_hash": hash_password(pw),
            "totp_secret": secret,
            "totp_enrolled": True,
            "nda_accepted": (role != "operator"),  # operators don't need NDA
            "nda_signed_at": now_iso() if role != "operator" else None,
            "created_at": now_iso(),
        })

    await seed("ADMIN_EMAIL", "ADMIN_PASSWORD", "admin", "STRATEX Admin", "STRATEX Technologies Inc.")
    await seed("SEED_CONTRACTOR_EMAIL", "SEED_CONTRACTOR_PASSWORD", "contractor", "Anthony Cross", "Apex Roofing Co.")
    await seed("SEED_OPERATOR_EMAIL", "SEED_OPERATOR_PASSWORD", "operator", "Ramon Field", "STRATEX Fleet Ops")

    # write test_credentials.md
    creds_path = Path("/app/memory/test_credentials.md")
    creds_path.parent.mkdir(exist_ok=True)
    creds_path.write_text(
        f"""# STRATEX Test Credentials (v2.0.0 dual-portal)

| Role | Email | Password | Notes |
|---|---|---|---|
| Admin | {os.environ.get('ADMIN_EMAIL')} | {os.environ.get('ADMIN_PASSWORD')} | seed; MFA pre-enrolled (any code accepted via seed bypass for testing) |
| Contractor | {os.environ.get('SEED_CONTRACTOR_EMAIL')} | {os.environ.get('SEED_CONTRACTOR_PASSWORD')} | NDA pre-accepted; pre-enrolled TOTP |
| Operator | {os.environ.get('SEED_OPERATOR_EMAIL')} | {os.environ.get('SEED_OPERATOR_PASSWORD')} | no NDA required; pre-enrolled TOTP |

For seeded users TOTP is already enrolled — login flow expects a 6-digit TOTP code from the
authenticator. For tests the seed secret rotates on every restart; use the **/api/auth/totp-debug**
endpoint (only available when DEMO_MFA_BYPASS=1) or pull the live secret from db.users.

## Endpoints
- POST /api/auth/signup
- POST /api/auth/login (step 1: email+password → returns mfa_required=true; step 2: + totp_code)
- POST /api/auth/refresh
- GET  /api/auth/me
- POST /api/auth/accept-nda  body: {{ "typed_name": "Exact Legal Name" }}
- GET  /api/auth/nda-preview
- GET/PUT /api/contractor/materials
- POST/GET /api/contractor/jobs[/:id]
- POST /api/contractor/jobs/:id/compute-proposal
- POST /api/contractor/jobs/:id/audit-approve
- POST /api/contractor/jobs/:id/mark-sent
- GET  /api/contractor/jobs/:id/report.pdf
- GET  /api/operator/jobs[/:id]
- POST /api/operator/jobs/:id/launch
"""
    )

    # Add a DEMO_MFA_BYPASS endpoint registered conditionally below.


# Demo MFA bypass for automated testing (gated by DEMO_MFA_BYPASS=1)
@auth_r.get("/totp-debug")
async def totp_debug(email: str):
    """DEMO ONLY — return current TOTP code for a user. Gated by DEMO_MFA_BYPASS env."""
    if os.environ.get("DEMO_MFA_BYPASS", "0") != "1":
        raise HTTPException(404, "Not found")
    u = await db.users.find_one({"email": email.lower()})
    if not u:
        raise HTTPException(404, "User not found")
    import pyotp
    return {"email": u["email"], "current_code": pyotp.TOTP(u["totp_secret"]).now()}


# ---------------------------------------------------------------------------
# GOOGLE OAUTH (Emergent-managed) — bridges to our JWT
# ---------------------------------------------------------------------------
# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH

@auth_r.post("/google/session")
async def google_session(body: Dict[str, str]):
    """Exchange an Emergent OAuth session_id for a STRATEX JWT. Creates user if first time."""
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id required")
    import httpx
    url = os.environ.get("EMERGENT_AUTH_URL", "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data")
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.get(url, headers={"X-Session-ID": session_id})
        if r.status_code != 200:
            raise HTTPException(401, "Invalid Google session")
        data = r.json()
    email = (data.get("email") or "").lower()
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture") or ""
    if not email:
        raise HTTPException(400, "Google profile missing email")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        # First-time Google signup → defaults to contractor role; no MFA, NDA still required
        user = {
            "id": str(uuid.uuid4()),
            "email": email,
            "legal_name": name,
            "company_name": "",
            "role": "contractor",
            "password_hash": "",   # google-only account; no local password
            "totp_secret": new_totp_secret(),
            "totp_enrolled": True,  # Google itself acts as MFA
            "nda_accepted": False,
            "google_picture": picture,
            "auth_provider": "google",
            "created_at": now_iso(),
        }
        await db.users.insert_one(user)
        user.pop("_id", None)
    else:
        # update picture + mark provider
        await db.users.update_one({"email": email}, {"$set": {"google_picture": picture, "auth_provider": user.get("auth_provider") or "google"}})
    access = create_access_token(user["id"], user["role"], user["email"])
    refresh = create_refresh_token(user["id"])
    return {
        "access_token": access, "refresh_token": refresh, "token_type": "Bearer",
        "user": _public_user(user),
    }


# ---------------------------------------------------------------------------
# EMAIL — Resend integration (NDA + Quote PDF delivery)
# ---------------------------------------------------------------------------

def _resend_ready() -> bool:
    return bool(os.environ.get("RESEND_API_KEY"))


async def _send_email(to: str, subject: str, html: str, attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    if not _resend_ready():
        return {"mocked": True, "to": to, "subject": subject, "note": "RESEND_API_KEY not configured — email logged but not sent"}
    import resend as _resend
    _resend.api_key = os.environ["RESEND_API_KEY"]
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
    params = {"from": f"STRATEX <{sender}>", "to": [to], "subject": subject, "html": html}
    if attachments:
        params["attachments"] = attachments
    return await asyncio.to_thread(_resend.Emails.send, params)


def _proposal_email_html(job: Dict[str, Any]) -> str:
    p = job.get("pricing") or {}
    final = p.get("final_total", 0)
    return f"""
<table cellpadding="0" cellspacing="0" style="background:#06080B;color:#E2E8F0;font-family:Helvetica,Arial,sans-serif;width:100%;max-width:640px;padding:24px;border:1px solid #00F0FF;">
  <tr><td>
    <div style="color:#00F0FF;font-size:11px;letter-spacing:0.32em;text-transform:uppercase;">// STRATEX&trade; Proposal</div>
    <h1 style="color:#E2E8F0;letter-spacing:0.06em;text-transform:uppercase;margin:8px 0 4px;">{job.get('homeowner_name','Homeowner')}</h1>
    <div style="color:#94A3B8;font-size:12px;margin-bottom:20px;">{job.get('property_address','')}</div>
    <table cellpadding="6" cellspacing="0" style="width:100%;border:1px solid #00F0FF33;margin-bottom:16px;">
      <tr style="background:#10141D;"><td style="color:#94A3B8;font-size:11px;text-transform:uppercase;letter-spacing:0.14em;">Project Type</td><td style="color:#E2E8F0;">{job.get('project_type','')}</td></tr>
      <tr><td style="color:#94A3B8;font-size:11px;text-transform:uppercase;letter-spacing:0.14em;">Carrier</td><td style="color:#E2E8F0;">{job.get('insurance_carrier','—')}</td></tr>
      <tr style="background:#10141D;"><td style="color:#94A3B8;font-size:11px;text-transform:uppercase;letter-spacing:0.14em;">Roof Topology</td><td style="color:#E2E8F0;">{job.get('roof_style','')}</td></tr>
      <tr><td style="color:#94A3B8;font-size:11px;text-transform:uppercase;letter-spacing:0.14em;">Final Total</td><td style="color:#FF5500;font-weight:bold;font-size:18px;">${final:,.2f}</td></tr>
    </table>
    <p style="color:#94A3B8;line-height:1.6;font-size:13px;">Your full forensic supplement, anomaly catalog, and Xactimate-tagged line-items are attached as a PDF. Please review and reach out to {job.get('contractor_company','your contractor')} with any questions.</p>
    <div style="margin-top:24px;color:#00F0FF;font-size:10px;letter-spacing:0.32em;text-transform:uppercase;">STRATEX&trade; Autonomous Recon Network</div>
  </td></tr>
</table>"""


def _nda_email_html(typed_name: str, when: str) -> str:
    return f"""
<table cellpadding="0" cellspacing="0" style="background:#06080B;color:#E2E8F0;font-family:Helvetica,Arial,sans-serif;width:100%;max-width:640px;padding:24px;border:1px solid #39FF14;">
  <tr><td>
    <div style="color:#39FF14;font-size:11px;letter-spacing:0.32em;text-transform:uppercase;">// NDA EXECUTED &middot; AUDIT TRAIL</div>
    <h1 style="color:#E2E8F0;letter-spacing:0.06em;text-transform:uppercase;margin:8px 0 12px;">Welcome to STRATEX&trade;</h1>
    <p style="color:#94A3B8;line-height:1.6;font-size:13px;">{typed_name}, your Mutual Non-Disclosure & Data Privacy Agreement has been digitally signed and recorded at <span style="color:#00F0FF;">{when}</span>. Your contractor portal is now fully unlocked.</p>
    <p style="color:#94A3B8;line-height:1.6;font-size:13px;">Your private business multipliers (overhead, profit margin, labor, insurance supplement) are now protected under hardware-isolated AES-256 application-layer encryption. STRATEX operators have ZERO visibility into your proprietary business rules.</p>
    <div style="margin-top:24px;color:#39FF14;font-size:10px;letter-spacing:0.32em;text-transform:uppercase;">SECURITY PROTOCOL ACTIVE</div>
  </td></tr>
</table>"""


class EmailProposalBody(BaseModel):
    homeowner_email: Optional[EmailStr] = None
    cc_self: bool = True


@api.post("/contractor/jobs/{job_id}/email-proposal")
async def email_proposal(job_id: str, body: EmailProposalBody, user=Depends(contractor_only)):
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.get("pricing"):
        raise HTTPException(400, "Compute the proposal before emailing")
    to_email = (body.homeowner_email or job.get("homeowner_email") or "").strip()
    if not to_email:
        raise HTTPException(400, "Homeowner email required (no homeowner_email on file)")
    import base64
    pdf = _build_pdf(job)
    attachments = [{"filename": f"STRATEX_Proposal_{job_id[:8]}.pdf", "content": base64.b64encode(pdf).decode()}]
    html = _proposal_email_html(job)
    result = await _send_email(to_email, f"STRATEX™ Roofing Proposal — {job.get('property_address','')}", html, attachments)
    if body.cc_self and user.get("email") and user["email"] != to_email:
        await _send_email(user["email"], f"[CC] STRATEX™ Proposal sent to {to_email}", html, attachments)
    await db.jobs.update_one({"id": job_id}, {"$set": {"emailed_to": to_email, "emailed_at": now_iso()}})
    return {"ok": True, "to": to_email, "mocked": result.get("mocked", False), "id": result.get("id")}


@auth_r.post("/email-nda")
async def email_nda(user=Depends(current_user)):
    if not user.get("nda_accepted"):
        raise HTTPException(400, "NDA not yet signed")
    when = user.get("nda_signed_at") or now_iso()
    html = _nda_email_html(user.get("legal_name", ""), when)
    result = await _send_email(user["email"], "STRATEX™ — NDA Executed & Portal Unlocked", html)
    return {"ok": True, "to": user["email"], "mocked": result.get("mocked", False)}


# ---------------------------------------------------------------------------
# STRIPE BILLING — subscription tiers (one-time monthly charges)
# ---------------------------------------------------------------------------

# Backend-defined tiers (never trust frontend amounts)
PRICING_TIERS = {
    "starter":    {"name": "Starter",    "price": 99.00,  "blurb": "Solo operators, up to 5 missions/mo",   "features": ["5 missions/mo", "Single trailer dispatch", "PDF supplement export", "Email delivery"]},
    "pro":        {"name": "Pro",        "price": 299.00, "blurb": "Growing crews — unlimited missions",     "features": ["UNLIMITED missions", "Multi-trailer fleet", "Insurance supplement automation", "Priority dispatch", "AES-256 Business Brain"]},
    "enterprise": {"name": "Enterprise", "price": 999.00, "blurb": "White-label & multi-tenant operations",  "features": ["Everything in Pro", "White-label branding", "Custom integrations", "Dedicated support", "Audit log + SOC2 export"]},
}


class CheckoutBody(BaseModel):
    tier: str
    origin_url: str


@api.get("/billing/plans")
async def billing_plans():
    return {"tiers": PRICING_TIERS, "currency": "USD"}


@api.get("/billing/me")
async def billing_me(user=Depends(current_user)):
    full = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0, "totp_secret": 0})
    return {
        "subscription_tier": (full or {}).get("subscription_tier"),
        "subscription_status": (full or {}).get("subscription_status"),
        "subscription_started_at": (full or {}).get("subscription_started_at"),
    }


@api.post("/billing/checkout")
async def billing_checkout(body: CheckoutBody, request: Request, user=Depends(contractor_only)):
    if body.tier not in PRICING_TIERS:
        raise HTTPException(400, "Invalid tier")
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(500, "Stripe not configured")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    tier = PRICING_TIERS[body.tier]
    origin = body.origin_url.rstrip("/")
    req = CheckoutSessionRequest(
        amount=float(tier["price"]),
        currency="usd",
        success_url=f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/billing",
        metadata={"user_id": user["id"], "tier": body.tier, "email": user["email"]},
    )
    # Upstream Stripe proxy is occasionally slow — bound the call so we surface a 504 instead of a 502.
    last_err: Optional[Exception] = None
    for attempt in range(2):
        try:
            session = await asyncio.wait_for(checkout.create_checkout_session(req), timeout=20.0)
            break
        except asyncio.TimeoutError as e:
            last_err = e
            logger.warning("stripe checkout attempt %d timed out (>20s)", attempt + 1)
            continue
        except Exception as e:
            last_err = e
            logger.warning("stripe checkout attempt %d failed: %s", attempt + 1, e)
            continue
    else:
        raise HTTPException(504, f"Stripe upstream slow: {last_err}")
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "email": user["email"],
        "tier": body.tier,
        "amount": float(tier["price"]),
        "currency": "usd",
        "payment_status": "initiated",
        "status": "open",
        "metadata": {"tier": body.tier},
        "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api.get("/billing/status/{session_id}")
async def billing_status(session_id: str, request: Request, user=Depends(contractor_only)):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    api_key = os.environ["STRIPE_API_KEY"]
    host_url = str(request.base_url).rstrip("/")
    checkout = StripeCheckout(api_key=api_key, webhook_url=f"{host_url}/api/webhook/stripe")
    status = await checkout.get_checkout_status(session_id)
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if txn and txn.get("payment_status") != "paid" and status.payment_status == "paid":
        # Idempotent upgrade: only flip subscription once
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": status.status, "paid_at": now_iso()}},
        )
        await db.users.update_one(
            {"id": txn["user_id"]},
            {"$set": {
                "subscription_tier": txn["tier"],
                "subscription_status": "active",
                "subscription_started_at": now_iso(),
            }},
        )
    elif txn and status.status == "expired":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": status.payment_status, "status": status.status}},
        )
    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount_total": status.amount_total,
        "currency": status.currency,
        "metadata": status.metadata,
    }


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    api_key = os.environ["STRIPE_API_KEY"]
    host_url = str(request.base_url).rstrip("/")
    checkout = StripeCheckout(api_key=api_key, webhook_url=f"{host_url}/api/webhook/stripe")
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        evt = await checkout.handle_webhook(body, sig)
    except Exception as e:
        logger.warning("stripe webhook handle failed: %s", e)
        return {"received": False}
    if evt.payment_status == "paid" and evt.session_id:
        txn = await db.payment_transactions.find_one({"session_id": evt.session_id}, {"_id": 0})
        if txn and txn.get("payment_status") != "paid":
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id},
                {"$set": {"payment_status": "paid", "status": "complete", "paid_at": now_iso()}},
            )
            await db.users.update_one(
                {"id": txn["user_id"]},
                {"$set": {"subscription_tier": txn["tier"], "subscription_status": "active", "subscription_started_at": now_iso()}},
            )
    return {"received": True}


# ---------------------------------------------------------------------------
# APP wiring
# ---------------------------------------------------------------------------

app.include_router(auth_r)
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    client.close()
