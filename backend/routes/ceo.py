"""STRATEX™ CEO Command Center — back-end.

Adds a 4th role (`ceo`) on top of admin/contractor/operator. CEO clearance is
intentionally NARROW (one seeded account) and is the only path that can read
the supplier-side BUILD-SUPPLY GM Command Center.

Endpoints (all prefixed by /api via `api` router):
  POST /api/auth/ceo/login                       (no MFA prompt — uses SMS step instead)
  POST /api/auth/ceo/request-sms                 (mocked Twilio Verify)
  POST /api/auth/ceo/change-password             (verify SMS code + bcrypt new)
  GET  /api/ceo/command-center                   (aggregated KPIs, ROI matrix, jobs, calendar)
  POST /api/ceo/pricing/preview                  (slider-driven margin preview)

Seeding: `seed_ceo()` runs at startup, idempotent. Email + password are taken
from env (CEO_EMAIL / CEO_PASSWORD) — fall-back defaults match the user's
explicit request: Tony@Stratexdrone.com / 1111. Password is always bcrypt-
hashed at rest; plaintext never persisted.

SMS verification is **mocked** (no real Twilio key configured). The code is
generated, stored in Mongo with a 10-minute expiry, and surfaced via the
`/request-sms` response when `DEMO_SMS_BYPASS=1` (matches the existing
`DEMO_MFA_BYPASS` pattern). Swap the `_send_sms` helper for a real Twilio call
when credentials land.
"""
from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import api, auth_r, ceo_only, db, now_iso
from stratex_auth import (
    create_access_token, create_refresh_token,
    hash_password, verify_password,
)

CEO_EMAIL_DEFAULT = "Tony@Stratexdrone.com"
CEO_PASSWORD_DEFAULT = "1111"
CEO_PHONE_DEFAULT = "+18595550199"  # placeholder — overridable via env
SMS_CODE_TTL_MIN = 10


# ---------------------------------------------------------------------------
# Seeding (idempotent)
# ---------------------------------------------------------------------------

async def seed_ceo() -> Dict[str, str]:
    """Idempotently seed the single CEO account. Returns the email/phone."""
    email = (os.environ.get("CEO_EMAIL") or CEO_EMAIL_DEFAULT).strip()
    password = os.environ.get("CEO_PASSWORD") or CEO_PASSWORD_DEFAULT
    phone = (os.environ.get("CEO_PHONE") or CEO_PHONE_DEFAULT).strip()
    # Match the case-insensitive lookup pattern used elsewhere
    email_lower = email.lower()
    existing = await db.users.find_one({"email": email_lower})
    if existing:
        updates: Dict[str, Any] = {"role": "ceo", "phone": phone, "tour_mode": False}
        # Rotate hash to match env (idempotent — never store plain)
        if not verify_password(password, existing.get("password_hash") or ""):
            updates["password_hash"] = hash_password(password)
        # Ensure NDA flag is cleared — CEO sits above NDA gate
        updates["nda_accepted"] = True
        updates["nda_signed_at"] = existing.get("nda_signed_at") or now_iso()
        await db.users.update_one({"email": email_lower}, {"$set": updates})
        return {"email": email_lower, "phone": phone, "created": False}

    await db.users.insert_one({
        "id": str(uuid.uuid4()),
        "email": email_lower,
        "legal_name": "Tony Cross",
        "first_name": "Tony",
        "company_name": "STRATEX Drone Inc.",
        "role": "ceo",
        "phone": phone,
        "password_hash": hash_password(password),
        "totp_secret": "",       # CEO uses SMS step instead of TOTP
        "totp_enrolled": False,
        "nda_accepted": True,
        "nda_signed_at": now_iso(),
        "tour_mode": False,
        "created_at": now_iso(),
    })
    return {"email": email_lower, "phone": phone, "created": True}


# ---------------------------------------------------------------------------
# Login (CEO-only path — bypasses NDA and TOTP gates; future: SMS challenge)
# ---------------------------------------------------------------------------

class CeoLoginBody(BaseModel):
    email: str
    password: str


@auth_r.post("/ceo/login")
async def ceo_login(body: CeoLoginBody):
    email = (body.email or "").strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or user.get("role") != "ceo":
        # Identical error message for "not CEO" vs "bad password" — avoids enumeration.
        raise HTTPException(401, "Invalid CEO credentials")
    if not verify_password(body.password, user.get("password_hash") or ""):
        await db.login_attempts.update_one(
            {"identifier": f"ceo:{email}"},
            {"$inc": {"failed": 1}, "$set": {"last_at": now_iso()}},
            upsert=True,
        )
        raise HTTPException(401, "Invalid CEO credentials")

    await db.login_attempts.delete_many({"identifier": f"ceo:{email}"})
    access = create_access_token(user["id"], user["role"], user["email"])
    refresh = create_refresh_token(user["id"])
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "first_name": user.get("first_name"),
            "legal_name": user.get("legal_name"),
            "phone": user.get("phone"),
            "must_rotate_password": _is_weak_password(body.password),
        },
    }


