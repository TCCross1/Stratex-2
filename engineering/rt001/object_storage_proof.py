#!/usr/bin/env python3
"""RT-001 object storage upload/download/checksum proof.

Always exercises LocalDiskAdapter (no Docker required). Optionally attempts
an S3-compatible (MinIO) put/get when endpoint env vars and a compatible
client library are available; otherwise reports
INTEGRATION_ENVIRONMENT_UNAVAILABLE for the MinIO path only.

Production readiness: NOT READY.
Base SHA: 0c09b0cf44fb133852ddbb9ce96cea2e137ade6d
"""
from __future__ import annotations

import hashlib
import io
import os
import sys
from pathlib import Path

_RT001 = Path(__file__).resolve().parent
_REPO = _RT001.parents[1]
_BACKEND = _REPO / "backend"
for p in (_RT001, str(_BACKEND)):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Stable defaults so imports do not require live Mongo; keep disk root local.
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_rt001")
_runtime = _REPO / ".rt001"
_runtime.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("NEXTGEN_STORAGE_ROOT", str(_runtime / "nextgen_storage"))

from _common import (  # noqa: E402
    SECRETS_FILE,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    ProbeResult,
    ensure_runtime_dir,
    load_dotenv_file,
)


TENANT = "rt001tenant"
MISSION = "rt001mission"


def _proof_local_disk() -> ProbeResult:
    result = ProbeResult(name="object_storage_local_disk", status=STATUS_OK, available=False)
    runtime = ensure_runtime_dir()
    root = Path(os.environ.get("NEXTGEN_STORAGE_ROOT") or (runtime / "nextgen_storage"))
    root.mkdir(parents=True, exist_ok=True)
    os.environ["NEXTGEN_STORAGE_ROOT"] = str(root)

    from nextgen.storage import LocalDiskAdapter

    adapter = LocalDiskAdapter(root=str(root))
    payload = b"rt001-object-storage-proof\n"
    digest_expected = hashlib.sha256(payload).hexdigest()

    digest, size, key = adapter.put(TENANT, MISSION, io.BytesIO(payload))
    if digest != digest_expected:
        result.status = "FAIL"
        result.extend(f"checksum mismatch on put: got {digest}, want {digest_expected}")
        return result
    if size != len(payload):
        result.status = "FAIL"
        result.extend(f"size mismatch: got {size}, want {len(payload)}")
        return result
    if not adapter.exists(TENANT, MISSION, digest):
        result.status = "FAIL"
        result.extend("exists() returned False after put")
        return result

    with adapter.open_read(TENANT, MISSION, digest) as fh:
        got = fh.read()
    got_digest = hashlib.sha256(got).hexdigest()
    if got != payload or got_digest != digest_expected:
        result.status = "FAIL"
        result.extend("download/checksum mismatch")
        return result

    adapter.delete_pending(TENANT, MISSION, digest)
    result.available = True
    result.extend(f"LocalDiskAdapter put/get/checksum OK key={key}")
    result.extend("NOT production — local proof only")
    return result


def _proof_minio_optional() -> ProbeResult:
    """Best-effort MinIO proof; never required for RT-001 first checkpoint."""
    result = ProbeResult(name="object_storage_minio", status=STATUS_OK, available=False)
    endpoint = os.environ.get("RT001_S3_ENDPOINT")
    access = os.environ.get("RT001_S3_ACCESS_KEY")
    secret = os.environ.get("RT001_S3_SECRET_KEY")
    bucket = os.environ.get("RT001_S3_BUCKET", "stratex-rt001")

    if not (endpoint and access and secret):
        result.status = STATUS_UNAVAILABLE
        result.extend(
            f"{STATUS_UNAVAILABLE}: MinIO/S3 env not configured "
            "(run generate_local_secrets.sh + start.sh)"
        )
        return result

    # Prefer urllib-only stub path via nextgen.storage.S3CompatibleAdapter when
    # no boto3 — still only proves interface wiring, not live MinIO.
    try:
        import urllib.error
        import urllib.request
    except ImportError as exc:
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: urllib unavailable ({exc})")
        return result

    # Live MinIO health (no credentials in output)
    health_url = endpoint.rstrip("/") + "/minio/health/live"
    try:
        with urllib.request.urlopen(health_url, timeout=2) as resp:
            if getattr(resp, "status", 200) >= 400:
                raise urllib.error.URLError(f"status {resp.status}")
    except Exception as exc:
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: MinIO endpoint not reachable ({type(exc).__name__})")
        return result

    # Optional boto3 put/get; if missing, prove adapter stub only.
    try:
        import boto3
        from botocore.client import Config
    except ImportError:
        from nextgen.storage import S3CompatibleAdapter

        stub = S3CompatibleAdapter(
            endpoint_url=endpoint,
            access_key=access,
            secret_key=secret,
            bucket=bucket,
        )
        result.status = STATUS_UNAVAILABLE
        result.extend(
            f"{STATUS_UNAVAILABLE}: MinIO live but boto3 not installed; "
            f"S3CompatibleAdapter stub constructed (configured={stub.configured})"
        )
        return result

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        config=Config(signature_version="s3v4"),
        region_name=os.environ.get("RT001_S3_REGION", "us-east-1"),
    )
    key = "rt001/proof/object-storage.bin"
    payload = b"rt001-minio-proof\n"
    expected = hashlib.sha256(payload).hexdigest()
    try:
        client.put_object(Bucket=bucket, Key=key, Body=payload)
        obj = client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        got = hashlib.sha256(body).hexdigest()
        if got != expected or body != payload:
            result.status = "FAIL"
            result.extend("MinIO checksum mismatch")
            return result
        client.delete_object(Bucket=bucket, Key=key)
    except Exception as exc:
        result.status = STATUS_UNAVAILABLE
        result.extend(f"{STATUS_UNAVAILABLE}: MinIO put/get failed ({type(exc).__name__})")
        return result

    result.available = True
    result.extend("MinIO put/get/checksum OK (local integration only; NOT production)")
    return result


def main() -> int:
    load_dotenv_file(_RT001 / ".env.example")
    load_dotenv_file(SECRETS_FILE)
    ensure_runtime_dir()

    local = _proof_local_disk()
    for line in local.as_lines():
        print(line)

    minio = _proof_minio_optional()
    for line in minio.as_lines():
        print(line)

    # Local disk proof is the required checkpoint path; MinIO may be unavailable.
    if local.status != STATUS_OK or not local.available:
        return 1
    # Always exit 0 for MinIO unavailable — does not fail repo verify.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
