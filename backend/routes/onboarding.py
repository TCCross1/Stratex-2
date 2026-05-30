"""STRATEX Onboarding / ROI Funnel routes — frictionless contractor sign-up
plus Stripe TEST-mode checkout for the selected ROI tier.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from core import _public_user, api, contractor_only, db, now_iso
from stratex_auth import create_access_token, hash_password, new_totp_secret

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

    - Creates a contractor account WITHOUT requiring TOTP enrollment up-front.
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
