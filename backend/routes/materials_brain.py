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

from typing import Any, Dict

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
