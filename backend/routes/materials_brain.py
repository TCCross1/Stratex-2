"""STRATEX™ Materials Brain — REST surface (Contractor + Admin scope).

Pure addition (preservation lock). Wraps `MaterialsMatrixEngine` for the
Contractor Business Brain and the Admin/GM Command Center.

Endpoints (mounted on shared /api router):
  GET  /api/contractor/materials-brain/matrix         — full siding + gutter catalog
  POST /api/contractor/materials-brain/siding-bom     — compute siding BOM
  POST /api/contractor/materials-brain/gutter-bom     — compute gutter BOM (scaffold)

Auth: contractor or admin (combined scope per build directive — Contractor
gets field-estimate dropdowns; Admin/GM gets visibility for invoicing and
margin multiplier sliders).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import api, current_user
from materials_brain import MATERIALS_BRAIN


# ---------------------------------------------------------------------------
# Auth gate — contractor + admin only (per main-agent directive 2026-05-31).
# ---------------------------------------------------------------------------
async def _contractor_or_admin(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"contractor", "admin"}:
        raise HTTPException(403, "Contractor or Admin clearance required")
    return user


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class SidingBomBody(BaseModel):
    wall_square_footage: float = Field(..., gt=0, le=100_000)
    style_type: str
    material_class: str  # "vinyl" | "composite" | "wood"
    use_foam_insulation: bool = False
    use_foil_face: bool = False


class GutterBomBody(BaseModel):
    linear_footage: float = Field(..., gt=0, le=10_000)
    size: str             # "5_Inch" | "6_Inch"
    style: str            # "K_Style" | "Half_Round"
    material_class: str   # "aluminum" | "copper"
    downspout_count: int = Field(..., ge=0, le=200)


class RoofingEnvelopeBody(BaseModel):
    """Quantities-only roofing scaffold inputs (pricing/labor stays in
    branch_console's full 4-agent pipeline)."""
    roof_square_footage: float = Field(..., gt=0, le=100_000)
    valleys_ft: float = Field(0.0, ge=0, le=10_000)
    perimeter_ft: float = Field(0.0, ge=0, le=10_000)
    pitch_multiplier: float = Field(1.0, ge=1.0, le=2.5)
    flashing_ft: float = Field(0.0, ge=0, le=2_000)


class FullEnvelopeBomBody(BaseModel):
    """All three scopes are optional — pass any combination."""
    roofing: Optional[RoofingEnvelopeBody] = None
    siding:  Optional[SidingBomBody] = None
    gutter:  Optional[GutterBomBody] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@api.get("/contractor/materials-brain/matrix")
async def get_materials_matrix(user=Depends(_contractor_or_admin)) -> Dict[str, Any]:
    """Return the full siding + gutter catalog so the UI can render dropdowns.

    Roofing is intentionally exposed as an empty bucket — roofing config lives
    in `routes/materials_config.py` and `routes/branch_console.py` and is not
    duplicated here under the preservation lock.
    """
    return {
        "matrix": MATERIALS_BRAIN.matrix,
        "scope": "siding+gutters",
        "note": "Roofing is owned by /api/contractor/materials and /api/branch/materials.",
    }


@api.post("/contractor/materials-brain/siding-bom")
async def post_siding_bom(body: SidingBomBody, user=Depends(_contractor_or_admin)) -> Dict[str, Any]:
    if body.material_class not in {"vinyl", "composite", "wood"}:
        raise HTTPException(400, f"Unsupported material_class '{body.material_class}'")
    result = MATERIALS_BRAIN.compute_siding_bill_of_materials(
        wall_square_footage=body.wall_square_footage,
        style_type=body.style_type,
        material_class=body.material_class,
        use_foam_insulation=body.use_foam_insulation,
        use_foil_face=body.use_foil_face,
    )
    return result


@api.post("/contractor/materials-brain/gutter-bom")
async def post_gutter_bom(body: GutterBomBody, user=Depends(_contractor_or_admin)) -> Dict[str, Any]:
    if body.material_class not in {"aluminum", "copper"}:
        raise HTTPException(400, f"Unsupported material_class '{body.material_class}'")
    result = MATERIALS_BRAIN.compute_gutter_bill_of_materials(
        linear_footage=body.linear_footage,
        size=body.size,
        style=body.style,
        material_class=body.material_class,
        downspout_count=body.downspout_count,
    )
    return result


@api.post("/contractor/materials-brain/full-envelope-bom")
async def post_full_envelope_bom(body: FullEnvelopeBomBody, user=Depends(_contractor_or_admin)) -> Dict[str, Any]:
    """Single-call Job Wizard rollup. Pass any combination of roofing/siding/
    gutter inputs and receive one envelope BOM with per-scope sections plus
    a flat `envelope_lines` list (each line tagged with its scope).

    Roofing scaffold lives here for quantities only — full pricing/labor
    quantification stays in `/api/branch/quantify` (branch_console).
    """
    if body.roofing is None and body.siding is None and body.gutter is None:
        raise HTTPException(400, "Provide at least one of: roofing, siding, gutter")

    if body.siding and body.siding.material_class not in {"vinyl", "composite", "wood"}:
        raise HTTPException(400, f"Unsupported siding material_class '{body.siding.material_class}'")
    if body.gutter and body.gutter.material_class not in {"aluminum", "copper"}:
        raise HTTPException(400, f"Unsupported gutter material_class '{body.gutter.material_class}'")

    return MATERIALS_BRAIN.compute_envelope_bill_of_materials(
        roofing=body.roofing.dict() if body.roofing else None,
        siding=body.siding.dict() if body.siding else None,
        gutter=body.gutter.dict() if body.gutter else None,
    )
