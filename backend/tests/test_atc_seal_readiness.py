"""Unit tests for pre-seal ATC readiness (Matrice 4E / 4T)."""

from backend.nextgen.atc.seal_readiness import (
    DAYTIME_MAPPING,
    MATRICE_4E,
    MATRICE_4T,
    NIGHTTIME_AWE,
    evaluate_seal_readiness,
)
from backend.nextgen.evidence_ingest import assemble_package_from_capture, ingest_media_item
from backend.nextgen.field_test_pipeline import run_single_path_pipeline


def _package_4e(**overrides):
    pkg = assemble_package_from_capture(
        mission_id="m-4e",
        tenant_id="t1",
        property_id="p1",
        capture_type=DAYTIME_MAPPING,
        media_items=[
            ingest_media_item("RGB", "2026-08-01T14:00:00Z", "Matrice 4E Wide", 8_000_000),
        ],
        aircraft="DJI Matrice 4E",
        geometry_candidate={"planes": [{"id": "a", "confidence": 0.9, "area_sqft": 100}]},
    )
    pkg.update(overrides)
    return pkg


def _package_4t(**overrides):
    pkg = assemble_package_from_capture(
        mission_id="m-4t",
        tenant_id="t1",
        property_id="p1",
        capture_type=NIGHTTIME_AWE,
        media_items=[
            ingest_media_item("THERMAL", "2026-08-01T22:00:00Z", "Matrice 4T Thermal", 3_000_000),
        ],
        aircraft="DJI Matrice 4T",
        awe_candidate={"findings": [{"id": "f1", "severity": "LOW", "truth_classification": "ESTIMATED"}]},
    )
    pkg.update(overrides)
    return pkg


def test_4e_day_rgb_checklist_passes():
    report = evaluate_seal_readiness(
        _package_4e(),
        aircraft_profile=MATRICE_4E,
        mission_type=DAYTIME_MAPPING,
    )
    assert report.ready is True
    assert report.blocking_failures == []


def test_4t_night_thermal_checklist_passes():
    report = evaluate_seal_readiness(
        _package_4t(),
        aircraft_profile=MATRICE_4T,
        mission_type=NIGHTTIME_AWE,
    )
    assert report.ready is True


def test_4e_missing_rgb_fails():
    pkg = _package_4e()
    pkg["evidence_manifest"]["items"] = [
        ingest_media_item("THERMAL", "2026-08-01T14:00:00Z", "Wrong sensor", 1_000_000),
    ]
    report = evaluate_seal_readiness(
        pkg,
        aircraft_profile=MATRICE_4E,
        mission_type=DAYTIME_MAPPING,
    )
    assert report.ready is False
    assert "required_evidence_media" in report.blocking_failures


def test_4e_wrong_mission_type_fails():
    report = evaluate_seal_readiness(
        _package_4e(),
        aircraft_profile=MATRICE_4E,
        mission_type=NIGHTTIME_AWE,
    )
    assert report.ready is False
    assert "mission_type_profile" in report.blocking_failures


def test_pipeline_blocks_seal_when_checklist_fails():
    result = run_single_path_pipeline(
        mission_id="m-bad-media",
        tenant_id="t1",
        property_id="p1",
        mission_type=DAYTIME_MAPPING,
        aircraft_profile=MATRICE_4E,
        media_items=[
            ingest_media_item("THERMAL", "2026-08-01T14:00:00Z", "Wrong", 1_000_000),
        ],
        geometry_candidate={"planes": [{"id": "a", "confidence": 0.9, "area_sqft": 50}]},
        seal_key=b"test-key",
        readiness_kwargs={"battery_pct": 90.0},
    )
    assert result.success is False
    assert result.sealed_package is None
    assert result.seal_readiness is not None
    assert result.seal_readiness["ready"] is False
    assert any("Pre-seal ATC checklist failed" in e for e in result.errors)
