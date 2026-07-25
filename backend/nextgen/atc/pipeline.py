"""Fixture pipeline: parse synthetic package → quality gate.

Helper for tests and future orchestration. No Passport writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .boundary import EvidenceBoundary, ProducerOutputKind, boundary_for
from .dji.synthetic import SyntheticDJIPackageParser
from .dji.warnings import PackageWarning
from .quality_gates import PackageQualityGate, QualityGateResult, evaluate_package_quality


@dataclass
class PackageAssessment:
    profile_id: str
    quality: QualityGateResult
    warnings: List[PackageWarning]
    producer_outputs: List[str]
    checksums_ok: bool
    pairing_ok: Optional[bool]
    format_supported: bool


def assess_synthetic_package(
    profile_id: str,
    *,
    parser: Optional[SyntheticDJIPackageParser] = None,
    limitations: Optional[List[str]] = None,
) -> PackageAssessment:
    parser = parser or SyntheticDJIPackageParser()
    boundary = boundary_for(profile_id)
    manifest = parser.parse_manifest(profile_id)
    inventory = parser.inventory(profile_id)
    checksums = parser.verify_checksums(inventory)
    pairing = parser.pair_visual_thermal(inventory)
    warnings = parser.collect_warnings(manifest, inventory)
    format_ok = parser.format_supported(profile_id)
    required_ok = not inventory.required_missing()

    # Pairing only required for AWE producer profiles.
    pairing_required = boundary.may_produce(ProducerOutputKind.AWE_EVIDENCE_CANDIDATE)
    pairing_ok: Optional[bool] = pairing.ok if pairing_required else None

    # C-N-003: synthetic/parser honesty limitations must affect the quality gate.
    # Pipeline remains foundational — candidate/readiness only; no complete review
    # or approval claim. Missing professional review stays explicit.
    honesty_codes = []
    for w in warnings:
        code = getattr(w, "code", w)
        honesty_codes.append(code.value if hasattr(code, "value") else str(code))
    honesty_limitations = list(limitations or [])
    for code in honesty_codes:
        if code not in honesty_limitations:
            honesty_limitations.append(code)
    # Always mark synthetic fixture path as limited.
    if "SYNTHETIC_FIXTURE" not in honesty_limitations:
        honesty_limitations.append("SYNTHETIC_FIXTURE")
    if "MISSING_PROFESSIONAL_REVIEW" not in honesty_limitations:
        honesty_limitations.append("MISSING_PROFESSIONAL_REVIEW")

    quality = evaluate_package_quality(
        profile_id=profile_id,
        format_supported=format_ok,
        checksums_ok=checksums.ok,
        required_artifacts_present=required_ok,
        pairing_ok=pairing_ok,
        limitations=honesty_limitations,
    )
    return PackageAssessment(
        profile_id=profile_id,
        quality=quality,
        warnings=warnings,
        producer_outputs=sorted(k.value for k in boundary.spec.producer_outputs),
        checksums_ok=checksums.ok,
        pairing_ok=pairing_ok,
        format_supported=format_ok,
    )