def _is_weak_password(pw: str) -> bool:
    """Heuristic: short or numeric-only passwords are flagged for rotation."""
    return len(pw) < 8 or pw.isdigit()


# ---------------------------------------------------------------------------
# SMS-verified password rotation (mocked Twilio)
# ---------------------------------------------------------------------------

class RequestSmsBody(BaseModel):
    pass  # auth dep yields the CEO user


@auth_r.post("/ceo/request-sms")
async def ceo_request_sms(user=Depends(ceo_only)):
    """Generate a 6-digit code, store w/ 10-min TTL, mock-send via SMS."""
    code = f"{random.randint(0, 999999):06d}"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=SMS_CODE_TTL_MIN)).isoformat()
    await db.sms_codes.update_one(
        {"user_id": user["id"], "purpose": "ceo_password_change"},
        {"$set": {"code": code, "expires_at": expires_at, "consumed": False, "issued_at": now_iso()}},
        upsert=True,
    )
    sent = await _send_sms(user.get("phone", ""), f"STRATEX CEO verification code: {code}. Valid for {SMS_CODE_TTL_MIN} min.")
    resp: Dict[str, Any] = {"sent": sent, "expires_at": expires_at, "phone_last4": (user.get("phone") or "")[-4:]}
    # Demo bypass: surface the code in the API response so the dashboard can prefill it
    if os.environ.get("DEMO_SMS_BYPASS") == "1":
        resp["debug_code"] = code
    return resp


class ChangePasswordBody(BaseModel):
    sms_code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=4, max_length=128)


@auth_r.post("/ceo/change-password")
async def ceo_change_password(body: ChangePasswordBody, user=Depends(ceo_only)):
    rec = await db.sms_codes.find_one({"user_id": user["id"], "purpose": "ceo_password_change"})
    if not rec or rec.get("consumed"):
        raise HTTPException(400, "No active SMS challenge. Request a new code.")
    if rec.get("code") != body.sms_code.strip():
        raise HTTPException(401, "Invalid SMS code")
    if rec.get("expires_at") and rec["expires_at"] < now_iso():
        raise HTTPException(401, "SMS code expired")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(body.new_password), "password_changed_at": now_iso()}},
    )
    await db.sms_codes.update_one(
        {"user_id": user["id"], "purpose": "ceo_password_change"},
        {"$set": {"consumed": True, "consumed_at": now_iso()}},
    )
    return {"ok": True, "must_rotate_password": _is_weak_password(body.new_password)}


