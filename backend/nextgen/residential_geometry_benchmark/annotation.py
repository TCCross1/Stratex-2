"""Manual annotation workflow for PX-006B benchmark truth."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .authority_guard import assert_benchmark_object
from .common import base_entity, benchmark_annotations_dir, new_benchmark_id, now_iso, write_json
from .constants import ALGORITHM_VERSION, ANNOTATION_REVIEW_STATES, TRUTH_CLASSIFICATIONS


class AnnotationError(RuntimeError):
    pass


def _validate_review_state(state: str) -> None:
    if state not in ANNOTATION_REVIEW_STATES:
        raise AnnotationError(f"invalid review state: {state}")


def _validate_truth_classification(value: str) -> None:
    if value not in TRUTH_CLASSIFICATIONS:
        raise AnnotationError(f"invalid truth classification: {value}")


def create_annotation_pass(
    *,
    dataset_id: str,
    structure_id: str,
    source_revision: str,
    annotator: str,
    annotation_method: str,
    source_view: str,
    confidence: str,
    uncertainty_reason: Optional[str],
    coordinate_system: str,
    truth_classification: str,
    review_state: str,
    building_footprint: Sequence[Tuple[float, float]],
    roof_outline: Sequence[Tuple[float, float]],
    roof_planes: Sequence[Mapping[str, Any]],
    roof_edges: Sequence[Mapping[str, Any]],
    obscured_regions: Sequence[Mapping[str, Any]],
    uncertain_regions: Sequence[Mapping[str, Any]],
    reconstruction_version: str,
    odm_digest: str,
    source_classification: str,
    pass_id: Optional[str] = None,
) -> Dict[str, Any]:
    _validate_truth_classification(truth_classification)
    _validate_review_state(review_state)
    benchmark_id = pass_id or new_benchmark_id("anno")
    entity = base_entity(
        benchmark_id=benchmark_id,
        dataset_id=dataset_id,
        structure_id=structure_id,
        source_revision=source_revision,
        truth_classification=truth_classification,
        coordinate_reference=coordinate_system,
        algorithm_version=ALGORITHM_VERSION,
        reconstruction_version=reconstruction_version,
        odm_digest=odm_digest,
        created_by=annotator,
        source_classification=source_classification,
        limitations=[
            "Manual benchmark annotation; not canonical property truth.",
            "No contractor-grade dimensional claim.",
        ],
    )
    entity.update(
        {
            "annotation_method": annotation_method,
            "source_view": source_view,
            "confidence": confidence,
            "uncertainty_reason": uncertainty_reason,
            "review_state": review_state,
            "version": "manual_v1",
            "revision_history": [{"at": now_iso(), "action": "created", "by": annotator}],
            "building_footprint": [list(p) for p in building_footprint],
            "roof_outline": [list(p) for p in roof_outline],
            "roof_planes": list(roof_planes),
            "roof_edges": list(roof_edges),
            "obscured_regions": list(obscured_regions),
            "uncertain_regions": list(uncertain_regions),
        }
    )
    assert_benchmark_object(entity)
    return entity


def compute_inter_annotator_disagreement(
    pass_a: Mapping[str, Any],
    pass_b: Mapping[str, Any],
) -> Dict[str, Any]:
    from .common import angular_difference_deg, iou_polygons, percent_difference

    footprint_iou = iou_polygons(pass_a.get("building_footprint") or [], pass_b.get("building_footprint") or [])
    roof_iou = iou_polygons(pass_a.get("roof_outline") or [], pass_b.get("roof_outline") or [])
    planes_a = pass_a.get("roof_planes") or []
    planes_b = pass_b.get("roof_planes") or []
    plane_count_delta = abs(len(planes_a) - len(planes_b))
    slope_diffs: List[float] = []
    azimuth_diffs: List[float] = []
    pair_count = min(len(planes_a), len(planes_b))
    for idx in range(pair_count):
        pa = planes_a[idx]
        pb = planes_b[idx]
        if "slope_degrees" in pa and "slope_degrees" in pb:
            slope_diffs.append(abs(float(pa["slope_degrees"]) - float(pb["slope_degrees"])))
        if "azimuth_degrees" in pa and "azimuth_degrees" in pb:
            azimuth_diffs.append(
                angular_difference_deg(float(pa["azimuth_degrees"]), float(pb["azimuth_degrees"]))
            )
    area_diffs: List[Optional[float]] = []
    for idx in range(pair_count):
        pa = planes_a[idx]
        pb = planes_b[idx]
        if "area_candidate" in pa and "area_candidate" in pb:
            area_diffs.append(percent_difference(float(pa["area_candidate"]), float(pb["area_candidate"])))
    return {
        "pass_a": pass_a.get("benchmark_id"),
        "pass_b": pass_b.get("benchmark_id"),
        "footprint_iou": footprint_iou,
        "roof_boundary_iou": roof_iou,
        "plane_count_difference": plane_count_delta,
        "slope_differences_deg": slope_diffs,
        "azimuth_differences_deg": azimuth_diffs,
        "area_percent_differences": area_diffs,
        "preserved_without_averaging": True,
        "review_state": "DISPUTED" if footprint_iou < 0.85 or plane_count_delta > 0 else "SECOND_REVIEW_REQUIRED",
        "authoritative": False,
        "physical_validation": "NOT_PERFORMED",
    }


def persist_annotation_pass(entity: Mapping[str, Any]) -> str:
    assert_benchmark_object(entity)
    path = (
        benchmark_annotations_dir()
        / entity["dataset_id"]
        / entity["structure_id"]
        / f"{entity['benchmark_id']}.json"
    )
    write_json(path, dict(entity))
    return str(path)
