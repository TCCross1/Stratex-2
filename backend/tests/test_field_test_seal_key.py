"""Tests for field-test MISSION_SEAL_KEY resolution."""

import os

import pytest

from backend.nextgen.field_test_seal_key import (
    DEMO_SEAL_KEY,
    reset_demo_key_warning_for_tests,
    resolve_field_test_seal_key,
)


@pytest.fixture(autouse=True)
def _reset_warning_flag():
    reset_demo_key_warning_for_tests()
    yield
    reset_demo_key_warning_for_tests()


def test_resolve_uses_mission_seal_key_from_env(monkeypatch):
    monkeypatch.setenv("MISSION_SEAL_KEY", "field-test-secret-from-env")
    key, source = resolve_field_test_seal_key(warn_on_fallback=False)
    assert key == b"field-test-secret-from-env"
    assert source == "env"


def test_resolve_falls_back_to_demo_key_with_warning(monkeypatch, capsys):
    monkeypatch.delenv("MISSION_SEAL_KEY", raising=False)
    key, source = resolve_field_test_seal_key()
    assert key == DEMO_SEAL_KEY
    assert source == "demo_fallback"
    captured = capsys.readouterr()
    assert "WARNING: MISSION_SEAL_KEY is not set" in captured.err
    assert "field-test-demo-key" in captured.err


def test_pipeline_honors_env_seal_key(monkeypatch):
    monkeypatch.setenv("MISSION_SEAL_KEY", "pipeline-env-key")
    from backend.nextgen.field_test_pipeline import run_single_path_pipeline
    from backend.nextgen.evidence_ingest import ingest_media_item

    result = run_single_path_pipeline(
        mission_id="m-env-key",
        tenant_id="t1",
        property_id="p1",
        media_items=[
            ingest_media_item("RGB", "2026-08-01T12:00:00Z", "Matrice 4E Wide", 8_000_000),
        ],
        geometry_candidate={
            "planes": [{"id": "a", "confidence": 0.95, "area_sqft": 500}],
        },
        readiness_kwargs={"battery_pct": 85.0},
    )
    assert result.success is True
    from backend.nextgen.mission_package_seal import verify_seal

    assert verify_seal(result.sealed_package, seal_key=b"pipeline-env-key") is True
    assert verify_seal(result.sealed_package, seal_key=DEMO_SEAL_KEY) is False
