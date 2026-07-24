"""Synthetic DJI package parser — fixtures only.

Claims explicitly refused:
- live DJI SDK
- physical field capture
- RTK accuracy
- automated thermal diagnosis
- Passport write / approval
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .checksums import ChecksumReport, verify_checksums
from .interfaces import (
    InventoryItem,
    PackageInventory,
    PackageManifest,
    RJPGMetadata,
)
from .pairing import PairingReport, pair_visual_thermal
from .warnings import PackageWarning, collect_baseline_warnings


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

SUPPORTED_FORMATS = frozenset(
    {
        "stratex.synthetic.dji_package/v0",
    }
)


def load_synthetic_fixture(profile_id: str) -> Dict[str, Any]:
    path = FIXTURES_DIR / f"{profile_id.lower()}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing synthetic fixture for {profile_id}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


class SyntheticDJIPackageParser:
    """Fixture-backed parser implementing the DJIPackageParser protocol."""

    def __init__(self, fixtures: Optional[Mapping[str, Dict[str, Any]]] = None) -> None:
        self._fixtures: Dict[str, Dict[str, Any]] = dict(fixtures or {})

    def _load(self, package_ref: str) -> Dict[str, Any]:
        if package_ref in self._fixtures:
            return self._fixtures[package_ref]
        # package_ref may be a profile id or fixture stem
        if package_ref.endswith(".json"):
            path = Path(package_ref)
            if not path.is_file():
                path = FIXTURES_DIR / Path(package_ref).name
            return json.loads(path.read_text(encoding="utf-8"))
        return load_synthetic_fixture(package_ref)

    def parse_manifest(self, package_ref: str) -> PackageManifest:
        raw = self._load(package_ref)
        m = raw["manifest"]
        return PackageManifest(
            package_id=m["package_id"],
            profile_id=m["profile_id"],
            format_id=m["format_id"],
            format_version=m["format_version"],
            manifest_sha256=m["manifest_sha256"],
            created_at_fixture=m["created_at_fixture"],
            synthetic=True,
            live_dji_sdk=False,
            physical_capture_claimed=False,
            rtk_accuracy_claimed=False,
        )

    def inventory(self, package_ref: str) -> PackageInventory:
        raw = self._load(package_ref)
        items = [
            InventoryItem(
                artifact_id=i["artifact_id"],
                relative_path=i["relative_path"],
                category=i["category"],
                sha256=i["sha256"],
                bytes_claimed=int(i.get("bytes_claimed") or 0),
                required=bool(i.get("required", True)),
                present=bool(i.get("present", True)),
                paired_with=i.get("paired_with"),
            )
            for i in raw.get("inventory", [])
        ]
        return PackageInventory(
            package_id=raw["manifest"]["package_id"],
            profile_id=raw["manifest"]["profile_id"],
            items=items,
        )

    def extract_rjpg_metadata(self, package_ref: str, artifact_id: str) -> RJPGMetadata:
        raw = self._load(package_ref)
        for entry in raw.get("rjpg_metadata", []):
            if entry["artifact_id"] == artifact_id:
                return RJPGMetadata(
                    artifact_id=entry["artifact_id"],
                    relative_path=entry["relative_path"],
                    radiometric=bool(entry.get("radiometric", True)),
                    camera_model_fixture=entry.get("camera_model_fixture", "synthetic"),
                    capture_timestamp_fixture=entry.get("capture_timestamp_fixture"),
                    ambient_c_fixture=entry.get("ambient_c_fixture"),
                    emissivity_fixture=entry.get("emissivity_fixture"),
                    automated_diagnosis=False,
                    synthetic=True,
                )
        raise KeyError(f"No synthetic R-JPG metadata for artifact {artifact_id}")

    def verify_checksums(self, inventory: PackageInventory) -> ChecksumReport:
        raw_contents = {
            item.artifact_id: f"synthetic:{item.artifact_id}:{item.sha256}".encode("utf-8")
            for item in inventory.items
            if item.present
        }
        # For synthetic fixtures, declared sha256 is authoritative; do not
        # re-hash placeholder bytes unless caller supplies content map.
        return verify_checksums(inventory)

    def pair_visual_thermal(self, inventory: PackageInventory) -> PairingReport:
        return pair_visual_thermal(inventory)

    def collect_warnings(
        self,
        manifest: PackageManifest,
        inventory: PackageInventory,
    ) -> List[PackageWarning]:
        warnings = collect_baseline_warnings(manifest, inventory)
        if manifest.format_id not in SUPPORTED_FORMATS:
            # Still return warnings; quality gate handles UNSUPPORTED_FORMAT.
            pass
        return warnings

    def format_supported(self, package_ref: str) -> bool:
        manifest = self.parse_manifest(package_ref)
        return manifest.format_id in SUPPORTED_FORMATS
