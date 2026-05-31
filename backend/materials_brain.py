"""STRATEX™ — Materials Matrix Engine (Contractor Business Brain)

Configuration database tracking roofing, siding, and gutter specifications,
plus deterministic Bill-of-Materials (BOM) compute kernels.

Pure addition (preservation lock). Roofing PRICING remains owned by
`routes/branch_console.py` (full 4-agent quantify pipeline) and roofing
CONFIG by `routes/materials_config.py`; this module adds **siding** +
**gutters** + a quantities-only **roofing scaffold** that stitches them
into a single Job Wizard envelope.

Author's verbatim spec preserved in `MaterialsMatrixEngine` below; minimal
composite + wood scaffolding stubs added per main-agent build directive
(2026-05-31, marked inline).

v3.32.0 (2026-05-31) — Locked starter coefficients (`_SCAFFOLD_COEFFS`)
and added `compute_envelope_bill_of_materials()` for single-call Job
Wizard rollups (roof + walls + gutters in one request).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# =============================================================================
# LOCKED SCAFFOLD COEFFICIENTS — v3.32.0 field-test baseline.
# Marked `scaffold:true` on every BOM line that uses these. Replace with
# field-measured values once Anthony's crews log enough installs to
# regress real waste / coverage rates. DO NOT change values without a
# corresponding test update.
# =============================================================================
_SCAFFOLD_COEFFS: Dict[str, Dict[str, float]] = {
    # ----- ROOFING (quantities-only scaffold; pricing lives in branch_console)
    "roofing": {
        "waste_multiplier":            1.10,   # 10% waste on shingles
        "felt_sq_per_roll":            4.0,    # 1 roll covers 4 squares
        "iws_linear_ft_per_roll":      50.0,
        "drip_edge_ft_per_piece":      10.0,
        "chimney_kit_per_job":         1,
        "nails_box_per_job":           2,
        "caps_box_per_job":            1,
    },
    # ----- SIDING (composite + wood — vinyl path stays user-authored verbatim)
    "siding_composite": {
        "board_coverage_sqft":         8.25,   # 12ft × 8.25" Hardie/LP board
        "waste_factor":                1.07,
        "housewrap_sqft_per_roll":     1000.0,
        "nails_per_sqft":              6.0,
        "sealant_sqft_per_tube":       250.0,
    },
    "siding_wood": {
        "plank_coverage_sqft":         4.0,    # 8ft × 6" T&G plank
        "waste_factor":                1.10,
        "felt_sqft_per_roll":          400.0,
        "nails_per_sqft":              5.0,
        "sealer_sqft_per_gallon":      150.0,
    },
    # ----- GUTTERS
    "gutter": {
        "section_length_ft":           10.0,
        "section_waste_factor":        1.05,
        "hanger_spacing_ft":           2.0,
        "elbows_per_downspout":        2,
        "downspout_sections_per_run":  2,
        "endcap_pair_per_60ft":        1,
        "sealant_ft_per_tube":         100.0,
    },
}


class MaterialsMatrixEngine:
    """Configuration database tracking roofing, siding, and gutter specifications."""

    def __init__(self):
        self.matrix: Dict[str, Dict[str, Any]] = {
            "roofing": {},
            "siding": {
                "composite": {
                    "brands": ["JamesHardie", "LP_SmartSide"],
                    "styles": ["Lap", "Vertical"],
                    "colors": ["Slate", "Sage"],
                },
                "vinyl": {
                    "brands": ["CertainTeed", "Mastic"],
                    "styles": ["Straight_Lap", "Dutch_Lap", "Shakes", "Wainscoting"],
                    "colors": ["White", "Beige", "Gray"],
                    "accessories": [
                        "Starter_Strips",
                        "J_Channel",
                        "Outside_Corner_Post",
                        "Undersill_Trim",
                    ],
                },
                "wood": {
                    "brands": ["Millwork_Local"],
                    "styles": [
                        "Pine_Tongue_And_Groove",
                        "Cedar_Beaded",
                        "Half_Log",
                    ],
                    "colors": ["Natural"],
                },
            },
            "gutters": {
                "aluminum": {
                    "sizes": ["5_Inch", "6_Inch"],
                    "styles": ["K_Style", "Half_Round"],
                    "colors": ["White", "Bronze"],
                },
                "copper": {
                    "sizes": ["6_Inch"],
                    "styles": ["Half_Round"],
                    "colors": ["Raw_Copper"],
                },
            },
        }

    # ------------------------------------------------------------------ #
    # SIDING BOM
    # ------------------------------------------------------------------ #
    def compute_siding_bill_of_materials(
        self,
        wall_square_footage: float,
        style_type: str,
        material_class: str,
        use_foam_insulation: bool,
        use_foil_face: bool,
    ) -> Dict[str, Any]:
        bom_list: List[Dict[str, Any]] = []
        osb_sheets = int((wall_square_footage / 32) * 1.05)
        bom_list.append({"item": "7/16 OSB Sheathing", "quantity": osb_sheets, "unit": "SHEETS"})

        if material_class == "vinyl":
            if use_foam_insulation:
                insulation_units = int((wall_square_footage / 32) * 1.02)
                item_name = (
                    "1 Inch Aluminum-Faced Foam Board"
                    if use_foil_face
                    else "1 Inch Standard Foam Underlayment"
                )
                bom_list.append({"item": item_name, "quantity": insulation_units, "unit": "SHEETS"})
                bom_list.append({"item": "2 Inch Galvanized Roofing Nails", "quantity": int(wall_square_footage * 4), "unit": "COUNT"})
                bom_list.append({"item": "Seam Tape", "quantity": int(wall_square_footage / 100) + 1, "unit": "ROLLS"})
                bom_list.append({"item": "Button Cap Nails", "quantity": int(wall_square_footage * 2), "unit": "COUNT"})
            else:
                bom_list.append({"item": "Standard Housewrap Roll", "quantity": int(wall_square_footage / 1000) + 1, "unit": "ROLLS"})
                bom_list.append({"item": "1.25 Inch Hand-Drive Galvanized Nails", "quantity": int(wall_square_footage * 4), "unit": "COUNT"})

        # --- SCAFFOLDING (v3.32.0 — coefficients locked in _SCAFFOLD_COEFFS).
        elif material_class == "composite":
            c = _SCAFFOLD_COEFFS["siding_composite"]
            board_count = int((wall_square_footage / c["board_coverage_sqft"]) * c["waste_factor"])
            bom_list.append({"item": "Composite Fiber-Cement Lap Board (12ft)", "quantity": board_count, "unit": "BOARDS", "scaffold": True})
            bom_list.append({"item": "Standard Housewrap Roll", "quantity": int(wall_square_footage / c["housewrap_sqft_per_roll"]) + 1, "unit": "ROLLS", "scaffold": True})
            bom_list.append({"item": "1.75 Inch Stainless Siding Nails", "quantity": int(wall_square_footage * c["nails_per_sqft"]), "unit": "COUNT", "scaffold": True})
            bom_list.append({"item": "Color-Matched Sealant Tube", "quantity": int(wall_square_footage / c["sealant_sqft_per_tube"]) + 1, "unit": "TUBES", "scaffold": True})

        elif material_class == "wood":
            c = _SCAFFOLD_COEFFS["siding_wood"]
            plank_count = int((wall_square_footage / c["plank_coverage_sqft"]) * c["waste_factor"])
            bom_list.append({"item": "Tongue-and-Groove Wood Plank (8ft)", "quantity": plank_count, "unit": "PLANKS", "scaffold": True})
            bom_list.append({"item": "Building Felt Roll (15lb)", "quantity": int(wall_square_footage / c["felt_sqft_per_roll"]) + 1, "unit": "ROLLS", "scaffold": True})
            bom_list.append({"item": "8d Galvanized Ring-Shank Nails", "quantity": int(wall_square_footage * c["nails_per_sqft"]), "unit": "COUNT", "scaffold": True})
            bom_list.append({"item": "Penetrating Wood Sealer (1gal)", "quantity": int(wall_square_footage / c["sealer_sqft_per_gallon"]) + 1, "unit": "GALLONS", "scaffold": True})

        return {
            "calculated_bom": bom_list,
            "inputs": {
                "wall_square_footage": wall_square_footage,
                "style_type": style_type,
                "material_class": material_class,
                "use_foam_insulation": use_foam_insulation,
                "use_foil_face": use_foil_face,
            },
        }

    # ------------------------------------------------------------------ #
    # GUTTER BOM (scaffold — locked coefficients)
    # ------------------------------------------------------------------ #
    def compute_gutter_bill_of_materials(
        self,
        linear_footage: float,
        size: str,
        style: str,
        material_class: str,
        downspout_count: int,
    ) -> Dict[str, Any]:
        c = _SCAFFOLD_COEFFS["gutter"]
        bom_list: List[Dict[str, Any]] = []
        section_count = int((linear_footage / c["section_length_ft"]) * c["section_waste_factor"])
        unit_name = "ALUMINUM" if material_class == "aluminum" else "COPPER"
        bom_list.append({"item": f"{size.replace('_', ' ')} {style.replace('_', ' ')} {unit_name} Gutter (10ft)", "quantity": section_count, "unit": "SECTIONS", "scaffold": True})
        bom_list.append({"item": f"{size.replace('_', ' ')} Hidden Hangers", "quantity": int(linear_footage / c["hanger_spacing_ft"]) + 1, "unit": "COUNT", "scaffold": True})
        bom_list.append({"item": "Downspout Elbows", "quantity": downspout_count * int(c["elbows_per_downspout"]), "unit": "COUNT", "scaffold": True})
        bom_list.append({"item": "Downspout Sections (10ft)", "quantity": downspout_count * int(c["downspout_sections_per_run"]), "unit": "SECTIONS", "scaffold": True})
        bom_list.append({"item": "End Caps (LR pair)", "quantity": max(int(c["endcap_pair_per_60ft"]), int(linear_footage / 60)), "unit": "PAIRS", "scaffold": True})
        bom_list.append({"item": "Gutter Sealant Tube", "quantity": int(linear_footage / c["sealant_ft_per_tube"]) + 1, "unit": "TUBES", "scaffold": True})
        return {
            "calculated_bom": bom_list,
            "inputs": {
                "linear_footage": linear_footage,
                "size": size,
                "style": style,
                "material_class": material_class,
                "downspout_count": downspout_count,
            },
        }

    # ------------------------------------------------------------------ #
    # ROOFING BOM — quantities-only scaffold for the envelope endpoint.
    # Pricing/labor/4-agent verification still lives in branch_console.
    # ------------------------------------------------------------------ #
    def compute_roofing_bill_of_materials(
        self,
        roof_square_footage: float,
        valleys_ft: float = 0.0,
        perimeter_ft: float = 0.0,
        pitch_multiplier: float = 1.0,
        flashing_ft: float = 0.0,
    ) -> Dict[str, Any]:
        c = _SCAFFOLD_COEFFS["roofing"]
        import math
        adjusted_sqft = roof_square_footage * pitch_multiplier
        roof_squares_net = adjusted_sqft / 100.0
        roof_squares_with_waste = roof_squares_net * c["waste_multiplier"]

        bom_list: List[Dict[str, Any]] = []
        bom_list.append({"item": "Premium Architectural Shingles", "quantity": math.ceil(roof_squares_with_waste), "unit": "SQUARES", "scaffold": True})
        bom_list.append({"item": "Synthetic Felt #15", "quantity": math.ceil(adjusted_sqft / (c["felt_sq_per_roll"] * 100)), "unit": "ROLLS", "scaffold": True})
        if valleys_ft > 0:
            bom_list.append({"item": "Ice & Water Shield", "quantity": math.ceil(valleys_ft / c["iws_linear_ft_per_roll"]), "unit": "ROLLS", "scaffold": True})
        if perimeter_ft > 0:
            bom_list.append({"item": "Drip Edge (10ft pieces)", "quantity": math.ceil(perimeter_ft / c["drip_edge_ft_per_piece"]), "unit": "PIECES", "scaffold": True})
        if flashing_ft > 0:
            bom_list.append({"item": "Wall Counter/Step Flashing", "quantity": flashing_ft, "unit": "LINEAR_FT", "scaffold": True})
        bom_list.append({"item": "Chimney Flashing & Caulk Combo Pack", "quantity": int(c["chimney_kit_per_job"]), "unit": "KITS", "scaffold": True})
        bom_list.append({"item": "Coil Roofing Fasteners", "quantity": int(c["nails_box_per_job"]), "unit": "BOXES", "scaffold": True})
        bom_list.append({"item": "Plastic Button Cap Nails", "quantity": int(c["caps_box_per_job"]), "unit": "BOXES", "scaffold": True})
        return {
            "calculated_bom": bom_list,
            "inputs": {
                "roof_square_footage": roof_square_footage,
                "valleys_ft": valleys_ft,
                "perimeter_ft": perimeter_ft,
                "pitch_multiplier": pitch_multiplier,
                "flashing_ft": flashing_ft,
            },
        }

    # ------------------------------------------------------------------ #
    # ENVELOPE BOM — single-call Job Wizard rollup (roof + walls + gutters)
    # ------------------------------------------------------------------ #
    def compute_envelope_bill_of_materials(
        self,
        roofing: Optional[Dict[str, Any]] = None,
        siding: Optional[Dict[str, Any]] = None,
        gutter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Stitch roofing + siding + gutter BOMs into one envelope rollup.

        Each section is optional — pass None / omit to skip that scope.
        Returns a unified structure with per-section BOMs + a flat
        `envelope_lines` array (every line tagged with `scope`) for easy
        rendering in the Job Wizard.
        """
        sections: Dict[str, Any] = {}
        envelope_lines: List[Dict[str, Any]] = []
        scopes_included: List[str] = []

        if roofing:
            r = self.compute_roofing_bill_of_materials(**roofing)
            sections["roofing"] = r
            scopes_included.append("roofing")
            for line in r["calculated_bom"]:
                envelope_lines.append({**line, "scope": "roofing"})

        if siding:
            s = self.compute_siding_bill_of_materials(**siding)
            sections["siding"] = s
            scopes_included.append("siding")
            for line in s["calculated_bom"]:
                envelope_lines.append({**line, "scope": "siding"})

        if gutter:
            g = self.compute_gutter_bill_of_materials(**gutter)
            sections["gutter"] = g
            scopes_included.append("gutter")
            for line in g["calculated_bom"]:
                envelope_lines.append({**line, "scope": "gutter"})

        return {
            "scopes_included": scopes_included,
            "sections": sections,
            "envelope_lines": envelope_lines,
            "line_count": len(envelope_lines),
            "scaffold_line_count": sum(1 for ln in envelope_lines if ln.get("scaffold")),
        }


# Process-local singleton — matches the pattern used by RegionalSwitchboard.
MATERIALS_BRAIN = MaterialsMatrixEngine()
