"""Deterministic measurement candidates for PX-006B."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .authority_guard import assert_benchmark_object, assert_no_pricing
from .common import base_entity, new_benchmark_id, polygon_area_xy, polygon_perimeter
from .constants import ALGORITHM_VERSION


ROUNDING_RULE = "half_up_2dp"


def _round(value: float) -> float:
    return round(float(value) + 1e-12, 2)


def evaluate_withholding(
    *,
    planes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    units: str,
    coordinate_reference: str,
    confidence_state: Optional[str] = None,
    failures: Optional[Sequence[Mapping[str, Any]]] = None,
    annotation_disputed: bool = False,
) -> Optional[str]:
    """Return withholding reason or None when generation may proceed."""
    if confidence_state == "INSUFFICIENT_EVIDENCE":
        return "confidence_insufficient_evidence"
    if annotation_disputed:
        return "annotation_disagreement_unresolved"
    if not units or units.upper() in {"UNKNOWN", "UNPROVEN"}:
        return "units_unproven"
    if not coordinate_reference or coordinate_reference.upper() in {"UNKNOWN", "UNPROVEN"}:
        return "coordinate_reference_unknown"
    if not planes:
        return "supporting_geometry_incomplete"
    if any(str(e.get("detected_class")) in {"UNKNOWN", "OCCLUDED"} and e.get("material") for e in edges):
        return "edge_materially_occluded"
    for failure in failures or []:
        if failure.get("withhold_measurements"):
            return f"failure_{failure.get('failure_class')}"
        if failure.get("failure_class") in {
            "POINT_CLOUD_HOLE",
            "VEGETATION_OCCLUSION",
            "NEIGHBORING_HOME_CONTAMINATION",
            "TREE_CANOPY_CONTAMINATION",
        }:
            return f"contamination_or_hole_{failure.get('failure_class')}"
    return None


def calculate_measurement_candidates(
    *,
    dataset_id: str,
    structure_id: str,
    source_revision: str,
    reconstruction_version: str,
    odm_digest: str,
    annotation: Optional[Mapping[str, Any]] = None,
    roof_planes: Optional[Sequence[Mapping[str, Any]]] = None,
    roof_edges: Optional[Sequence[Mapping[str, Any]]] = None,
    segmentation: Optional[Mapping[str, Any]] = None,
    confidence_state: Optional[str] = None,
    failures: Optional[Sequence[Mapping[str, Any]]] = None,
    annotation_disputed: bool = False,
    units: str = "meters",
    coordinate_reference: str = "LOCAL_ENU",
) -> Dict[str, Any]:
    footprint = []
    roof_outline = []
    if annotation:
        footprint = annotation.get("building_footprint") or []
        roof_outline = annotation.get("roof_outline") or []
    elif segmentation:
        footprint = segmentation.get("segments", {}).get("building_footprint") or []
        roof_outline = segmentation.get("segments", {}).get("roof_boundary") or []
    planes = list(roof_planes or (annotation or {}).get("roof_planes") or [])
    edges = list(roof_edges or (annotation or {}).get("roof_edges") or [])

    withhold_reason = evaluate_withholding(
        planes=planes,
        edges=edges,
        units=units,
        coordinate_reference=coordinate_reference,
        confidence_state=confidence_state,
        failures=failures,
        annotation_disputed=annotation_disputed,
    )
    if withhold_reason:
        return withhold_measurements(
            withhold_reason,
            dataset_id=dataset_id,
            structure_id=structure_id,
            recapture_recommendation="human_review_or_additional_capture",
        )

    fp_tuples = [(float(p[0]), float(p[1])) for p in footprint]
    roof_tuples = [(float(p[0]), float(p[1])) for p in roof_outline]

    footprint_area = _round(polygon_area_xy(fp_tuples))
    roof_plane_areas = [_round(float(p.get("area_candidate") or 0.0)) for p in planes]
    total_roof_surface = _round(sum(roof_plane_areas))
    horizontal_projected = _round(polygon_area_xy(roof_tuples))

    edge_lengths: Dict[str, float] = {}
    for edge in edges:
        cls = str(edge.get("detected_class", "UNKNOWN"))
        if cls in {"UNKNOWN", "OCCLUDED", "INSUFFICIENT_EVIDENCE"}:
            continue
        edge_lengths[cls] = edge_lengths.get(cls, 0.0) + float(edge.get("length_candidate") or 0.0)
    for key in list(edge_lengths.keys()):
        edge_lengths[key] = _round(edge_lengths[key])

    pitches = [_round(float(p.get("slope_degrees") or 0.0)) for p in planes]
    penetration_count = sum(
        1
        for p in planes
        if str(p.get("plane_id", "")).startswith("penetration")
    )

    entity = base_entity(
        benchmark_id=new_benchmark_id("meas"),
        dataset_id=dataset_id,
        structure_id=structure_id,
        source_revision=source_revision,
        truth_classification="RECONSTRUCTION_DERIVED_CANDIDATE",
        algorithm_version=ALGORITHM_VERSION,
        reconstruction_version=reconstruction_version,
        odm_digest=odm_digest,
        source_classification="DETERMINISTIC_GEOMETRY_CALCULATION",
        limitations=[
            "Measurement candidates only; not purchase quantities or approved truth.",
            "measured_area_candidate != purchase_quantity",
        ],
    )
    measurements = {
        "footprint_area": {
            "value": footprint_area,
            "units": "square_meters",
            "formula": "shoelace_polygon_area(building_footprint)",
            "source_plane_or_edge_ids": ["building_footprint"],
            "rounding_rule": ROUNDING_RULE,
            "uncertainty": "development_only",
            "occlusion_status": "unknown",
            "status": "GENERATED",
        },
        "roof_plane_area": {
            "value": roof_plane_areas,
            "units": "square_meters",
            "formula": "per_plane_shoelace_area",
            "source_plane_or_edge_ids": [p.get("plane_id") for p in planes],
            "rounding_rule": ROUNDING_RULE,
            "status": "GENERATED",
        },
        "total_roof_surface_area": {
            "value": total_roof_surface,
            "units": "square_meters",
            "formula": "sum(roof_plane_area)",
            "rounding_rule": ROUNDING_RULE,
            "status": "GENERATED",
        },
        "horizontal_projected_roof_area": {
            "value": horizontal_projected,
            "units": "square_meters",
            "formula": "shoelace_polygon_area(roof_outline)",
            "rounding_rule": ROUNDING_RULE,
            "status": "GENERATED",
        },
        "ridge_length": {"value": edge_lengths.get("RIDGE", 0.0), "units": "meters", "status": "GENERATED"},
        "hip_length": {"value": edge_lengths.get("HIP", 0.0), "units": "meters", "status": "GENERATED"},
        "valley_length": {"value": edge_lengths.get("VALLEY", 0.0), "units": "meters", "status": "GENERATED"},
        "eave_length": {"value": edge_lengths.get("EAVE", 0.0), "units": "meters", "status": "GENERATED"},
        "rake_length": {"value": edge_lengths.get("RAKE", 0.0), "units": "meters", "status": "GENERATED"},
        "roof_pitch_degrees": {"value": pitches, "units": "degrees", "status": "GENERATED"},
        "roof_penetration_count": {"value": penetration_count, "units": "count", "status": "GENERATED"},
    }
    entity["measurements"] = measurements
    entity["status"] = "GENERATED"
    entity["estimator_distinction"] = {
        "measured_area_candidate": total_roof_surface,
        "base_quantity": None,
        "waste_quantity": None,
        "purchase_quantity": None,
        "package_rounding": None,
    }
    assert_benchmark_object(entity)
    assert_no_pricing(entity)
    return entity


def withhold_measurements(
    reason: str,
    *,
    dataset_id: str,
    structure_id: str,
    recapture_recommendation: str = "additional_capture_or_human_review",
) -> Dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "structure_id": structure_id,
        "status": "WITHHELD",
        "withheld": True,
        "reason": reason,
        "value": None,
        "recapture_or_review_recommendation": recapture_recommendation,
        "authoritative": False,
        "physical_validation": "NOT_PERFORMED",
        "measurements": {},
    }
