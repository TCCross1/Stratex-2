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
  • v3.34.0 — added admin-controlled override layer:
    siding prices flow as `db.siding_pricing_overrides._encrypted`
    (sealed, global) → fall back to `_SIDING_DEFAULT_PLAINTEXT` (field
    tune v1) → swap is transparent to the envelope endpoint.

Roofing + gutter unit prices flow through the existing encrypted
contractor doc. Siding prices flow through this module's sealed book.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from stratex_auth import encrypt_value, decrypt_value  # noqa: F401  (re-exported for routes layer)


# =============================================================================
# FIELD-TUNED v1 SIDING PRICE BOOK — KY/Midwest 2026 supply-house baseline.
# Replaces starter values from v3.33.0. Pricing is FIELD-TUNED; quantity
# coefficients remain in materials_brain._SCAFFOLD_COEFFS (still scaffold).
# UI distinguishes via the `pricing_tune` marker on each priced line.
#
# Tune cadence: Anthony's GMs can override via the admin endpoint
#   PUT /api/contractor/materials-brain/siding-prices
# without a code deploy. The override flows through the same Fernet
# channel and supersedes these defaults the moment it's written.
# =============================================================================
_SIDING_PRICE_TUNE_VERSION = "field_tune_v1"  # 2026-05-31, KY/Midwest baseline

_SIDING_DEFAULT_PLAINTEXT: Dict[str, float] = {
    # Sheathing (shared across all siding classes)
    "7/16 OSB Sheathing":                       42.00,   # USD / SHEET (post-tariff)
    # Vinyl path (matches user-authored compute_siding_bill_of_materials)
    "1 Inch Aluminum-Faced Foam Board":         24.50,
    "1 Inch Standard Foam Underlayment":        19.75,
    "2 Inch Galvanized Roofing Nails":           0.045,  # per nail (~5lb box $22)
    "Seam Tape":                                18.50,   # per roll (3M 8067)
    "Button Cap Nails":                          0.065,
    "Standard Housewrap Roll":                 185.00,   # Tyvek 9' × 100'
    "1.25 Inch Hand-Drive Galvanized Nails":     0.032,
    # Composite scaffold (HardiePlank/LP SmartSide 12ft)
    "Composite Fiber-Cement Lap Board (12ft)":  14.50,
    "1.75 Inch Stainless Siding Nails":          0.085,
    "Color-Matched Sealant Tube":                8.95,
    # Wood scaffold (pine/cedar T&G)
    "Tongue-and-Groove Wood Plank (8ft)":        8.25,
    "Building Felt Roll (15lb)":                36.50,
    "8d Galvanized Ring-Shank Nails":            0.058,
    "Penetrating Wood Sealer (1gal)":           44.00,
}

# Sealed lazily — encryption is done once on first access. From that
# moment on, plaintext is reconstructed only by `decrypt_value`, exactly
# like the contractor's roofing/gutter prices.
_SIDING_SEALED_DEFAULTS: Optional[str] = None


def _seal_default_siding_prices() -> str:
    """Encrypt the v1 field-tune defaults once. Subsequent reads always
    round-trip through decrypt_value."""
    global _SIDING_SEALED_DEFAULTS
    if _SIDING_SEALED_DEFAULTS is None:
        _SIDING_SEALED_DEFAULTS = encrypt_value(_SIDING_DEFAULT_PLAINTEXT)
    return _SIDING_SEALED_DEFAULTS


def _default_siding_prices() -> Dict[str, float]:
    """Decrypt the sealed v1 defaults."""
    return decrypt_value(_seal_default_siding_prices()) or {}


async def get_active_siding_prices(db) -> Dict[str, Any]:
    """Return the active siding price book + tune metadata.

    Resolution order:
      1. Admin-saved override in `db.siding_pricing_overrides` (Fernet-sealed)
      2. Module-sealed v1 field-tune defaults

    The envelope endpoint always calls this — the swap is transparent.
    """
    override = await db.siding_pricing_overrides.find_one({"key": "global"}, {"_id": 0})
    if override and override.get("_encrypted"):
        try:
            decrypted = decrypt_value(override["_encrypted"]) or {}
            # Overlay any missing keys with v1 defaults so the override can
            # be partial (admin tunes one brand without losing the rest).
            merged = dict(_default_siding_prices())
            merged.update({k: float(v) for k, v in decrypted.items() if isinstance(v, (int, float))})
            return {
                "prices": merged,
                "tune_version": override.get("tune_version") or _SIDING_PRICE_TUNE_VERSION,
                "source": "admin_override",
                "updated_at": override.get("updated_at"),
            }
        except Exception:
            pass
    return {
        "prices": _default_siding_prices(),
        "tune_version": _SIDING_PRICE_TUNE_VERSION,
        "source": "module_default",
        "updated_at": None,
    }


def seal_siding_override(prices: Dict[str, float]) -> str:
    """Encrypt an admin-supplied price dict for persistence."""
    clean = {k: float(v) for k, v in prices.items() if isinstance(v, (int, float))}
    return encrypt_value(clean)


def known_siding_item_keys() -> set:
    """Whitelist used by the admin PUT endpoint."""
    return set(_SIDING_DEFAULT_PLAINTEXT.keys())


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


def attach_unit_prices(
    envelope_lines,
    contractor_price_book: Dict[str, Any],
    siding_book: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Mutates `envelope_lines` in place to stamp `unit_price_usd` +
    `line_total_usd` on every line. Returns the per-scope subtotals +
    envelope grand total + a `pricing_meta` block describing which
    encryption channel each line came from.

    Roofing + gutter lines → contractor's encrypted price book (Fernet).
    Siding lines           → resolved siding book (admin override or v1 defaults, both Fernet).
    Unresolved lines       → `unit_price_usd: null` + reason marker.

    `siding_book` is the dict returned by `get_active_siding_prices(db)`;
    if not provided, the module v1 defaults are used.
    """
    if siding_book is None:
        siding_prices = _default_siding_prices()
        siding_source_tag = "module_default"
        siding_tune = _SIDING_PRICE_TUNE_VERSION
    else:
        siding_prices = siding_book.get("prices") or {}
        siding_source_tag = siding_book.get("source") or "module_default"
        siding_tune = siding_book.get("tune_version") or _SIDING_PRICE_TUNE_VERSION

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
        pricing_tune: Optional[str] = None

        # 1. Try the roofing/gutter encrypted contractor book.
        cfg_key = _ROOFING_GUTTER_KEY_MAP.get(item)
        if cfg_key and cfg_key in contractor_price_book:
            unit_price = float(contractor_price_book[cfg_key])
            source = "contractor_encrypted_book"
            roof_gutter_priced += 1
        elif scope == "gutter":
            run_price = _match_gutter_run_price(item, contractor_price_book)
            if run_price is not None:
                unit_price = run_price
                source = "contractor_encrypted_book"
                roof_gutter_priced += 1

        # 2. Fall back to the sealed siding book (admin override or v1 defaults).
        if unit_price is None and item in siding_prices:
            unit_price = float(siding_prices[item])
            source = "sealed_siding_book"
            pricing_tune = siding_tune
            siding_priced += 1

        if unit_price is not None:
            line_total = round(qty * unit_price, 2)
            ln["unit_price_usd"] = round(unit_price, 4)
            ln["line_total_usd"] = line_total
            ln["pricing_source"] = source
            if pricing_tune:
                ln["pricing_tune"] = pricing_tune
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
            "siding_tune_version": siding_tune,
            "siding_book_source": siding_source_tag,
        },
    }