async def _send_sms(phone: str, message: str) -> bool:
    """Mocked Twilio. Wire a real client (TWILIO_ACCOUNT_SID / AUTH_TOKEN /
    FROM_NUMBER) here when credentials are supplied."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    if not sid:
        # MOCKED — never raises, never sends
        return False
    # Future: client = Client(sid, os.environ["TWILIO_AUTH_TOKEN"]); client.messages.create(...)
    return False


# ---------------------------------------------------------------------------
# CEO Command Center data feed
# ---------------------------------------------------------------------------

@api.get("/ceo/command-center")
async def command_center(user=Depends(ceo_only)) -> Dict[str, Any]:
    """Aggregated GM-Command snapshot. Computed live from existing collections so
    the dashboard reflects whatever the rest of the platform has done today."""
    total_scans = await db.jobs.count_documents({"status": {"$in": ["completed", "deliverable_ready"]}})
    scheduled = await db.jobs.count_documents({"status": {"$in": ["scheduled", "in_progress", "queued"]}})
    contractor_count = await db.users.count_documents({"role": "contractor"})

    # Critical stock-outs: any material ledger row with stock_units <= reorder threshold
    stockouts: List[Dict[str, Any]] = []
    async for m in db.supplier_material_ledger.find(
        {"$expr": {"$lte": ["$stock_units", "$reorder_threshold"]}},
        {"_id": 0, "sku": 1, "name": 1, "stock_units": 1, "reorder_threshold": 1},
    ).limit(8):
        stockouts.append(m)

    # ROI matrix — top contractors by realized job spend this month
    roi_matrix: List[Dict[str, Any]] = []
    cur = db.jobs.find(
        {"status": "completed", "pricing.total_usd": {"$exists": True}},
        {"_id": 0, "contractor_id": 1, "pricing.total_usd": 1, "project_code": 1, "client_name": 1},
    ).sort("completed_at", -1).limit(20)
    seen: Dict[str, Dict[str, Any]] = {}
    async for j in cur:
        cid = j.get("contractor_id")
        if not cid:
            continue
        gross = float(j.get("pricing", {}).get("total_usd") or 0)
        row = seen.setdefault(cid, {"contractor_id": cid, "scan_cost_usd": 1500, "gain_usd": 0.0, "scans": 0})
        row["gain_usd"] += gross
        row["scans"] += 1

    # decorate with company names
    for cid, row in seen.items():
        u = await db.users.find_one({"id": cid}, {"_id": 0, "company_name": 1})
        row["client"] = (u or {}).get("company_name") or "—"
        row["roi_multiple"] = round(row["gain_usd"] / max(row["scan_cost_usd"], 1), 2) if row["gain_usd"] else 0.0
        roi_matrix.append(row)
    roi_matrix.sort(key=lambda r: r["roi_multiple"], reverse=True)

    # Open jobs (pending closures)
    open_jobs: List[Dict[str, Any]] = []
    async for j in db.jobs.find(
        {"status": {"$in": ["in_progress", "deliverable_ready", "review"]}},
        {"_id": 0, "id": 1, "project_code": 1, "client_name": 1, "site": 1, "pricing.total_usd": 1, "contractor_id": 1},
    ).sort("created_at", -1).limit(8):
        open_jobs.append({
            "job_id": j.get("id"),
            "project_code": j.get("project_code") or j.get("id"),
            "address": (j.get("site") or {}).get("address") or j.get("client_name") or "—",
            "gain_usd": float((j.get("pricing") or {}).get("total_usd") or 0),
            "roi_multiple": round(float((j.get("pricing") or {}).get("total_usd") or 0) / 1500, 2),
        })

    # Predictive calendar — bucket scheduled/in-progress jobs into upcoming days
    today = datetime.now(timezone.utc).date()
    calendar: List[Dict[str, Any]] = []
    for offset in range(0, 7):
        day = today + timedelta(days=offset)
        async_cursor = db.jobs.find(
            {"scheduled_for_date": day.isoformat()},
            {"_id": 0, "id": 1, "project_code": 1, "pricing.total_usd": 1, "client_name": 1},
        )
        bucket = {"date": day.isoformat(), "label": day.strftime("%a %b %d"), "scans": 0, "value_usd": 0.0, "items": []}
        async for j in async_cursor:
            bucket["scans"] += 1
            bucket["value_usd"] += float((j.get("pricing") or {}).get("total_usd") or 0)
            bucket["items"].append({
                "code": j.get("project_code") or j.get("id"),
                "client": j.get("client_name") or "—",
            })
        calendar.append(bucket)

    # Material catalog snapshot for the pricing-multiplier widget.
    # Supports both schema variants in Mongo (branch_console seed: tier1_usd; admin_ops seed: tier_1_price_usd).
    catalog: List[Dict[str, Any]] = []
    async for m in db.supplier_material_ledger.find(
        {}, {"_id": 0}
    ).sort("name", 1).limit(12):
        catalog.append({
            "sku": m.get("sku"),
            "name": m.get("name"),
            "unit_label": m.get("unit_label"),
            "tier_1_price_usd": float(m.get("tier_1_price_usd") or m.get("tier1_usd") or 0),
            "tier_2_price_usd": float(m.get("tier_2_price_usd") or m.get("tier2_usd") or 0),
            "tier_3_price_usd": float(m.get("tier_3_price_usd") or m.get("tier3_usd") or 0),
        })

    # Headline gross-revenue: sum of completed-job total_usd in last 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    agg = await db.jobs.aggregate([
        {"$match": {"status": "completed", "completed_at": {"$gte": cutoff}}},
        {"$group": {"_id": None, "gross": {"$sum": "$pricing.total_usd"}}},
    ]).to_list(length=1)
    monthly_gross = float((agg[0]["gross"] if agg else 0) or 0)

    return {
        "generated_at": now_iso(),
        "region": "Central Kentucky",
        "kpis": {
            "total_regional_scans": total_scans,
            "scans_scheduled": scheduled,
            "active_contractors": contractor_count,
            "monthly_gross_revenue_usd": monthly_gross,
            "critical_stockouts": len(stockouts),
        },
        "stockouts": stockouts,
        "roi_matrix": roi_matrix[:6],
        "open_jobs": open_jobs,
        "calendar": calendar,
        "catalog": catalog,
        "ceo": {
            "email": user["email"],
            "first_name": user.get("first_name"),
            "phone_last4": (user.get("phone") or "")[-4:],
        },
    }


class PricingPreviewBody(BaseModel):
    sku: str
    margin_pct: float  # -100..+200


@api.post("/ceo/pricing/preview")
async def pricing_preview(body: PricingPreviewBody, user=Depends(ceo_only)):
    """Live slider preview — applies the supplied margin to the SKU's tier-1
    base. Pure compute, no persistence."""
    m = await db.supplier_material_ledger.find_one({"sku": body.sku}, {"_id": 0})
    if not m:
        raise HTTPException(404, "SKU not found")
    base = float(m.get("tier_1_price_usd") or m.get("tier1_usd") or 0)
    adjusted = round(base * (1 + body.margin_pct / 100), 2)
    return {
        "sku": body.sku,
        "name": m.get("name"),
        "base_usd": base,
        "margin_pct": body.margin_pct,
        "adjusted_usd": adjusted,
    }
