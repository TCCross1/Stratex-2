"""Tests for Field Test Pipeline orchestrator"""

from backend.nextgen.field_test_pipeline import (
    run_single_path_pipeline,
    run_dual_path_pipeline,
)
from backend.nextgen.evidence_ingest import ingest_media_item


def test_single_path_success():
    result = run_single_path_pipeline(
        mission_id="m-single-1",
        tenant_id="t1",
        property_id="p1",
        mission_type="DAYTIME_PRECISION_MAPPING",
        media_items=[
            ingest_media_item("RGB", "2026-08-01T12:00:00Z", "Matrice 4E Wide", 8_000_000),
        ],
        geometry_candidate={
            "planes": [
                {"id": "a", "confidence": 0.95, "area_sqft": 500},
                {"id": "b", "confidence": 0.40, "area_sqft": 20},
            ]
        },
        seal_key=b"test-pipeline-key",
        readiness_kwargs={"battery_pct": 85.0},
    )
    assert result.success is True
    assert result.sealed_package is not None
    assert result.publication_request is not None
    assert result.report is not None
    assert result.report.get("report_id")
    # low confidence plane withheld
    summary = result.publication_request["payload"]["geometry_summary"]
    assert summary["withheld_count"] >= 1


def test_single_path_readiness_blocks():
    result = run_single_path_pipeline(
        mission_id="m-blocked",
        tenant_id="t1",
        property_id="p1",
        seal_key=b"test-pipeline-key",
        readiness_kwargs={"battery_pct": 10.0},
        skip_readiness=False,
    )
    assert result.success is False
    assert any("ATC not ready" in e for e in result.errors)


def test_dual_path_pair():
    result = run_dual_path_pipeline(
        mapping_mission_id="m-4e",
        awe_mission_id="m-4t",
        tenant_id="t1",
        property_id="p1",
        seal_key=b"test-pipeline-key",
        readiness_kwargs={"battery_pct": 90.0},
    )
    assert result["both_sealed"] is True
    assert result["mapping"]["success"] is True
    assert result["awe"]["success"] is True
