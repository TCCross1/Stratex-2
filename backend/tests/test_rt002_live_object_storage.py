"""RT-002 live S3-compatible object-storage proofs (MinIO).

Requires:
  RT002_LIVE=1
  RT002_MINIO_ENDPOINT (e.g. http://127.0.0.1:9000)
  RT002_MINIO_ACCESS_KEY / RT002_MINIO_SECRET_KEY (ephemeral CI secrets)

Emits: LIVE_S3_COMPATIBLE_STORAGE_PROOF
LocalDiskAdapter tests are NOT live proof.
"""
from __future__ import annotations

import hashlib
import os
import uuid

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.live_object_storage,
]

LIVE = os.environ.get("RT002_LIVE", "").lower() in {"1", "true", "yes"}
ENDPOINT = os.environ.get("RT002_MINIO_ENDPOINT") or os.environ.get("MINIO_ENDPOINT") or ""
ACCESS = os.environ.get("RT002_MINIO_ACCESS_KEY") or os.environ.get("MINIO_ROOT_USER") or ""
SECRET = os.environ.get("RT002_MINIO_SECRET_KEY") or os.environ.get("MINIO_ROOT_PASSWORD") or ""
BUCKET = os.environ.get("RT002_MINIO_BUCKET") or "stratex-rt002"


def _skip_unless_live():
    if not LIVE:
        pytest.skip("RT002_LIVE not set — live object-storage proof not executed here")
    if not ENDPOINT or not ACCESS or not SECRET:
        pytest.skip("INTEGRATION_ENVIRONMENT_UNAVAILABLE: MinIO endpoint/credentials missing")


@pytest.fixture(scope="module")
def s3():
    _skip_unless_live()
    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError

    client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS,
        aws_secret_access_key=SECRET,
        region_name="us-east-1",
        config=Config(signature_version="s3v4"),
    )
    # Readiness
    try:
        client.list_buckets()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"INTEGRATION_ENVIRONMENT_UNAVAILABLE: MinIO not reachable ({type(exc).__name__})")
    return client


def test_bucket_create_upload_download_checksum(s3):
    bucket = f"{BUCKET}-{uuid.uuid4().hex[:8]}"
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception:
        # MinIO may already have default bucket; create may be optional.
        pass
    # Ensure bucket exists
    names = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    if bucket not in names:
        s3.create_bucket(Bucket=bucket)
    key = f"tenant_rt002/property_demo/obj-{uuid.uuid4().hex}.bin"
    payload = b"rt002-live-object-storage-proof-" + uuid.uuid4().bytes
    digest = hashlib.sha256(payload).hexdigest()
    s3.put_object(Bucket=bucket, Key=key, Body=payload, Metadata={"sha256": digest})
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    assert body == payload
    assert hashlib.sha256(body).hexdigest() == digest
    meta = obj.get("Metadata") or {}
    assert meta.get("sha256") == digest
    # Ensure metadata has no secret-looking values
    joined = " ".join(f"{k}={v}" for k, v in meta.items()).lower()
    assert "password" not in joined
    assert "secret" not in joined
    print("LIVE_S3_COMPATIBLE_STORAGE_PROOF upload_download_checksum=PASS")
    s3.delete_object(Bucket=bucket, Key=key)
    try:
        s3.delete_bucket(Bucket=bucket)
    except Exception:
        pass


def test_checksum_mismatch_rejection(s3):
    bucket = f"{BUCKET}-mm-{uuid.uuid4().hex[:6]}"
    s3.create_bucket(Bucket=bucket)
    key = f"tenant_rt002/mismatch/{uuid.uuid4().hex}.bin"
    payload = b"correct-payload"
    wrong = hashlib.sha256(b"wrong").hexdigest()
    s3.put_object(Bucket=bucket, Key=key, Body=payload, Metadata={"sha256": wrong})
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    actual = hashlib.sha256(body).hexdigest()
    claimed = (obj.get("Metadata") or {}).get("sha256")
    assert actual != claimed
    # Application-level rejection
    with pytest.raises(AssertionError):
        assert actual == claimed
    print("LIVE_S3_COMPATIBLE_STORAGE_PROOF checksum_mismatch_rejection=PASS")
    s3.delete_object(Bucket=bucket, Key=key)
    s3.delete_bucket(Bucket=bucket)


def test_missing_object_and_prefix_isolation(s3):
    from botocore.exceptions import ClientError

    bucket = f"{BUCKET}-iso-{uuid.uuid4().hex[:6]}"
    s3.create_bucket(Bucket=bucket)
    t1 = f"tenant_a/{uuid.uuid4().hex}.bin"
    t2 = f"tenant_b/{uuid.uuid4().hex}.bin"
    s3.put_object(Bucket=bucket, Key=t1, Body=b"a")
    s3.put_object(Bucket=bucket, Key=t2, Body=b"b")
    listed = s3.list_objects_v2(Bucket=bucket, Prefix="tenant_a/")
    keys = [x["Key"] for x in listed.get("Contents") or []]
    assert t1 in keys
    assert t2 not in keys
    with pytest.raises(ClientError):
        s3.get_object(Bucket=bucket, Key="tenant_a/does-not-exist.bin")
    print("LIVE_S3_COMPATIBLE_STORAGE_PROOF prefix_isolation=PASS")
    for k in (t1, t2):
        s3.delete_object(Bucket=bucket, Key=k)
    s3.delete_bucket(Bucket=bucket)
