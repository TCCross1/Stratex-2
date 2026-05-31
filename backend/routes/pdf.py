"""STRATEX™ · Server-side Playwright PDF renderer for deliverables + deck.

Endpoints:
  GET /api/contractor/deliverable/{job_id}/pdf   → 8.5×11 portrait PDF of the
                                                   comprehensive deliverable.
  GET /api/contractor/deliverable/{job_id}/deck.pdf → 11×8.5 landscape, 10
                                                   pages, one slide per page.

Both forward the caller's Bearer token to the headless browser via a
short-lived signed cookie so the React deliverable / deck pages render
identically to what the user sees. PDF is streamed back as
`application/pdf`.

Owner check delegates to the same logic the JSON deliverable endpoint uses
(see routes/deliverable.py).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response

from core import api, current_user, db

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
