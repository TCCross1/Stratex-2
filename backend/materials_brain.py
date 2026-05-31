"""STRATEX™ — Materials Matrix Engine (Contractor Business Brain)

Configuration database tracking roofing, siding, and gutter specifications,
plus deterministic Bill-of-Materials (BOM) compute kernels.

Pure addition (preservation lock). Roofing BOM remains owned by
`routes/branch_console.py` and `routes/materials_config.py`; this module
adds the **siding** + **gutter** surface only.

Author's verbatim spec preserved in `MaterialsMatrixEngine` below; minimal
composite + wood scaffolding stubs added per main-agent build directive
(2026-05-31, marked inline).
"""
from __future__ import annotations

from typing import Any, Dict, List


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

        # --- SCAFFOLDING (2026-05-31) — minimal composite + wood BOM stubs.
        # Clearly marked as starter lines; tune coefficients in a later pass.
        elif material_class == "composite":
            # Hardie/LP boards are typically 12ft × 8.25" (~8.25 sqft/board).
            board_count = int((wall_square_footage / 8.25) * 1.07)  # 7% waste
            bom_list.append({"item": "Composite Fiber-Cement Lap Board (12ft)", "quantity": board_count, "unit": "BOARDS", "scaffold": True})
            bom_list.append({"item": "Standard Housewrap Roll", "quantity": int(wall_square_footage / 1000) + 1, "unit": "ROLLS", "scaffold": True})
            bom_list.append({"item": "1.75 Inch Stainless Siding Nails", "quantity": int(wall_square_footage * 6), "unit": "COUNT", "scaffold": True})
            bom_list.append({"item": "Color-Matched Sealant Tube", "quantity": int(wall_square_footage / 250) + 1, "unit": "TUBES", "scaffold": True})

        elif material_class == "wood":
            # Tongue-and-groove planks ~6" wide × 8ft = 4 sqft/plank.
            plank_count = int((wall_square_footage / 4.0) * 1.10)  # 10% waste (wood splits more)
            bom_list.append({"item": "Tongue-and-Groove Wood Plank (8ft)", "quantity": plank_count, "unit": "PLANKS", "scaffold": True})
            bom_list.append({"item": "Building Felt Roll (15lb)", "quantity": int(wall_square_footage / 400) + 1, "unit": "ROLLS", "scaffold": True})
            bom_list.append({"item": "8d Galvanized Ring-Shank Nails", "quantity": int(wall_square_footage * 5), "unit": "COUNT", "scaffold": True})
            bom_list.append({"item": "Penetrating Wood Sealer (1gal)", "quantity": int(wall_square_footage / 150) + 1, "unit": "GALLONS", "scaffold": True})

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
    # GUTTER BOM (scaffolding hook — main-agent stub for future expansion)
    # ------------------------------------------------------------------ #
    def compute_gutter_bill_of_materials(
        self,
        linear_footage: float,
        size: str,
        style: str,
        material_class: str,
        downspout_count: int,
    ) -> Dict[str, Any]:
        """Minimal gutter BOM. Marked `scaffold=True` so the contractor UI
        can render an 'Engineering Preview' badge until tuned."""
        bom_list: List[Dict[str, Any]] = []
        section_len = 10.0  # standard stock length in feet
        section_count = int((linear_footage / section_len) * 1.05)  # 5% waste
        unit_name = "ALUMINUM" if material_class == "aluminum" else "COPPER"
        bom_list.append({"item": f"{size.replace('_', ' ')} {style.replace('_', ' ')} {unit_name} Gutter (10ft)", "quantity": section_count, "unit": "SECTIONS", "scaffold": True})
        bom_list.append({"item": f"{size.replace('_', ' ')} Hidden Hangers", "quantity": int(linear_footage / 2) + 1, "unit": "COUNT", "scaffold": True})
        bom_list.append({"item": "Downspout Elbows", "quantity": downspout_count * 2, "unit": "COUNT", "scaffold": True})
        bom_list.append({"item": "Downspout Sections (10ft)", "quantity": downspout_count * 2, "unit": "SECTIONS", "scaffold": True})
        bom_list.append({"item": "End Caps (LR pair)", "quantity": max(1, int(linear_footage / 60)), "unit": "PAIRS", "scaffold": True})
        bom_list.append({"item": "Gutter Sealant Tube", "quantity": int(linear_footage / 100) + 1, "unit": "TUBES", "scaffold": True})
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


# Process-local singleton — matches the pattern used by RegionalSwitchboard.
MATERIALS_BRAIN = MaterialsMatrixEngine()
