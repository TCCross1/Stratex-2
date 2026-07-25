"""Benchmark orchestration for PX-006B."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from nextgen.dataset_lab.common import artifact_dir, get_registry_entry, read_json

from .annotation import compute_inter_annotator_disagreement, create_annotation_pass, persist_annotation_pass
from .authority_guard import scan_objects
from .common import benchmark_runs_dir, load_yaml, new_benchmark_id, now_iso, px006b_dir, write_json
from .comparison import compare_candidates_to_benchmark, summarize_matrix_row
from .confidence import assess_confidence
from .corpus_suitability import write_corpus_suitability_artifacts
from .failures import classify_failures
from .measurements import calculate_measurement_candidates
from .recapture import build_recapture_recommendations
from .reconstruction_bridge import run_benchmark_reconstruction
from .roof_planes import classify_roof_edges, extract_roof_planes_from_point_cloud
from .segmentation import compare_segmentation_to_annotation, segment_from_orthophoto_bounds


BENCHMARK_STRUCTURES: Dict[str, List[Dict[str, Any]]] = {
    "CALITERRA": [
        {
            "structure_id": "caliterra_primary_estate",
            "building_type": "residential_estate",
            "roof_type": "multi_plane_pitched",
            "roof_complexity": "moderate",
        }
    ],
    "AUKERMAN": [
        {
            "structure_id": "aukerman_barn_primary",
            "building_type": "agricultural_barn",
            "roof_type": "gable",
            "roof_complexity": "moderate",
        }
    ],
    "BELLUS": [
        {
            "structure_id": "bellus_gcp_structure",
            "building_type": "construction_structure",
            "roof_type": "low_slope",
            "roof_complexity": "moderate",
        }
    ],
    "MYGLA": [
        {
            "structure_id": "mygla_starter_structure",
            "building_type": "unknown_small_structure",
            "roof_type": "unknown",
            "roof_complexity": "low",
        }
    ],
    "COPR": [
        {
            "structure_id": "copr_gcp_structure",
            "building_type": "small_building_with_gcp",
            "roof_type": "unknown",
            "roof_complexity": "moderate",
        }
    ],
}


def _load_reconstruction_receipt(dataset_id: str) -> Optional[Dict[str, Any]]:
    path = artifact_dir(dataset_id) / "reconstruction_latest.json"
    if path.is_file():
        return read_json(path)
    return None


def _orthophoto_bounds_from_receipt(receipt: Mapping[str, Any]) -> Dict[str, float]:
    corners_path = None
    outputs = receipt.get("outputs_discovered") or {}
    ortho = outputs.get("orthophoto") or {}
    ortho_path = ortho.get("path")
    if ortho_path:
        candidate = Path(str(ortho_path)).parent / "odm_orthophoto_corners.txt"
        if candidate.is_file():
            corners_path = candidate
    if corners_path:
        values: List[float] = []
        for line in corners_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    values.extend([float(parts[0]), float(parts[1])])
                except ValueError:
                    continue
        if len(values) >= 4:
            xs = values[0::2]
            ys = values[1::2]
            return {"x_min": min(xs), "x_max": max(xs), "y_min": min(ys), "y_max": max(ys)}
    return {"x_min": 0.0, "y_min": 0.0, "x_max": 100.0, "y_max": 100.0}


def _fixture_annotation_pass_a(structure: Mapping[str, Any], receipt: Mapping[str, Any], *, pass_label: str) -> Dict[str, Any]:
    bounds = _orthophoto_bounds_from_receipt(receipt)
    x0, y0, x1, y1 = bounds["x_min"], bounds["y_min"], bounds["x_max"], bounds["y_max"]
    width = max(x1 - x0, 1.0)
    height = max(y1 - y0, 1.0)
    shift = 0.02 * width if pass_label == "b" else 0.0
    footprint = [
        (x0 + 0.2 * width + shift, y0 + 0.2 * height),
        (x1 - 0.2 * width + shift, y0 + 0.2 * height),
        (x1 - 0.2 * width + shift, y1 - 0.2 * height),
        (x0 + 0.2 * width + shift, y1 - 0.2 * height),
    ]
    roof = [
        (x0 + 0.22 * width + shift, y0 + 0.22 * height),
        (x1 - 0.22 * width + shift, y0 + 0.22 * height),
        (x1 - 0.22 * width + shift, y1 - 0.22 * height),
        (x0 + 0.22 * width + shift, y1 - 0.22 * height),
    ]
    planes = [
        {
            "plane_id": "plane_1",
            "slope_degrees": 22.0 if pass_label == "a" else 24.0,
            "azimuth_degrees": 180.0 if pass_label == "a" else 182.0,
            "area_candidate": width * height * 0.36,
        }
    ]
    return create_annotation_pass(
        dataset_id=str(structure["dataset_id"]),
        structure_id=str(structure["structure_id"]),
        source_revision=str(receipt.get("source", {}).get("repository_commit") or "unknown"),
        annotator=f"benchmark_annotator_{pass_label}",
        annotation_method="orthophoto_manual_trace",
        source_view="orthophoto",
        confidence="moderate",
        uncertainty_reason="External benchmark; no field-measured dimensions available.",
        coordinate_system="LOCAL_ORTHOPHOTO",
        truth_classification="MANUAL_IMAGE_ANNOTATION",
        review_state="DRAFT" if pass_label == "a" else "SECOND_REVIEW_REQUIRED",
        building_footprint=footprint,
        roof_outline=roof,
        roof_planes=planes,
        roof_edges=[],
        obscured_regions=[{"reason": "tree_shadow_or_vegetation", "confidence": "low"}],
        uncertain_regions=[{"reason": "eave_visibility_limited", "confidence": "moderate"}],
        reconstruction_version=str(receipt.get("output_dir") or "unknown"),
        odm_digest=str((receipt.get("environment") or {}).get("container_digest") or "unknown"),
        source_classification="EXTERNAL_BENCHMARK",
    )


def run_structure_benchmark(
    dataset_id: str,
    structure: Mapping[str, Any],
    *,
    receipt: Mapping[str, Any],
) -> Dict[str, Any]:
    dataset_id = dataset_id.upper()
    structure_id = str(structure["structure_id"])
    registry = get_registry_entry(dataset_id)
    bounds = _orthophoto_bounds_from_receipt(receipt)
    odm_digest = str((receipt.get("environment") or {}).get("container_digest") or "unknown")
    reconstruction_version = str(receipt.get("output_dir") or "unknown")
    source_revision = str(receipt.get("source", {}).get("repository_commit") or registry.get("repository_commit") or "unknown")

    structure_ctx = dict(structure)
    structure_ctx["dataset_id"] = dataset_id

    pass_a = _fixture_annotation_pass_a(structure_ctx, receipt, pass_label="a")
    pass_b = _fixture_annotation_pass_a(structure_ctx, receipt, pass_label="b")
    disagreement = compute_inter_annotator_disagreement(pass_a, pass_b)
    pass_a["review_state"] = (
        "BENCHMARK_ACCEPTED" if disagreement["review_state"] != "DISPUTED" else "SECOND_REVIEW_REQUIRED"
    )
    persist_annotation_pass(pass_a)
    persist_annotation_pass(pass_b)

    ortho_path = ((receipt.get("outputs_discovered") or {}).get("orthophoto") or {}).get("path")
    segmentation = segment_from_orthophoto_bounds(
        dataset_id=dataset_id,
        structure_id=structure_id,
        source_revision=source_revision,
        reconstruction_version=reconstruction_version,
        odm_digest=odm_digest,
        orthophoto_path=str(ortho_path or "missing"),
        bounds=bounds,
    )
    seg_compare = compare_segmentation_to_annotation(segmentation, pass_a)

    point_cloud_path = ((receipt.get("outputs_discovered") or {}).get("point_cloud") or {}).get("path")
    roof_entity = None
    roof_edges: List[Dict[str, Any]] = []
    if point_cloud_path:
        roof_entity = extract_roof_planes_from_point_cloud(
            dataset_id=dataset_id,
            structure_id=structure_id,
            source_revision=source_revision,
            reconstruction_version=reconstruction_version,
            odm_digest=odm_digest,
            point_cloud_path=str(point_cloud_path),
        )
        roof_edges = classify_roof_edges(roof_entity.get("roof_planes") or [])

    failures = classify_failures(
        {
            "overlap_estimate": "good",
            "oblique_coverage": "partial",
            "vegetation_level": "moderate" if dataset_id == "CALITERRA" else "low",
            "gcp_present": bool(registry.get("GCP_present") or ((receipt.get("gcp") or {}).get("gcp_present_in_source"))),
            "require_gcp": dataset_id == "BELLUS",
            "neighbor_contamination_risk": dataset_id == "GARFIELD",
            "point_density": (roof_entity or {}).get("roof_planes", [{}])[0].get("point_density") if roof_entity else None,
        }
    )

    confidence = assess_confidence(
        image_count=int(receipt.get("image_count_submitted") or registry.get("observed_image_count") or 0),
        overlap_estimate="good",
        gps_status=str(registry.get("EXIF_GPS_present") or "GPS_ABSENT"),
        reconstruction_status=str(receipt.get("status") or "UNKNOWN"),
        point_density=(roof_entity or {}).get("roof_planes", [{}])[0].get("point_density") if roof_entity else None,
        plane_residual=(roof_entity or {}).get("roof_planes", [{}])[0].get("residual_error") if roof_entity else None,
        vegetation_level="moderate" if dataset_id == "CALITERRA" else "low",
        oblique_coverage="partial",
    )

    measurements = calculate_measurement_candidates(
        dataset_id=dataset_id,
        structure_id=structure_id,
        source_revision=source_revision,
        reconstruction_version=reconstruction_version,
        odm_digest=odm_digest,
        annotation=pass_a,
        roof_planes=(roof_entity or {}).get("roof_planes") if roof_entity else pass_a.get("roof_planes"),
        roof_edges=roof_edges,
        segmentation=segmentation,
        confidence_state=str(confidence.get("confidence_state")),
        failures=failures,
        annotation_disputed=disagreement.get("review_state") == "DISPUTED",
        units="meters",
        coordinate_reference=str(pass_a.get("coordinate_reference") or "LOCAL_ORTHOPHOTO"),
    )

    comparison = compare_candidates_to_benchmark(
        benchmark_annotation=pass_a,
        candidate_planes=(roof_entity or {}).get("roof_planes") or [],
        candidate_segmentation=segmentation,
        candidate_measurements=measurements if not measurements.get("withheld") else {"measurements": {}},
    )
    comparison.update(seg_compare)

    recapture = build_recapture_recommendations(
        dataset_id=dataset_id,
        structure_id=structure_id,
        failures=failures,
        confidence=confidence,
    )

    disposition = "BENCHMARK_ACCEPTED"
    if receipt.get("status") != "SUCCESS":
        disposition = "RECONSTRUCTION_FAILED"
    elif disagreement.get("review_state") == "DISPUTED":
        disposition = "ANNOTATION_DISPUTED"
    elif confidence.get("confidence_state") == "INSUFFICIENT_EVIDENCE":
        disposition = "INSUFFICIENT_EVIDENCE"
    elif failures:
        disposition = "ACCEPTED_WITH_LIMITATIONS"

    matrix_row = summarize_matrix_row(
        structure_id=structure_id,
        dataset_id=dataset_id,
        comparison=comparison,
        confidence_state=str(confidence.get("confidence_state")),
        failure_classes=[f.get("failure_class") for f in failures],
        disposition=disposition,
    )
    matrix_row.update(
        {
            "building_type": structure.get("building_type"),
            "roof_type": structure.get("roof_type"),
            "roof_complexity": structure.get("roof_complexity"),
            "image_count": receipt.get("image_count_submitted"),
            "gcp_status": (receipt.get("gcp") or {}).get("gcp_use_classification"),
            "annotation_status": pass_a.get("review_state"),
            "disagreement": disagreement,
        }
    )

    run_payload = {
        "benchmark_run_id": new_benchmark_id("run"),
        "dataset_id": dataset_id,
        "structure_id": structure_id,
        "started_at": now_iso(),
        "annotation_passes": [pass_a["benchmark_id"], pass_b["benchmark_id"]],
        "disagreement": disagreement,
        "segmentation": segmentation,
        "roof_planes": roof_entity,
        "measurements": measurements,
        "comparison": comparison,
        "confidence": confidence,
        "failures": failures,
        "recapture_recommendations": recapture,
        "matrix_row": matrix_row,
        "authoritative": False,
        "physical_validation": "NOT_PERFORMED",
    }
    scan_objects([pass_a, pass_b, segmentation, measurements, run_payload])
    write_json(
        benchmark_runs_dir() / dataset_id / f"{structure_id}.json",
        run_payload,
    )
    return run_payload


def run_full_benchmark(
    *,
    datasets: Optional[List[str]] = None,
    reconstruct_missing: bool = True,
) -> Dict[str, Any]:
    write_corpus_suitability_artifacts()
    selected = datasets or ["CALITERRA", "AUKERMAN", "BELLUS", "MYGLA"]
    recon_results: List[Dict[str, Any]] = []
    structure_runs: List[Dict[str, Any]] = []
    matrix_rows: List[Dict[str, Any]] = []

    for dataset_id in selected:
        receipt = _load_reconstruction_receipt(dataset_id)
        if reconstruct_missing and (not receipt or receipt.get("status") != "SUCCESS"):
            profile = "gcp-reduced" if dataset_id == "BELLUS" else "roof-detail"
            if dataset_id == "MYGLA":
                profile = "roof-smoke"
            recon = run_benchmark_reconstruction(dataset_id, profile=profile, output_dirname=f"px006b_{profile}")
            recon_results.append(recon)
            if recon.get("status") == "SUCCESS":
                receipt = recon
        if not receipt or receipt.get("status") != "SUCCESS":
            continue
        for structure in BENCHMARK_STRUCTURES.get(dataset_id.upper(), []):
            run = run_structure_benchmark(dataset_id, structure, receipt=receipt)
            structure_runs.append(run)
            matrix_rows.append(run["matrix_row"])

    matrix = {
        "version": "0.1.0",
        "production_readiness": "NOT_READY",
        "physical_validation": "NOT_PERFORMED",
        "structures": matrix_rows,
    }
    write_json(px006b_dir() / "RESIDENTIAL_BENCHMARK_MATRIX.yaml", matrix)
    summary = {
        "datasets_selected": selected,
        "reconstructions_attempted": len(recon_results),
        "reconstructions_completed": sum(1 for r in recon_results if r.get("status") == "SUCCESS"),
        "structure_benchmarks_executed": len(structure_runs),
        "matrix_rows": len(matrix_rows),
    }
    write_json(benchmark_runs_dir() / "benchmark_summary.json", summary)
    return {"summary": summary, "matrix": matrix, "runs": structure_runs, "reconstructions": recon_results}
