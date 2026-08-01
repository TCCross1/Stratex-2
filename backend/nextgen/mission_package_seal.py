"""
Canonical Mission Package Sealing Service
Stratex Core — Field Test v1

Enforces the Mission Package Sealing Contract.
Only sealed packages may be submitted to the governed publisher.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Truth classifications allowed in the system
TRUTH_CLASSES = {"VERIFIED", "ESTIMATED", "PROJECTED", "UNKNOWN", "WITHHELD"}

REQUIRED_SECTIONS = [
    "mission_metadata",
    "evidence_manifest",
    "geometry_candidate",
    "awe_candidate",
    "seal_record",
]


class SealingError(Exception):
    """Raised when a package fails sealing validation."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(obj: Any) -> str:
    """Stable JSON serialization for hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(payload: Dict[str, Any]) -> str:
    """SHA-256 of the canonical payload (excluding the seal_record itself)."""
    to_hash = {k: v for k, v in payload.items() if k != "seal_record"}
    return hashlib.sha256(_canonical_json(to_hash).encode("utf-8")).hexdigest()


def seal_package(
    package: Dict[str, Any],
    seal_key: Optional[bytes] = None,
    key_version: str = "v1",
) -> Dict[str, Any]:
    """
    Validate and seal a mission package.
    Returns the sealed package or raises SealingError.
    """
    # 1. Required top-level identity
    for field in ("package_id", "mission_id", "tenant_id", "property_id"):
        if not package.get(field):
            raise SealingError("MISSING_IDENTITY", f"Missing required field: {field}")

    # 2. Required sections
    for section in REQUIRED_SECTIONS:
        if section not in package:
            raise SealingError("MISSING_SECTION", f"Missing required section: {section}")

    # 3. Geometry withholding rules
    geometry = package.get("geometry_candidate", {})
    planes = geometry.get("planes", [])
    for plane in planes:
        conf = plane.get("confidence")
        if conf is not None and conf < 0.65:
            plane["truth_classification"] = "WITHHELD"
            plane["withheld_reason"] = "confidence_below_threshold"

    # 4. AWE findings must carry truth classification
    awe = package.get("awe_candidate", {})
    for finding in awe.get("findings", []):
        if finding.get("truth_classification") not in TRUTH_CLASSES:
            finding["truth_classification"] = "UNKNOWN"

    # 5. Compute content hash
    chash = content_hash(package)

    # 6. Create seal record
    if seal_key is None:
        # In production this comes from PASSPORT_SEAL_KEY_<version>
        seal_key = os.environ.get("MISSION_SEAL_KEY", "dev-only-insecure-key").encode()

    signature = hmac.new(seal_key, chash.encode("utf-8"), hashlib.sha256).hexdigest()

    package["seal_record"] = {
        "seal_algorithm": "HMAC-SHA256",
        "seal_key_version": key_version,
        "content_hash": chash,
        "signature": signature,
        "sealed_at": _now_iso(),
        "sealer_identity": "stratex.core.mission_package_seal",
    }

    package["content_hash"] = chash
    return package


def verify_seal(package: Dict[str, Any], seal_key: Optional[bytes] = None) -> bool:
    """Verify an already-sealed package. Returns True if valid."""
    seal = package.get("seal_record")
    if not seal:
        return False

    expected_hash = content_hash(package)
    if seal.get("content_hash") != expected_hash:
        return False

    if seal_key is None:
        seal_key = os.environ.get("MISSION_SEAL_KEY", "dev-only-insecure-key").encode()

    expected_sig = hmac.new(
        seal_key, expected_hash.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(seal.get("signature", ""), expected_sig)


def create_empty_package(
    mission_id: str,
    tenant_id: str,
    property_id: str,
    capture_type: str = "DAYTIME_PRECISION_MAPPING",
) -> Dict[str, Any]:
    """Factory for a minimal valid package skeleton."""
    return {
        "package_id": str(uuid.uuid4()),
        "mission_id": mission_id,
        "tenant_id": tenant_id,
        "property_id": property_id,
        "created_at": _now_iso(),
        "mission_metadata": {
            "capture_type": capture_type,
            "aircraft": "Matrice_4E" if "DAYTIME" in capture_type else "Matrice_4T",
        },
        "evidence_manifest": {"items": []},
        "geometry_candidate": {"planes": [], "measurements": {}},
        "awe_candidate": {"findings": []},
        "seal_record": {},
    }
