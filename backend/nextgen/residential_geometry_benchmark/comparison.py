"""Benchmark comparison metrics for PX-006B."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from .common import angular_difference_deg, iou_polygons, percent_difference
from .constants import METRIC_GROUPS


def compare_candidates_to_benchmark(
    *,
    benchmark_annotation: Mapping[str, Any],
    candidate_planes: Sequence[Mapping[str, Any]],
    candidate_segmentation: Mapping[str, Any],
    candidate_measurements: Mapping[str, Any],
) -> Dict[str, Any]:
    truth_planes = benchmark_annotation.get("roof_planes") or []
    cand_planes = list(candidate_planes)
    truth_fp = benchmark_annotation.get("building_footprint") or []
    cand_fp = candidate_segmentation.get("segments", {}).get("building_footprint") or []
    truth_roof = benchmark_annotation.get("roof_outline") or []
    cand_roof = candidate_segmentation.get("segments", {}).get("roof_boundary") or []

    structure_iou = iou_polygons(truth_fp, cand_fp)
    roof_boundary_iou = iou_polygons(truth_roof, cand_roof)
    plane_count_difference = abs(len(truth_planes) - len(cand_planes))
    slope_diffs: List[float] = []
    azimuth_diffs: List[float] = []
    area_abs_diffs: List[float] = []
    area_pct_diffs: List[Optional[float]] = []
    pair_count = min(len(truth_planes), len(cand_planes))
    false_split = plane_count_difference > 0 and len(cand_planes) > len(truth_planes)
    missed_plane = plane_count_difference > 0 and len(cand_planes) < len(truth_planes)
    merged_planes = len(cand_planes) < len(truth_planes) and len(cand_planes) == 1 and len(truth_planes) > 1

    for idx in range(pair_count):
        tp = truth_planes[idx]
        cp = cand_planes[idx]
        if "slope_degrees" in tp and "slope_degrees" in cp:
            slope_diffs.append(abs(float(tp["slope_degrees"]) - float(cp["slope_degrees"])))
        if "azimuth_degrees" in tp and "azimuth_degrees" in cp:
            azimuth_diffs.append(
                angular_difference_deg(float(tp["azimuth_degrees"]), float(cp["azimuth_degrees"]))
            )
        if "area_candidate" in tp and "area_candidate" in cp:
            t_area = float(tp["area_candidate"])
            c_area = float(cp["area_candidate"])
            area_abs_diffs.append(abs(t_area - c_area))
            area_pct_diffs.append(percent_difference(t_area, c_area))

    truth_area = sum(float(p.get("area_candidate") or 0.0) for p in truth_planes)
    cand_area = float(
        (candidate_measurements.get("measurements") or {})
        .get("total_roof_surface_area", {})
        .get("value", 0.0)
    )
    total_area_pct = percent_difference(truth_area, cand_area)

    precision = structure_iou
    recall = roof_boundary_iou
    f1 = 0.0
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)

    groups = {
        "STRUCTURE_SEGMENTATION": {"iou": structure_iou, "precision_proxy": precision, "recall_proxy": recall, "f1_proxy": f1},
        "ROOF_BOUNDARY": {"iou": roof_boundary_iou},
        "ROOF_PLANES": {
            "plane_count_difference": plane_count_difference,
            "false_split": false_split,
            "missed_plane": missed_plane,
            "merged_planes": merged_planes,
        },
        "ROOF_SLOPE": {"slope_differences_deg": slope_diffs, "azimuth_differences_deg": azimuth_diffs},
        "AREA_CANDIDATES": {
            "area_absolute_differences": area_abs_diffs,
            "area_percentage_differences": area_pct_diffs,
            "total_area_percentage_difference": total_area_pct,
        },
    }
    return {
        "benchmark_id": benchmark_annotation.get("benchmark_id"),
        "metric_groups": groups,
        "combined_score": None,
        "authoritative": False,
        "physical_validation": "NOT_PERFORMED",
        "limitations": ["Separate metric groups; no single misleading composite score."],
    }


def summarize_matrix_row(
    *,
    structure_id: str,
    dataset_id: str,
    comparison: Mapping[str, Any],
    confidence_state: str,
    failure_classes: Sequence[str],
    disposition: str,
) -> Dict[str, Any]:
    groups = comparison.get("metric_groups") or {}
    return {
        "benchmark_structure_id": structure_id,
        "dataset": dataset_id,
        "structure_iou": (groups.get("STRUCTURE_SEGMENTATION") or {}).get("iou"),
        "roof_boundary_metric": (groups.get("ROOF_BOUNDARY") or {}).get("iou"),
        "roof_plane_metric": groups.get("ROOF_PLANES"),
        "area_difference": (groups.get("AREA_CANDIDATES") or {}).get("total_area_percentage_difference"),
        "confidence_state": confidence_state,
        "failure_classes": list(failure_classes),
        "benchmark_disposition": disposition,
        "authoritative": False,
    }
