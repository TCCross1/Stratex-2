"""STRATEX™ — Structural Anomaly Estimator (multi-tier thermal damage engine).

Pure addition (preservation lock). Pairs with the drone-based thermal
imaging + 3D roof modeling pipeline already feeding the deliverable
processor. Maps RED / ORANGE / YELLOW thermal signatures to per-tier
repair material lists, labor allocations, and state-tax-locked financial
summaries.

Pricing flows through the contractor's encrypted MaterialsConfig
(Fernet/AES-256 channel) — same architecture as v3.33–v3.36. Hard-coded
defaults from the original spec are used only when the encrypted book
lacks a key, preserving back-compat with un-configured tenants.

Author's verbatim RED path preserved; YELLOW + ORANGE tiers added per
the v3.39 build directive with `scaffold: true` flag for UI badging.

Decimal precision: every financial value is rounded to 2 decimals at the
boundary to prevent IEEE-754 drift in the persisted ledger view.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


# =============================================================================
# State sales-tax map. Locked at scan execution time into pricing_version_id
# so historical scans never drift if a state rate changes later.
# =============================================================================
DEFAULT_TAX_RATES_BY_STATE: Dict[str, float] = {
    "KY": 0.0600,
    "OH": 0.0575,
    "IN": 0.0700,
    "TN": 0.0700,
}


# =============================================================================
# TIER MATRIX — per directive v3.39 (multi-temporal severity expansion).
# Each tier maps a thermal_signature_color to its remediation profile.
# Hard-coded `unit_cost_usd` and `labor_per_unit_hours` are the fallback
# defaults; `mc_price_key` and `mc_labor_key` (when set) override them
# from the contractor's encrypted MaterialsConfig.
# =============================================================================
ANOMALY_TIERS: Dict[str, Dict[str, Any]] = {
    "YELLOW": {
        "severity_index":     "VAPOR_BARRIER_INFILTRATION",
        "layer":              "VAPOR_BARRIER_FIELD",
        "item":               "Breathable Synthetic Vapor Barrier (Roll)",
        "unit":               "ROLLS",
        "coverage_sqft":      250.0,
        "unit_cost_usd":      45.00,
        "labor_per_unit_hrs": 0.5,
        "scaffold":           True,
        "mc_price_key":       None,    # no encrypted-book key — defaults rule
        "mc_labor_key":       None,
    },
    "ORANGE": {
        "severity_index":     "MEMBRANE_COMPROMISE_PATCH",
        "layer":              "MEMBRANE_FIELD",
        "item":               "EPDM Self-Adhering Membrane Patch",
        "unit":               "PATCHES",
        "coverage_sqft":      15.0,
        "unit_cost_usd":      18.50,
        "labor_per_unit_hrs": 1.0,
        "scaffold":           True,
        "mc_price_key":       None,
        "mc_labor_key":       None,
    },
    "RED": {
        "severity_index":     "CRITICAL_ROT_ALERT",
        "layer":              "ROOF_DECK_STRUCTURAL_FRAMING",
        "item":               "CDX Plywood Sheets 4x8",
        "unit":               "SHEETS",
        "coverage_sqft":      32.0,
        "unit_cost_usd":      28.50,
        "labor_per_unit_hrs": 1.5,
        "scaffold":           False,
        "mc_price_key":       "osb_sheet_price",       # contractor's encrypted price book
        "mc_labor_key":       "labor_rate_per_hour",
    },
}

# Default hourly labor rate when contractor has no encrypted book value.
# (RED path uses its tier-specific override; YELLOW/ORANGE share this fallback.)
DEFAULT_LABOR_RATE_USD_PER_HR = 65.00


def _resolve_tier_pricing(tier_key: str, contractor_price_book: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return effective `unit_cost_usd` + `labor_rate_usd_per_hr` for a tier,
    overlaying contractor's encrypted book values when the tier defines a
    mapping. Plain copy of the tier metadata for everything else."""
    tier = ANOMALY_TIERS[tier_key]
    eff = dict(tier)

    unit_cost = tier["unit_cost_usd"]
    labor_rate = DEFAULT_LABOR_RATE_USD_PER_HR
    pricing_source = "spec_default"

    if contractor_price_book:
        if tier.get("mc_price_key") and contractor_price_book.get(tier["mc_price_key"]) is not None:
            try:
                unit_cost = float(contractor_price_book[tier["mc_price_key"]])
                pricing_source = "contractor_encrypted_book"
            except (TypeError, ValueError):
                pass
        if tier.get("mc_labor_key") and contractor_price_book.get(tier["mc_labor_key"]) is not None:
            try:
                labor_rate = float(contractor_price_book[tier["mc_labor_key"]])
                pricing_source = "contractor_encrypted_book"
            except (TypeError, ValueError):
                pass

    eff["effective_unit_cost_usd"]   = round(unit_cost, 4)
    eff["effective_labor_rate_usd"]  = round(labor_rate, 4)
    eff["pricing_source"]            = pricing_source
    return eff


