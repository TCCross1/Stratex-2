"""ATC-001B evidence producer/consumer boundary package.

Owns executable boundary, compatibility validation, DJI parser foundation
(synthetic fixtures only), and package quality gates.

Does **not** own Passport writer, governed publisher, or approval authority.
Does **not** claim live DJI SDK, RTK accuracy, or physical field flights.
"""
from __future__ import annotations

from .authority import AuthorityViolation, refuse_approved_emission, refuse_passport_write
from .boundary import (
    EVIDENCE_PROFILES,
    PROFILE_IDS,
    ConsumerKind,
    EvidenceBoundary,
    ProducerOutputKind,
    boundary_for,
)
from .compatibility import CompatibilityIssue, CompatibilityResult, validate_compatibility
from .quality_gates import PackageQualityGate, QualityGateResult, evaluate_package_quality

__all__ = [
    "AuthorityViolation",
    "CompatibilityIssue",
    "CompatibilityResult",
    "ConsumerKind",
    "EVIDENCE_PROFILES",
    "EvidenceBoundary",
    "PROFILE_IDS",
    "PackageQualityGate",
    "ProducerOutputKind",
    "QualityGateResult",
    "boundary_for",
    "evaluate_package_quality",
    "refuse_approved_emission",
    "refuse_passport_write",
    "validate_compatibility",
]
