"""STRATEX™ — Claim Snapshot Co-Sign Module.

Implements the carrier-side counter-signature flow that closes the
LAE-bypass loop. End-to-end story:

  1. Contractor / homeowner opens a Claim Snapshot → clicks
     "Request Carrier Co-Sign". Backend mints a 32-byte secret token,
     stores a pending COSIGN row keyed to the passport, returns a
     shareable signing URL (`/cosign/{token}`).
  2. Adjuster opens the URL. Frontend calls `GET /verify/{token}` →
     returns the diff snapshot + signer fields to populate.
  3. Adjuster submits name + company + license + decision + notes →
     `POST /submit/{token}`. Backend computes a SHA-256 receipt over
     {diff, signer, ts}, marks the row signed, and appends an immutable
     COSIGN entry to the passport's hash-chained ledger.
  4. ClaimSnapshot UI re-renders with a "CO-SIGNED · APPROVED" badge
     showing adjuster + receipt hash.

The receipt hash is what carriers can verify against the passport ledger
to prove "this exact diff was approved by this licensed adjuster at this
instant" — auditable years later without trusting STRATEX.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core import db, logger
from routes.passport import _append_ledger, require_legacy_passport_writer, _log_blocked_write
from routes.claim_snapshot import _get_passport, diff_baseline_vs_latest

router = APIRouter(prefix="/api/claim-snapshot", tags=["claim-snapshot-cosign"])


# ──────────────────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────────────────
class CosignRequestIn(BaseModel):
    requester_name: Optional[str] = None      # contractor / homeowner who initiated
    carrier_email: Optional[str] = None       # adjuster's email (for the share link)
    carrier_company: Optional[str] = None     # e.g. "State Farm Claims"


class CosignSubmitIn(BaseModel):
    adjuster_name: str = Field(min_length=2, max_length=120)
    adjuster_company: str = Field(min_length=2, max_length=160)
    adjuster_license: Optional[str] = None
    decision: str = Field(default="APPROVED")  # APPROVED | NEEDS_INSPECTION | DENIED
    notes: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────
async def _get_cosign(token: str) -> Optional[Dict[str, Any]]:
    rec = await db["claim_cosigns"].find_one({"token": token})
    return rec


def _receipt_hash(diff: Dict[str, Any], signer: Dict[str, Any], signed_at: str) -> str:
    """Receipt = SHA-256 over the canonical JSON of {diff + signer + ts}.
    Carriers can re-derive this against the passport ledger to prove
    tamper-evidence."""
    payload = {
        "passport_id": diff.get("passport", {}).get("passport_id"),
        "verdict": diff.get("verdict"),
        "confidence_pct": diff.get("confidence_pct"),
        "deltas": diff.get("deltas"),
        "narrative": diff.get("narrative"),
        "signer": signer,
        "signed_at": signed_at,
    }
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ──────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────
@router.post("/{passport_id}/cosign/request")
async def request_cosign(passport_id: str, body: CosignRequestIn,
                         _writer=Depends(require_legacy_passport_writer)):
    """Mint a one-time signing token for the adjuster.

    Privileged operators only (C-P-001C). Minting a purpose-bound token is a
    Legacy Passport mutation and must not be anonymous.

    Idempotent — if an unsigned token already exists for this passport,
    reuse it so the same link keeps working until the carrier signs."""
    rec = await _get_passport(passport_id)
    pid = rec["passport_id"]

    existing = await db["claim_cosigns"].find_one(
        {"passport_id": pid, "signed_at": None}
    )
    if existing:
        return {
            "token": existing["token"],
            "sign_path": f"/cosign/{existing['token']}",
            "reused": True,
            "requested_at": existing.get("requested_at"),
        }

    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc).isoformat()
    # Snapshot the diff at mint time so the adjuster signs the exact
    # payload they review — receipt becomes bit-stable across the
    # verify→submit window.
    pinned_diff = await diff_baseline_vs_latest(pid)
    row = {
        "token": token,
        "passport_id": pid,
        "requested_at": now,
        "requester_name": body.requester_name,
        "carrier_email": body.carrier_email,
        "carrier_company": body.carrier_company,
        "signed_at": None,
        "signer": None,
        "receipt_hash": None,
        "pinned_diff": pinned_diff,
    }
    await db["claim_cosigns"].insert_one(row)

    # Drop a ledger entry — even a *request* is auditable
    _append_ledger(rec, "COSIGN",
                   note=f"Co-sign requested · token …{token[-8:]} · carrier={body.carrier_company or 'TBD'}",
                   status="REQUESTED",
                   payload={"token_tail": token[-8:], "carrier": body.carrier_company})
    await db["property_passports"].update_one(
        {"passport_id": pid},
        {"$set": {"ledger": rec["ledger"], "updated_at": rec["updated_at"]}},
    )
    return {
        "token": token,
        "sign_path": f"/cosign/{token}",
        "reused": False,
        "requested_at": now,
    }


@router.get("/cosign/verify/{token}")
async def verify_cosign(token: str):
    """Adjuster lands at /cosign/:token — frontend pulls everything it
    needs from this endpoint: passport diff + cosign row state."""
    cs = await _get_cosign(token)
    if not cs:
        raise HTTPException(404, "Co-sign token not found or expired")
    # Prefer the pinned diff captured at request-mint time so the adjuster
    # always sees the exact payload they will sign.
    diff = cs.get("pinned_diff") or await diff_baseline_vs_latest(cs["passport_id"])
    return {
        "token": token,
        "passport_id": cs["passport_id"],
        "requested_at": cs.get("requested_at"),
        "carrier_company": cs.get("carrier_company"),
        "signed_at": cs.get("signed_at"),
        "signer": cs.get("signer"),
        "receipt_hash": cs.get("receipt_hash"),
        "decision": (cs.get("signer") or {}).get("decision"),
        "diff": diff,
    }


@router.post("/cosign/submit/{token}")
async def submit_cosign(token: str, body: CosignSubmitIn, request: Request):
    """Carrier co-sign submission authorized by a purpose-bound one-time token.

    C-P-001C governed model:
      * Tokens may only be minted by privileged operators via /cosign/request.
      * Submission is permitted solely when the token is present, unused, and
        matches a stored claim_cosigns row (purpose-bound authorization).
      * Anonymous unrestricted mutation is prohibited: without a valid minted
        token the route returns 404 and records a safe blocked-write audit.
    """
    token = (token or "").strip()
    if not token:
        await _log_blocked_write(request, "cosign_token_missing")
        raise HTTPException(403, "Co-sign submission requires a purpose-bound token.")

    cs = await _get_cosign(token)
    if not cs:
        await _log_blocked_write(request, "cosign_token_invalid")
        raise HTTPException(404, "Co-sign token not found")
    if cs.get("signed_at"):
        raise HTTPException(409, "Token already used — Claim Snapshot has been co-signed")

    pid = cs["passport_id"]
    # Sign the pinned diff (what the adjuster saw at verify-time).  Falls
    # back to a fresh compute for legacy rows without pinned_diff.
    diff = cs.get("pinned_diff") or await diff_baseline_vs_latest(pid)
    signed_at = datetime.now(timezone.utc).isoformat()
    signer = body.model_dump()
    receipt = _receipt_hash(diff, signer, signed_at)

    await db["claim_cosigns"].update_one(
        {"token": token},
        {"$set": {
            "signed_at": signed_at,
            "signer": signer,
            "receipt_hash": receipt,
        }},
    )

    # Immutable ledger entry — what makes this killer-feature truly killer
    rec = await _get_passport(pid)
    _append_ledger(rec, "COSIGN",
                   note=f"Carrier co-signed by {body.adjuster_name} · {body.adjuster_company} · "
                        f"{body.decision} · receipt {receipt[:12]}…",
                   status=body.decision,
                   payload={
                       "adjuster_name": body.adjuster_name,
                       "adjuster_company": body.adjuster_company,
                       "adjuster_license": body.adjuster_license,
                       "decision": body.decision,
                       "notes": body.notes,
                       "receipt_hash": receipt,
                       "signed_at": signed_at,
                       "verdict_at_sign": diff.get("verdict"),
                       "repair_estimate_delta_usd":
                           diff.get("deltas", {}).get("repair_estimate_delta_usd"),
                   })
    await db["property_passports"].update_one(
        {"passport_id": pid},
        {"$set": {"ledger": rec["ledger"], "updated_at": rec["updated_at"]}},
    )

    # Broadcast to Live-Ops so Mission Control panels and the contractor's
    # ClaimSnapshot view light up the moment the adjuster signs.
    try:
        from routes.live_ops import fan_out
        await fan_out({
            "type": "COSIGN_RECEIVED",
            "passport_id": pid,
            "decision": body.decision,
            "adjuster": body.adjuster_name,
            "company": body.adjuster_company,
            "receipt_hash": receipt,
        })
    except Exception as e:
        logger.warning("cosign fan-out failed: %s", e)

    return {
        "passport_id": pid,
        "signed_at": signed_at,
        "decision": body.decision,
        "receipt_hash": receipt,
    }


@router.get("/{passport_id}/cosign/status")
async def cosign_status(passport_id: str):
    """Used by ClaimSnapshot.jsx to render the 'CO-SIGNED' badge when one
    exists — newest signed row wins."""
    pid = passport_id.upper()
    signed = await db["claim_cosigns"].find_one(
        {"passport_id": pid, "signed_at": {"$ne": None}},
        sort=[("signed_at", -1)],
    )
    pending = await db["claim_cosigns"].find_one(
        {"passport_id": pid, "signed_at": None},
        sort=[("requested_at", -1)],
    )
    if signed:
        return {
            "state": "SIGNED",
            "signed_at": signed["signed_at"],
            "signer": signed["signer"],
            "receipt_hash": signed["receipt_hash"],
            "token_tail": signed["token"][-8:],
        }
    if pending:
        return {
            "state": "PENDING",
            "requested_at": pending["requested_at"],
            "token": pending["token"],
            "carrier_company": pending.get("carrier_company"),
        }
    return {"state": "NONE"}
