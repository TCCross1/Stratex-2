"""RT-002 unit honesty tests — no live infrastructure required.

Failure paths must not report READY. No silent FakeMongo/LocalDisk fallback
classification as live proof.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
RT002 = ROOT / "engineering" / "rt002"
COMPOSE = ROOT / "engineering" / "rt001" / "docker-compose.yml"
DIGESTS = RT002 / "IMAGE_DIGESTS.yaml"


def test_image_digests_file_present_and_pinned():
    data = yaml.safe_load(DIGESTS.read_text(encoding="utf-8"))
    assert data["production_readiness"] == "NOT_READY"
    for key in ("mongo", "minio", "minio_mc"):
        img = data["images"][key]
        assert img["digest"].startswith("sha256:")
        assert "@sha256:" in img["reference"]
        assert ":latest" not in img["reference"]
    actions = data["github_actions"]
    assert len(actions["actions/checkout"]["commit"]) == 40
    assert len(actions["actions/setup-python"]["commit"]) == 40


def test_compose_uses_digest_pinned_images_not_latest():
    text = COMPOSE.read_text(encoding="utf-8")
    assert "mongo:7.0@sha256:" in text
    assert "minio/minio:" in text and "@sha256:" in text
    assert "minio/mc:" in text and "@sha256:" in text
    assert "minio/minio:latest" not in text
    assert "minio/mc:latest" not in text


def test_lane5_owns_rt001_rt002_paths():
    lanes = yaml.safe_load((ROOT / "engineering" / "lanes.yaml").read_text())
    lane5 = next(l for l in lanes["lanes"] if l["id"] == "LANE_5_RUNTIME_QE")
    owned = lane5["owned_paths"]
    assert "engineering/rt001/" in owned
    assert "engineering/rt002/" in owned
    assert "backend/tests/test_rt002_live_mongo.py" in owned
    prohibited = lane5["prohibited_paths"]
    assert "backend/nextgen/passport_service.py" in prohibited
    assert "backend/nextgen/outbox_worker.py" in prohibited
    assert lane5["authority_modules"] == []


def test_readiness_never_ready_without_components():
    import sys

    sys.path.insert(0, str(ROOT / "engineering"))
    from rt002.readiness import ReadinessReport, OverallState

    r = ReadinessReport()
    assert r.compute_overall() == OverallState.NOT_INITIALIZED
    r.set("mongo_reachable", False, "INTEGRATION_ENVIRONMENT_UNAVAILABLE: docker")
    assert r.compute_overall() == OverallState.UNAVAILABLE
    assert r.overall != OverallState.READY


def test_rt002_does_not_commit_cp003_business_modules():
    assert not (ROOT / "backend" / "nextgen" / "outbox_worker.py").exists()
    assert not (ROOT / "backend" / "nextgen" / "projection_reconciliation.py").exists()


def test_live_markers_documented():
    readme = (RT002 / "README.md").read_text(encoding="utf-8")
    assert "LIVE_MONGO_REPLICA_SET_PROOF" in readme
    assert "LIVE_S3_COMPATIBLE_STORAGE_PROOF" in readme
    assert "NOT READY" in readme


def test_workflow_file_exists_with_least_privilege():
    wf = ROOT / ".github" / "workflows" / "stratex-live-integration.yml"
    assert wf.is_file()
    text = wf.read_text(encoding="utf-8")
    assert "permissions:" in text
    assert "contents: read" in text
    assert "deploy" not in text.lower() or "no deployment" in text.lower()
    assert "workflow_dispatch" in text
    assert "pull_request" in text
    # Action pinning by commit SHA
    assert "actions/checkout@" in text
    assert "actions/setup-python@" in text