class StructuralAnomalyEngine:
    """Maps identified moisture anomalies to accurate building material repair lists."""

    def __init__(self):
        self.tax_rates_by_state = dict(DEFAULT_TAX_RATES_BY_STATE)

    # ------------------------------------------------------------------ #
    def evaluate_moisture_damage_anomalies(
        self,
        thermal_matrix_scan: List[Dict[str, Any]],
        home_state: str,
        contractor_price_book: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        damage_anomalies_log: List[Dict[str, Any]] = []
        total_additional_materials_cost = 0.0
        calculated_labor_hours = 0.0
        tier_counts: Dict[str, int] = {"YELLOW": 0, "ORANGE": 0, "RED": 0}
        pricing_sources_seen: set = set()

        for index, reading in enumerate(thermal_matrix_scan):
            color = (reading.get("thermal_signature_color") or "").upper()
            if color not in ANOMALY_TIERS:
                continue  # skip GREEN / unrecognized — no remediation needed

            tier = _resolve_tier_pricing(color, contractor_price_book)
            damaged_area_sqft = float(reading.get("pixel_damaged_area", 0.0) or 0.0)
            if damaged_area_sqft <= 0:
                continue

            # Ceiling division — fractional sqft still consumes one full unit.
            qty = max(1, math.ceil(damaged_area_sqft / tier["coverage_sqft"]))
            unit_cost = tier["effective_unit_cost_usd"]
            labor_per_unit = tier["labor_per_unit_hrs"]

            material_cost  = round(qty * unit_cost, 2)
            labor_hours    = round(qty * labor_per_unit, 2)

            anomaly_code = f"A-{index + 101}"
            anomaly_report: Dict[str, Any] = {
                "code":              anomaly_code,
                "thermal_color":     color,
                "layer":             tier["layer"],
                "damage_extent_sqft": round(damaged_area_sqft, 2),
                "severity_index":    tier["severity_index"],
                "required_materials": [{
                    "item":          tier["item"],
                    "qty":           qty,
                    "unit":          tier["unit"],
                    "unit_cost_usd": unit_cost,
                    "line_total_usd": material_cost,
                    "pricing_source": tier["pricing_source"],
                    "scaffold":      tier["scaffold"],
                }],
                "labor_hours_estimated":  labor_hours,
                "labor_rate_usd_per_hr":  tier["effective_labor_rate_usd"],
                "labor_line_total_usd":   round(labor_hours * tier["effective_labor_rate_usd"], 2),
                "scaffold":               tier["scaffold"],
            }

            # Carry coordinate metadata through if the drone supplied it.
            for k in ("centroid_x", "centroid_y", "centroid_lat", "centroid_lng", "altitude_ft", "frame_id"):
                if k in reading:
                    anomaly_report[k] = reading[k]

            damage_anomalies_log.append(anomaly_report)
            total_additional_materials_cost += material_cost
            calculated_labor_hours += labor_hours
            tier_counts[color] += 1
            pricing_sources_seen.add(tier["pricing_source"])

        # ---- Financial summary (single labor blend rate — RED's effective rate
        # is authoritative when present; otherwise spec default).
        labor_rate = (
            _resolve_tier_pricing("RED", contractor_price_book)["effective_labor_rate_usd"]
            if "RED" in ANOMALY_TIERS else DEFAULT_LABOR_RATE_USD_PER_HR
        )
        labor_subtotal = round(calculated_labor_hours * labor_rate, 2)
        tax_multiplier = float(self.tax_rates_by_state.get(home_state, 0.0))
        total_sales_tax = round(total_additional_materials_cost * tax_multiplier, 2)
        final_gross_repair_cost = round(
            total_additional_materials_cost + total_sales_tax + labor_subtotal, 2
        )

        return {
            "anomaly_ledger": damage_anomalies_log,
            "tier_counts": tier_counts,
            "financial_summary": {
                "base_materials_cost":      round(total_additional_materials_cost, 2),
                "sales_tax_applied":        total_sales_tax,
                "sales_tax_rate_locked":    round(tax_multiplier, 4),
                "allocated_labor_hours":    round(calculated_labor_hours, 2),
                "labor_blended_rate_usd":   round(labor_rate, 4),
                "labor_subtotal_usd":       labor_subtotal,
                "gross_combined_phase_cost": final_gross_repair_cost,
                "home_state":               home_state,
                "pricing_sources":          sorted(pricing_sources_seen),
            },
        }


# Process-local singleton.
ANOMALY_ENGINE = StructuralAnomalyEngine()
