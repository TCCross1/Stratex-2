"""Tests for field_test_governed_publish_demo dry-run path."""

from backend.nextgen.field_test_governed_publish_demo import (
    run_dry_run,
    validate_publication_request,
)


def test_validate_publication_request_accepts_pipeline_output():
    summary = run_dry_run()
    assert summary["pipeline_success"] is True
    assert summary["status"] == "DRY_RUN_OK"
    assert summary["publication_request_valid"] is True
    assert summary["validation_errors"] == []
    assert summary["seal_readiness_ready"] is True


def test_validate_publication_request_rejects_incomplete():
    ok, errors = validate_publication_request({"tenant_id": "t1"})
    assert ok is False
    assert any("missing publication_request" in e for e in errors)
