"""Checksum verification for DJI package inventories (fixture-driven)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional

from .interfaces import InventoryItem, PackageInventory


@dataclass
class ChecksumReport:
    ok: bool
    verified: List[str] = field(default_factory=list)
    mismatched: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    notes: str = "Fixture checksum verification — not a live device integrity claim"


def _normalize_digest(value: str) -> str:
    v = value.strip().lower()
    if v.startswith("sha256:"):
        v = v.split(":", 1)[1]
    return v


def digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def verify_checksums(
    inventory: PackageInventory,
    *,
    content_by_artifact: Optional[Mapping[str, bytes]] = None,
    expected_by_artifact: Optional[Mapping[str, str]] = None,
) -> ChecksumReport:
    """Verify inventory item digests against provided fixture content/expectations.

    If neither map is provided, items with present=True and non-empty sha256
    are treated as self-consistent fixture digests (synthetic trust).
    """
    verified: List[str] = []
    mismatched: List[str] = []
    missing: List[str] = []
    content_by_artifact = content_by_artifact or {}
    expected_by_artifact = expected_by_artifact or {}

    for item in inventory.items:
        if not item.present:
            if item.required:
                missing.append(item.artifact_id)
            continue
        expected = expected_by_artifact.get(item.artifact_id, item.sha256)
        if not expected:
            mismatched.append(item.artifact_id)
            continue
        if item.artifact_id in content_by_artifact:
            actual = digest_bytes(content_by_artifact[item.artifact_id])
            if actual == _normalize_digest(expected):
                verified.append(item.artifact_id)
            else:
                mismatched.append(item.artifact_id)
        else:
            # Synthetic mode: inventory sha256 is the declared fixture digest.
            if _normalize_digest(item.sha256) == _normalize_digest(expected):
                verified.append(item.artifact_id)
            else:
                mismatched.append(item.artifact_id)

    ok = not mismatched and not missing
    return ChecksumReport(ok=ok, verified=verified, mismatched=mismatched, missing=missing)
