"""
Integration-style tests for Mission → Passport handoff
"""

import pytest
from backend.nextgen.mission_package_seal import create_empty_package, seal_package
from backend.nextgen.mission_to_passport import prepare_for_governed_publish, HandoffError


def test_full_seal_and_prepare_flow():
    raw = create_empty_package(
        mission_id="mission-ft-001",
        tenant_id="tenant-demo",
        property_id="prop-orlando-001",
        capture_type="DAYTIME_PRECISION_MAPPING",
    )
    raw["geometry_candidate"]["planes"] = [
        {"id": "ridge-1", "confidence": 0.94, "area_sqft": 420},
        {"id": "eave-front", "confidence": 0.88, "length_ft": 48},
        {"id": "low-conf", "confidence": 0.52, "area_sqft": 12},  # should withhold
    ]
    raw["awe_candidate"]["findings"] = [
        {
            "id": "f1",
            "severity": "HIGH",
            "description": "Granule loss pattern on front slope",
            "truth_classification": "ESTIMATED",
        }
    ]

    result = prepare_for_governed_publish(raw, seal_key=b"test-key-ft")

    assert result["status"] == "READY_FOR_GOVERNED_PUBLISH"
    assert result["sealed_package"]["seal_record"]["signature"]
    assert result["publication_request"]["source_type"] == "mission_package"
    assert result["publication_request"]["entry_type"] == "MISSION_EVIDENCE"
    assert result["publication_request"]["idempotency_key"].startswith("mission_package:")

    # Withheld plane must not be counted in geometry_summary
    summary = result["publication_request"]["payload"]["geometry_summary"]
    assert summary["plane_count"] == 2
    assert summary["withheld_count"] == 1


def test_already_sealed_package_is_verified():
    raw = create_empty_package("m2", "t1", "p1")
    sealed = seal_package(raw, seal_key=b"test-key-ft")
    result = prepare_for_governed_publish(sealed, seal_key=b"test-key-ft")
    assert result["status"] == "READY_FOR_GOVERNED_PUBLISH"
