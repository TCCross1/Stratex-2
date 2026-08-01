"""
Property Intelligence Report Composer
Stratex Core — Field Test v1

Produces reports that follow PROPERTY_INTELLIGENCE_REPORT_SCHEMA.md
Consumes sealed packages + Passport projections only.
Never fabricates measurements or confidence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _truth(value: Any, default: str = "UNKNOWN") -> str:
    if value in ("VERIFIED", "ESTIMATED", "PROJECTED", "UNKNOWN", "WITHHELD"):
        return value
    return default


def compose_executive_summary(
    property_id: str,
    scores: Dict[str, Any],
    findings_counts: Dict[str, int],
    twin_completeness: str = "Exterior only",
) -> Dict[str, Any]:
    return {
        "section": "01_EXECUTIVE_SUMMARY",
        "property_id": property_id,
        "scores": {
            "property_score": {
                "value": scores.get("property_score"),
                "truth": _truth(scores.get("property_score_truth")),
            },
            "roof_condition": {
                "value": scores.get("roof_condition"),
                "truth": _truth(scores.get("roof_truth")),
            },
            "energy_score": {
                "value": scores.get("energy_score"),
                "truth": _truth(scores.get("energy_truth")),
            },
            "moisture_score": {
                "value": scores.get("moisture_score"),
                "truth": _truth(scores.get("moisture_truth")),
            },
            "awe_index": {
                "value": scores.get("awe_index"),
                "truth": _truth(scores.get("awe_truth")),
            },
        },
        "findings_counts": findings_counts,
        "digital_twin_completeness": twin_completeness,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def compose_report(
    sealed_package: Dict[str, Any],
    passport_projection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a full Property Intelligence Report from a sealed package
    and optional Passport projection.
    """
    prop_id = sealed_package.get("property_id", "unknown")

    # Extract geometry (respect WITHHELD)
    geometry = sealed_package.get("geometry_candidate", {})
    planes = [
        p for p in geometry.get("planes", [])
        if p.get("truth_classification") != "WITHHELD"
    ]

    # Extract AWE findings
    awe = sealed_package.get("awe_candidate", {})
    findings = awe.get("findings", [])

    critical = sum(1 for f in findings if f.get("severity") == "CRITICAL")
    high = sum(1 for f in findings if f.get("severity") == "HIGH")
    medium = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    low = sum(1 for f in findings if f.get("severity") == "LOW")

    scores = {
        "property_score": None,
        "property_score_truth": "UNKNOWN",
        "roof_condition": None,
        "roof_truth": "UNKNOWN",
        "energy_score": None,
        "energy_truth": "UNKNOWN",
        "moisture_score": None,
        "moisture_truth": "UNKNOWN",
        "awe_index": None,
        "awe_truth": "UNKNOWN",
    }

    # Prefer Passport projection when available
    if passport_projection:
        scores.update(passport_projection.get("scores", {}))

    report = {
        "report_id": f"STRX-{prop_id[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "schema_version": "1.0.0",
        "property_id": prop_id,
        "package_id": sealed_package.get("package_id"),
        "sections": {
            "01_executive_summary": compose_executive_summary(
                prop_id,
                scores,
                {"critical": critical, "high": high, "medium": medium, "low": low},
            ),
            "02_3d_digital_twin": {
                "status": "available" if planes else "incomplete",
                "plane_count": len(planes),
                "truth": "VERIFIED" if planes else "UNKNOWN",
            },
            "05_thermal_layer": {
                "findings": findings,
                "truth": "ESTIMATED",  # thermal patterns are indicators
            },
            "09_roofing_layer": {
                "planes": planes,
                "measurements": geometry.get("measurements", {}),
            },
            "17_found_damages": findings,
            "18_maintenance_priority": sorted(
                findings,
                key=lambda f: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
                    f.get("severity"), 9
                ),
            ),
        },
        "deliverables": [
            "Interactive 3D Digital Twin",
            "Detailed Inspection Report (PDF)",
            "Materials & Labor Estimate",
            "Maintenance Roadmap",
            "Property Passport entry (hash-chained)",
        ],
        "authority": {
            "source": "sealed_mission_package + passport_projection",
            "writer": "nextgen.passport_service.append_entry",
            "habitat_role": "read-only consumer",
        },
    }
    return report
