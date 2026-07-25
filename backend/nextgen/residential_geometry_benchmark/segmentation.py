"""Structure segmentation candidates for PX-006B."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .authority_guard import assert_benchmark_object
from .common import base_entity, iou_polygons, new_benchmark_id, polygon_area_xy
from .constants import ALGORITHM_VERSION, SEGMENTATION_STATES


class SegmentationError(RuntimeError):
    pass


def _validate_state(state: str) -> None:
    if state not in SEGMENTATION_STATES:
        raise SegmentationError(f"invalid segmentation state: {state}")


def propose_structure_segmentation(
    *,
    dataset_id: str,
    structure_id: str,
    source_revision: str,
    reconstruction_version: str,
    odm_digest: str,
    input_artifact: str,
    input_checksum: str,
    algorithm_id: str,
    algorithm_version: str,
    footprint_polygon: Sequence[Tuple[float, float]],
    primary_structure: Sequence[Tuple[float, float]],
    roof_boundary: Sequence[Tuple[float, float]],
    background_terrain: Sequence[Tuple[float, float]],
    vegetation_mask: Sequence[Tuple[float, float]],
    confidence: float,
    review_state: str = "PROPOSED",
    human_edit_history: Optional[List[Dict[str, Any]]] = None,
    uncertainty: Optional[str] = None,
) -> Dict[str, Any]:
    _validate_state(review_state)
    entity = base_entity(
        benchmark_id=new_benchmark_id("seg"),
        dataset_id=dataset_id,
        structure_id=structure_id,
        source_revision=source_revision,
        truth_classification="RECONSTRUCTION_DERIVED_CANDIDATE",
        algorithm_version=algorithm_version,
        reconstruction_version=reconstruction_version,
        odm_digest=odm_digest,
        source_classification="MACHINE_PROPOSED_SEGMENTATION",
        limitations=[
            "Segmentation is proposed only; AI does not approve geometry.",
            "No ApprovedGeometry emission.",
        ],
    )
    entity.update(
        {
            "algorithm_id": algorithm_id,
            "input_artifact": input_artifact,
            "input_checksum": input_checksum,
            "confidence": confidence,
            "review_state": review_state,
            "human_edit_history": human_edit_history or [],
            "uncertainty": uncertainty,
            "segments": {
                "building_footprint": [list(p) for p in footprint_polygon],
                "primary_structure": [list(p) for p in primary_structure],
                "roof_boundary": [list(p) for p in roof_boundary],
                "background_terrain": [list(p) for p in background_terrain],
                "vegetation": [list(p) for p in vegetation_mask],
            },
        }
    )
    assert_benchmark_object(entity)
    return entity


def segment_from_orthophoto_bounds(
    *,
    dataset_id: str,
    structure_id: str,
    source_revision: str,
    reconstruction_version: str,
    odm_digest: str,
    orthophoto_path: str,
    bounds: Mapping[str, float],
) -> Dict[str, Any]:
    """Deterministic bbox segmentation from orthophoto extent metadata."""
    x0 = float(bounds["x_min"])
    y0 = float(bounds["y_min"])
    x1 = float(bounds["x_max"])
    y1 = float(bounds["y_max"])
    width = max(x1 - x0, 1.0)
    height = max(y1 - y0, 1.0)
    margin_x = width * 0.15
    margin_y = height * 0.15
    footprint = [
        (x0 + margin_x, y0 + margin_y),
        (x1 - margin_x, y0 + margin_y),
        (x1 - margin_x, y1 - margin_y),
        (x0 + margin_x, y1 - margin_y),
    ]
    roof = [
        (x0 + margin_x * 1.2, y0 + margin_y * 1.2),
        (x1 - margin_x * 1.2, y0 + margin_y * 1.2),
        (x1 - margin_x * 1.2, y1 - margin_y * 1.2),
        (x0 + margin_x * 1.2, y1 - margin_y * 1.2),
    ]
    return propose_structure_segmentation(
        dataset_id=dataset_id,
        structure_id=structure_id,
        source_revision=source_revision,
        reconstruction_version=reconstruction_version,
        odm_digest=odm_digest,
        input_artifact=orthophoto_path,
        input_checksum="derived_from_reconstruction_receipt",
        algorithm_id="orthophoto_extent_bbox_v1",
        algorithm_version=ALGORITHM_VERSION,
        footprint_polygon=footprint,
        primary_structure=footprint,
        roof_boundary=roof,
        background_terrain=[],
        vegetation_mask=[],
        confidence=0.45,
        review_state="REVIEW_REQUIRED",
        uncertainty="Extent-only heuristic; requires manual benchmark review.",
    )


def segmentation_footprint_area(segment: Mapping[str, Any]) -> float:
    points = segment.get("segments", {}).get("building_footprint") or []
    tuples = [(float(p[0]), float(p[1])) for p in points]
    return polygon_area_xy(tuples)


def compare_segmentation_to_annotation(
    segmentation: Mapping[str, Any],
    annotation: Mapping[str, Any],
) -> Dict[str, Any]:
    seg_fp = segmentation.get("segments", {}).get("building_footprint") or []
    ann_fp = annotation.get("building_footprint") or []
    seg_roof = segmentation.get("segments", {}).get("roof_boundary") or []
    ann_roof = annotation.get("roof_outline") or []
    return {
        "structure_iou": iou_polygons(seg_fp, ann_fp),
        "roof_boundary_iou": iou_polygons(seg_roof, ann_roof),
        "metric_group": "STRUCTURE_SEGMENTATION",
        "authoritative": False,
    }
