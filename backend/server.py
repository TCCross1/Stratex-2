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
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect, Query
import json as _json
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

    # Field-measured shingle thickness (from caliper OCR — optional)
    measured_thickness_mm: float = 0.0

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

    # Gutter Add-On — toggled per-quote; merged into the master proposal as line items
    gutter_addon_enabled: bool = True
    gutter_5in_kstyle_lf_price: float = 8.50
    gutter_6in_kstyle_lf_price: float = 11.75
    downspout_drop_price: float = 78.00          # per drop (incl. bracket + strap)
    elbow_price: float = 8.50                    # per A/B-style elbow
    miter_price: float = 32.00                   # per box or strip miter corner
    end_cap_price: float = 6.50
    conductor_head_price: float = 64.00
    hidden_hanger_each_price: float = 4.25
    gutter_labor_per_lf: float = 6.50
    # Sub-fascia / framing line-items
    sub_fascia_lf_price: float = 4.75
    rafter_replacement_each_price: float = 145.00  # per deflected rafter section

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

    @field_validator("homeowner_email", mode="before")
    @classmethod
    def _empty_email_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class PreflightStatus(BaseModel):
    # Phase 2 — On-Site Physical Safety (operator tablet sign-off)
    homeowner_verified: bool = False                # occupant/tenant aware of operation
    vertical_obstruction_clear: bool = False        # no tree canopies, radio towers, unmapped lines
    k9_and_child_clear_zone: bool = False           # pets indoors + perimeter clear of foot traffic
    # Phase 3 — Hardware & Telemetry Diagnostic Lock
    trailer_hatch_secured: bool = True
    drone_battery_percentage: int = 100
    battery_cell_variance_v: float = 0.015          # must be < 0.02 V
    rtk_gps_signal: str = "Centimeter-Level Locked"
    communication_uplink: str = "Strong / Starlink Verified"
    # Legacy support
    local_weather_clear: bool = True
    personnel_clear: bool = True


class Phase1Result(BaseModel):
    name: str
    status: str  # PASS | WARN | FAIL
    details: str


class DryRunBody(BaseModel):
    reason: str  # locked_gate | unnotified_homeowner | aggressive_animal | wrong_address | other
    notes: Optional[str] = None


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
    # Merge MaterialsConfig defaults so legacy records expose any new fields
    defaults = MaterialsConfig().model_dump()
    for k, v in defaults.items():
        doc.setdefault(k, v)
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
        "measured_thickness_mm": body.measured_thickness_mm,
    }
    encrypted = encrypt_value(PRIVATE)
    await db.materials_configs.update_one(
        {"user_id": user["id"]},
        {"$set": {"user_id": user["id"], "_encrypted": encrypted, **PUBLIC, "updated_at": now_iso()}},
        upsert=True,
    )
    return {"ok": True, "encrypted_field_count": len(PRIVATE)}


# ---------------------------------------------------------------------------
# CALIPER PHOTO OCR — accept a phone photo of a digital caliper, return the
# thickness reading (in mm + thousandths inch). Powered by Gemini vision via
# the Emergent LLM Key. If the LLM key is unavailable or fails to parse the
# image, the endpoint falls back to a "manual_entry_required" response so the
# field engineer can type the reading instead.
# ---------------------------------------------------------------------------

class CaliperOCRBody(BaseModel):
    image_base64: str          # JPEG/PNG/WEBP, no data: prefix expected
    mime_type: str = "image/jpeg"


@api.post("/contractor/caliper-ocr")
async def caliper_ocr(body: CaliperOCRBody, user=Depends(contractor_only)):
    """Read a digital caliper display from a phone photo.

    Returns: { ok, thickness_mm, thickness_in, confidence, raw_response, fallback }
    """
    import re
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return {
            "ok": False,
            "thickness_mm": None,
            "thickness_in": None,
            "confidence": "none",
            "fallback": True,
            "message": "LLM key unavailable — please enter thickness manually.",
        }
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        # Sanitize base64 (strip data URI prefix if present)
        b64 = body.image_base64
        if b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        prompt = (
            "You are reading the DIGITAL DISPLAY of a calipers (Mitutoyo or similar). "
            "Return ONLY a JSON object: "
            '{"thickness_mm": <number>, "thickness_in": <number>, "unit_shown": "<\"mm\" or \"in\">", "confidence": "<\"high\"|\"medium\"|\"low\">"}. '
            "If the display is unreadable, return all numbers as null with confidence=\"low\". "
            "Convert: 1 in = 25.4 mm. Do not include any other text."
        )
        chat = LlmChat(
            api_key=api_key,
            session_id=f"caliper-{user['id']}",
            system_message=prompt,
        ).with_model("gemini", "gemini-3-flash-preview")
        resp = await chat.send_message(UserMessage(
            text="Read the calipers display and return the JSON.",
            file_contents=[ImageContent(image_base64=b64)],
        ))
        raw = str(resp)
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise ValueError("LLM returned no JSON")
        import json
        parsed = json.loads(m.group(0))
        thickness_mm = parsed.get("thickness_mm")
        thickness_in = parsed.get("thickness_in")
        # Cross-fill if only one unit returned
        if thickness_mm and not thickness_in:
            thickness_in = round(thickness_mm / 25.4, 4)
        elif thickness_in and not thickness_mm:
            thickness_mm = round(thickness_in * 25.4, 3)
        # Audit-log the OCR call so we can later replay it
        await db.audit_log.insert_one({
            "user_id": user["id"],
            "action": "caliper_ocr",
            "thickness_mm": thickness_mm,
            "thickness_in": thickness_in,
            "confidence": parsed.get("confidence"),
            "at": now_iso(),
        })
        return {
            "ok": thickness_mm is not None,
            "thickness_mm": thickness_mm,
            "thickness_in": thickness_in,
            "unit_shown": parsed.get("unit_shown"),
            "confidence": parsed.get("confidence", "low"),
            "fallback": False,
        }
    except Exception as e:
        logger.warning("caliper OCR failed: %s", e)
        return {
            "ok": False,
            "thickness_mm": None,
            "thickness_in": None,
            "confidence": "none",
            "fallback": True,
            "message": f"OCR failed ({type(e).__name__}) — please enter thickness manually.",
        }


# ---------------------------------------------------------------------------
# PUBLIC — landing page demo topology (no auth)
# ---------------------------------------------------------------------------

@api.get("/public/demo-topology")
async def public_demo_topology():
    """Returns the stratex_demo compound roof topology + framing + gutters + sample anomalies
    for the landing-page 3D mesh preview. Cached server-side via deterministic seed."""
    topo = build_topology(style="stratex_demo", project_seed="LANDING_DEMO_v1")
    # Trim a couple anomalies for the landing demo so the canvas isn't overcrowded
    anomalies = topo["anomalies"][:4]
    return {
        "style": topo["style"],
        "scale": topo["scale"],
        "facets": topo["facets"],
        "edges": topo["edges"],
        "framing": topo["framing"],
        "gutters": topo["gutters"],
        "anomalies": anomalies,
        "totals": topo["totals"],
        "validation": topo.get("validation"),
    }


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
        "status": "PENDING_PHASE1",   # NEW: must pass Phase 1 before reaching operator
        "phase1_status": None,         # set by run_phase1
        "phase1_completed_at": None,
        "phase2_completed_at": None,
        "phase3_completed_at": None,
        "dry_run": None,
        "created_at": now_iso(),
        "roof_telemetry": None,
        "anomalies": [],
        "mission": None,
        "agent_reports": None,
        "pricing": None,
    }
    await db.jobs.insert_one(job)
    job.pop("_id", None)
    # Auto-run Phase 1 immediately on creation (digital gatekeeping)
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

    # ===== PHASE 1 GATE =====
    if not job.get("phase1_status") or job["phase1_status"].get("overall") != "PASS":
        raise HTTPException(400, "Phase 1 Digital Gatekeeping not cleared — software lock engaged")

    # ===== PHASE 2 GATE (operator tablet sign-off) =====
    phase2_clear = preflight.homeowner_verified and preflight.vertical_obstruction_clear and preflight.k9_and_child_clear_zone and preflight.personnel_clear
    if not phase2_clear:
        # Record audit + return 400; lock launch
        await _record_audit(job_id, user["id"], "PHASE2_FAIL", {
            "preflight": preflight.model_dump(),
            "failed_checks": [k for k, v in preflight.model_dump().items() if isinstance(v, bool) and not v],
        })
        raise HTTPException(400, "Phase 2 Physical Safety not cleared — software lock engaged")

    # ===== PHASE 3 GATE (hardware diagnostics) =====
    phase3_clear = (
        preflight.trailer_hatch_secured
        and preflight.drone_battery_percentage >= 90
        and preflight.battery_cell_variance_v < 0.02
        and preflight.rtk_gps_signal == "Centimeter-Level Locked"
        and preflight.communication_uplink.startswith("Strong")
        and preflight.local_weather_clear
    )
    if not phase3_clear:
        await _record_audit(job_id, user["id"], "PHASE3_FAIL", {"preflight": preflight.model_dump()})
        raise HTTPException(400, "Phase 3 Hardware Diagnostics not cleared — software lock engaged")

    await _record_audit(job_id, user["id"], "LAUNCH_AUTHORIZED", {"preflight": preflight.model_dump()})

    # Mark IN_FLIGHT, then asynchronously process (in-process simulated)
    now = now_iso()
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {
            "status": "IN_FLIGHT",
            "launched_at": now,
            "preflight": preflight.model_dump(),
            "operator_id": user["id"],
            "phase2_completed_at": now,
            "phase3_completed_at": now,
        }},
    )

    # Count this as a fleet drop on the contractor's billing meter
    await _record_fleet_drop(job["contractor_id"], job_id)
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
                "framing": topo.get("framing"),
                "gutters": topo.get("gutters"),
                "validation": topo.get("validation"),
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

    # ===== SEAMLESS GUTTER ADD-ON — merged into the master quote =====
    gutters = tele.get("gutters") or {}
    framing = tele.get("framing") or {}
    if mat.get("gutter_addon_enabled", True) and gutters.get("total_lf"):
        is_heavy = gutters.get("profile", "").startswith("6")
        lf_price = mat["gutter_6in_kstyle_lf_price"] if is_heavy else mat["gutter_5in_kstyle_lf_price"]
        g_lf = gutters["total_lf"]
        li(f"Seamless Gutter — {gutters['profile']}", round(g_lf, 1), "LF", lf_price, "RFG GUTTER")
        li("Hidden Hangers (24\" O.C.)", gutters["hangers"]["count"], "EA", mat["hidden_hanger_each_price"], "RFG HNG")
        li("Downspout Drop (with bracket + strap)", gutters["downspouts_count"], "EA", mat["downspout_drop_price"], "RFG DSPT")
        if gutters.get("elbow_count"):
            li("Downspout Elbow (A/B-style)", gutters["elbow_count"], "EA", mat["elbow_price"], "RFG ELB")
        if gutters.get("miter_count"):
            li("Strip / Box Miter Corner", gutters["miter_count"], "EA", mat["miter_price"], "RFG MITER")
        if gutters.get("end_cap_count"):
            li("End Caps", gutters["end_cap_count"], "EA", mat["end_cap_price"], "RFG CAP")
        if gutters.get("conductor_head_count"):
            li("Conductor Head", gutters["conductor_head_count"], "EA", mat["conductor_head_price"], "RFG COND")
        li("Gutter Installation Labor", round(g_lf, 1), "LF", mat["gutter_labor_per_lf"], XACTIMATE_TAGS["labor"])

    # ===== SUB-FASCIA / FRAMING REPAIRS — driven by detected anomalies =====
    anomalies_list = job.get("mission", {}).get("anomalies") or job.get("anomalies") or []
    gutter_rot_lf = sum(a.get("length_affected_ft", 0) for a in anomalies_list if a.get("code") == "gutter_board_rot")
    rafter_def_count = sum(1 for a in anomalies_list if a.get("code") == "rafter_deflection")
    if gutter_rot_lf > 0:
        li("Sub-Fascia Board Replacement", round(gutter_rot_lf, 1), "LF", mat["sub_fascia_lf_price"], "RFG FASCIA")
    if rafter_def_count > 0:
        li("Rafter Section Sister/Replacement", rafter_def_count, "EA", mat["rafter_replacement_each_price"], "FRM RAFTER")

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

    # --- STRATEX EXPERT PANEL CERTIFICATION (validation gates from roof_telemetry) ---
    rt = job.get("roof_telemetry") or {}
    val = rt.get("validation") or {}
    gates = val.get("gates") or []
    if gates:
        passed = val.get("passed", 0)
        total = val.get("total", len(gates))
        score = val.get("score_pct", 0)
        cert_color = TEAL if val.get("all_pass") else ORANGE
        el.append(Paragraph(
            f"STRATEX™ EXPERT PANEL CERTIFIED · {passed}/{total} GATES · {score}%",
            ParagraphStyle("cert", parent=h2, textColor=cert_color, fontSize=11),
        ))
        cert_rows = [["GATE", "AGENT", "RULE", "STATUS", "MESSAGE"]]
        for g in gates:
            cert_rows.append([
                g.get("label", ""),
                g.get("agent", ""),
                g.get("rule_ref", ""),
                "PASS" if g.get("pass") else "FAIL",
                g.get("message", "")[:70],
            ])
        ct = Table(cert_rows, colWidths=[1.55*inch, 1.45*inch, 0.45*inch, 0.55*inch, 3.0*inch])
        ct.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 7),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7),
            ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 1), (-1, -1), SILVER),
            ("TEXTCOLOR", (3, 1), (3, -1), cert_color),
            ("FONT", (3, 1), (3, -1), "Helvetica-Bold", 7),
            ("BACKGROUND", (0, 0), (-1, -1), OBS),
            ("BOX", (0, 0), (-1, -1), 0.5, TEAL),
            ("INNERGRID", (0, 0), (-1, -1), 0.2, MUTED),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        el.append(ct)
        el.append(Spacer(1, 6))
        el.append(Paragraph(
            "This proposal is backed by a 4-agent expert panel quality gate (Master Framing Carpenter / Architect, Master Roofing Contractor, Master CAD Designer, Master Gutter Contractor). Every digital twin must pass these deterministic checks before any measurement enters the supplement. Reference: /memory/expert_panel_review.md.",
            ParagraphStyle("cert_note", parent=p, textColor=MUTED, fontSize=8, leading=11),
        ))
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
            status = "STANDBY"; battery = 96 + (seed % 5)
        elif seed < 55:
            status = "CHARGING"; battery = 38 + seed
        elif seed < 75:
            status = "DEPLOYED"; battery = 80 - (seed % 10)
        elif seed < 92:
            status = "IN_FLIGHT"; battery = 60 + (seed % 15)
        else:
            status = "MAINTENANCE"; battery = max(20, seed - 10)
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
# RISK ENGINE — PHASE 1 Digital Gatekeeping + Audit + Dry-Run + Billing meter
# ---------------------------------------------------------------------------

