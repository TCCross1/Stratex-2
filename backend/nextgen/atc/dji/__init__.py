"""DJI package parser foundation — interfaces + synthetic fixtures only.

No live DJI SDK. No physical capture. No RTK accuracy claims.
"""
from __future__ import annotations

from .checksums import ChecksumReport, verify_checksums
from .interfaces import (
    DJIPackageParser,
    PackageInventory,
    PackageManifest,
    RJPGMetadata,
    InventoryItem,
)
from .pairing import PairingReport, pair_visual_thermal
from .synthetic import SyntheticDJIPackageParser, load_synthetic_fixture
from .warnings import PackageWarning, WarningCode

__all__ = [
    "ChecksumReport",
    "DJIPackageParser",
    "InventoryItem",
    "PackageInventory",
    "PackageManifest",
    "PackageWarning",
    "PairingReport",
    "RJPGMetadata",
    "SyntheticDJIPackageParser",
    "WarningCode",
    "load_synthetic_fixture",
    "pair_visual_thermal",
    "verify_checksums",
]
