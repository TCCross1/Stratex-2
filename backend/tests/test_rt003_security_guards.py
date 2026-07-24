"""RT-003 security / failure guards — floating images, DLQ scrub, writers, READY.

Production readiness: NOT READY.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / "engineering"
if str(ENG) not in sys.path:
    sys.path.insert(0, str(ENG))

from rt003.guards import (  # noqa: E402
    guard_dlq_scrub_detection,
    guard_duplicate_writer,
    guard_false_ready,
    guard_floating_python_image,
    run_security_failure_guards,
)

DIGESTS = ROOT / "engineering" / "rt002" / "IMAGE_DIGESTS.yaml"
WORKFLOW = ROOT / ".github" / "workflows" / "stratex-live-integration.yml"
CONTRACT = ROOT / "engineering" / "px004" / "lane5" / "CONTRACT_READINESS.md"


def test_python_harness_digest_resolved_and_not_invented():
    data = yaml.safe_load(DIGESTS.read_text(encoding="utf-8"))
    assert data["production_readiness"] == "NOT_READY"
    # Preserve prior pins.
    for key in ("mongo", "minio", "minio_mc"):
        assert data["images"][key]["digest"].startswith("sha256:")
        assert "@sha256:" in data["images"][key]["reference"]
    py = data["images"]["python_harness"]
    assert py["tag"] == "3.12-slim"
    assert py["digest"] == (
        "sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
    )
    assert py["reference"] == (
        "python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de"
    )
    assert "docker pull" in (py.get("source") or "").lower() or "hub.docker.com" in (
        py.get("source") or ""
    )
    # Action pins preserved.
    assert data["github_actions"]["actions/checkout"]["commit"] == (
        "11d5960a326750d5838078e36cf38b85af677262"
    )
    assert data["github_actions"]["actions/setup-python"]["commit"] == (
        "a26af69be951a213d495a4c3e4e4022e16d87065"
    )


def test_workflow_uses_pinned_harness_and_keeps_contents_read():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "contents: read" in text
    assert "PYTHON_HARNESS_REF" in text
    # No bare floating image argument.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "python:3.12-slim" in stripped and "@sha256:" not in stripped:
            # Allow prose in comments only — already skipped; any code line fails.
            raise AssertionError(f"floating python tag: {stripped}")
    finding = guard_floating_python_image()
    assert finding.status == "PASS", finding.as_public_dict()


def test_guard_duplicate_writer_pass():
    finding = guard_duplicate_writer()
    assert finding.status == "PASS", finding.as_public_dict()


def test_guard_false_ready_pass():
    finding = guard_false_ready()
    assert finding.status == "PASS", finding.as_public_dict()


def test_guard_dlq_scrub_detection_classifies_honestly():
    finding = guard_dlq_scrub_detection()
    # Lane 5 detects residual risk; does not silently claim PASS if scrub absent.
    assert finding.status in {"FINDING", "PASS", "UNAVAILABLE"}
    assert finding.remediation_owner == "LANE_1_CORE_PASSPORT"
    worker = ROOT / "backend" / "nextgen" / "outbox_worker.py"
    if worker.is_file():
        body = worker.read_text(encoding="utf-8")
        copies_raw = '"payload": event.get("payload")' in body
        # Current tree copies raw payload in DLQ — expect FINDING.
        if copies_raw and "_scrub(event.get(\"payload\")" not in body:
            assert finding.status == "FINDING"
            assert "raw" in finding.summary.lower() or "scrub" in finding.summary.lower()


def test_run_security_failure_guards_aggregate():
    findings = run_security_failure_guards()
    by_id = {f.guard_id: f for f in findings}
    assert by_id["floating_python_image"].status == "PASS"
    assert by_id["duplicate_writer"].status == "PASS"
    assert by_id["false_ready"].status == "PASS"
    assert by_id["dlq_scrub_detection"].status in {"FINDING", "PASS", "UNAVAILABLE"}
    # No guard may claim production ready.
    for f in findings:
        assert f.as_public_dict()["production_readiness"] == "NOT_READY"


def test_contract_readiness_document():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "NOT READY" in text
    assert "READY_FOR_INDEPENDENT_AUDIT" in text
    assert "ATLAS_MERGE_AUTHORIZATION" in text
    assert "dlq_scrub_detection" in text
    assert "LANE_1_CORE_PASSPORT" in text
    assert "NEVER AUTHORITY" in text


def test_lane5_owns_rt003_paths():
    lanes = yaml.safe_load((ROOT / "engineering" / "lanes.yaml").read_text())
    lane5 = next(l for l in lanes["lanes"] if l["id"] == "LANE_5_RUNTIME_QE")
    owned = lane5["owned_paths"]
    assert "engineering/rt003/" in owned
    assert "engineering/px004/lane5/" in owned
    assert "backend/tests/test_rt003_observability.py" in owned
    assert "backend/tests/test_rt003_load_budgets.py" in owned
    assert "backend/tests/test_rt003_security_guards.py" in owned
    assert lane5["authority_modules"] == []
    assert "backend/nextgen/outbox_worker.py" in lane5["prohibited_paths"]