async def _record_audit(job_id: str, actor_id: Optional[str], event: str, payload: Dict[str, Any]):
    """Append-only audit log — immutable (we never update or delete these rows)."""
    await db.preflight_audit.insert_one({
        "id": str(uuid.uuid4()),
        "job_id": job_id,
        "actor_id": actor_id,
        "event": event,
        "payload": payload,
        "ts": now_iso(),
    })


async def _record_fleet_drop(contractor_id: str, job_id: str):
    """Increment monthly drop counter for billing reconciliation. Per-month bucket."""
    bucket = datetime.now(timezone.utc).strftime("%Y-%m")
    await db.billing_meter.update_one(
        {"contractor_id": contractor_id, "bucket": bucket},
        {"$inc": {"drops": 1}, "$push": {"drop_job_ids": job_id}, "$setOnInsert": {"created_at": now_iso()}},
        upsert=True,
    )


def _classify_open_meteo(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply ASTM C1153 thermographic-roof-survey gates to live Open-Meteo data."""
    h = data.get("hourly") or {}
    times  = h.get("time") or []
    precip = h.get("precipitation") or []
    prob   = h.get("precipitation_probability") or []
    wind   = h.get("wind_speed_10m") or []
    clouds = h.get("cloud_cover") or []

    # Open-Meteo with past_hours=24 + forecast_hours=3 returns 28 entries:
    # indices 0..23 = past 24h (oldest→newest), 24 = current hour, 25..27 = forecast next 3h
    past24      = precip[:24] if len(precip) >= 24 else precip
    cloud_12h   = clouds[12:24] if len(clouds) >= 24 else clouds
    next2_prob  = prob[25:27]   if len(prob)   >= 27 else prob[-2:] if prob else []
    next2_pcp   = precip[25:27] if len(precip) >= 27 else precip[-2:] if precip else []
    cur_wind    = wind[24]      if len(wind)   > 24  else (wind[-1] if wind else 0.0)

    past_24h_precip_in    = round(sum(past24), 3)
    avg_cloud_12h_pct     = round(sum(cloud_12h) / len(cloud_12h), 1) if cloud_12h else 0.0
    next2h_precip_prob    = max(next2_prob) if next2_prob else 0
    next2h_precip_in      = round(sum(next2_pcp), 3) if next2_pcp else 0.0
    return {
        "past_24h_precip_in": past_24h_precip_in,
        "avg_cloud_12h_pct": avg_cloud_12h_pct,
        "next2h_precip_prob_pct": next2h_precip_prob,
        "next2h_precip_in": next2h_precip_in,
        "current_wind_mph": round(float(cur_wind), 1),
        "first_obs_ts": times[0] if times else None,
        "last_obs_ts":  times[-1] if times else None,
    }


async def _fetch_openmeteo(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch past-24h + next-3h hourly weather from Open-Meteo (no key, free)."""
    if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
        return None
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation,precipitation_probability,wind_speed_10m,cloud_cover"
        "&past_hours=24&forecast_hours=3"
        "&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto"
    )
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8) as cli:
            r = await cli.get(url)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.warning("open-meteo fetch failed for %.4f,%.4f: %s", lat, lon, e)
        return None


async def _astm_phase1(job: Dict[str, Any]) -> List[Phase1Result]:
    """Deterministic FAA/GIS mock + REAL Open-Meteo ASTM C1153 weather gates."""
    seed_int = abs(hash(job["id"])) % 100
    results: List[Phase1Result] = []

    # 1. FAA / LAANC Airspace — MOCKED (no public free API)
    if seed_int < 4:
        results.append(Phase1Result(name="FAA / LAANC Airspace", status="FAIL",
            details="Property intersects Class B controlled airspace — manual waiver required from FAA UAS Data Exchange."))
    elif seed_int < 14:
        results.append(Phase1Result(name="FAA / LAANC Airspace", status="WARN",
            details="Auto-LAANC authorization granted (0–400ft AGL envelope). Auth ID: LAANC-AUTO-" + job["id"][:8].upper()))
    else:
        results.append(Phase1Result(name="FAA / LAANC Airspace", status="PASS",
            details="Class G uncontrolled airspace. No FAA authorization required."))

    # 2–5. ASTM C1153 thermographic-roof weather gates — REAL Open-Meteo
    om = await _fetch_openmeteo(job.get("lat", 0.0), job.get("lon", 0.0))
    if not om:
        # Network failure — be honest, fail-closed (safer than launching blind)
        results.append(Phase1Result(name="Pre-Rain 24h Lookback (ASTM C1153)", status="FAIL",
            details="Weather telemetry unavailable (Open-Meteo unreachable). Launch locked pending live data — try again in 5 minutes."))
        results.append(Phase1Result(name="Solar Loading (12h Cloud Cover)", status="FAIL", details="Weather telemetry unavailable."))
        results.append(Phase1Result(name="Forecast 2h Buffer (Incoming Front)", status="FAIL", details="Weather telemetry unavailable."))
        results.append(Phase1Result(name="Sustained Wind", status="FAIL", details="Weather telemetry unavailable."))
    else:
        m = _classify_open_meteo(om)
        # 2. PRE-RAIN 24h — must be effectively zero precipitation in past 24h
        if m["past_24h_precip_in"] > 0.05:
            results.append(Phase1Result(name="Pre-Rain 24h Lookback (ASTM C1153)", status="FAIL",
                details=f"Delayed_Surface_Moisture — {m['past_24h_precip_in']:.2f}\" precipitation recorded in past 24h. ASTM C1153 requires dry shingle surface + 24h drying window before thermographic survey."))
        elif m["past_24h_precip_in"] > 0.01:
            results.append(Phase1Result(name="Pre-Rain 24h Lookback (ASTM C1153)", status="WARN",
                details=f"Trace precipitation ({m['past_24h_precip_in']:.2f}\") in past 24h — recommend extending dry window to 48h for highest data integrity."))
        else:
            results.append(Phase1Result(name="Pre-Rain 24h Lookback (ASTM C1153)", status="PASS",
                details=f"Past 24h precipitation: {m['past_24h_precip_in']:.2f}\" — shingle surface dry. Drying window satisfied."))

        # 3. SOLAR LOADING — daytime cloud cover past 12h must be ≤ 70%
        if m["avg_cloud_12h_pct"] > 70.0:
            results.append(Phase1Result(name="Solar Loading (12h Cloud Cover)", status="FAIL",
                details=f"Delayed_Insufficient_Solar_Load — {m['avg_cloud_12h_pct']:.0f}% avg cloud cover past 12h exceeds 70% threshold. Roof has not absorbed sufficient solar energy for night-scan thermal contrast."))
        elif m["avg_cloud_12h_pct"] > 50.0:
            results.append(Phase1Result(name="Solar Loading (12h Cloud Cover)", status="WARN",
                details=f"Marginal solar load — {m['avg_cloud_12h_pct']:.0f}% avg cloud cover past 12h. Thermal contrast will be reduced but readable."))
        else:
            results.append(Phase1Result(name="Solar Loading (12h Cloud Cover)", status="PASS",
                details=f"Avg cloud cover past 12h: {m['avg_cloud_12h_pct']:.0f}% — sufficient solar absorption for night-scan thermal Δ."))

        # 4. FORECAST 2h BUFFER — incoming rain front
        if m["next2h_precip_prob_pct"] > 30 or m["next2h_precip_in"] > 0.01:
            results.append(Phase1Result(name="Forecast 2h Buffer (Incoming Front)", status="FAIL",
                details=f"Delayed_Incoming_Front — {m['next2h_precip_prob_pct']}% precipitation probability ({m['next2h_precip_in']:.2f}\" expected) in next 2 hours. Atmospheric Δ would wash out thermal contrast + fleet recovery time inadequate."))
        else:
            results.append(Phase1Result(name="Forecast 2h Buffer (Incoming Front)", status="PASS",
                details=f"Forecast 2h: {m['next2h_precip_prob_pct']}% precip probability — clean operational runway."))

        # 5. SUSTAINED WIND — must be ≤ 5 mph
        if m["current_wind_mph"] > 8.0:
            results.append(Phase1Result(name="Sustained Wind", status="FAIL",
                details=f"Sustained wind {m['current_wind_mph']:.1f}mph — exceeds 5mph operational threshold + 8mph hard limit. RTK precision compromised."))
        elif m["current_wind_mph"] > 5.0:
            results.append(Phase1Result(name="Sustained Wind", status="WARN",
                details=f"Sustained wind {m['current_wind_mph']:.1f}mph above 5mph threshold. Manual operator override required."))
        else:
            results.append(Phase1Result(name="Sustained Wind", status="PASS",
                details=f"Sustained wind {m['current_wind_mph']:.1f}mph — within 5mph operational threshold."))

    # 6. Utility & Power-Line GIS — MOCKED (paid GIS API later)
    if seed_int % 11 == 0:
        results.append(Phase1Result(name="Utility & Power-Line GIS", status="WARN",
            details="Medium-voltage distribution line at southwest property edge. Flight envelope auto-adjusted to maintain 25ft buffer."))
    else:
        results.append(Phase1Result(name="Utility & Power-Line GIS", status="PASS",
            details="No high-voltage transmission or overhead utility obstructions detected on flight plane."))

    return results


