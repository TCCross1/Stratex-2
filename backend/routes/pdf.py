"""STRATEX™ · Server-side Playwright PDF renderer for deliverables + deck.

Endpoints:
  GET  /api/contractor/deliverable/{job_id}/pdf      → portrait PDF (auth)
  GET  /api/contractor/deliverable/{job_id}/deck.pdf → landscape deck (auth)
  POST /api/contractor/deliverable/{job_id}/share-link → mint 24h signed URL
  GET  /api/public/deliverable/share/{token}/pdf     → public no-auth download
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core import api, current_user, db, now_iso
from stratex_auth import decrypt_value, encrypt_value

logger = logging.getLogger("stratex.pdf")

# Singleton browser launched lazily on first request — avoids paying the
# 700ms Chromium boot cost on every PDF request.
_PW = None
_BROWSER = None
_LOCK = asyncio.Lock()


async def _browser():
    global _PW, _BROWSER
    async with _LOCK:
        if _BROWSER is None or not _BROWSER.is_connected():
            from playwright.async_api import async_playwright
            _PW = await async_playwright().start()
            _BROWSER = await _PW.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
        return _BROWSER


async def _check_owner(job_id: str, user: Dict[str, Any]):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0, "contractor_id": 1, "is_public_demo": 1})
    role = user.get("role")
    if role == "operator":
        raise HTTPException(403, "operators don't access pricing deliverables")
    is_demo = (job_id in ("crown-demo", "AD-KY041")) or (job and job.get("is_public_demo") is True)
    if role == "contractor" and not is_demo and job and job.get("contractor_id") != user["id"]:
        raise HTTPException(403, "not your job")
    # v3.40.0 — blacklist gate: RESTRICTED_PERIMETER_VIOLATION freezes raw 3D
    # deliverable access (per spec section 4 blacklist enforcement).
    if role == "contractor":
        restricted = await db.contractor_blacklist.find_one(
            {"contractor_user_id": user["id"], "account_status": "RESTRICTED_PERIMETER_VIOLATION"},
            {"_id": 0, "strikes": 1, "last_breach_id": 1},
        )
        if restricted:
            raise HTTPException(
                403,
                f"Account RESTRICTED_PERIMETER_VIOLATION · "
                f"{restricted.get('strikes', 0)} verified breach strike(s) · "
                f"Raw 3D deliverable frozen pending administrator review."
            )
    # admins / ceo / investor tour-mode pass through
    return is_demo, job


async def _render_pdf(path: str, token: str, landscape: bool) -> bytes:
    """Spin up a page, set the auth token in localStorage (same key the React
    app reads), navigate, wait for the deliverable to settle, then emit PDF."""
    public_url = os.environ.get("PUBLIC_FRONTEND_URL") or "http://localhost:3000"
    # If REACT_APP_BACKEND_URL points to https://x.preview.emergentagent.com,
    # we want the frontend on the same origin (port 3000 internally is
    # reverse-proxied). We render against the same external preview URL so
    # the React app fetches `/api` correctly.
    target = f"{public_url.rstrip('/')}{path}"

    browser = await _browser()
    context = await browser.new_context(
        viewport={"width": 1366 if landscape else 1024, "height": 900},
        ignore_https_errors=True,
    )
    page = await context.new_page()
    try:
        # Inject the JWT BEFORE first nav, by visiting the origin first.
        await page.goto(public_url.rstrip("/"), wait_until="domcontentloaded", timeout=30000)
        await page.evaluate("(t) => window.localStorage.setItem('stratex_token', t)", token)
        await page.goto(target, wait_until="networkidle", timeout=45000)
        # Wait until the React deliverable / deck root is in the DOM.
        await page.wait_for_selector(
            "[data-testid='deliverable-paper'], [data-testid='deck-root']",
            timeout=15000,
        )
        # Slight settle for the 3D twin image + radar tiles.
        await page.wait_for_timeout(1200)
        pdf_bytes = await page.pdf(
            format="Letter",
            landscape=landscape,
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        return pdf_bytes
    finally:
        await context.close()


def _extract_bearer(request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    return auth[7:]


@api.get("/contractor/deliverable/{job_id}/pdf")
async def deliverable_pdf(job_id: str, request: Request, user=Depends(current_user)):
    """Render the comprehensive deliverable page at /contractor/deliverable/{job_id}
    (or /deliverable/demo for the canonical demo) as a portrait PDF."""
    await _check_owner(job_id, user)
    token = _extract_bearer(request)
    path = "/deliverable/demo" if job_id in ("crown-demo", "AD-KY041") else f"/contractor/deliverable/{job_id}"
    try:
        pdf = await _render_pdf(path, token, landscape=False)
    except Exception as e:
        logger.exception("PDF render failed")
        raise HTTPException(502, f"PDF render failed: {e}")
    filename = f"STRATEX-{job_id}-deliverable.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@api.get("/contractor/deliverable/{job_id}/deck.pdf")
async def deliverable_deck_pdf(job_id: str, request: Request, user=Depends(current_user)):
    """Render the 10-slide presentation deck as a landscape Letter PDF."""
    await _check_owner(job_id, user)
    token = _extract_bearer(request)
    path = "/deck/demo" if job_id in ("crown-demo", "AD-KY041") else f"/contractor/deliverable/{job_id}/deck"
    try:
        pdf = await _render_pdf(path, token, landscape=True)
    except Exception as e:
        logger.exception("Deck PDF render failed")
        raise HTTPException(502, f"PDF render failed: {e}")
    filename = f"STRATEX-{job_id}-deck.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ============================================================================
# v3.42.0 — Signed 24-hour share-link (Tier-1 PDF only, no JWT required).
# ============================================================================
class ShareLinkMintBody(BaseModel):
    ttl_hours: int = Field(24, ge=1, le=72, description="Time-to-live in hours")


@api.post("/contractor/deliverable/{job_id}/share-link")
async def mint_deliverable_share_link(
    job_id: str,
    body: ShareLinkMintBody,
    request: Request,
    user=Depends(current_user),
) -> Dict[str, Any]:
    """Mint a Fernet-sealed 24h share token for the Tier-1 deliverable PDF.
    Re-uses _check_owner so the v3.40 RESTRICTED_PERIMETER_VIOLATION gate
    auto-applies: blacklisted contractors cannot mint share links."""
    await _check_owner(job_id, user)

    exp = datetime.now(timezone.utc) + timedelta(hours=body.ttl_hours)
    sealed = encrypt_value({
        "job_id":     job_id,
        "exp_iso":    exp.isoformat(),
        "minted_by":  user["id"],
        "scope":      "tier1_pdf",
        "nonce":      uuid.uuid4().hex,
    })

    await db.deliverable_share_links.insert_one({
        "job_id":     job_id,
        "minted_by":  user["id"],
        "minted_at":  now_iso(),
        "expires_at": exp.isoformat(),
        "scope":      "tier1_pdf",
        "active":     True,
        "token_head": sealed[:24],
    })

    origin = os.environ.get("PUBLIC_FRONTEND_URL") or str(request.base_url).rstrip("/")
    share_url = f"{origin.rstrip('/')}/api/public/deliverable/share/{sealed}/pdf"

    return {
        "ok":             True,
        "share_url":      share_url,
        "expires_at":     exp.isoformat(),
        "ttl_hours":      body.ttl_hours,
        "scope":          "tier1_pdf",
        "token_preview":  sealed[:18] + "…",
    }


@api.get("/public/deliverable/share/{token}/pdf")
async def public_deliverable_share_pdf(token: str, request: Request):
    """No-auth download. Strict scope: tier1_pdf only. Never serves the deck,
    raw JSON, or 3D mesh viewer."""
    try:
        payload = decrypt_value(token)
    except Exception:
        raise HTTPException(404, "Invalid or expired share link")
    if not isinstance(payload, dict):
        raise HTTPException(404, "Invalid share link payload")
    if payload.get("scope") != "tier1_pdf":
        raise HTTPException(403, "Share token scope mismatch — Tier-1 only")
    job_id  = payload.get("job_id")
    exp_iso = payload.get("exp_iso")
    if not job_id or not exp_iso:
        raise HTTPException(404, "Malformed share link")
    try:
        exp = datetime.fromisoformat(exp_iso.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(404, "Malformed share link expiry")
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(410, "Share link expired")

    # Defense in depth: re-validate the original minter still exists + isn't
    # blacklisted. Mint a fresh service JWT bound to that account so the
    # headless Playwright render flows through the same auth surface.
    minter = await db.users.find_one(
        {"id": payload.get("minted_by")},
        {"_id": 0, "id": 1, "role": 1, "email": 1},
    )
    if not minter:
        raise HTTPException(410, "Original minter account no longer active")
    if minter.get("role") == "contractor":
        restricted = await db.contractor_blacklist.find_one(
            {"contractor_user_id": minter["id"], "account_status": "RESTRICTED_PERIMETER_VIOLATION"},
            {"_id": 0},
        )
        if restricted:
            raise HTTPException(410, "Share link revoked — minter under perimeter violation")

    from stratex_auth import create_access_token
    service_token = create_access_token(minter["id"], minter.get("role", "contractor"), minter.get("email", ""))

    path = "/deliverable/demo" if job_id in ("crown-demo", "AD-KY041") else f"/contractor/deliverable/{job_id}"
    try:
        pdf = await _render_pdf(path, service_token, landscape=False)
    except Exception as e:
        logger.exception("Public share PDF render failed")
        raise HTTPException(502, f"PDF render failed: {e}")

    filename = f"STRATEX-{job_id}-tier1.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":     f'inline; filename="{filename}"',
            "X-Stratex-Share-Scope":   "tier1_pdf",
            "X-Stratex-Share-Expires": exp.isoformat(),
        },
    )

