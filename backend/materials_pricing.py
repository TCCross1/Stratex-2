"""STRATEX™ — Materials Brain Pricing Resolver

Stitches **encrypted** unit prices from the contractor's Business Brain
(`db.materials_configs._encrypted` — same Fernet/AES-256 envelope used by
the primary roofing materials module) onto every BOM line emitted by
`materials_brain.MaterialsMatrixEngine`.

Pure addition (preservation lock):
  • Does NOT modify `MaterialsConfig` (roofing master price DB unchanged).
  • Does NOT modify `db.materials_configs` collection schema.
  • Does NOT alter frontend dropdowns.
  • Adds a parallel SEALED siding price book — defaults are encrypted via
    `encrypt_value` at lazy-init and decrypted on every read, matching
    the roofing module's secure logic exactly.

Roofing + gutter unit prices flow through the existing encrypted
contractor doc. Siding prices flow through this module's sealed book.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from stratex_auth import encrypt_value, decrypt_value


# =============================================================================
# SEALED SIDING PRICE BOOK — encrypted-at-rest defaults (per-line USD).
# Values are sealed via Fernet at first access; every subsequent read
# round-trips through `decrypt_value`, mirroring the roofing pattern in
# routes/server.py:GET /api/contractor/materials.
#
# Per directive: do NOT add these to the master `MaterialsConfig` Pydantic
# model. Siding pricing remains a parallel sealed channel until field
# data calibrates per-brand rates.
# =============================================================================
_SIDING_DEFAULT_PLAINTEXT: Dict[str, float] = {
    # Sheathing (shared across all siding classes)
    "7/16 OSB Sheathing":                       38.75,   # USD / SHEET
    # Vinyl path (matches user-authored compute_siding_bill_of_materials)
    "1 Inch Aluminum-Faced Foam Board":          22.50,
    "1 Inch Standard Foam Underlayment":         18.00,
    "2 Inch Galvanized Roofing Nails":            0.04,   # per nail
    "Seam Tape":                                 14.00,   # per roll
    "Button Cap Nails":                           0.06,
    "Standard Housewrap Roll":                  168.00,
    "1.25 Inch Hand-Drive Galvanized Nails":      0.03,
    # Composite scaffold
    "Composite Fiber-Cement Lap Board (12ft)":    9.85,
    "1.75 Inch Stainless Siding Nails":           0.07,
    "Color-Matched Sealant Tube":                 7.25,
    # Wood scaffold
    "Tongue-and-Groove Wood Plank (8ft)":         6.40,
    "Building Felt Roll (15lb)":                 32.00,
    "8d Galvanized Ring-Shank Nails":             0.05,
    "Penetrating Wood Sealer (1gal)":            38.00,
}

# Sealed lazily — encryption is done once on first access. From that
# moment on, plaintext is reconstructed only by `decrypt_value`, exactly
# like the contractor's roofing/gutter prices.
_SIDING_SEALED: Optional[str] = None


def _sealed_siding_prices() -> Dict[str, float]:
    """Round-trip the siding defaults through Fernet on every read."""
    global _SIDING_SEALED
    if _SIDING_SEALED is None:
        _SIDING_SEALED = encrypt_value(_SIDING_DEFAULT_PLAINTEXT)
    return decrypt_value(_SIDING_SEALED) or {}


# =============================================================================
# ROOFING + GUTTER KEY MAP — line item label → MaterialsConfig field name.
# Mirrors the existing `branch_console.py` add_line() pattern but uses
# the contractor's encrypted price book directly.
# =============================================================================
_ROOFING_GUTTER_KEY_MAP: Dict[str, str] = {
    # Roofing (priced per SQUARE / per ROLL / per PIECE etc.)
    "Premium Architectural Shingles":           "shingle_bundle_price",
    "Synthetic Felt #15":                       "underlayment_square_price",
    "Ice & Water Shield":                       "ice_water_roll_price",
    "Drip Edge (10ft pieces)":                  "drip_edge_lf_price",     # per piece (~10 lf)
    "Wall Counter/Step Flashing":               "drip_edge_lf_price",     # closest mapping (lf)
    "Chimney Flashing & Caulk Combo Pack":      "starter_bundle_price",   # closest stocked SKU
    "Coil Roofing Fasteners":                   "fastener_square_price",  # priced per box (~1 sq)
    "Plastic Button Cap Nails":                 "fastener_square_price",
    # Gutter (priced per LF / per piece)
    "Hidden Hangers":                           "hidden_hanger_each_price",
    "Downspout Elbows":                         "elbow_price",
    "Downspout Sections (10ft)":                "downspout_drop_price",
    "End Caps (LR pair)":                       "end_cap_price",
    "Gutter Sealant Tube":                      "elbow_price",            # nearest small-part SKU
}


def _match_gutter_run_price(item_label: str, config: Dict[str, Any]) -> Optional[float]:
    """Resolve dynamic gutter labels.

    Two patterns are handled:
      1. Gutter run sections — '6 Inch K Style ALUMINUM Gutter (10ft)' → LF × 10
      2. Hidden hangers      — '6 Inch Hidden Hangers' → per-each price
    """
    lo = item_label.lower()
    if "hidden hangers" in lo:
        return float(config.get("hidden_hanger_each_price", 4.25))
    if "gutter" not in lo or "(10ft)" not in lo:
        return None
    if "5 inch" in lo:
        per_lf = float(config.get("gutter_5in_kstyle_lf_price", 8.50))
    else:
        per_lf = float(config.get("gutter_6in_kstyle_lf_price", 11.75))
    return per_lf * 10.0


async def resolve_unit_price_book(db, user_id: str) -> Dict[str, Any]:
    """Pull the caller's encrypted MaterialsConfig and decrypt it. Returns a
    flat dict of unit prices that the roofing/gutter mapper can use.

    If the contractor has not yet saved a price book, returns the
    MaterialsConfig() Pydantic defaults — still routed through Fernet so
    the access pattern matches the saved-book pattern.

    Partial books (e.g. legacy save that omitted gutter keys) are
    overlaid with MaterialsConfig defaults for any missing keys —
    matches the exact behavior of GET /api/contractor/materials in
    server.py so the envelope endpoint never sees holes.
    """
    doc = await db.materials_configs.find_one({"user_id": user_id}, {"_id": 0})
    if doc and doc.get("_encrypted"):
        try:
            decrypted = decrypt_value(doc["_encrypted"])
            doc.update(decrypted or {})
        except Exception:
            pass
    if doc:
        doc.pop("_encrypted", None)
        doc.pop("user_id", None)
        doc.pop("updated_at", None)
    if not doc:
        doc = {}
    # Overlay MaterialsConfig defaults for any missing fields — same logic
    # the contractor-facing GET endpoint uses.
    from server import MaterialsConfig  # local import — avoids cycle
    defaults = MaterialsConfig().model_dump()
    for k, v in defaults.items():
        doc.setdefault(k, v)
    return doc


def attach_unit_prices(envelope_lines, contractor_price_book: Dict[str, Any]) -> Dict[str, Any]:
    """Mutates `envelope_lines` in place to stamp `unit_price_usd` +
    `line_total_usd` on every line. Returns the per-scope subtotals +
    envelope grand total + a `pricing_meta` block describing which
    encryption channel each line came from.

    Roofing + gutter lines → contractor's encrypted price book (Fernet).
    Siding lines           → sealed siding default book (Fernet).
    Unresolved lines       → `unit_price_usd: null` + reason marker.
    """
    siding_prices = _sealed_siding_prices()

    subtotals: Dict[str, float] = {}
    unresolved = 0
    siding_priced = 0
    roof_gutter_priced = 0

    for ln in envelope_lines:
        item = ln.get("item", "")
        qty = float(ln.get("quantity", 0) or 0)
        scope = ln.get("scope", "")
        unit_price: Optional[float] = None
        source: Optional[str] = None

        # 1. Try the roofing/gutter encrypted contractor book.
        cfg_key = _ROOFING_GUTTER_KEY_MAP.get(item)
        if cfg_key and cfg_key in contractor_price_book:
            unit_price = float(contractor_price_book[cfg_key])
            source = "contractor_encrypted_book"
            roof_gutter_priced += 1
        elif scope == "gutter":
            # dynamic gutter run label
            run_price = _match_gutter_run_price(item, contractor_price_book)
            if run_price is not None:
                unit_price = run_price
                source = "contractor_encrypted_book"
                roof_gutter_priced += 1

        # 2. Fall back to the sealed siding book.
        if unit_price is None and item in siding_prices:
            unit_price = float(siding_prices[item])
            source = "sealed_siding_book"
            siding_priced += 1

        if unit_price is not None:
            line_total = round(qty * unit_price, 2)
            ln["unit_price_usd"] = round(unit_price, 4)
            ln["line_total_usd"] = line_total
            ln["pricing_source"] = source
            subtotals[scope] = round(subtotals.get(scope, 0.0) + line_total, 2)
        else:
            ln["unit_price_usd"] = None
            ln["line_total_usd"] = None
            ln["pricing_source"] = "unresolved"
            unresolved += 1

    grand_total = round(sum(subtotals.values()), 2)
    return {
        "subtotals_by_scope": subtotals,
        "envelope_grand_total_usd": grand_total,
        "pricing_meta": {
            "lines_priced_via_contractor_encrypted_book": roof_gutter_priced,
            "lines_priced_via_sealed_siding_book": siding_priced,
            "lines_unresolved": unresolved,
            "encryption_channel": "Fernet/AES-256 (HKDF-SHA256 derived from AES_KEY)",
        },
    }