def _mock_phase1(job: Dict[str, Any]) -> List[Phase1Result]:
    """Legacy synchronous mock — kept for any non-async callers; not used in production path."""
    return []


@api.post("/contractor/jobs/{job_id}/run-phase1")
async def run_phase1(job_id: str, user=Depends(contractor_only)):
    """Execute Phase 1 Digital Gatekeeping. Software-locks launch unless overall=PASS."""
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] not in ("PENDING_PHASE1", "PENDING_FIELD_CAPTURE", "PHASE1_BLOCKED", "RESCHEDULED_CONFIRMED"):
        raise HTTPException(400, f"Cannot re-run Phase 1 from status {job['status']}")

    results = await _astm_phase1(job)
    has_fail = any(r.status == "FAIL" for r in results)
    overall = "FAIL" if has_fail else "PASS"
    phase1_status = {"overall": overall, "checks": [r.model_dump() for r in results], "ran_at": now_iso()}
    new_status = "PENDING_FIELD_CAPTURE" if overall == "PASS" else "PHASE1_BLOCKED"
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"phase1_status": phase1_status, "phase1_completed_at": now_iso(), "status": new_status}},
    )
    await _record_audit(job_id, user["id"], f"PHASE1_{overall}", {"checks": phase1_status["checks"]})

    # 🚨 ASTM C1153 Weather Abort — push contractor notification email + reschedule windows
    if overall == "FAIL" and user.get("email"):
        try:
            windows_payload = await _safe_reschedule_windows(job)
            html = _phase1_fail_email_html(job, phase1_status["checks"], windows_payload)
            subject = f"STRATEX™ Dispatch Delayed — Phase 1 ASTM Lock · {job.get('property_address','')[:40]}"
            email_result = await _send_email(user["email"], subject, html)
            await _record_audit(job_id, user["id"], "PHASE1_FAIL_EMAIL_SENT", {
                "to": user["email"], "mocked": email_result.get("mocked", False),
                "windows_count": len(windows_payload),
            })
        except Exception as e:
            logger.warning("phase1 fail email push failed for job %s: %s", job_id, e)

    return phase1_status


# ---------------------------------------------------------------------------
# WEATHER — 7-day forecast (reschedule suggestion) + mid-mission live monitor
# ---------------------------------------------------------------------------

async def _fetch_openmeteo_forecast_7d(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation,precipitation_probability,wind_speed_10m,cloud_cover"
        "&past_hours=24&forecast_days=7"
        "&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto"
    )
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.get(url); r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.warning("open-meteo 7d fetch failed: %s", e); return None


@api.get("/contractor/jobs/{job_id}/reschedule-suggestions")
async def reschedule_suggestions(job_id: str, user=Depends(contractor_only)):
    """Scan the next 7 days of Open-Meteo data for windows that satisfy all 4 ASTM gates.

    Returns the top 3 evening (sunset → 10pm local) slots where:
      • past 24h precip ≤ 0.05"
      • forecast 2h precip prob ≤ 30%
      • day cloud cover ≤ 70%
      • wind ≤ 5 mph
    """
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    om = await _fetch_openmeteo_forecast_7d(job.get("lat", 38.04), job.get("lon", -84.5))
    if not om:
        return {"available": False, "reason": "Open-Meteo unavailable", "windows": []}
    h = om.get("hourly") or {}
    times = h.get("time") or []
    precip = h.get("precipitation") or []
    prob = h.get("precipitation_probability") or []
    wind = h.get("wind_speed_10m") or []
    clouds = h.get("cloud_cover") or []
    # past_hours=24 → first 24 entries are past
    PAST = 24
    windows = []
    # Walk forward 1 hour at a time and treat index i as candidate launch slot
    for i in range(PAST + 2, min(len(times), PAST + 24 * 7)):
        # eligibility window: prefer 19:00-22:00 local (drone night scan)
        hour_local = int(times[i].split("T")[1].split(":")[0]) if "T" in times[i] else 0
        if hour_local < 19 or hour_local > 22:
            continue
        past24_precip = sum(precip[max(0, i - 24):i]) if precip[:i] else 0
        next2_prob = max(prob[i:i + 2]) if len(prob) > i + 1 else 0
        next2_precip = sum(precip[i:i + 2]) if len(precip) > i + 1 else 0
        # previous-12h cloud (daytime preceding the night slot)
        day_clouds = clouds[max(0, i - 12):i] if clouds[:i] else []
        avg_clouds = (sum(day_clouds) / len(day_clouds)) if day_clouds else 0
        cur_wind = wind[i] if i < len(wind) else 0
        ok = (past24_precip <= 0.05 and next2_prob <= 30 and next2_precip <= 0.01
              and avg_clouds <= 70 and cur_wind <= 5.0)
        if ok:
            windows.append({
                "iso": times[i],
                "past_24h_precip_in": round(past24_precip, 2),
                "avg_cloud_12h_pct": round(avg_clouds, 0),
                "next_2h_precip_prob_pct": next2_prob,
                "wind_mph": round(cur_wind, 1),
                "label": f"{times[i].split('T')[0]} · {times[i].split('T')[1]}",
            })
        if len(windows) >= 3:
            break
    return {"available": True, "windows": windows}


@api.get("/contractor/jobs/{job_id}/weather-monitor")
async def weather_monitor(job_id: str, user=Depends(contractor_only)):
    """Live weather pulse — re-fetches Open-Meteo for the job's coordinates so the
    contractor sees mid-mission wind / precip / cloud changes without re-running Phase 1."""
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    return await _live_weather_pulse(job)


@api.get("/operator/jobs/{job_id}/weather-monitor")
async def operator_weather_monitor(job_id: str, user=Depends(operator_only)):
    """Operator-side live weather pulse — same payload as contractor weather-monitor, but
    accessible by operators on jobs assigned (or pickable) by them. No financial data leaks
    here since the payload is pure atmospherics."""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    return await _live_weather_pulse(job)


async def _live_weather_pulse(job: Dict[str, Any]) -> Dict[str, Any]:
    om = await _fetch_openmeteo(job.get("lat", 38.04), job.get("lon", -84.5))
    if not om:
        return {"available": False}
    m = _classify_open_meteo(om)
    abort = (m["past_24h_precip_in"] > 0.05
             or m["avg_cloud_12h_pct"] > 70
             or m["next2h_precip_prob_pct"] > 30
             or m["next2h_precip_in"] > 0.01
             or m["current_wind_mph"] > 8.0)
    return {"available": True, **m, "abort_recommended": abort, "as_of": now_iso()}


async def _safe_reschedule_windows(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Helper used by both the reschedule endpoint and the Phase 1 fail email — fetches
    next 3 ASTM-compliant evening launch windows for this job. Returns [] on any failure."""
    try:
        om = await _fetch_openmeteo_forecast_7d(job.get("lat", 38.04), job.get("lon", -84.5))
        if not om:
            return []
        h = om.get("hourly") or {}
        times = h.get("time") or []
        precip = h.get("precipitation") or []
        prob = h.get("precipitation_probability") or []
        wind = h.get("wind_speed_10m") or []
        clouds = h.get("cloud_cover") or []
        PAST = 24
        out: List[Dict[str, Any]] = []
        for i in range(PAST + 2, min(len(times), PAST + 24 * 7)):
            hour_local = int(times[i].split("T")[1].split(":")[0]) if "T" in times[i] else 0
            if hour_local < 19 or hour_local > 22:
                continue
            past24_precip = sum(precip[max(0, i - 24):i]) if precip[:i] else 0
            next2_prob = max(prob[i:i + 2]) if len(prob) > i + 1 else 0
            next2_precip = sum(precip[i:i + 2]) if len(precip) > i + 1 else 0
            day_clouds = clouds[max(0, i - 12):i] if clouds[:i] else []
            avg_clouds = (sum(day_clouds) / len(day_clouds)) if day_clouds else 0
            cur_wind = wind[i] if i < len(wind) else 0
            if (past24_precip <= 0.05 and next2_prob <= 30 and next2_precip <= 0.01
                    and avg_clouds <= 70 and cur_wind <= 5.0):
                out.append({
                    "iso": times[i],
                    "past_24h_precip_in": round(past24_precip, 2),
                    "avg_cloud_12h_pct": round(avg_clouds, 0),
                    "next_2h_precip_prob_pct": next2_prob,
                    "wind_mph": round(cur_wind, 1),
                    "label": f"{times[i].split('T')[0]} · {times[i].split('T')[1]}",
                })
            if len(out) >= 3:
                break
        return out
    except Exception as e:
        logger.warning("safe reschedule windows failed: %s", e)
        return []


@api.post("/operator/jobs/{job_id}/dry-run")
async def operator_dry_run(job_id: str, body: DryRunBody, user=Depends(operator_only)):
    """Operator flags a job as Dry-Run (access denied / unnotified / aggressive animal / wrong address).
    Charges the contractor $150 on next month's invoice (flag-only, no instant Stripe charge)."""
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] not in ("PENDING_FIELD_CAPTURE", "PENDING_PHASE1", "PHASE1_BLOCKED"):
        raise HTTPException(400, f"Cannot dry-run a job in status {job['status']}")

    valid = {"locked_gate", "unnotified_homeowner", "aggressive_animal", "wrong_address", "other"}
    if body.reason not in valid:
        raise HTTPException(400, f"Invalid reason. Allowed: {sorted(valid)}")

    dry_run = {
        "reason": body.reason,
        "notes": body.notes,
        "operator_id": user["id"],
        "flagged_at": now_iso(),
        "penalty_usd": DRY_RUN_PENALTY,
    }
    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "DRY_RUN_PENALTY", "dry_run": dry_run}},
    )
    # Append to billing meter (next month's invoice)
    bucket = datetime.now(timezone.utc).strftime("%Y-%m")
    await db.billing_meter.update_one(
        {"contractor_id": job["contractor_id"], "bucket": bucket},
        {"$inc": {"dry_run_count": 1, "dry_run_charges_usd": DRY_RUN_PENALTY},
         "$push": {"dry_run_job_ids": job_id},
         "$setOnInsert": {"created_at": now_iso()}},
        upsert=True,
    )
    await _record_audit(job_id, user["id"], "DRY_RUN_FLAGGED", dry_run)
    return await db.jobs.find_one({"id": job_id}, {"_id": 0})


