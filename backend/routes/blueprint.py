"""Preview-only download endpoints for the NextGen Architecture Blueprint.

These routes exist to satisfy the executive-review hold:
  - GET /api/blueprint/md         → raw Markdown of the Blueprint
  - GET /api/blueprint/appendix   → raw Markdown of the Review Appendix
  - GET /api/blueprint/pdf        → professionally-formatted PDF (cover + TOC + page numbers)
  - GET /api/blueprint/bundle     → concatenated Blueprint + Appendix Markdown

Preview environment ONLY. NOT exposed on stratexdrone.com per the
executive hold instruction dated 2026-02-26.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

router = APIRouter(prefix="/api/blueprint", tags=["blueprint"])

MEMORY = Path("/app/memory")
BLUEPRINT_MD = MEMORY / "NEXTGEN_ARCHITECTURE_BLUEPRINT.md"
APPENDIX_MD = MEMORY / "NEXTGEN_ARCHITECTURE_REVIEW_APPENDIX.md"
PDF_PATH = MEMORY / "_blueprint_out" / "STRATEX_NextGen_Architecture_Blueprint_v1.0.pdf"


@router.get("/md")
async def blueprint_md():
    if not BLUEPRINT_MD.exists():
        raise HTTPException(404, "Blueprint markdown not found")
    return PlainTextResponse(
        BLUEPRINT_MD.read_text(),
        media_type="text/markdown",
        headers={
            "Content-Disposition":
                'attachment; filename="STRATEX_NextGen_Architecture_Blueprint_v1.0.md"'
        },
    )


@router.get("/appendix")
async def review_appendix_md():
    if not APPENDIX_MD.exists():
        raise HTTPException(404, "Appendix markdown not found")
    return PlainTextResponse(
        APPENDIX_MD.read_text(),
        media_type="text/markdown",
        headers={
            "Content-Disposition":
                'attachment; filename="STRATEX_NextGen_Review_Appendix_v1.0.md"'
        },
    )


@router.get("/bundle")
async def bundle_md():
    if not BLUEPRINT_MD.exists() or not APPENDIX_MD.exists():
        raise HTTPException(404, "Blueprint documents not found")
    combined = (
        BLUEPRINT_MD.read_text() + "\n\n---\n\n" + APPENDIX_MD.read_text()
    )
    return PlainTextResponse(
        combined,
        media_type="text/markdown",
        headers={
            "Content-Disposition":
                'attachment; filename="STRATEX_NextGen_Architecture_Bundle_v1.0.md"'
        },
    )


@router.get("/pdf")
async def blueprint_pdf():
    if not PDF_PATH.exists():
        raise HTTPException(
            404,
            "Blueprint PDF not yet rendered. "
            "Run /app/memory/_build_blueprint_pdf.py to generate it.",
        )
    return FileResponse(
        str(PDF_PATH),
        media_type="application/pdf",
        filename="STRATEX_NextGen_Architecture_Blueprint_v1.0.pdf",
    )
