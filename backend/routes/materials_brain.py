"""STRATEX™ Materials Brain — REST surface (Contractor + Admin scope).

Pure addition (preservation lock). Wraps `MaterialsMatrixEngine` for the
Contractor Business Brain and the Admin/GM Command Center.

Endpoints (mounted on shared /api router):
  GET  /api/contractor/materials-brain/matrix              — full siding + gutter catalog
  POST /api/contractor/materials-brain/siding-bom          — compute siding BOM
  POST /api/contractor/materials-brain/gutter-bom          — compute gutter BOM (scaffold)
  POST /api/contractor/materials-brain/full-envelope-bom   — single-call roof+wall+gutter envelope rollup
       (v3.33.0 — natively attaches encrypted unit prices + scope subtotals + grand total)

Auth: contractor or admin (combined scope per build directive — Contractor
gets field-estimate dropdowns; Admin/GM gets visibility for invoicing and
margin multiplier sliders).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from core import api, current_user, db, now_iso
from materials_brain import MATERIALS_BRAIN
from materials_pricing import (
    attach_unit_prices,
    decrypt_value,
    get_active_siding_prices,
    known_siding_item_keys,
    resolve_unit_price_book,
    seal_siding_override,
    _SIDING_PRICE_TUNE_VERSION,
)


# ---------------------------------------------------------------------------
# Auth gate — contractor + admin only (per main-agent directive 2026-05-31).
# ---------------------------------------------------------------------------
async def _contractor_or_admin(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"contractor", "admin"}:
        raise HTTPException(403, "Contractor or Admin clearance required")
    return user


async def _admin_only(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role != "admin":
        raise HTTPException(403, "Admin clearance required")
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

    v3.33.0 — natively stitches encrypted unit prices on every line. Roofing
    + gutter prices come from the caller's `db.materials_configs` doc
    (Fernet/AES-256 envelope, same channel as the primary materials module).
    Siding prices come from this module's sealed default book (also Fernet).
    Response gains `subtotals_by_scope`, `envelope_grand_total_usd`, and
    `pricing_meta` blocks.
    """
    if body.roofing is None and body.siding is None and body.gutter is None:
        raise HTTPException(400, "Provide at least one of: roofing, siding, gutter")

    if body.siding and body.siding.material_class not in {"vinyl", "composite", "wood"}:
        raise HTTPException(400, f"Unsupported siding material_class '{body.siding.material_class}'")
    if body.gutter and body.gutter.material_class not in {"aluminum", "copper"}:
        raise HTTPException(400, f"Unsupported gutter material_class '{body.gutter.material_class}'")

    envelope = MATERIALS_BRAIN.compute_envelope_bill_of_materials(
        roofing=body.roofing.dict() if body.roofing else None,
        siding=body.siding.dict() if body.siding else None,
        gutter=body.gutter.dict() if body.gutter else None,
    )

    # Decrypt the caller's contractor price book (admin → defaults). Both
    # paths route through the same Fernet/AES-256 channel that the primary
    # roofing module uses.
    price_book = await resolve_unit_price_book(db, user["id"])
    # Resolve active siding book — admin override (if present) or v1 defaults.
    siding_book = await get_active_siding_prices(db)
    pricing_summary = attach_unit_prices(envelope["envelope_lines"], price_book, siding_book)
    envelope.update(pricing_summary)
    return envelope


# ---------------------------------------------------------------------------
# v3.34.0 — Sealed siding-price swap layer.
# GET   /siding-prices  → admin sees override + defaults; contractor sees union.
# PUT   /siding-prices  → admin-only; encrypts & persists override.
# ---------------------------------------------------------------------------
class SidingPriceOverrideBody(BaseModel):
    """Admin-supplied per-item siding price overrides. Partial updates allowed
    — any key omitted falls back to the v1 field-tune default automatically."""
    prices: Dict[str, float] = Field(..., description="Item label → USD price")
    tune_version: Optional[str] = Field(None, description="Optional label, e.g. 'field_tune_v2_KY_2026Q3'")


@api.get("/contractor/materials-brain/siding-prices")
async def get_siding_prices(user=Depends(_contractor_or_admin)) -> Dict[str, Any]:
    """Return the **active** siding price book (admin override or v1 defaults).
    Contractor: read-only view. Admin: same view, plus knows it can PUT."""
    book = await get_active_siding_prices(db)
    return {
        "active_prices": book["prices"],
        "tune_version":  book["tune_version"],
        "source":        book["source"],
        "updated_at":    book["updated_at"],
        "known_item_keys": sorted(known_siding_item_keys()),
        "encryption_channel": "Fernet/AES-256 (HKDF-SHA256 derived from AES_KEY)",
    }


