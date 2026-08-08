"""
Sample high-fidelity Mission Package for Field Test validation.
Demonstrates geometry withholding, AWE findings, and full seal → report path.
"""

from __future__ import annotations

import json
from backend.nextgen.mission_package_seal import create_empty_package, seal_package
from backend.nextgen.mission_to_passport import prepare_for_governed_publish
from backend.nextgen.report_composer import compose_full_report

SAMPLE_ADDRESS_LINE = "1234 Appalachian Way"
SAMPLE_CITY_STATE_ZIP = "London, KY 40741"


def build_sample_package() -> dict:
    pkg = create_empty_package(
        mission_id="MISSION-2026-0801-FT-001",
        tenant_id="tenant-stratex-demo",
        property_id="prop-1234-infinity-orlando",
        capture_type="DAYTIME_PRECISION_MAPPING",
    )

    pkg["mission_metadata"].update({
        "aircraft": "DJI Matrice 4E",
        "pilot": "Anthony Cross",
        "weather": "Clear, 79°F",
        "rtk_status": "FIXED",
        "capture_date": "2026-08-01T14:30:00Z",
        "property_address_line": SAMPLE_ADDRESS_LINE,
        "property_city_state_zip": SAMPLE_CITY_STATE_ZIP,
    })

    pkg["evidence_manifest"]["items"] = [
        {
            "content_hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
            "media_type": "RGB",
            "capture_timestamp": "2026-08-01T14:32:00Z",
            "camera_model": "Matrice 4E Wide",
            "size_bytes": 12400000,
        },
        {
            "content_hash": "b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678",
            "media_type": "RGB",
            "capture_timestamp": "2026-08-01T14:33:15Z",
            "camera_model": "Matrice 4E Wide",
            "size_bytes": 11800000,
        },
    ]

    pkg["geometry_candidate"] = {
        "planes": [
            {"id": "roof-front-slope", "confidence": 0.94, "area_sqft": 820, "pitch": "6/12", "material": "architectural_shingle"},
            {"id": "roof-rear-slope", "confidence": 0.91, "area_sqft": 780, "pitch": "6/12", "material": "architectural_shingle"},
            {"id": "roof-left-hip", "confidence": 0.87, "area_sqft": 210, "pitch": "6/12"},
            {"id": "roof-right-hip", "confidence": 0.86, "area_sqft": 205, "pitch": "6/12"},
            {"id": "low-conf-valley", "confidence": 0.48, "area_sqft": 45},  # will be WITHHELD
        ],
        "measurements": {
            "total_roof_area_sqft": 2015,
            "ridge_length_ft": 48,
            "eave_length_ft": 112,
            "hip_length_ft": 36,
            "pitch_primary": "6/12",
        },
    }

    pkg["awe_candidate"] = {
        "findings": [
            {
                "id": "awe-001",
                "severity": "HIGH",
                "category": "ROOF",
                "description": "Moderate granule loss detected on front slope. Elevated risk of future leakage.",
                "location": "Roof - Front Slope",
                "truth_classification": "ESTIMATED",
                "estimated_repair_cost_usd": 1250,
                "impact": "18% elevated leak risk",
            },
            {
                "id": "awe-002",
                "severity": "MEDIUM",
                "category": "THERMAL",
                "description": "Heat-loss pattern consistent with attic insulation gap near ridge.",
                "location": "Attic / Ridge interface",
                "truth_classification": "ESTIMATED",
            },
            {
                "id": "awe-003",
                "severity": "MEDIUM",
                "category": "FLASHING",
                "description": "Flashing deterioration indicators at chimney penetration.",
                "location": "Chimney - North side",
                "truth_classification": "ESTIMATED",
            },
            {
                "id": "awe-004",
                "severity": "LOW",
                "category": "GUTTER",
                "description": "Minor debris accumulation pattern in front gutter run.",
                "location": "Front eave",
                "truth_classification": "ESTIMATED",
            },
        ]
    }

    return pkg


def sample_pipeline_kwargs(seal_key: bytes | None = None) -> dict:
    """Kwargs for run_single_path_pipeline using the field-test sample mission.

    When seal_key is omitted, the pipeline resolves MISSION_SEAL_KEY from the
    environment (or demo fallback with warning).
    """
    raw = build_sample_package()
    meta = raw.get("mission_metadata") or {}
    kwargs = {
        "mission_id": raw["mission_id"],
        "tenant_id": raw["tenant_id"],
        "property_id": raw["property_id"],
        "mission_type": "DAYTIME_PRECISION_MAPPING",
        "aircraft_profile": "Matrice_4E",
        "media_items": list((raw.get("evidence_manifest") or {}).get("items") or []),
        "geometry_candidate": raw.get("geometry_candidate"),
        "awe_candidate": raw.get("awe_candidate"),
        "pilot": meta.get("pilot"),
        "weather": meta.get("weather"),
        "rtk_status": meta.get("rtk_status", "FIXED"),
        "readiness_kwargs": {
            "battery_pct": 90.0,
            "pilot_authorized": True,
            "rtk_ready": True,
            "weather_ok": True,
        },
    }
    if seal_key is not None:
        kwargs["seal_key"] = seal_key
    return kwargs


def run_demo():
    """Seal → prepare → compose report → register Passport property + claim_code."""
    from backend.nextgen.passport_property_registry import register_sealed_mission

    raw = build_sample_package()
    sealed = seal_package(raw, seal_key=b"field-test-demo-key")
    handoff = prepare_for_governed_publish(sealed, seal_key=b"field-test-demo-key")
    report = compose_full_report(sealed)
    registration = register_sealed_mission(
        sealed,
        address_line=SAMPLE_ADDRESS_LINE,
        city_state_zip=SAMPLE_CITY_STATE_ZIP,
    )

    summary = {
        "package_id": sealed["package_id"],
        "content_hash": sealed["content_hash"][:16] + "...",
        "seal_valid": True,
        "planes_published": handoff["publication_request"]["payload"]["geometry_summary"]["plane_count"],
        "planes_withheld": handoff["publication_request"]["payload"]["geometry_summary"]["withheld_count"],
        "findings": len(sealed["awe_candidate"]["findings"]),
        "report_id": report["report_id"],
        "sections_present": list(report["sections"].keys()),
        "status": handoff["status"],
        "normalized_address": registration["normalized_address"]["normalized_display"],
        "claim_code": registration["claim_code"],
        "habitat_owner_exists": registration["habitat_owner_exists"],
    }
    print(json.dumps(summary, indent=2))
    return sealed, handoff, report, registration


if __name__ == "__main__":
    run_demo()
