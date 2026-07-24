"""RT-001 integration environment foundation tests (Lane 5).

Docker is optional. When Docker is unavailable, scripts must report
INTEGRATION_ENVIRONMENT_UNAVAILABLE and must not fail repository verify.
LocalDiskAdapter object-storage proof must pass without Docker.

Production readiness: NOT READY.
Base SHA: 0c09b0cf44fb133852ddbb9ce96cea2e137ade6d
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RT001 = ROOT / "engineering" / "rt001"
BACKEND = ROOT / "backend"
STATUS_UNAVAILABLE = "INTEGRATION_ENVIRONMENT_UNAVAILABLE"

# Ensure backend imports work (mirrors conftest).
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_rt001_unit")


def _run(script: str, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    path = RT001 / script
    assert path.is_file(), f"missing {path}"
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [str(path), *args] if path.suffix == ".sh" else [sys.executable, str(path), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=full_env,
        timeout=60,
    )


def test_rt001_scaffold_files_exist():
    required = [
        "README.md",
        "docker-compose.yml",
        ".env.example",
        "start.sh",
        "stop.sh",
        "generate_local_secrets.sh",
        "healthcheck.sh",
        "mongo_txn_probe.py",
        "object_storage_proof.py",
        "_common.py",
    ]
    for name in required:
        assert (RT001 / name).is_file(), name


def test_scripts_are_executable():
    for name in ("start.sh", "stop.sh", "generate_local_secrets.sh", "healthcheck.sh"):
        mode = (RT001 / name).stat().st_mode
        assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), f"{name} not executable"


def test_env_example_has_placeholders_only_no_real_secrets():
    text = (RT001 / ".env.example").read_text(encoding="utf-8")
    assert "RT001_MONGO_PORT" in text
    assert "MONGO_URL=" in text
    assert "RT001_MINIO_ROOT_USER=" in text
    assert "NEXTGEN_STORAGE_ROOT=" in text
    assert "RT001_PRODUCTION_READY=false" in text
    # No PEM / AWS live key patterns
    assert "BEGIN " not in text
    assert "AKIA" not in text
    assert "password=prod" not in text.lower()


def test_compose_defines_mongo_replset_and_minio():
    text = (RT001 / "docker-compose.yml").read_text(encoding="utf-8")
    assert "replSet" in text or "rs0" in text
    assert "minio" in text.lower()
    assert "mongo" in text.lower()
    assert "NOT READY" in text or "Production readiness" in (RT001 / "README.md").read_text()


def test_gitignore_covers_rt001_runtime():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".rt001/" in gi
    assert "!engineering/rt001/.env.example" in gi


def test_mission_record_exists():
    path = ROOT / "engineering" / "px001" / "missions" / "LANE_5_RT001.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "0c09b0cf44fb133852ddbb9ce96cea2e137ade6d" in text
    assert "NOT READY" in text
    assert "INTEGRATION_ENVIRONMENT_UNAVAILABLE" in text
    assert "No production deployment" in text or "No production" in text


def test_generate_local_secrets_writes_gitignored_file(tmp_path, monkeypatch):
    # Run against real script; secrets go under repo .rt001 which is gitignored.
    proc = _run("generate_local_secrets.sh")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    secrets = ROOT / ".rt001" / "secrets.env"
    assert secrets.is_file()
    body = secrets.read_text(encoding="utf-8")
    assert "MONGO_URL=" in body
    assert "RT001_S3_SECRET_KEY=" in body
    assert "DO NOT COMMIT" in body
    # Confirm path is ignored by git
    check = subprocess.run(
        ["git", "check-ignore", "-v", str(secrets)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_start_stop_honest_when_docker_missing():
    """When docker is absent, start/stop must classify unavailable and exit 0."""
    docker = shutil.which("docker")
    if docker:
        pytest.skip("Docker present — honesty path for missing Docker not exercised here")

    for script in ("start.sh", "stop.sh", "healthcheck.sh"):
        proc = _run(script)
        out = proc.stdout + proc.stderr
        assert proc.returncode == 0, out
        assert STATUS_UNAVAILABLE in out


def test_docker_common_helper_reports_unavailable_without_docker():
    sys.path.insert(0, str(RT001))
    from _common import docker_available  # type: ignore

    result = docker_available()
    if shutil.which("docker"):
        # May still be unavailable if daemon down
        assert result.status in ("OK", STATUS_UNAVAILABLE)
    else:
        assert result.available is False
        assert result.status == STATUS_UNAVAILABLE
        assert any(STATUS_UNAVAILABLE in m for m in result.messages)


def test_mongo_txn_probe_unavailable_or_skip_without_replica_set():
    proc = _run("mongo_txn_probe.py")
    out = proc.stdout + proc.stderr
    # Must not crash; exit 0 on unavailable/skip
    assert proc.returncode == 0, out
    assert (
        STATUS_UNAVAILABLE in out
        or "[SKIP]" in out
        or "[OK] mongo_transaction_probe" in out
    )


def test_object_storage_local_disk_proof_passes():
    proc = _run("object_storage_proof.py")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "LocalDiskAdapter" in out or "object_storage_local_disk" in out
    assert "[OK] object_storage_local_disk" in out


def test_local_disk_adapter_checksum_roundtrip(tmp_path):
    from nextgen.storage import LocalDiskAdapter, S3CompatibleAdapter

    adapter = LocalDiskAdapter(root=str(tmp_path / "store"))
    payload = b"rt001-unit-checksum"
    digest, size, key = adapter.put("rt001tenant", "rt001mission", io.BytesIO(payload))
    assert size == len(payload)
    assert digest == hashlib.sha256(payload).hexdigest()
    with adapter.open_read("rt001tenant", "rt001mission", digest) as fh:
        assert fh.read() == payload
    assert key.startswith("nextgen://")

    stub = S3CompatibleAdapter(
        endpoint_url="http://127.0.0.1:9000",
        access_key="x",
        secret_key="y",
        bucket="stratex-rt001",
    )
    assert stub.configured is True
    with pytest.raises(NotImplementedError):
        stub.put("rt001tenant", "rt001mission", io.BytesIO(payload))


def test_no_production_claims_in_rt001_docs():
    for rel in (
        "engineering/rt001/README.md",
        "engineering/px001/missions/LANE_5_RT001.md",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "NOT READY" in text
        lower = text.lower()
        assert "production ready" not in lower or "not ready" in lower
        assert "deployed to production" not in lower
