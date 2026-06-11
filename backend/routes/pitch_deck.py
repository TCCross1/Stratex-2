"""STRATEX™ pitch-deck download endpoint.

Exposes the rendered Strategic Briefing PDF at:
  GET /api/pitch/strategic-briefing.pdf

Public, no auth required — this is the marketing artifact Doug Piercy receives.
"""
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from core import api

PDF_PATH = Path("/app/stratex_pitch/STRATEX_Piercy_Briefing.pdf")


@api.get("/pitch/strategic-briefing.pdf")
async def get_strategic_briefing():
    if not PDF_PATH.exists():
        raise HTTPException(404, "Strategic Briefing not yet rendered")
    return FileResponse(
        path=str(PDF_PATH),
        media_type="application/pdf",
        filename="STRATEX_Strategic_Briefing_Doug_Piercy.pdf",
        headers={"Cache-Control": "no-store"},
    )
