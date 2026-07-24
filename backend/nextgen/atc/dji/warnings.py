"""Structured package warnings for DJI parser foundation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .interfaces import PackageInventory, PackageManifest


class WarningCode(str, Enum):
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    NO_LIVE_DJI_SDK = "NO_LIVE_DJI_SDK"
    NO_PHYSICAL_CAPTURE = "NO_PHYSICAL_CAPTURE"
    NO_RTK_CLAIM = "NO_RTK_CLAIM"
    MISSING_OPTIONAL_ARTIFACT = "MISSING_OPTIONAL_ARTIFACT"
    UNPAIRED_VISUAL = "UNPAIRED_VISUAL"
    FUTURE_PROFILE_STUB = "FUTURE_PROFILE_STUB"
    UNKNOWN_FORMAT_FIELD = "UNKNOWN_FORMAT_FIELD"


@dataclass(frozen=True)
class PackageWarning:
    code: WarningCode
    message: str
    artifact_id: Optional[str] = None


def collect_baseline_warnings(
    manifest: PackageManifest,
    inventory: PackageInventory,
) -> List[PackageWarning]:
    warnings: List[PackageWarning] = [
        PackageWarning(
            code=WarningCode.SYNTHETIC_FIXTURE,
            message="Package is synthetic fixture data — not field evidence",
        ),
        PackageWarning(
            code=WarningCode.NO_LIVE_DJI_SDK,
            message="No live DJI SDK invocation in ATC-001B parser foundation",
        ),
        PackageWarning(
            code=WarningCode.NO_PHYSICAL_CAPTURE,
            message="physical_capture_claimed must remain false",
        ),
        PackageWarning(
            code=WarningCode.NO_RTK_CLAIM,
            message="rtk_accuracy_claimed must remain false",
        ),
    ]
    if manifest.profile_id in {"M400_P1_MAPPING", "M400_H30T_AWE"}:
        warnings.append(
            PackageWarning(
                code=WarningCode.FUTURE_PROFILE_STUB,
                message=f"{manifest.profile_id} is a forward-compat profile stub",
            )
        )
    for item in inventory.items:
        if not item.required and not item.present:
            warnings.append(
                PackageWarning(
                    code=WarningCode.MISSING_OPTIONAL_ARTIFACT,
                    message=f"Optional artifact missing: {item.artifact_id}",
                    artifact_id=item.artifact_id,
                )
            )
    return warnings