@api.put("/contractor/materials-brain/siding-prices")
async def put_siding_prices(body: SidingPriceOverrideBody, user=Depends(_admin_only)) -> Dict[str, Any]:
    """Admin-only. Encrypt the supplied override dict (partial updates OK) and
    persist as a single sealed document under `db.siding_pricing_overrides`.

    v3.35.0 — every PUT also snapshots the **previous** override doc (if any)
    into `db.siding_pricing_history` for audit + revert. The history doc
    keeps the previous `_encrypted` blob verbatim — same Fernet/AES-256
    seal, same channel.
    """
    if not body.prices:
        raise HTTPException(400, "prices payload must include at least one key")
    known = known_siding_item_keys()
    unknown = sorted(k for k in body.prices.keys() if k not in known)
    if unknown:
        raise HTTPException(400, f"Unknown siding item keys: {unknown}")
    for k, v in body.prices.items():
        if not isinstance(v, (int, float)) or v < 0 or v > 100_000:
            raise HTTPException(400, f"Price for '{k}' out of bounds (0–100000)")

    sealed = seal_siding_override(body.prices)
    tune_version = body.tune_version or f"{_SIDING_PRICE_TUNE_VERSION}_override"

    # --- Snapshot the prior override BEFORE we overwrite it.
    prior = await db.siding_pricing_overrides.find_one({"key": "global"}, {"_id": 0})
    snapshot_id: Optional[str] = None
    if prior and prior.get("_encrypted"):
        snapshot_id = str(uuid.uuid4())
        await db.siding_pricing_history.insert_one({
            "snapshot_id": snapshot_id,
            "key": "global",
            "_encrypted": prior["_encrypted"],         # opaque ciphertext — preserved verbatim
            "tune_version": prior.get("tune_version"),
            "snapshotted_at": now_iso(),
            "snapshotted_from_updated_at": prior.get("updated_at"),
            "snapshotted_from_updated_by": prior.get("updated_by"),
            "replaced_with_tune_version": tune_version,
            "triggered_by": user["id"],
            "trigger_action": "put_override",
        })

    await db.siding_pricing_overrides.update_one(
        {"key": "global"},
        {"$set": {
            "key": "global",
            "_encrypted": sealed,
            "tune_version": tune_version,
            "updated_at": now_iso(),
            "updated_by": user["id"],
        }},
        upsert=True,
    )
    return {
        "ok": True,
        "encrypted_field_count": len(body.prices),
        "tune_version": tune_version,
        "encryption_channel": "Fernet/AES-256 (HKDF-SHA256 derived from AES_KEY)",
        "previous_snapshot_id": snapshot_id,
    }


# ---------------------------------------------------------------------------
# v3.35.0 — History + Revert (admin-only audit ledger).
# ---------------------------------------------------------------------------
@api.get("/contractor/materials-brain/siding-prices/history")
async def get_siding_prices_history(
    limit: int = 50,
    user=Depends(_admin_only),
) -> Dict[str, Any]:
    """Return the audit ledger of past siding-price overrides. Newest first.
    Each entry is decrypted server-side and returned with the prior price dict
    so the admin UI can render a diff column."""
    limit = max(1, min(int(limit or 50), 200))
    cursor = db.siding_pricing_history.find({"key": "global"}, {"_id": 0}).sort("snapshotted_at", -1).limit(limit)
    rows: List[Dict[str, Any]] = []
    async for doc in cursor:
        prices: Optional[Dict[str, float]] = None
        try:
            prices = decrypt_value(doc.get("_encrypted")) or None
        except Exception:
            prices = None
        rows.append({
            "snapshot_id": doc.get("snapshot_id"),
            "tune_version": doc.get("tune_version"),
            "snapshotted_at": doc.get("snapshotted_at"),
            "snapshotted_from_updated_at": doc.get("snapshotted_from_updated_at"),
            "snapshotted_from_updated_by": doc.get("snapshotted_from_updated_by"),
            "replaced_with_tune_version": doc.get("replaced_with_tune_version"),
            "triggered_by": doc.get("triggered_by"),
            "trigger_action": doc.get("trigger_action"),
            "prices": prices,
        })
    return {
        "history": rows,
        "count": len(rows),
        "encryption_channel": "Fernet/AES-256 (HKDF-SHA256 derived from AES_KEY)",
    }


@api.post("/contractor/materials-brain/siding-prices/revert/{snapshot_id}")
async def revert_siding_prices(snapshot_id: str, user=Depends(_admin_only)) -> Dict[str, Any]:
    """Admin-only. Restore a prior sealed override as the new active book.
    The current override is itself snapshotted first (so revert is also
    revertable — full bidirectional audit trail)."""
    target = await db.siding_pricing_history.find_one({"snapshot_id": snapshot_id, "key": "global"}, {"_id": 0})
    if not target or not target.get("_encrypted"):
        raise HTTPException(404, f"Snapshot '{snapshot_id}' not found or empty")

    # Snapshot current state first.
    current = await db.siding_pricing_overrides.find_one({"key": "global"}, {"_id": 0})
    pre_revert_snapshot_id: Optional[str] = None
    if current and current.get("_encrypted"):
        pre_revert_snapshot_id = str(uuid.uuid4())
        await db.siding_pricing_history.insert_one({
            "snapshot_id": pre_revert_snapshot_id,
            "key": "global",
            "_encrypted": current["_encrypted"],
            "tune_version": current.get("tune_version"),
            "snapshotted_at": now_iso(),
            "snapshotted_from_updated_at": current.get("updated_at"),
            "snapshotted_from_updated_by": current.get("updated_by"),
            "replaced_with_tune_version": target.get("tune_version"),
            "triggered_by": user["id"],
            "trigger_action": "pre_revert_snapshot",
        })

    restored_tune = (target.get("tune_version") or "reverted") + "_reverted"
    await db.siding_pricing_overrides.update_one(
        {"key": "global"},
        {"$set": {
            "key": "global",
            "_encrypted": target["_encrypted"],
            "tune_version": restored_tune,
            "updated_at": now_iso(),
            "updated_by": user["id"],
            "reverted_from_snapshot_id": snapshot_id,
        }},
        upsert=True,
    )
    return {
        "ok": True,
        "restored_snapshot_id": snapshot_id,
        "restored_as_tune_version": restored_tune,
        "pre_revert_snapshot_id": pre_revert_snapshot_id,
        "encryption_channel": "Fernet/AES-256 (HKDF-SHA256 derived from AES_KEY)",
    }
