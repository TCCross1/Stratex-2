"""Package quality gates for ATC-001B evidence intake.

Gates (exactly these values):
- READY_FOR_REVIEW
- USABLE_WITH_LIMITATIONS
- ADDITIONAL_CAPTURE_REQUIRED
- REJECTED_PACKAGE
- UNSUPPORTED_FORMAT

Evaluation is deterministic over synthetic/fixture package reports.
Does not claim live capture quality or RTK accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, List, Mapping, Optional, Sequence


class PackageQualityGate(str, Enum):
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    USABLE_WITH_LIMITATIONS = "USABLE_WITH_LIMITATIONS"
    ADDITIONAL_CAPTURE_REQUIRED = "ADDITIONAL_CAPTURE_REQUIRED"
    REJECTED_PACKAGE = "REJECTED_PACKAGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"


@dataclass
class QualityGateResult:
    gate: PackageQualityGate
    profile_id: str
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    physical_capture_claimed: bool = False
    live_dji_sdk: bool = False

    def as_dict(self) -> dict:
        return {
            "gate": self.gate.value,
            "profile_id": self.profile_id,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "physical_capture_claimed": self.physical_capture_claimed,
            "live_dji_sdk": self.live_dji_sdk,
        }


def evaluate_package_quality(
    *,
    profile_id: str,
    format_supported: bool,
    checksums_ok: bool,
    required_artifacts_present: bool,
    pairing_ok: Optional[bool] = None,
    limitations: Optional[Sequence[str]] = None,
    hard_reject_reasons: Optional[Sequence[str]] = None,
    unsupported_reason: Optional[str] = None,
) -> QualityGateResult:
    """Deterministic quality-gate evaluation for a capture package report."""
    limitations = list(limitations or [])
    hard = list(hard_reject_reasons or [])
    warnings: List[str] = []

    if not format_supported:
        return QualityGateResult(
            gate=PackageQualityGate.UNSUPPORTED_FORMAT,
            profile_id=profile_id,
            reasons=[unsupported_reason or "package format not supported by ATC-001B parser foundation"],
            warnings=warnings,
        )

    if hard or not checksums_ok:
        reasons = hard or ["checksum verification failed"]
        if not checksums_ok and "checksum verification failed" not in reasons:
            reasons.append("checksum verification failed")
        return QualityGateResult(
            gate=PackageQualityGate.REJECTED_PACKAGE,
            profile_id=profile_id,
            reasons=reasons,
            warnings=warnings,
        )

    if not required_artifacts_present:
        return QualityGateResult(
            gate=PackageQualityGate.ADDITIONAL_CAPTURE_REQUIRED,
            profile_id=profile_id,
            reasons=["required artifacts missing — additional capture required"],
            warnings=warnings + limitations,
        )

    if pairing_ok is False:
        return QualityGateResult(
            gate=PackageQualityGate.ADDITIONAL_CAPTURE_REQUIRED,
            profile_id=profile_id,
            reasons=["visual/thermal pairing incomplete — additional capture required"],
            warnings=warnings + limitations,
        )

    if limitations:
        return QualityGateResult(
            gate=PackageQualityGate.USABLE_WITH_LIMITATIONS,
            profile_id=profile_id,
            reasons=["package usable with explicit limitations"],
            warnings=list(limitations),
        )

    return QualityGateResult(
        gate=PackageQualityGate.READY_FOR_REVIEW,
        profile_id=profile_id,
        reasons=["synthetic package meets ATC-001B review gate (fixture only)"],
        warnings=warnings,
    )


def gate_values() -> List[str]:
    return [g.value for g in PackageQualityGate]