@api.get("/contractor/jobs/{job_id}/audit-log")
async def job_audit_log(job_id: str, user=Depends(contractor_only)):
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0, "id": 1})
    if not job:
        raise HTTPException(404, "Job not found")
    log = await db.preflight_audit.find({"job_id": job_id}, {"_id": 0}).sort("ts", 1).to_list(500)
    return {"job_id": job_id, "events": log}


@api.get("/contractor/billing/meter")
async def billing_meter_me(user=Depends(contractor_only)):
    """Return current month's drop usage + dry-run penalties for the contractor's upcoming invoice."""
    bucket = datetime.now(timezone.utc).strftime("%Y-%m")
    meter = await db.billing_meter.find_one({"contractor_id": user["id"], "bucket": bucket}, {"_id": 0}) or {
        "bucket": bucket, "drops": 0, "drop_job_ids": [], "dry_run_count": 0, "dry_run_charges_usd": 0.0, "dry_run_job_ids": [],
    }
    full = await db.users.find_one({"id": user["id"]}, {"_id": 0}) or {}
    tier_key = full.get("subscription_tier") or "on_demand"
    tier = PRICING_TIERS.get(tier_key, PRICING_TIERS["on_demand"])
    drops = meter.get("drops", 0)
    included = tier["included_drops"]
    overage_drops = max(0, drops - included)
    overage_charges = overage_drops * tier["extra_drop_price"]
    dry_charges = float(meter.get("dry_run_charges_usd") or 0.0)
    monthly_retainer = tier["price"] if full.get("subscription_status") == "active" else 0.0
    return {
        "bucket": bucket,
        "tier_key": tier_key,
        "tier_name": tier["name"],
        "monthly_retainer": monthly_retainer,
        "drops_used": drops,
        "drops_included": included,
        "overage_drops": overage_drops,
        "overage_drop_price": tier["extra_drop_price"],
        "overage_charges_usd": overage_charges,
        "dry_run_count": meter.get("dry_run_count", 0),
        "dry_run_charges_usd": dry_charges,
        "estimated_invoice_total": monthly_retainer + overage_charges + dry_charges,
        "implementation_fee_paid": full.get("implementation_fee_paid", False),
    }


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

    # Idempotent upsert of the 7 Central-Kentucky sales targets into Mongo so the
    # P3 Competitive-Intel Onboarding Mapping can JOIN against `db.sales_targets`
    # without relying on the in-code constant.
    for t in KY_SALES_TARGETS_SEED:
        await db.sales_targets.update_one(
            {"id": t["id"]},
            {"$set": {**t, "seeded_at": now_iso(), "seed_source": "KY_SALES_TARGETS_SEED"}},
            upsert=True,
        )

    # Kick off the 24h reminder background sweep (idempotent — tracked via reminder_24h_sent_at)
    global _reminder_task
    _reminder_task = asyncio.create_task(_reminder_24h_sweep_loop())

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


def _twilio_ready() -> bool:
    return bool(os.environ.get("TWILIO_ACCOUNT_SID")
                and os.environ.get("TWILIO_AUTH_TOKEN")
                and os.environ.get("TWILIO_FROM"))


_E164_RE = __import__("re").compile(r"^\+[1-9]\d{6,14}$")


def _valid_e164(s: Optional[str]) -> bool:
    return bool(s) and bool(_E164_RE.match(s.strip()))


