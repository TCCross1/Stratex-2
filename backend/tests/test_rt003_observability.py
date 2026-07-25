"""RT-003 observability foundation tests — safe logs/metrics, no secrets.

Production readiness: NOT READY.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / "engineering"
if str(ENG) not in sys.path:
    sys.path.insert(0, str(ENG))

from rt003.observability import SafeLogger, SafeMetrics, scrub_for_log  # noqa: E402


def test_scrub_redacts_secrets_and_customer_payloads():
    raw = {
        "component": "rt003",
        "password": "super-secret-value",
        "api_key": "AKIA_SHOULD_NOT_APPEAR",
        "payload": {"customer_name": "Ada", "note": "hidden"},
        "mongo_url": "mongodb://user:pass@host:27017/db",
        "ok": True,
        "count": 3,
    }
    scrubbed = scrub_for_log(raw)
    assert scrubbed["component"] == "rt003"
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["api_key"] == "[REDACTED]"
    assert scrubbed["payload"] == "[REDACTED]"
    assert scrubbed["mongo_url"] == "[REDACTED]"
    assert scrubbed["ok"] is True
    assert scrubbed["count"] == 3
    blob = json.dumps(scrubbed)
    assert "super-secret-value" not in blob
    assert "Ada" not in blob
    assert "user:pass" not in blob


def test_scrub_redacts_embedded_connection_credentials_in_strings():
    text = scrub_for_log("mongodb://alice:hunter2@mongo.internal:27017")
    assert "hunter2" not in text
    assert "alice" not in text
    assert "mongo.internal:27017" in text


def test_safe_logger_emits_structured_json_without_secrets(caplog):
    logger = SafeLogger(name="stratex.rt003.test")
    with caplog.at_level(logging.INFO, logger="stratex.rt003.test"):
        line = logger.info(
            "unit_probe",
            component="observability",
            secret="should-not-leak",
            token="abc12345",
            outcome="ok",
        )
    parsed = json.loads(line)
    assert parsed["event"] == "unit_probe"
    assert parsed["production_readiness"] == "NOT_READY"
    assert parsed["attrs"]["secret"] == "[REDACTED]"
    assert parsed["attrs"]["token"] == "[REDACTED]"
    assert parsed["attrs"]["component"] == "observability"
    assert "should-not-leak" not in line
    assert "abc12345" not in line


def test_safe_metrics_rejects_payload_labels_and_tracks_counters():
    metrics = SafeMetrics()
    sample = metrics.incr(
        "rt003_ops_total",
        labels={
            "component": "load_harness",
            "operation": "hash",
            "outcome": "ok",
            "payload": "CUSTOMER_SHOULD_DROP",
            "password": "nope",
        },
    )
    assert sample.value == 1.0
    assert "payload" not in sample.labels
    assert "password" not in sample.labels
    assert sample.labels["component"] == "load_harness"
    metrics.observe_ms("rt003_op_ms", 12.5, labels={"component": "load_harness"})
    snap = metrics.snapshot()
    assert snap["production_readiness"] == "NOT_READY"
    assert snap["counters"]
    assert snap["timings_ms"]


def test_safe_metrics_invalid_name_rejected():
    metrics = SafeMetrics()
    try:
        metrics.incr("BAD-NAME")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_safe_metrics_rejects_high_cardinality_and_secret_labels():
    from rt003.observability import bound_exception_text

    metrics = SafeMetrics()
    sample = metrics.incr(
        "rt003_ops_total",
        labels={
            "component": "observability",
            "operation": "emit",
            "outcome": "ok",
            "tenant_id": "tenant-should-drop",
            "property_id": "property-should-drop",
            "object_url": "https://minio/x?X-Amz-Signature=abc",
            "password": "nope",
            "presigned_url": "https://signed",
        },
    )
    assert "tenant_id" not in sample.labels
    assert "property_id" not in sample.labels
    assert "object_url" not in sample.labels
    assert "password" not in sample.labels
    assert "presigned_url" not in sample.labels
    assert sample.labels["component"] == "observability"

    scrubbed = scrub_for_log(
        {
            "object_url": "https://minio/bucket/o?X-Amz-Signature=deadbeef",
            "contractor_margin": 0.33,
            "ok": 1,
        }
    )
    assert scrubbed["object_url"] == "[REDACTED]"
    assert scrubbed["contractor_margin"] == "[REDACTED]"
    assert scrubbed["ok"] == 1

    long_exc = bound_exception_text("x" * 1000)
    assert len(long_exc) < 300
    assert long_exc.endswith("...[truncated]")
