"""Shared constants and helpers for the External Drone Dataset Laboratory.

PX-006A — development/compatibility laboratory only.
Not physical property truth. Not customer evidence. Not production readiness.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

MODULE_IDENTITY = "nextgen.dataset_lab"
LAB_VERSION = "px006a.1.0.0"
CONTRACT_STATUS = "PROPOSED"
PRODUCTION_READINESS = "NOT_READY"

DEFAULT_DATASET_ROOT = Path("/tmp/stratex-external-datasets")
ENV_DATASET_ROOT = "STRATEX_DATASET_ROOT"

# Global data-governance labels applied to every external corpus.
GOVERNANCE_LABELS: Dict[str, str] = {
    "data_origin": "EXTERNAL_PUBLIC_DATASET",
    "truth_status": "NON_CANONICAL_TEST_DATA",
    "physical_validation": "NOT_PERFORMED",
    "property_use": "DEVELOPMENT_ONLY",
    "customer_use": "PROHIBITED",
    "passport_publication": "PROHIBITED",
    "habitat_canonical_display": "PROHIBITED",
    "field_accuracy_claim": "PROHIBITED",
}

LICENSE_STATUSES = frozenset(
    {
        "VERIFIED_PERMISSIVE",
        "VERIFIED_RESTRICTED",
        "REVIEW_REQUIRED",
        "UNKNOWN",
        "REJECTED",
    }
)

READINESS_RESULTS = frozenset(
    {
        "READY_FOR_DEVELOPMENT_REVIEW",
        "USABLE_WITH_LIMITATIONS",
        "ADDITIONAL_DATA_REQUIRED",
        "REJECTED_DATASET",
        "UNSUPPORTED_FORMAT",
        "LICENSE_BLOCKED",
    }
)

# Acquisition safety ceilings.
MAX_ARCHIVE_BYTES = 8 * 1024 * 1024 * 1024  # 8 GiB bound (DJI Terra sample Content-Length ~6.39 GiB)
MAX_REPO_BYTES = 3 * 1024 * 1024 * 1024  # 3 GiB
MAX_REDIRECTS = 3
DEFAULT_TIMEOUT_SECONDS = 120
MAX_ARCHIVE_ENTRIES = 50_000
MAX_SINGLE_ENTRY_BYTES = 7 * 1024 * 1024 * 1024  # 7 GiB per entry (nested DJI 3D sample ~2.8GiB+)
MAX_COMPRESSION_RATIO = 100.0

IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".tif", ".tiff", ".png", ".dng", ".rjpeg"})
EXECUTABLE_SUFFIXES = frozenset(
    {".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1", ".sh", ".com"}
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def dataset_root() -> Path:
    raw = os.environ.get(ENV_DATASET_ROOT, str(DEFAULT_DATASET_ROOT))
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def dataset_dir(dataset_id: str) -> Path:
    safe = sanitize_dataset_id(dataset_id)
    path = dataset_root() / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_dataset_id(dataset_id: str) -> str:
    text = (dataset_id or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9_]{2,64}", text):
        raise ValueError(f"invalid dataset_id: {dataset_id!r}")
    return text


def sha256_file(path: Path, *, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_bytes(encoded.encode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_root() -> Path:
    # backend/nextgen/dataset_lab/common.py -> repo root
    return Path(__file__).resolve().parents[3]


def registry_path() -> Path:
    return repo_root() / "engineering" / "px006a" / "datasets" / "EXTERNAL_DATASET_REGISTRY.yaml"


def load_registry() -> Dict[str, Any]:
    import yaml

    path = registry_path()
    if not path.is_file():
        raise FileNotFoundError(f"dataset registry missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping) or "datasets" not in data:
        raise ValueError("invalid EXTERNAL_DATASET_REGISTRY.yaml")
    return data


def get_registry_entry(dataset_id: str) -> Dict[str, Any]:
    safe = sanitize_dataset_id(dataset_id)
    reg = load_registry()
    for entry in reg.get("datasets") or []:
        if str(entry.get("dataset_id", "")).upper() == safe:
            return dict(entry)
    raise KeyError(f"dataset not in allowlist registry: {safe}")


def receipt_dir(dataset_id: str) -> Path:
    path = dataset_dir(dataset_id) / "receipts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def experiments_dir(dataset_id: str) -> Path:
    path = dataset_dir(dataset_id) / "experiments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def faults_dir(dataset_id: str) -> Path:
    path = dataset_dir(dataset_id) / "faults"
    path.mkdir(parents=True, exist_ok=True)
    return path


def quarantine_dir(dataset_id: str) -> Path:
    path = dataset_dir(dataset_id) / "quarantine"
    path.mkdir(parents=True, exist_ok=True)
    return path


def content_dir(dataset_id: str) -> Path:
    path = dataset_dir(dataset_id) / "content"
    path.mkdir(parents=True, exist_ok=True)
    return path


def governance_block() -> Dict[str, str]:
    return dict(GOVERNANCE_LABELS)


def redacted_summary_gps(status: str) -> str:
    allowed = {"GPS_PRESENT", "GPS_ABSENT", "GPS_PARTIAL"}
    if status not in allowed:
        return "GPS_ABSENT"
    return status


def artifact_dir(dataset_id: str) -> Path:
    path = dataset_dir(dataset_id) / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


# Compatibility aliases used by inventory/corpus adapters.
GOVERNANCE = GOVERNANCE_LABELS
checksum_file = sha256_file
load_registry_entry = get_registry_entry
load_json = read_json
dataset_checkout_dir = content_dir
dataset_artifact_dir = artifact_dir


def sha256_hex(data: bytes) -> str:
    return sha256_bytes(data)

