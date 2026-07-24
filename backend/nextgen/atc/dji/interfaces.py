"""DJI package parser interfaces (ATC-001B foundation).

These protocols define the contract surface for future real parsers.
ATC-001B ships a synthetic implementation only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Protocol, runtime_checkable


AircraftProfileId = Literal[
    "M4E_MAPPING",
    "M4T_AWE",
    "M400_P1_MAPPING",
    "M400_H30T_AWE",
]


@dataclass
class PackageManifest:
    """Parsed package manifest — synthetic or future DJI export."""

    package_id: str
    profile_id: AircraftProfileId
    format_id: str
    format_version: str
    manifest_sha256: str
    created_at_fixture: str
    synthetic: bool = True
    live_dji_sdk: bool = False
    physical_capture_claimed: bool = False
    rtk_accuracy_claimed: bool = False


@dataclass
class InventoryItem:
    artifact_id: str
    relative_path: str
    category: str
    sha256: str
    bytes_claimed: int
    required: bool = True
    present: bool = True
    paired_with: Optional[str] = None


@dataclass
class PackageInventory:
    package_id: str
    profile_id: AircraftProfileId
    items: List[InventoryItem] = field(default_factory=list)

    def required_missing(self) -> List[str]:
        return [i.artifact_id for i in self.items if i.required and not i.present]


@dataclass
class RJPGMetadata:
    """R-JPG / radiometric metadata interface — fixture fields only.

    Does not parse real DJI radiometric JPEGs. No thermal diagnosis.
    """

    artifact_id: str
    relative_path: str
    radiometric: bool
    camera_model_fixture: str
    capture_timestamp_fixture: Optional[str] = None
    ambient_c_fixture: Optional[float] = None
    emissivity_fixture: Optional[float] = None
    automated_diagnosis: bool = False
    synthetic: bool = True
    notes: str = "Synthetic R-JPG metadata interface — not live radiometric parse"


@runtime_checkable
class DJIPackageParser(Protocol):
    """Parser foundation protocol — implement with synthetic or future real backend."""

    def parse_manifest(self, package_ref: str) -> PackageManifest: ...

    def inventory(self, package_ref: str) -> PackageInventory: ...

    def extract_rjpg_metadata(self, package_ref: str, artifact_id: str) -> RJPGMetadata: ...

    def verify_checksums(self, inventory: PackageInventory) -> "ChecksumReport": ...  # noqa: F821

    def pair_visual_thermal(self, inventory: PackageInventory) -> "PairingReport": ...  # noqa: F821

    def collect_warnings(
        self,
        manifest: PackageManifest,
        inventory: PackageInventory,
    ) -> List["PackageWarning"]: ...  # noqa: F821
