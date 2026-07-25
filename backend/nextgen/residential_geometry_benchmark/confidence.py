"""Explainable candidate-confidence model for PX-006B."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .constants import CONFIDENCE_STATES


def assess_confidence(
    *,
    image_count: int,
    overlap_estimate: str,
    gps_status: str,
    reconstruction_status: str,
    point_density: Optional[float],
    plane_residual: Optional[float],
    vegetation_level: str,
    oblique_coverage: str,
    benchmark_history: Optional[Sequence[str]] = None,
    occlusion_estimate: str = "unknown",
) -> Dict[str, Any]:
    contributing: List[str] = []
    degrading: List[str] = []
    missing: List[str] = []
    score = 0

    if image_count >= 75:
        score += 2
        contributing.append("adequate_image_count")
    elif image_count >= 25:
        score += 1
        contributing.append("moderate_image_count")
    else:
        degrading.append("low_image_count")
        missing.append("additional_images")

    if overlap_estimate in {"good", "high"}:
        score += 1
        contributing.append("overlap_estimate_good")
    else:
        degrading.append("overlap_unknown_or_low")

    if gps_status == "GPS_PRESENT":
        score += 1
        contributing.append("geotag_complete")
    elif gps_status == "GPS_PARTIAL":
        degrading.append("partial_gps")
    else:
        degrading.append("missing_gps")

    if reconstruction_status == "SUCCESS":
        score += 2
        contributing.append("reconstruction_success")
    else:
        degrading.append("reconstruction_not_successful")
        missing.append("successful_reconstruction")

    if point_density is not None and point_density > 1.0:
        score += 1
        contributing.append("point_density_observed")
    else:
        missing.append("point_density_measurement")

    if plane_residual is not None and plane_residual <= 0.2:
        score += 1
        contributing.append("low_plane_residual")
    elif plane_residual is not None:
        degrading.append("high_plane_residual")

    if vegetation_level in {"high", "moderate"}:
        degrading.append("vegetation_present")

    if oblique_coverage in {"limited", "none", "partial"}:
        degrading.append("limited_oblique_coverage")
        missing.append("oblique_pass")

    if benchmark_history:
        contributing.append("prior_benchmark_history")

    if score >= 6:
        state = "HIGH_DEVELOPMENT_CONFIDENCE"
    elif score >= 4:
        state = "MODERATE_DEVELOPMENT_CONFIDENCE"
    elif score >= 2:
        state = "LOW_DEVELOPMENT_CONFIDENCE"
    elif reconstruction_status != "SUCCESS":
        state = "INSUFFICIENT_EVIDENCE"
    else:
        state = "UNVALIDATED"

    if state not in CONFIDENCE_STATES:
        state = "UNVALIDATED"

    human_review_required = state in {
        "LOW_DEVELOPMENT_CONFIDENCE",
        "INSUFFICIENT_EVIDENCE",
        "UNVALIDATED",
    }

    return {
        "confidence_state": state,
        "contributing_factors": contributing,
        "degrading_factors": degrading,
        "missing_evidence": missing,
        "recommended_additional_capture": _recapture_hints(degrading, missing),
        "human_review_required": human_review_required,
        "authoritative": False,
        "physical_validation": "NOT_PERFORMED",
        "limitations": ["Development confidence only; not contractor-grade accuracy."],
    }


def _recapture_hints(degrading: Sequence[str], missing: Sequence[str]) -> List[str]:
    hints: List[str] = []
    if "limited_oblique_coverage" in degrading or "oblique_pass" in missing:
        hints.append("upper_oblique_orbit")
    if "low_image_count" in degrading or "additional_images" in missing:
        hints.append("additional_nadir_orbit")
    if "vegetation_present" in degrading:
        hints.append("vegetation_side_recapture")
    if "partial_gps" in degrading or "missing_gps" in degrading:
        hints.append("manual_checkpoint_collection")
    return hints