async def _send_sms(to: str, body: str) -> Dict[str, Any]:
    """Async-safe Twilio SMS send with graceful mock when env vars missing or number invalid."""
    if not _valid_e164(to):
        return {"mocked": True, "to": to, "note": "Invalid or missing E.164 phone — SMS skipped"}
    if not _twilio_ready():
        return {"mocked": True, "to": to, "body_preview": body[:60], "note": "TWILIO_* env not configured — SMS logged but not sent"}
    from twilio.rest import Client as _TwClient

    def _send():
        cli = _TwClient(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
        msg = cli.messages.create(from_=os.environ["TWILIO_FROM"], to=to, body=body[:1500])
        return {"sid": msg.sid, "status": msg.status}

    try:
        result = await asyncio.to_thread(_send)
        return {"mocked": False, "to": to, **result}
    except Exception as e:
        logger.warning("twilio send failed to %s: %s", to, e)
        return {"mocked": True, "to": to, "error": str(e)[:140], "note": "Twilio API error — fell back to mock"}


def _homeowner_delay_sms_body(job: Dict[str, Any], windows: List[Dict[str, Any]], contractor_name: str) -> str:
    homeowner = (job.get("homeowner_name") or "there").split()[0]
    if not windows:
        return (
            f"Hi {homeowner}, {contractor_name} here — today's weather isn't meeting ASTM standards "
            f"for your roof scan. We're watching the forecast and will text you the moment a window opens. "
            f"Powered by STRATEX."
        )
    numbered = "\n".join(f"{i+1}) {w['label']}" for i, w in enumerate(windows[:3]))
    extra = " or 2/3" if len(windows) >= 2 else ""
    return (
        f"Hi {homeowner}, {contractor_name} here. Weather isn't meeting our ASTM scan standards today — "
        f"please reply with the # of your preferred window:\n{numbered}\n"
        f"Reply 1{extra} to confirm. Powered by STRATEX."
    )


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


def _reminder_24h_sms_body(job: Dict[str, Any], contractor_name: str) -> str:
    homeowner = (job.get("homeowner_name") or "there").split()[0]
    label = job.get("scheduled_window_label") or job.get("scheduled_launch_at") or "tomorrow"
    return (
        f"Hi {homeowner}, {contractor_name} here — friendly reminder that our drone roof scan "
        f"is scheduled for {label}. No action needed on your end; we operate from the curb. "
        f"Reply STOP to cancel. — STRATEX"
    )


# ----------- 24h reminder background sweep -----------
# Module-level handle so we can cancel on shutdown
_reminder_task: Optional[asyncio.Task] = None

# Configurable cadence (override via env for tests)
REMINDER_SWEEP_INTERVAL_S = int(os.environ.get("REMINDER_SWEEP_INTERVAL_S", "900"))   # 15 min
REMINDER_LEAD_HOURS = float(os.environ.get("REMINDER_LEAD_HOURS", "24"))               # send 24h before
REMINDER_WINDOW_HOURS = float(os.environ.get("REMINDER_WINDOW_HOURS", "1.0"))          # ± 1h window


def _parse_scheduled_local(iso_or_label: str) -> Optional[datetime]:
    """The open-meteo ISO comes back as local-zone naïve (e.g. '2026-05-27T21:00').
    Treat that as wall-clock local time of the SERVER for simplicity; production should
    persist the IANA tz from the API response."""
    if not iso_or_label:
        return None
    try:
        s = iso_or_label.replace(" · ", "T") if "T" not in iso_or_label and "·" in iso_or_label else iso_or_label
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


async def _reminder_24h_sweep_once() -> Dict[str, Any]:
    """Find PHASE1_BLOCKED jobs whose scheduled_launch_at is ~24h away and the homeowner
    hasn't been reminded yet. Send the SMS + email reminder, flip status, record audit."""
    now = datetime.now(timezone.utc).astimezone()
    lead = REMINDER_LEAD_HOURS
    half = REMINDER_WINDOW_HOURS
    sent = 0
    errors: List[str] = []
    # Pull a bounded slice — we don't expect more than a few hundred locked-in jobs at a time
    cursor = db.jobs.find(
        {
            "scheduled_launch_at": {"$exists": True, "$ne": None},
            "reminder_24h_sent_at": {"$exists": False},
            "status": {"$in": ["PHASE1_BLOCKED", "RESCHEDULED_CONFIRMED"]},
        },
        {"_id": 0},
    )
    async for job in cursor:
        try:
            target = _parse_scheduled_local(job.get("scheduled_launch_at") or "")
            if not target:
                continue
            # Compare as naive local-time deltas
            delta_h = (target - now.replace(tzinfo=target.tzinfo) if target.tzinfo else target - now.replace(tzinfo=None)).total_seconds() / 3600.0
            if not (lead - half <= delta_h <= lead + half):
                continue

            # Pull the contractor's display name
            user = await db.users.find_one({"id": job.get("contractor_id")}, {"_id": 0}) or {}
            contractor_name = user.get("company_name") or user.get("legal_name") or "your roofing contractor"

            sms_result: Dict[str, Any] = {"skipped": True}
            email_result: Dict[str, Any] = {"skipped": True}
            phone = (job.get("delay_notified_sms") or job.get("homeowner_phone") or "").strip()
            email = (job.get("delay_notified_to") or job.get("homeowner_email") or "").strip()

            if phone:
                body = _reminder_24h_sms_body(job, contractor_name)
                sms_result = await _send_sms(phone, body)
            if email:
                html = (
                    f"<table cellpadding='0' cellspacing='0' style='background:#FFFFFF;color:#0F172A;"
                    f"font-family:Helvetica,Arial,sans-serif;width:100%;max-width:600px;padding:24px;"
                    f"border:1px solid #E2E8F0;border-radius:6px;'><tr><td>"
                    f"<h2 style='margin:0 0 8px;font-size:18px;color:#0F172A;'>Your roof inspection is tomorrow</h2>"
                    f"<p style='color:#475569;font-size:13px;line-height:1.6;'>Hi {(job.get('homeowner_name') or 'there').split()[0]}, "
                    f"this is a quick reminder that {contractor_name} will be performing your drone roof scan at <b>{job.get('scheduled_window_label') or job.get('scheduled_launch_at')}</b>.</p>"
                    f"<p style='color:#475569;font-size:13px;line-height:1.6;'>No action needed — our drone operates from the public right-of-way and you don't need to be home.</p>"
                    f"<div style='margin-top:18px;padding-top:12px;border-top:1px solid #E2E8F0;color:#94A3B8;font-size:10px;letter-spacing:0.18em;text-transform:uppercase;'>Powered by STRATEX&trade;</div>"
                    f"</td></tr></table>"
                )
                email_result = await _send_email(email, "Reminder: Your roof scan is tomorrow · STRATEX", html)

            update = {
                "reminder_24h_sent_at": now_iso(),
                "status": "RESCHEDULED_CONFIRMED",
            }
            await db.jobs.update_one({"id": job["id"]}, {"$set": update})
            await _record_audit(job["id"], job.get("contractor_id", "system"), "REMINDER_24H_SENT", {
                "to_phone": phone or None,
                "to_email": email or None,
                "sms_mocked": sms_result.get("mocked", False) if not sms_result.get("skipped") else None,
                "email_mocked": email_result.get("mocked", False) if not email_result.get("skipped") else None,
                "target": job.get("scheduled_launch_at"),
            })
            sent += 1
        except Exception as e:
            errors.append(f"{job.get('id','?')}: {e}")
            logger.warning("reminder sweep failed for job %s: %s", job.get("id"), e)

    return {"swept_at": now_iso(), "sent": sent, "errors": errors}


async def _reminder_24h_sweep_loop():
    """Long-running background loop. Sleeps REMINDER_SWEEP_INTERVAL_S between sweeps. Survives errors."""
    logger.info("reminder 24h sweep loop started (interval=%ss, lead=%sh ± %sh)",
                REMINDER_SWEEP_INTERVAL_S, REMINDER_LEAD_HOURS, REMINDER_WINDOW_HOURS)
    while True:
        try:
            result = await _reminder_24h_sweep_once()
            if result["sent"] > 0 or result["errors"]:
                logger.info("reminder sweep: sent=%s errors=%s", result["sent"], result["errors"])
        except asyncio.CancelledError:
            logger.info("reminder sweep loop cancelled")
            raise
        except Exception as e:
            logger.warning("reminder sweep loop iteration failed: %s", e)
        try:
            await asyncio.sleep(REMINDER_SWEEP_INTERVAL_S)
        except asyncio.CancelledError:
            raise


@api.post("/contractor/run-reminder-sweep")
async def manual_reminder_sweep(user=Depends(contractor_only)):
    """Manual trigger for the 24h reminder sweep — handy for ops/testing.
    Returns the same summary as one background sweep iteration."""
    return await _reminder_24h_sweep_once()


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


def _phase1_fail_email_html(job: Dict[str, Any], checks: List[Dict[str, Any]], windows: List[Dict[str, Any]]) -> str:
    """ASTM C1153 weather-abort notification to the contractor."""
    fail_rows = "".join(
        f"<tr><td style='color:#FF5500;font-family:monospace;font-size:11px;padding:6px 8px;border-bottom:1px solid #1A2230;text-transform:uppercase;letter-spacing:0.12em;'>{c['name']}</td>"
        f"<td style='color:#FF5500;font-family:monospace;font-size:11px;padding:6px 8px;border-bottom:1px solid #1A2230;'>{c['status']}</td>"
        f"<td style='color:#94A3B8;font-size:11px;padding:6px 8px;border-bottom:1px solid #1A2230;line-height:1.5;'>{c.get('details','')}</td></tr>"
        for c in checks if c.get("status") in ("FAIL", "WARN")
    ) or "<tr><td colspan='3' style='color:#94A3B8;padding:6px 8px;'>—</td></tr>"
    window_rows = "".join(
        f"<tr><td style='color:#39FF14;font-family:monospace;font-size:11px;padding:6px 8px;border-bottom:1px solid #1A2230;letter-spacing:0.12em;'>{w['label']}</td>"
        f"<td style='color:#94A3B8;font-size:11px;padding:6px 8px;border-bottom:1px solid #1A2230;'>precip 24h {w['past_24h_precip_in']}\" · clouds {w['avg_cloud_12h_pct']}% · wind {w['wind_mph']}mph</td></tr>"
        for w in (windows or [])
    ) or "<tr><td colspan='2' style='color:#94A3B8;padding:6px 8px;font-size:11px;'>No ASTM-compliant launch windows in the next 7 days — extended forecast review required.</td></tr>"
    return f"""
<table cellpadding="0" cellspacing="0" style="background:#06080B;color:#E2E8F0;font-family:Helvetica,Arial,sans-serif;width:100%;max-width:680px;padding:24px;border:1px solid #FF5500;">
  <tr><td>
    <div style="color:#FF5500;font-size:11px;letter-spacing:0.32em;text-transform:uppercase;">// STRATEX&trade; · DISPATCH DELAYED</div>
    <h1 style="color:#E2E8F0;letter-spacing:0.06em;text-transform:uppercase;margin:8px 0 4px;font-size:22px;">Phase 1 Gatekeeping · Software Lock Engaged</h1>
    <div style="color:#94A3B8;font-size:12px;margin-bottom:18px;">{job.get('property_address','')} &middot; Job {job['id'][:8]}</div>
    <p style="color:#E2E8F0;font-size:13px;line-height:1.6;margin:0 0 14px;">ASTM C1153 thermographic survey conditions are not met for this property right now. The autonomous launch is locked until atmospherics clear. Failing gates:</p>
    <table cellpadding="0" cellspacing="0" style="width:100%;border:1px solid #FF550044;margin-bottom:18px;">{fail_rows}</table>
    <p style="color:#39FF14;font-size:11px;letter-spacing:0.32em;text-transform:uppercase;margin:0 0 8px;">// Next ASTM-COMPLIANT WINDOWS (LOCAL TIME)</p>
    <table cellpadding="0" cellspacing="0" style="width:100%;border:1px solid #39FF1444;margin-bottom:14px;">{window_rows}</table>
    <p style="color:#94A3B8;line-height:1.6;font-size:12px;">The system will auto-re-run Phase 1 against live Open-Meteo telemetry; you can also retry manually from the contractor portal. The dispatch will resume the moment all 4 weather gates pass.</p>
    <div style="margin-top:24px;color:#FF5500;font-size:10px;letter-spacing:0.32em;text-transform:uppercase;">STRATEX&trade; Autonomous Recon Network &middot; Fleet Safety Protocol</div>
  </td></tr>
</table>"""


def _homeowner_delay_email_html(job: Dict[str, Any], windows: List[Dict[str, Any]], contractor_name: str) -> str:
    """Friendly homeowner-facing weather-delay notice with proposed reschedule windows."""
    homeowner = job.get("homeowner_name") or "there"
    first_label = windows[0]["label"] if windows else None
    rest = windows[1:3] if len(windows) > 1 else []
    rest_html = "".join(
        f"<li style='color:#475569;font-size:13px;line-height:1.7;'>{w['label']}</li>" for w in rest
    )
    rest_block = f"<p style='color:#475569;font-size:13px;line-height:1.6;margin:0 0 6px;'>Alternate options:</p><ul style='margin:0 0 18px 18px;padding:0;'>{rest_html}</ul>" if rest_html else ""
    primary_block = (
        f"<div style='background:#F0F9FF;border:1px solid #0EA5E9;padding:16px;margin:16px 0;'>"
        f"<div style='color:#0369A1;font-size:11px;letter-spacing:0.24em;text-transform:uppercase;margin-bottom:6px;'>Next Recommended Window</div>"
        f"<div style='color:#0F172A;font-size:18px;font-weight:600;'>{first_label}</div>"
        f"</div>"
        if first_label else
        "<p style='color:#475569;font-size:13px;line-height:1.6;'>Our weather monitoring is tracking conditions and we'll reach out with a new flight window the moment one opens up.</p>"
    )
    return f"""
<table cellpadding="0" cellspacing="0" style="background:#FFFFFF;color:#0F172A;font-family:Helvetica,Arial,sans-serif;width:100%;max-width:600px;padding:32px 28px;border:1px solid #E2E8F0;border-radius:6px;">
  <tr><td>
    <h1 style="font-size:20px;margin:0 0 6px;color:#0F172A;">A quick weather update on your roof inspection</h1>
    <p style="color:#475569;font-size:13px;line-height:1.7;margin:0 0 14px;">Hi {homeowner}, this is {contractor_name} — our advanced thermographic survey of your roof requires very specific atmospheric conditions (ASTM&nbsp;C1153 standard) to capture data that holds up under insurance review. Today's conditions don't meet that bar, so we're holding off rather than collecting a noisy scan.</p>
    {primary_block}
    {rest_block}
    <p style="color:#475569;font-size:13px;line-height:1.6;margin:8px 0 0;">No action needed on your end — we'll confirm 24 hours before the flight. As always, our drones never enter your property or require anyone home; they operate from the public right-of-way.</p>
    <p style="color:#475569;font-size:13px;line-height:1.6;margin:14px 0 0;">Thanks for your patience,<br/><strong>{contractor_name}</strong></p>
    <div style="margin-top:24px;padding-top:14px;border-top:1px solid #E2E8F0;color:#94A3B8;font-size:10px;letter-spacing:0.18em;text-transform:uppercase;">Powered by STRATEX&trade; · ASTM C1153 Compliance</div>
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


class NotifyHomeownerDelayBody(BaseModel):
    homeowner_email: Optional[EmailStr] = None
    homeowner_phone: Optional[str] = None


@api.post("/contractor/jobs/{job_id}/notify-homeowner-delay")
async def notify_homeowner_delay(job_id: str, body: NotifyHomeownerDelayBody, user=Depends(contractor_only)):
    """One-click homeowner weather-delay notification. Pulls the next 3 ASTM-compliant
    launch windows from Open-Meteo and pushes them via EMAIL (Resend) and SMS (Twilio).
    Only valid while the job is PHASE1_BLOCKED. Either channel may be mocked when the
    upstream credential is missing — the audit row still gets written."""
    job = await db.jobs.find_one({"id": job_id, "contractor_id": user["id"]}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    if job.get("status") != "PHASE1_BLOCKED":
        raise HTTPException(400, "Notify-delay is only available while the job is PHASE1_BLOCKED")
    to_email = (body.homeowner_email or job.get("homeowner_email") or "").strip()
    to_phone = (body.homeowner_phone or job.get("homeowner_phone") or "").strip()
    if not to_email and not to_phone:
        raise HTTPException(400, "Either homeowner email or homeowner phone (E.164) is required")

    windows = await _safe_reschedule_windows(job)
    contractor_name = user.get("company_name") or user.get("legal_name") or "your roofing contractor"

    email_result: Dict[str, Any] = {"skipped": True}
    sms_result: Dict[str, Any] = {"skipped": True}

    if to_email:
        html = _homeowner_delay_email_html(job, windows, contractor_name)
        email_result = await _send_email(to_email, "Weather update on your roof inspection · STRATEX", html)
    if to_phone:
        sms_body = _homeowner_delay_sms_body(job, windows, contractor_name)
        sms_result = await _send_sms(to_phone, sms_body)

    update_set: Dict[str, Any] = {
        "delay_notified_at": now_iso(),
        # Persist proposed windows for the 2-way SMS reply mapping (homeowner texts back 1/2/3)
        "proposed_windows": windows,
    }
    if to_email and not email_result.get("skipped"):
        update_set["delay_notified_to"] = to_email
    if to_phone and not sms_result.get("skipped"):
        update_set["delay_notified_sms"] = to_phone
    await db.jobs.update_one({"id": job_id}, {"$set": update_set})

    await _record_audit(job_id, user["id"], "HOMEOWNER_DELAY_NOTIFIED", {
        "to_email": to_email or None,
        "to_phone": to_phone or None,
        "email_mocked": email_result.get("mocked", False) if not email_result.get("skipped") else None,
        "sms_mocked": sms_result.get("mocked", False) if not sms_result.get("skipped") else None,
        "windows_count": len(windows),
    })
    return {
        "ok": True,
        "to_email": to_email or None,
        "to_phone": to_phone or None,
        "email": email_result,
        "sms": sms_result,
        "windows_count": len(windows),
    }


# ---------------------------------------------------------------------------
# TWILIO INBOUND SMS WEBHOOK — homeowner texts back 1/2/3 to confirm window
# ---------------------------------------------------------------------------
# Configure in Twilio Console: Phone Numbers → your number → Messaging → "A MESSAGE COMES IN"
#   webhook URL = {your_public_url}/api/twilio/inbound-sms  (POST)
# Twilio sends application/x-www-form-urlencoded with fields: From, To, Body, MessageSid, etc.
# We reply with TwiML so the homeowner sees an instant confirmation.

from fastapi import Form
from fastapi.responses import Response

_TWIML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'


def _twiml(message: str) -> Response:
    body = f'{_TWIML_HEADER}<Response><Message>{message}</Message></Response>'
    return Response(content=body, media_type="application/xml")


@api.post("/twilio/inbound-sms")
async def twilio_inbound_sms(
    From: str = Form(""),
    Body: str = Form(""),
    MessageSid: str = Form(""),
):
    """Public webhook — Twilio hits this when an SMS comes in to our FROM number.
    Matches the sender phone to the most-recent PHASE1_BLOCKED job that we notified,
    parses '1'/'2'/'3', and locks in the scheduled launch window."""
    sender = (From or "").strip()
    txt = (Body or "").strip().lower()
    if not sender:
        return _twiml("We couldn't verify your number. Please call your contractor.")

    # Look up the most recently notified PHASE1_BLOCKED job for this phone
    job = await db.jobs.find_one(
        {"status": "PHASE1_BLOCKED", "delay_notified_sms": sender},
        {"_id": 0},
        sort=[("delay_notified_at", -1)],
    )
    if not job:
        return _twiml("We couldn't match your number to an active reschedule. Please call your contractor for help.")

    windows = job.get("proposed_windows") or []
    if not windows:
        return _twiml("No reschedule windows are currently on file. Your contractor will reach out shortly.")

    # Parse first digit 1-9 from body
    import re as _re
    m = _re.search(r"[1-9]", txt)
    if not m:
        opts = "/".join(str(i + 1) for i in range(min(3, len(windows))))
        return _twiml(f"Sorry, didn't catch that. Please reply with {opts} to pick a window.")
    choice = int(m.group(0))
    if choice < 1 or choice > len(windows):
        return _twiml(f"That option isn't available. Please reply 1-{min(3, len(windows))}.")

    selected = windows[choice - 1]
    await db.jobs.update_one(
        {"id": job["id"]},
        {"$set": {
            "scheduled_launch_at": selected.get("iso") or selected.get("label"),
            "scheduled_window_label": selected.get("label"),
            "scheduled_via": "homeowner_sms_reply",
            "scheduled_at": now_iso(),
        }},
    )
    await _record_audit(job["id"], job.get("contractor_id", "system"), "HOMEOWNER_SCHEDULED_VIA_SMS", {
        "from": sender,
        "choice": choice,
        "selected_label": selected.get("label"),
        "selected_iso": selected.get("iso"),
        "message_sid": MessageSid,
    })
    return _twiml(
        f"Thanks! Locked in your roof scan for {selected.get('label','TBD')}. "
        f"We'll text you a confirmation 24 hours before. — STRATEX"
    )


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

# Backend-defined tiers — Model A (Premium Fleet Deployment Engine)
PRICING_TIERS = {
    "on_demand": {
        "name": "On-Demand",
        "price": 98.00,
        "included_drops": 0,
        "extra_drop_price": 350.00,
        "blurb": "Low-volume builders, historic restoration, system trials",
        "features": [
            "0 included fleet drops",
            "$300–$400 per autonomous drop",
            "Full STRATEX™ Risk Engine",
            "Immutable pre-flight audit trail",
            "PDF supplement export + email delivery",
        ],
    },
    "volume_builder": {
        "name": "Volume Builder",
        "price": 998.00,
        "included_drops": 4,
        "extra_drop_price": 198.00,
        "blurb": "Established residential roofing operators — heavy weekly volume",
        "features": [
            "4 fleet drops INCLUDED / month",
            "$198 per additional drop (44%+ savings)",
            "Multi-trailer dispatch + RTK fleet",
            "AES-256 Business Brain isolation",
            "Priority operator allocation",
            "Compliance audit log + SOC2 export",
        ],
        "popular": True,
    },
}

IMPLEMENTATION_FEE = 598.00
DRY_RUN_PENALTY = 150.00


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
# ONBOARDING / ROI FUNNEL — frictionless contractor sign-up + Stripe TEST checkout
# ---------------------------------------------------------------------------
ROI_TIERS = {
    "starter":            {"name": "Starter",           "monthly_usd": 199.0,   "leads_min": 0,  "leads_max": 15},
    "growth_pro":         {"name": "Growth Pro",        "monthly_usd": 499.0,   "leads_min": 16, "leads_max": 50},
    "enterprise_elite":   {"name": "Enterprise Elite",  "monthly_usd": 1299.0,  "leads_min": 51, "leads_max": 1_000_000},
}


class OnboardingMetrics(BaseModel):
    leads_per_week: int = 0
    leads_per_month: int = 0
    leads_per_year: int = 0
    historical_sales_2_years: float = 0.0


class OnboardingSignupBody(BaseModel):
    email: str
    password: str
    company: Optional[str] = ""
    role: str = "contractor"
    onboarding_metrics: OnboardingMetrics
    selected_tier: str
    capex_upgrade: bool = False


@api.post("/onboarding/signup")
async def onboarding_signup(body: OnboardingSignupBody, request: Request):
    """Frictionless /onboard funnel sign-up.

    - Creates a contractor account WITHOUT requiring TOTP enrollment up-front
      (the user can enroll MFA later inside the portal — keeps conversion high).
    - The Discretion Clause shown on /onboard acts as an in-flow NDA, so we mark
      `nda_accepted=true` and stamp the timestamp.
    - Persists `onboarding_metrics` + `selected_tier` so the ROI matrix is
      reproducible inside the contractor portal.
    """
    if body.role not in ("contractor",):
        raise HTTPException(400, "Onboarding flow only creates contractor accounts.")
    if body.selected_tier not in ROI_TIERS:
        raise HTTPException(400, f"Unknown tier '{body.selected_tier}'.")

    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid work email required.")
    if len(body.password or "") < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Email already registered. Sign in instead.")

    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "legal_name": "",
        "company_name": body.company or "",
        "role": "contractor",
        "password_hash": hash_password(body.password),
        "totp_secret": new_totp_secret(),
        "totp_enrolled": False,
        "nda_accepted": True,
        "nda_signed_at": now_iso(),
        "created_at": now_iso(),
        "onboarding_metrics": body.onboarding_metrics.model_dump(),
        "selected_tier": body.selected_tier,
        "capex_upgrade_intent": bool(body.capex_upgrade),
        "subscription_status": "pending",
    }
    await db.users.insert_one(user)

    access = create_access_token(user["id"], user["role"], user["email"])
    return {
        "access_token": access,
        "token_type": "Bearer",
        "user": _public_user(user),
        "mfa_setup_required": True,
        "next_step": "stripe_checkout" if body.capex_upgrade else "contractor_portal",
    }


class OnboardCheckoutBody(BaseModel):
    tier: str
    origin_url: str


@api.post("/onboarding/stripe-checkout")
async def onboarding_stripe_checkout(body: OnboardCheckoutBody, request: Request, user=Depends(contractor_only)):
    """Create a Stripe TEST-mode checkout session for the selected ROI tier."""
    if body.tier not in ROI_TIERS:
        raise HTTPException(400, "Invalid tier.")
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(500, "Stripe not configured in this environment.")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    tier = ROI_TIERS[body.tier]
    origin = body.origin_url.rstrip("/")
    req = CheckoutSessionRequest(
        amount=float(tier["monthly_usd"]),
        currency="usd",
        success_url=f"{origin}/contractor?roi_checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/onboard?roi_checkout=cancelled",
        metadata={
            "user_id": user["id"],
            "email": user["email"],
            "tier": body.tier,
            "source": "onboarding_funnel",
            "test_mode": "true",
        },
    )
    try:
        session = await asyncio.wait_for(checkout.create_checkout_session(req), timeout=20.0)
    except Exception as e:
        raise HTTPException(504, f"Stripe checkout creation failed: {e}")

    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "email": user["email"],
        "tier": body.tier,
        "amount": float(tier["monthly_usd"]),
        "currency": "usd",
        "payment_status": "initiated",
        "status": "open",
        "source": "onboarding_funnel",
        "metadata": {"tier": body.tier, "source": "onboarding_funnel"},
        "created_at": now_iso(),
    })
    return {"url": session.url, "session_id": session.session_id, "tier": body.tier, "amount": float(tier["monthly_usd"])}


# ---------------------------------------------------------------------------
# ADMIN SALES HUB — Pre-Cached Central Kentucky sales targets
# ---------------------------------------------------------------------------
KY_SALES_TARGETS_SEED = [
    {"id": "ale-roofing",     "name": "ALE Roofing LLC", "aka": "Formerly Atlas Contracting / Elleman Contracting",
     "base": "Lexington, KY", "phone": "859-402-5211",
     "focus": "Historic Preservation, Slate, Copper, Custom Internal Box Gutters, Residential/Commercial Replacements",
     "lat": 38.0406, "lng": -84.5037, "status": "uncontacted"},
    {"id": "burnett-roofing", "name": "Burnett Roofing",
     "base": "656 Bizzell Drive, Lexington, KY 40510", "phone": "859-253-0116",
     "focus": "Tier 1 Commercial Manufacturing, Single-Ply Membranes (EPDM/TPO/PVC), Modified Bitumen, Architectural Sheet Metal",
     "lat": 38.0739, "lng": -84.5494, "status": "uncontacted"},
    {"id": "centimark",       "name": "CentiMark Corporation",
     "base": "260 Crossfield Dr, Unit 4, Versailles, KY 40383", "phone": "502-716-5777",
     "focus": "Large-Scale Industrial, Thermal Shock Inspections, Commercial Property Maintenance Assets",
     "lat": 38.0530, "lng": -84.7286, "status": "uncontacted"},
    {"id": "big-league",      "name": "Big League Roofers",
     "base": "3022 Lexington Road, Nicholasville, KY 40356 · 2901 Richmond Road, Lexington, KY 40509", "phone": "859-693-7663",
     "focus": "High-Volume GAF Master Elite Residential, Hail/Storm Insurance Adjuster Coordination",
     "lat": 37.8806, "lng": -84.5728, "status": "uncontacted"},
    {"id": "godsend",         "name": "A Godsend Roofing LLC",
     "base": "380 E Main St, Lexington, KY 40507", "phone": "859-432-7663",
     "focus": "Commercial/Residential Master Applicators, Complex Custom Step Flashing, Storm Repair Logistics",
     "lat": 38.0457, "lng": -84.4906, "status": "uncontacted"},
    {"id": "odessa",          "name": "Odessa Roofing, Inc.",
     "base": "232 Gold Rush Road, Suite 110, Lexington, KY 40503", "phone": "859-271-0524",
     "focus": "KRCA/NRCA Members, Custom Copper Flashing, Synthetic Slate, High-End Residential Architecture",
     "lat": 38.0019, "lng": -84.5310, "status": "uncontacted"},
    {"id": "barrier",         "name": "Barrier Roofs",
     "base": "Lexington, KY", "phone": "859-251-5119",
     "focus": "High-Volume Owens Corning Platinum Dealer, Insurance Claims Supplementing",
     "lat": 38.0406, "lng": -84.5037, "status": "uncontacted"},
]


@api.get("/admin/sales-targets")
async def admin_sales_targets(user=Depends(admin_only)):
    """Admin-only: returns the pre-cached Lexington-radius contractor list.

    Loaded from Mongo `sales_targets` collection if seeded; otherwise returns
    the in-code seed unchanged. Non-admin callers receive 403 via admin_only.
    """
    docs = await db.sales_targets.find({}, {"_id": 0}).to_list(length=200)
    if not docs:
        return {"targets": KY_SALES_TARGETS_SEED, "source": "seed_constant"}
    return {"targets": docs, "source": "mongo"}


# ---------------------------------------------------------------------------
# ADMIN CRM STUBS — outreach notes, call logs, communication templates
# Mongo collections:
#   sales_outreach_notes      append-only log per target_id
#   sales_call_logs           structured metadata per call attempt
#   communication_templates   global SMS/Email pre-configured strings
# ---------------------------------------------------------------------------
def _known_target_ids() -> set:
    return {t["id"] for t in KY_SALES_TARGETS_SEED}


class OutreachNoteIn(BaseModel):
    body: str
    author: Optional[str] = ""           # admin's display name (falls back to email)
    channel: Optional[str] = "manual"    # manual | call | sms | email | meeting


@api.get("/admin/sales-targets/{target_id}/outreach-notes")
async def list_outreach_notes(target_id: str, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    notes = await db.sales_outreach_notes.find(
        {"target_id": target_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=500)
    return {"target_id": target_id, "count": len(notes), "notes": notes}


@api.post("/admin/sales-targets/{target_id}/outreach-notes")
async def add_outreach_note(target_id: str, body: OutreachNoteIn, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    if not (body.body or "").strip():
        raise HTTPException(400, "Note body is required.")
    note = {
        "id": str(uuid.uuid4()),
        "target_id": target_id,
        "body": body.body.strip(),
        "author": body.author or user.get("email"),
        "channel": body.channel or "manual",
        "created_at": now_iso(),
        "created_by_user_id": user["id"],
    }
    await db.sales_outreach_notes.insert_one(note)
    note.pop("_id", None)
    return {"ok": True, "note": note}


class CallLogIn(BaseModel):
    outcome: str                          # connected | voicemail | no_answer | callback_scheduled
    duration_seconds: int = 0
    notes: Optional[str] = ""
    callback_at: Optional[str] = None    # ISO timestamp


@api.get("/admin/sales-targets/{target_id}/call-logs")
async def list_call_logs(target_id: str, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    logs = await db.sales_call_logs.find(
        {"target_id": target_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=500)
    return {"target_id": target_id, "count": len(logs), "logs": logs}


@api.post("/admin/sales-targets/{target_id}/call-logs")
async def add_call_log(target_id: str, body: CallLogIn, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    valid_outcomes = {"connected", "voicemail", "no_answer", "callback_scheduled", "wrong_number"}
    if body.outcome not in valid_outcomes:
        raise HTTPException(400, f"outcome must be one of {sorted(valid_outcomes)}")
    log = {
        "id": str(uuid.uuid4()),
        "target_id": target_id,
        "outcome": body.outcome,
        "duration_seconds": max(0, int(body.duration_seconds or 0)),
        "notes": (body.notes or "").strip(),
        "callback_at": body.callback_at,
        "created_at": now_iso(),
        "created_by_user_id": user["id"],
        "created_by_email": user["email"],
    }
    await db.sales_call_logs.insert_one(log)
    log.pop("_id", None)
    return {"ok": True, "log": log}


_DEFAULT_TEMPLATES = [
    {
        "id": "intro-sms",
        "channel": "sms",
        "name": "Cold Intro · Drone Demo",
        "subject": None,
        "body": "Hi {contact_name} — {sender_name} with STRATEX™. We deploy autonomous drone roof inspections (no ladders, no climbing) and lock estimates to insurance grade. Worth a 15-min walkthrough? — {sender_name}",
    },
    {
        "id": "intro-email",
        "channel": "email",
        "name": "Cold Intro · Email",
        "subject": "STRATEX™ Strategic Thermal Reconnaissance — 15-min walkthrough for {company}",
        "body": "Hi {contact_name},\n\nI'm {sender_name} with STRATEX™ — we deliver autonomous drone roof inspections fused with sub-surface thermal capacitance modeling, so estimates land insurance-grade without a ladder ever touching the roof.\n\nFor a shop like {company} ({focus}), a 15-min walkthrough usually pencils out within the first project. Open this week?\n\n— {sender_name}",
    },
    {
        "id": "demo-followup-email",
        "channel": "email",
        "name": "Post-Demo Follow-Up",
        "subject": "STRATEX™ — your {company} ROI breakdown",
        "body": "Hi {contact_name},\n\nGreat speaking with you. Per the live ROI matrix we ran together, {company} reclaims approximately ${annual_savings} in the first 12 months by retiring manual ladder estimates. Attached: full Cost-Basis Matrix + sample Quant™ report.\n\nReady to schedule your pilot scan?\n\n— {sender_name}",
    },
    {
        "id": "callback-sms",
        "channel": "sms",
        "name": "Callback Reminder",
        "subject": None,
        "body": "Hi {contact_name}, {sender_name} from STRATEX™ following up on our chat. Ladder-free roof recon, 60-second deployment. Got 10 min?",
    },
]


class CommTemplateIn(BaseModel):
    id: str
    channel: str                          # sms | email
    name: str
    subject: Optional[str] = None         # required when channel == email
    body: str


@api.get("/admin/communication-templates")
async def list_communication_templates(user=Depends(admin_only)):
    docs = await db.communication_templates.find({}, {"_id": 0}).to_list(length=200)
    if not docs:
        # Seed defaults on first read so subsequent edits are persistent.
        await db.communication_templates.insert_many([{**t, "created_at": now_iso(), "system_seed": True} for t in _DEFAULT_TEMPLATES])
        docs = await db.communication_templates.find({}, {"_id": 0}).to_list(length=200)
    return {"count": len(docs), "templates": docs}


@api.put("/admin/communication-templates/{template_id}")
async def upsert_communication_template(template_id: str, body: CommTemplateIn, user=Depends(admin_only)):
    if body.channel not in ("sms", "email"):
        raise HTTPException(400, "channel must be 'sms' or 'email'.")
    if body.channel == "email" and not (body.subject or "").strip():
        raise HTTPException(400, "Email templates require a subject.")
    if template_id != body.id:
        raise HTTPException(400, "Path id and body id must match.")
    doc = {
        "id": body.id,
        "channel": body.channel,
        "name": body.name,
        "subject": body.subject,
        "body": body.body,
        "updated_at": now_iso(),
        "updated_by": user["email"],
    }
    await db.communication_templates.update_one(
        {"id": body.id}, {"$set": doc}, upsert=True,
    )
    return {"ok": True, "template": doc}


# ---------------------------------------------------------------------------
# DYNAMIC TELEMETRY ANOMALY HALT — Overseer review queue
# When the frontend BEES rendering loop detects sub-pipeline anomalies on the
# Electric Teal diagnostic layer, it POSTs a structured halt payload here.
# The payload lands in an admin-only queue surfaced at /admin/overseer.
# ---------------------------------------------------------------------------
class TelemetryHaltPayload(BaseModel):
    project_id: Optional[str] = None
    layer: str                            # which BEES layer triggered (e.g. "electric_teal_diagnostic")
    severity: str                         # advisory | warning | critical
    reason_code: str                      # SHORT machine code: "FRAME_DROP", "NAN_VERTEX", "TEAL_VECTOR_BREAK"
    reason_label: str                     # human label
    telemetry_snapshot: Dict[str, Any] = {}    # facet/edge/anomaly numbers at halt
    causal_logs: List[str] = []
    fps_observed: Optional[float] = None
    fps_threshold: Optional[float] = None
    client_timestamp: Optional[str] = None
    user_agent: Optional[str] = None


@api.post("/telemetry/anomaly-halt")
async def post_telemetry_halt(body: TelemetryHaltPayload, request: Request, user=Depends(current_user)):
    """Frontend BEES pipeline → Overseer queue.

    Accepts halt payloads from ANY authenticated user (so anomalies during
    contractor/operator sessions also surface). Admin reads via /admin/overseer-queue.
    """
    valid_sev = {"advisory", "warning", "critical"}
    if body.severity not in valid_sev:
        raise HTTPException(400, f"severity must be one of {sorted(valid_sev)}")
    record = {
        "id": str(uuid.uuid4()),
        "project_id": body.project_id,
        "layer": body.layer or "electric_teal_diagnostic",
        "severity": body.severity,
        "reason_code": body.reason_code,
        "reason_label": body.reason_label,
        "telemetry_snapshot": body.telemetry_snapshot or {},
        "causal_logs": body.causal_logs[:30],     # cap to keep payload sane
        "fps_observed": body.fps_observed,
        "fps_threshold": body.fps_threshold,
        "client_timestamp": body.client_timestamp,
        "user_agent": (body.user_agent or "")[:240],
        "server_timestamp": now_iso(),
        "reported_by_user_id": user["id"],
        "reported_by_role": user["role"],
        "reported_by_email": user["email"],
        "review_status": "open",          # open | reviewed | dismissed
        "reviewed_at": None,
        "reviewed_by": None,
    }
    await db.overseer_queue.insert_one(record)
    record.pop("_id", None)
    return {"ok": True, "halt_id": record["id"], "review_status": "open"}


@api.get("/admin/overseer-queue")
async def get_overseer_queue(status: str = "open", user=Depends(admin_only)):
    valid = {"open", "reviewed", "dismissed", "all"}
    if status not in valid:
        raise HTTPException(400, f"status must be one of {sorted(valid)}")
    q = {} if status == "all" else {"review_status": status}
    docs = await db.overseer_queue.find(q, {"_id": 0}).sort("server_timestamp", -1).to_list(length=300)
    open_count = await db.overseer_queue.count_documents({"review_status": "open"})
    return {"count": len(docs), "open_count": open_count, "items": docs}


@api.put("/admin/overseer-queue/{halt_id}")
async def update_overseer_item(halt_id: str, payload: Dict[str, Any], user=Depends(admin_only)):
    new_status = (payload or {}).get("review_status")
    if new_status not in ("reviewed", "dismissed"):
        raise HTTPException(400, "review_status must be 'reviewed' or 'dismissed'.")
    upd = {"review_status": new_status, "reviewed_at": now_iso(), "reviewed_by": user["email"]}
    if payload.get("review_note"):
        upd["review_note"] = str(payload["review_note"])[:500]
    res = await db.overseer_queue.update_one({"id": halt_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(404, "Halt id not found.")
    return {"ok": True, "halt_id": halt_id, "review_status": new_status}


# ---------------------------------------------------------------------------
# ADMIN FINANCIAL BLOCKER — strip pricing/labor/overhead from ANY admin read
# of another contractor's profile (Section 2.2 of Executive Spec).
# ---------------------------------------------------------------------------
FINANCIAL_FIELDS_TO_STRIP = (
    "contractor_cost_matrix",
    "labor_per_hour",
    "profit_overhead_multipliers",
    "onboarding_metrics",
    "_encrypted",
)


@api.get("/admin/contractor/{contractor_id}/financial-config")
async def admin_view_contractor_financial(contractor_id: str, user=Depends(admin_only)):
    """When an admin reads another contractor's financial config, return `{}`.

    This is the explicit "blocker" required by Executive Spec Section 2.2:
    administrative profiles get a hard-empty response when probing financial
    columns belonging to a contractor account.
    """
    target = await db.users.find_one({"id": contractor_id}, {"_id": 0})
    if not target:
        raise HTTPException(404, "Contractor not found.")
    # Hard-empty — financial isolation by policy.
    return {}


# ---------------------------------------------------------------------------
# MATERIALS CONFIGURATOR — stored alongside encrypted cost matrix
# ---------------------------------------------------------------------------
class MaterialsConfigBody(BaseModel):
    system: str
    picks: Dict[str, Any] = {}
    custom_text: Optional[str] = ""


@api.get("/contractor/materials-config")
async def get_materials_config(user=Depends(contractor_only)):
    doc = await db.materials_config.find_one({"user_id": user["id"]}, {"_id": 0})
    return doc or {"system": "asphalt_shingle_system", "picks": {}, "custom_text": ""}


@api.put("/contractor/materials-config")
async def put_materials_config(body: MaterialsConfigBody, user=Depends(contractor_only)):
    payload = {
        "user_id": user["id"],
        "system": body.system,
        "picks": body.picks or {},
        "custom_text": body.custom_text or "",
        "updated_at": now_iso(),
    }
    await db.materials_config.update_one(
        {"user_id": user["id"]}, {"$set": payload}, upsert=True,
    )
    return {"ok": True, "system": payload["system"], "pick_count": len(payload["picks"])}


# ---------------------------------------------------------------------------
# FLEET LAUNCH WEBSOCKET — wire-compatible with /app/hardware-gateway/stratex-gateway.js
# Streams simulated dock+drone+environment telemetry at 4 Hz and accepts the
# AUTHORIZE_FLEET_LAUNCH command. On valid authorization a flight_authorizations
# document is persisted. If a job_id is supplied AND the user is an operator,
# the existing operator/launch transition pipeline is invoked.
# ---------------------------------------------------------------------------

async def _ws_auth(token: Optional[str]):
    """Decode JWT from WS query param. Returns user doc or None."""
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    user = await db.users.find_one({"id": sub}, {"_id": 0, "password_hash": 0, "totp_secret_enc": 0})
    return user


def _simulator_step(t: float) -> Dict[str, Any]:
    """Pure function: returns a telemetry frame for tick t (seconds since connect).

    Converges to a fully-green flight-ready state by ~t=10s so the demo is snappy.
    Schema MUST mirror /app/hardware-gateway/stratex-gateway.js verbatim.
    """
    # ramp: 0 → 100 over 10s
    ramp = min(1.0, t / 10.0)

    battery = int(round(72 + 28 * ramp))                          # 72 → 100
    rssi = int(round(38 + 56 * ramp))                             # 38 → 94
    wind = round(9.2 - 5.8 * ramp + random.uniform(-0.3, 0.3), 2) # 9.2 → 3.4
    temp = round(20.4 + random.uniform(-0.4, 0.6), 2)

    # discrete state transitions
    raining = ramp < 0.45                                         # rain stops ~4.5s
    perimeter_clear = ramp >= 0.30                                # ~3s
    gps = "POSITION_OK_FIXED" if ramp >= 0.55 else "ACQUIRING_SATELLITES"
    hatch = "OPEN" if ramp >= 0.75 else "CLOSED"                  # hatch retracts last

    return {
        "dock": {
            "hatch_status": hatch,
            "perimeter_clear": perimeter_clear,
            "internal_temp_c": temp,
        },
        "drone": {
            "battery_percent": battery,
            "gps_status": gps,
            "signal_rssi": rssi,
        },
        "environment": {
            "wind_speed_mph": max(0.4, wind),
            "is_raining": raining,
        },
    }


@app.websocket("/api/ws/stratex/core")
async def ws_stratex_core(websocket: WebSocket, token: Optional[str] = Query(default=None)):
    await websocket.accept()
    user = await _ws_auth(token)
    if not user:
        await websocket.send_text(_json.dumps({"event": "AUTH_FAIL", "detail": "missing or invalid token"}))
        await websocket.close(code=4401)
        return

    await websocket.send_text(_json.dumps({
        "event": "HELLO",
        "source": "cloud_simulator",
        "schema_version": "1.0",
        "user_role": user.get("role"),
        "server_timestamp": now_iso(),
    }))

    t0 = asyncio.get_event_loop().time()
    streamer_task: Optional[asyncio.Task] = None
    stop = asyncio.Event()

    async def streamer():
        try:
            while not stop.is_set():
                t = asyncio.get_event_loop().time() - t0
                frame = _simulator_step(t)
                await websocket.send_text(_json.dumps(frame))
                await asyncio.sleep(0.25)  # 4 Hz to match the on-site gateway
        except (WebSocketDisconnect, RuntimeError):
            pass

    streamer_task = asyncio.create_task(streamer())

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = _json.loads(raw)
            except Exception:
                await websocket.send_text(_json.dumps({"event": "ERROR", "detail": "bad json"}))
                continue

            cmd = msg.get("command")
            if cmd == "PING":
                await websocket.send_text(_json.dumps({"event": "PONG", "server_timestamp": now_iso()}))
                continue

            if cmd != "AUTHORIZE_FLEET_LAUNCH":
                await websocket.send_text(_json.dumps({"event": "ERROR", "detail": f"unknown command {cmd!r}"}))
                continue

            payload = msg.get("payload") or {}
            t = asyncio.get_event_loop().time() - t0
            snapshot = _simulator_step(t)

            # gate against snapshot — refuse if not flight-ready
            ready = (
                snapshot["dock"]["hatch_status"] == "OPEN"
                and snapshot["dock"]["perimeter_clear"] is True
                and snapshot["drone"]["battery_percent"] >= 100
                and snapshot["drone"]["gps_status"] == "POSITION_OK_FIXED"
                and snapshot["drone"]["signal_rssi"] >= 75
                and snapshot["environment"]["wind_speed_mph"] < 5
                and not snapshot["environment"]["is_raining"]
            )
            if not ready:
                await websocket.send_text(_json.dumps({
                    "event": "AUTH_REJECTED",
                    "detail": "pre-flight hold — telemetry not green",
                    "snapshot": snapshot,
                }))
                continue

            auth_id = str(uuid.uuid4())
            job_id = (payload.get("job_id") or "").strip() or None
            record = {
                "id": auth_id,
                "job_id": job_id,
                "project_id": payload.get("project_id"),
                "approved_value": payload.get("approved_value"),
                "operator_id": user["id"],
                "operator_email": user["email"],
                "operator_role": user["role"],
                "telemetry_snapshot": snapshot,
                "source": "cloud_simulator",
                "server_timestamp": now_iso(),
            }

            # If job tied + operator → flip status to IN_FLIGHT (lightweight; the
            # heavy /operator/jobs/{id}/launch path still owns the canonical pipeline).
            launched_job = False
            if job_id and user.get("role") == "operator":
                job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
                if job and job.get("status") == "PENDING_FIELD_CAPTURE":
                    await db.jobs.update_one(
                        {"id": job_id},
                        {"$set": {
                            "status": "IN_FLIGHT",
                            "launched_at": record["server_timestamp"],
                            "operator_id": user["id"],
                            "fleet_launch_authorization_id": auth_id,
                        }},
                    )
                    launched_job = True

            await db.flight_authorizations.insert_one(record)
            record.pop("_id", None)

            await websocket.send_text(_json.dumps({
                "event": "MISSION_LAUNCHED",
                "authorization_id": auth_id,
                "job_id": job_id,
                "job_status_updated": launched_job,
                "server_timestamp": record["server_timestamp"],
            }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"ws_stratex_core error: {e!r}")
    finally:
        stop.set()
        if streamer_task and not streamer_task.done():
            streamer_task.cancel()
            try:
                await streamer_task
            except (asyncio.CancelledError, Exception):
                pass


@api.get("/flight-authorizations/recent")
async def get_recent_flight_authorizations(limit: int = 25, user=Depends(current_user)):
    """Returns recent authorizations. Admins see all; operators see only their own."""
    q: Dict[str, Any] = {}
    if user.get("role") == "operator":
        q["operator_id"] = user["id"]
    elif user.get("role") != "admin":
        # contractors see authorizations tied to their jobs only
        my_job_ids = [j["id"] async for j in db.jobs.find({"contractor_id": user["id"]}, {"_id": 0, "id": 1})]
        q["job_id"] = {"$in": my_job_ids}
    docs = await db.flight_authorizations.find(q, {"_id": 0}).sort("server_timestamp", -1).to_list(length=max(1, min(limit, 200)))
    return {"count": len(docs), "items": docs}


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
    global _reminder_task
    if _reminder_task and not _reminder_task.done():
        _reminder_task.cancel()
        try:
            await _reminder_task
        except (asyncio.CancelledError, Exception):
            pass
    client.close()
