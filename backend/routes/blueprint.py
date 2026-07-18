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
# v1.0 (preserved)
BLUEPRINT_MD = MEMORY / "NEXTGEN_ARCHITECTURE_BLUEPRINT.md"
APPENDIX_MD = MEMORY / "NEXTGEN_ARCHITECTURE_REVIEW_APPENDIX.md"
PDF_PATH = MEMORY / "_blueprint_out" / "STRATEX_NextGen_Architecture_Blueprint_v1.0.pdf"

# v1.1 (preserved, frozen)
BLUEPRINT_V11_MD = MEMORY / "NEXTGEN_ARCHITECTURE_BLUEPRINT_v1.1.md"
REDLINE_V11_MD = MEMORY / "NEXTGEN_ARCHITECTURE_REDLINE_v1.0_to_v1.1.md"
ADRs_V11_MD = MEMORY / "NEXTGEN_ARCHITECTURE_ADRs_v1.1.md"
SUMMARY_V11_MD = MEMORY / "NEXTGEN_EXECUTIVE_SUMMARY_v1.1.md"
PDF_V11_PATH = MEMORY / "_blueprint_out" / "STRATEX_NextGen_Architecture_Blueprint_v1.1.pdf"

# v1.2 (current, revised)
BLUEPRINT_V12_MD = MEMORY / "NEXTGEN_ARCHITECTURE_BLUEPRINT_v1.2.md"
REDLINE_V12_MD = MEMORY / "NEXTGEN_ARCHITECTURE_REDLINE_v1.1_to_v1.2.md"
PDF_V12_PATH = MEMORY / "_blueprint_out" / "STRATEX_NextGen_Architecture_Blueprint_v1.2.pdf"


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


# ── Version 1.1 endpoints (current, revised) ─────────────────────────
def _serve_md(path: Path, filename: str):
    if not path.exists():
        raise HTTPException(404, f"{filename} not found")
    return PlainTextResponse(
        path.read_text(),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/v1.1/md")
async def blueprint_v11_md():
    return _serve_md(BLUEPRINT_V11_MD, "STRATEX_NextGen_Architecture_Blueprint_v1.1.md")


@router.get("/v1.1/redline")
async def blueprint_v11_redline():
    return _serve_md(REDLINE_V11_MD, "STRATEX_Blueprint_v1.1_REDLINE.md")


@router.get("/v1.1/adrs")
async def blueprint_v11_adrs():
    return _serve_md(ADRs_V11_MD, "STRATEX_Blueprint_v1.1_ADRs.md")


@router.get("/v1.1/summary")
async def blueprint_v11_summary():
    return _serve_md(SUMMARY_V11_MD, "STRATEX_Blueprint_v1.1_Executive_Summary.md")


@router.get("/v1.1/pdf")
async def blueprint_v11_pdf():
    if not PDF_V11_PATH.exists():
        raise HTTPException(404, "v1.1 PDF not yet rendered.")
    return FileResponse(
        str(PDF_V11_PATH),
        media_type="application/pdf",
        filename="STRATEX_NextGen_Architecture_Blueprint_v1.1.pdf",
    )


@router.get("/v1.0/preserved-pdf")
async def blueprint_v10_preserved_pdf():
    """Confirm v1.0 is preserved read-only for comparison."""
    p = MEMORY / "_v1.0_PRESERVED_Blueprint.pdf"
    if not p.exists():
        raise HTTPException(404, "v1.0 preserved copy not found")
    return FileResponse(
        str(p),
        media_type="application/pdf",
        filename="STRATEX_NextGen_Architecture_Blueprint_v1.0_PRESERVED.pdf",
    )


# ── Version 1.2 endpoints (current, revised) ─────────────────────────
@router.get("/v1.2/md")
async def blueprint_v12_md():
    return _serve_md(BLUEPRINT_V12_MD, "STRATEX_NextGen_Architecture_Blueprint_v1.2.md")


@router.get("/v1.2/redline")
async def blueprint_v12_redline():
    return _serve_md(REDLINE_V12_MD, "STRATEX_Blueprint_v1.1_to_v1.2_REDLINE.md")


@router.get("/v1.2/adrs")
async def blueprint_v12_adrs():
    return _serve_md(ADRs_V11_MD, "STRATEX_Blueprint_v1.2_ADRs.md")


@router.get("/v1.2/pdf")
async def blueprint_v12_pdf():
    if not PDF_V12_PATH.exists():
        raise HTTPException(404, "v1.2 PDF not yet rendered.")
    return FileResponse(
        str(PDF_V12_PATH),
        media_type="application/pdf",
        filename="STRATEX_NextGen_Architecture_Blueprint_v1.2.pdf",
    )
