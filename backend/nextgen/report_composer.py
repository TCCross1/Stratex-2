"""
Property Intelligence Report Composer — Expanded
Stratex Core — Field Test v1

Produces a full report structure matching the Comprehensive Property Report mockups.
Every numeric value and finding carries a truth classification.
Subsurface layers are never claimed as VERIFIED from exterior imagery alone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


TRUTH = ("VERIFIED", "ESTIMATED", "PROJECTED", "UNKNOWN", "WITHHELD")


def _t(value: Any, default: str = "UNKNOWN") -> str:
    return value if value in TRUTH else default


def compose_full_report(
    sealed_package: Dict[str, Any],
    passport_projection: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a complete Property Intelligence Report.
    """
    extra = extra or {}
    prop_id = sealed_package.get("property_id", "unknown")
    pkg_id = sealed_package.get("package_id")
    geometry = sealed_package.get("geometry_candidate", {})
    awe = sealed_package.get("awe_candidate", {})
    findings = awe.get("findings", [])

    # Filter withheld geometry
    planes = [p for p in geometry.get("planes", []) if p.get("truth_classification") != "WITHHELD"]
    withheld_planes = [p for p in geometry.get("planes", []) if p.get("truth_classification") == "WITHHELD"]

    critical = sum(1 for f in findings if f.get("severity") == "CRITICAL")
    high = sum(1 for f in findings if f.get("severity") == "HIGH")
    medium = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    low = sum(1 for f in findings if f.get("severity") == "LOW")

    # Scores — prefer Passport projection when present
    scores = {
        "property_score": {"value": None, "truth": "UNKNOWN"},
        "roof_condition": {"value": None, "truth": "UNKNOWN"},
        "energy_score": {"value": None, "truth": "UNKNOWN"},
        "moisture_score": {"value": None, "truth": "UNKNOWN"},
        "awe_index": {"value": None, "truth": "UNKNOWN"},
    }
    if passport_projection and "scores" in passport_projection:
        for k, v in passport_projection["scores"].items():
            if k in scores:
                scores[k] = v if isinstance(v, dict) else {"value": v, "truth": "PROJECTED"}

    # Materials list (placeholder structure — real takeoff comes from verified geometry)
    materials = extra.get("materials", [
        {"item": "Architectural Shingles", "qty": None, "unit": "SQ", "truth": "UNKNOWN"},
        {"item": "Roof Underlayment", "qty": None, "unit": "SQ", "truth": "PROJECTED"},
        {"item": "Ridge Vent", "qty": None, "unit": "LF", "truth": "ESTIMATED"},
        {"item": "Flashing", "qty": None, "unit": "LF", "truth": "ESTIMATED"},
    ])

    report = {
        "report_id": f"STRX-{str(prop_id)[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')}",
        "schema_version": "1.1.0",
        "property_id": prop_id,
        "package_id": pkg_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": {
            "source": "sealed_mission_package + passport_projection",
            "writer": "nextgen.passport_service.append_entry",
            "habitat_role": "read-only consumer of projections",
        },
        "sections": {
            "01_executive_summary": {
                "scores": scores,
                "findings_counts": {
                    "critical": critical,
                    "high": high,
                    "medium": medium,
                    "low": low,
                },
                "digital_twin_completeness": "Exterior" if planes else "Incomplete",
                "notes": "All scores carry truth classification. Subsurface layers are candidate only.",
            },
            "02_3d_digital_twin_overview": {
                "status": "available" if planes else "incomplete",
                "plane_count": len(planes),
                "withheld_plane_count": len(withheld_planes),
                "truth": "VERIFIED" if planes else "UNKNOWN",
            },
            "03_cad_bim_overall": {
                "status": "candidate",
                "truth": "PROJECTED",
                "note": "Full CAD/BIM export available only after geometry is VERIFIED.",
            },
            "04_cad_bim_structural": {
                "status": "candidate",
                "truth": "PROJECTED",
                "note": "Framing inferred from exterior geometry only. Not verified.",
            },
            "05_cad_bim_thermal": {
                "findings": findings,
                "truth": "ESTIMATED",
                "note": "Thermal patterns are surface indicators. Require confirmation for moisture claims.",
            },
            "06_framing_layer": {
                "status": "candidate_model",
                "truth": "PROJECTED",
                "note": "Not directly observable from exterior drone imagery.",
            },
            "07_sheathing_layer": {
                "status": "candidate_model",
                "truth": "PROJECTED",
            },
            "08_decking_layer": {
                "status": "candidate_model",
                "truth": "PROJECTED",
            },
            "09_roofing_layer": {
                "planes": planes,
                "measurements": geometry.get("measurements", {}),
                "truth": "VERIFIED" if planes else "UNKNOWN",
            },
            "10_system_health_thermal": {
                "awe_index": scores.get("awe_index"),
                "energy_score": scores.get("energy_score"),
                "moisture_score": scores.get("moisture_score"),
                "findings": findings,
            },
            "11_window_schedule": extra.get("window_schedule", []),
            "12_door_schedule": extra.get("door_schedule", []),
            "13_energy_efficiency": {
                "score": scores.get("energy_score"),
                "truth": _t(scores.get("energy_score", {}).get("truth")),
            },
            "14_ventilation_report": extra.get("ventilation", {}),
            "15_materials_list": materials,
            "16_labor_report": extra.get("labor", {
                "total_hours": None,
                "total_cost": None,
                "truth": "PROJECTED",
                "note": "Planning figures only until verified takeoff.",
            }),
            "17_found_damages": findings,
            "18_maintenance_priority_list": sorted(
                findings,
                key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
                    f.get("severity"), 9
                ),
            ),
        },
        "deliverables": [
            "Interactive 3D Digital Twin (Habitat)",
            "CAD/BIM files (when geometry VERIFIED)",
            "High-resolution imagery package",
            "Detailed Inspection Report (PDF)",
            "Materials & Labor Estimate",
            "Maintenance Roadmap",
            "Property Passport entry (hash-chained)",
        ],
    }
    return report
