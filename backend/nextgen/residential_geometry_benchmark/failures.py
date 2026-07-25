"""Residential reconstruction failure taxonomy for PX-006B."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .constants import FAILURE_CLASSES


FAILURE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "INSUFFICIENT_OVERLAP": {
        "detector": "inventory_overlap_estimate",
        "severity": "high",
        "affected_outputs": ["reconstruction", "roof_planes"],
        "reconstruction_may_continue": False,
        "withhold_measurements": True,
        "recapture_pattern": "additional_nadir_orbit",
        "homeowner_safe_explanation": "More overlapping photos are needed before roof measurements can be proposed.",
        "audit_event": "benchmark_failure_insufficient_overlap",
    },
    "NADIR_ONLY_ROOF_LIMITATION": {
        "detector": "coverage_audit",
        "severity": "moderate",
        "affected_outputs": ["roof_edges", "wall_planes"],
        "reconstruction_may_continue": True,
        "withhold_measurements": False,
        "recapture_pattern": "upper_oblique_orbit",
        "homeowner_safe_explanation": "Roof edges may be unclear without angled photos.",
        "audit_event": "benchmark_failure_nadir_only",
    },
    "VEGETATION_OCCLUSION": {
        "detector": "suitability_audit",
        "severity": "moderate",
        "affected_outputs": ["roof_planes", "footprint"],
        "reconstruction_may_continue": True,
        "withhold_measurements": True,
        "recapture_pattern": "vegetation_side_recapture",
        "homeowner_safe_explanation": "Trees or plants may hide parts of the roof.",
        "audit_event": "benchmark_failure_vegetation",
    },
    "GCP_MISSING": {
        "detector": "inventory_gcp_check",
        "severity": "low",
        "affected_outputs": ["absolute_accuracy"],
        "reconstruction_may_continue": True,
        "withhold_measurements": False,
        "recapture_pattern": "manual_checkpoint_collection",
        "homeowner_safe_explanation": "Ground checkpoints were not available for this benchmark dataset.",
        "audit_event": "benchmark_failure_gcp_missing",
    },
    "LICENSE_BLOCKED": {
        "detector": "license_gate",
        "severity": "critical",
        "affected_outputs": ["all"],
        "reconstruction_may_continue": False,
        "withhold_measurements": True,
        "recapture_pattern": "none",
        "homeowner_safe_explanation": "This dataset cannot be processed under current license rules.",
        "audit_event": "benchmark_failure_license_blocked",
    },
    "ATTACHED_GARAGE_MERGED": {
        "detector": "segmentation_comparison",
        "severity": "moderate",
        "affected_outputs": ["footprint", "roof_planes"],
        "reconstruction_may_continue": True,
        "withhold_measurements": False,
        "recapture_pattern": "accessory_structure_separation",
        "homeowner_safe_explanation": "Garage and home may appear as one structure in the model.",
        "audit_event": "benchmark_failure_garage_merged",
    },
    "NEIGHBORING_HOME_CONTAMINATION": {
        "detector": "suitability_audit",
        "severity": "moderate",
        "affected_outputs": ["footprint", "roof_planes"],
        "reconstruction_may_continue": True,
        "withhold_measurements": True,
        "recapture_pattern": "lower_altitude_detail_orbit",
        "homeowner_safe_explanation": "Nearby buildings may interfere with structure detection.",
        "audit_event": "benchmark_failure_neighbor_contamination",
    },
    "POINT_CLOUD_HOLE": {
        "detector": "point_cloud_density",
        "severity": "moderate",
        "affected_outputs": ["roof_planes", "mesh"],
        "reconstruction_may_continue": True,
        "withhold_measurements": True,
        "recapture_pattern": "valley_focused_pass",
        "homeowner_safe_explanation": "Some roof areas did not reconstruct densely enough.",
        "audit_event": "benchmark_failure_point_cloud_hole",
    },
}


def classify_failures(context: Mapping[str, Any]) -> List[Dict[str, Any]]:
    detected: List[Dict[str, Any]] = []
    overlap = str(context.get("overlap_estimate", "unknown"))
    if overlap in {"low", "unknown"}:
        detected.append(_instance("INSUFFICIENT_OVERLAP"))
    if context.get("oblique_coverage") in {"limited", "none", "partial"}:
        detected.append(_instance("NADIR_ONLY_ROOF_LIMITATION"))
    if context.get("vegetation_level") in {"high", "moderate"}:
        detected.append(_instance("VEGETATION_OCCLUSION"))
    if context.get("gcp_present") is False and context.get("require_gcp"):
        detected.append(_instance("GCP_MISSING"))
    if context.get("license_blocked"):
        detected.append(_instance("LICENSE_BLOCKED"))
    if context.get("neighbor_contamination_risk"):
        detected.append(_instance("NEIGHBORING_HOME_CONTAMINATION"))
    if context.get("point_density") is not None and float(context["point_density"]) < 0.5:
        detected.append(_instance("POINT_CLOUD_HOLE"))
    if context.get("garage_merge_suspected"):
        detected.append(_instance("ATTACHED_GARAGE_MERGED"))
    return detected


def _instance(name: str) -> Dict[str, Any]:
    if name not in FAILURE_CLASSES:
        raise KeyError(name)
    definition = FAILURE_DEFINITIONS.get(name)
    if not definition:
        return {
            "failure_class": name,
            "detector": "taxonomy_registry",
            "severity": "unknown",
            "authoritative": False,
        }
    payload = dict(definition)
    payload["failure_class"] = name
    payload["authoritative"] = False
    payload["physical_validation"] = "NOT_PERFORMED"
    return payload


def should_withhold_measurements(failures: Sequence[Mapping[str, Any]]) -> bool:
    return any(f.get("withhold_measurements") for f in failures)
