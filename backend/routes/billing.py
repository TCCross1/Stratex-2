"""STRATEX Stripe Billing routes — subscription tiers (one-time monthly charges).

Model A pricing. Uses emergentintegrations.payments.stripe with the
contractor's STRIPE_API_KEY from the platform environment.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from core import api, contractor_only, current_user, db, logger, now_iso

# v4.1 — STRATEX™ Enterprise-Only Pricing (per founder directive 2026-06-01)
# Old on_demand + volume_builder tiers deleted per STRICT_DELETE_OTHERS directive.
# Single tier: $1,500 platform signup + $200 per autonomous scan.
PRICING_TIERS = {
    "enterprise": {
        "name": "Enterprise",
        "price": 1500.00,             # one-time platform signup / activation
        "included_drops": 0,
        "extra_drop_price": 200.00,   # per autonomous scan
        "blurb": "Strategic deployment for multi-branch suppliers and high-volume contractors",
        "features": [
            "$1,500 one-time platform activation",
            "$200 per autonomous scan (no caps, no minimums)",
            "Full STRATEX™ Trifecta Verification Stack",
            "Tripwire cost-shopping defense (perimeter + gutter node)",
            "Triple-layer 3D digital twin in every report",
            "AES-256 Business Brain + immutable pricing ledger",
            "Co-brand toggle (QXO / ABC Supply / blank-label)",
            "24h Fernet-sealed homeowner share links",
            "Real-time fleet USA map + breach alerting",
            "SOC2 audit log + compliance export",
        ],
        "popular": True,
    },
}

IMPLEMENTATION_FEE = 0.00   # Folded into the $1,500 activation
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
