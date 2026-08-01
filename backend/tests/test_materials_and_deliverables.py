"""Tests for materials takeoff and deliverables package"""

from backend.nextgen.materials_takeoff import takeoff_from_geometry, labor_estimate_from_squares
from backend.nextgen.deliverables_package import build_contractor_deliverables


def test_takeoff_computes_squares():
    geo = {
        "planes": [
            {"id": "a", "confidence": 0.9, "area_sqft": 500},
            {"id": "b", "confidence": 0.9, "area_sqft": 500},
            {"id": "c", "confidence": 0.3, "area_sqft": 50, "truth_classification": "WITHHELD"},
        ],
        "measurements": {
            "total_roof_area_sqft": 1000,
            "ridge_length_ft": 40,
            "eave_length_ft": 80,
        },
    }
    t = takeoff_from_geometry(geo)
    assert t["basis"]["roof_area_sqft"] == 1000
    assert t["basis"]["squares_with_waste"] == 11.0  # 10 * 1.1
    shingles = next(i for i in t["materials"] if i["item"] == "Architectural Shingles")
    assert shingles["qty"] == 11.0
    assert shingles["truth"] == "ESTIMATED"


def test_labor_estimate():
    lab = labor_estimate_from_squares(11.0)
    assert lab["total_hours"] == 44.0
    assert lab["truth"] == "PROJECTED"


def test_deliverables_package_ready():
    result = build_contractor_deliverables(
        mission_id="m-del-1",
        tenant_id="t1",
        property_id="p1",
        geometry_candidate={
            "planes": [
                {"id": "front", "confidence": 0.94, "area_sqft": 800},
            ],
            "measurements": {"total_roof_area_sqft": 800, "ridge_length_ft": 30, "eave_length_ft": 60},
        },
        awe_candidate={
            "findings": [
                {
                    "id": "f1",
                    "severity": "HIGH",
                    "description": "Test finding",
                    "truth_classification": "ESTIMATED",
                }
            ]
        },
        seal_key=b"test-del-key",
        readiness_kwargs={"battery_pct": 95.0},
    )
    assert result["status"] == "READY"
    assert result["report"]["report_id"]
    assert result["materials_takeoff"]["materials"]
    assert result["html"]["contractor"]
    assert "STRATEX" in result["html"]["contractor"]
    assert result["publication_request"] is not None
