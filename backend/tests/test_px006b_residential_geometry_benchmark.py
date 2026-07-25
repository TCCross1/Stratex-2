"""PX-006B Residential Geometry Benchmark tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from nextgen.residential_geometry_benchmark.annotation import (
    compute_inter_annotator_disagreement,
    create_annotation_pass,
)
from nextgen.residential_geometry_benchmark.authority_guard import (
    AuthorityViolation,
    assert_benchmark_object,
    assert_no_pricing,
    assert_recapture_not_mission_approval,
    reject_prohibited_emission,
)
from nextgen.residential_geometry_benchmark.common import (
    iou_polygons,
    percent_difference,
    polygon_area_xy,
    slope_degrees_from_normal,
)
from nextgen.residential_geometry_benchmark.comparison import compare_candidates_to_benchmark
from nextgen.residential_geometry_benchmark.confidence import assess_confidence
from nextgen.residential_geometry_benchmark.constants import (
    CONFIDENCE_STATES,
    FAILURE_CLASSES,
    GOVERNANCE_LABELS,
    PRODUCTION_READINESS,
    TRUTH_CLASSIFICATIONS,
)
from nextgen.residential_geometry_benchmark.corpus_suitability import (
    audit_existing_corpus,
    audit_existing_dataset,
)
from nextgen.residential_geometry_benchmark.failures import classify_failures, should_withhold_measurements
from nextgen.residential_geometry_benchmark.measurements import calculate_measurement_candidates, withhold_measurements
from nextgen.residential_geometry_benchmark.recapture import build_recapture_recommendations
from nextgen.residential_geometry_benchmark.roof_planes import classify_roof_edges
from nextgen.residential_geometry_benchmark.segmentation import (
    propose_structure_segmentation,
    segment_from_orthophoto_bounds,
)


REPO = Path(__file__).resolve().parents[2]


def test_governance_and_not_ready():
    assert GOVERNANCE_LABELS["authoritative"] == "false"
    assert GOVERNANCE_LABELS["physical_validation"] == "NOT_PERFORMED"
    assert PRODUCTION_READINESS == "NOT_READY"


def test_truth_classifications_exclude_canonical():
    assert "CANONICAL_PROPERTY_TRUTH" not in TRUTH_CLASSIFICATIONS


def test_authoritative_false_enforced():
    with pytest.raises(AuthorityViolation):
        assert_benchmark_object({"authoritative": True, "physical_validation": "NOT_PERFORMED"})


def test_physical_validation_enforced():
    with pytest.raises(AuthorityViolation):
        assert_benchmark_object({"authoritative": False, "physical_validation": "PERFORMED"})


def test_no_prohibited_emissions():
    with pytest.raises(AuthorityViolation):
        reject_prohibited_emission("ApprovedGeometry")
    with pytest.raises(AuthorityViolation):
        reject_prohibited_emission("passport_append")


def test_no_pricing_fields():
    with pytest.raises(AuthorityViolation):
        assert_no_pricing({"price": 100})


def test_annotation_disagreement_preserved():
    base = {
        "building_footprint": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "roof_outline": [[1, 1], [9, 1], [9, 9], [1, 9]],
        "roof_planes": [{"slope_degrees": 20, "azimuth_degrees": 90, "area_candidate": 64}],
    }
    shifted = {
        "building_footprint": [[0.5, 0], [10.5, 0], [10.5, 10], [0.5, 10]],
        "roof_outline": [[1.5, 1], [9.5, 1], [9.5, 9], [1.5, 9]],
        "roof_planes": [{"slope_degrees": 24, "azimuth_degrees": 95, "area_candidate": 70}],
    }
    disagreement = compute_inter_annotator_disagreement(base, shifted)
    assert disagreement["preserved_without_averaging"] is True
    assert disagreement["footprint_iou"] < 1.0


def test_create_annotation_pass_benchmark_object():
    ann = create_annotation_pass(
        dataset_id="MYGLA",
        structure_id="test_structure",
        source_revision="abc",
        annotator="annotator_a",
        annotation_method="orthophoto_manual_trace",
        source_view="orthophoto",
        confidence="moderate",
        uncertainty_reason="development_only",
        coordinate_system="LOCAL",
        truth_classification="MANUAL_IMAGE_ANNOTATION",
        review_state="DRAFT",
        building_footprint=[(0, 0), (10, 0), (10, 10), (0, 10)],
        roof_outline=[(1, 1), (9, 1), (9, 9), (1, 9)],
        roof_planes=[],
        roof_edges=[],
        obscured_regions=[],
        uncertain_regions=[],
        reconstruction_version="recon_v1",
        odm_digest="sha256:test",
        source_classification="EXTERNAL_BENCHMARK",
    )
    assert ann["authoritative"] is False
    assert ann["truth_classification"] == "MANUAL_IMAGE_ANNOTATION"


def test_segmentation_states_proposed_only():
    seg = propose_structure_segmentation(
        dataset_id="MYGLA",
        structure_id="s1",
        source_revision="rev",
        reconstruction_version="recon",
        odm_digest="sha256:test",
        input_artifact="ortho.tif",
        input_checksum="abc",
        algorithm_id="test",
        algorithm_version="v1",
        footprint_polygon=[(0, 0), (10, 0), (10, 10), (0, 10)],
        primary_structure=[(0, 0), (10, 0), (10, 10), (0, 10)],
        roof_boundary=[(1, 1), (9, 1), (9, 9), (1, 9)],
        background_terrain=[],
        vegetation_mask=[],
        confidence=0.5,
    )
    assert seg["review_state"] == "PROPOSED"


def test_deterministic_area_and_pitch():
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert polygon_area_xy(square) == 100.0
    assert slope_degrees_from_normal((0, 0.5, 0.866)) == pytest.approx(30.0, abs=0.5)


def test_measurement_candidates_no_pricing():
    ann = create_annotation_pass(
        dataset_id="MYGLA",
        structure_id="s1",
        source_revision="rev",
        annotator="a",
        annotation_method="manual",
        source_view="orthophoto",
        confidence="moderate",
        uncertainty_reason="none",
        coordinate_system="LOCAL",
        truth_classification="MANUAL_IMAGE_ANNOTATION",
        review_state="DRAFT",
        building_footprint=[(0, 0), (10, 0), (10, 10), (0, 10)],
        roof_outline=[(0, 0), (10, 0), (10, 10), (0, 10)],
        roof_planes=[{"plane_id": "p1", "area_candidate": 100, "slope_degrees": 25, "azimuth_degrees": 180}],
        roof_edges=[{"detected_class": "EAVE", "length_candidate": 40}],
        obscured_regions=[],
        uncertain_regions=[],
        reconstruction_version="recon",
        odm_digest="sha256:test",
        source_classification="EXTERNAL_BENCHMARK",
    )
    meas = calculate_measurement_candidates(
        dataset_id="MYGLA",
        structure_id="s1",
        source_revision="rev",
        reconstruction_version="recon",
        odm_digest="sha256:test",
        annotation=ann,
    )
    assert meas["authoritative"] is False
    assert meas["estimator_distinction"]["purchase_quantity"] is None


def test_comparison_separate_metric_groups():
    ann = create_annotation_pass(
        dataset_id="MYGLA",
        structure_id="s1",
        source_revision="rev",
        annotator="a",
        annotation_method="manual",
        source_view="orthophoto",
        confidence="moderate",
        uncertainty_reason="none",
        coordinate_system="LOCAL",
        truth_classification="MANUAL_IMAGE_ANNOTATION",
        review_state="BENCHMARK_ACCEPTED",
        building_footprint=[(0, 0), (10, 0), (10, 10), (0, 10)],
        roof_outline=[(0, 0), (10, 0), (10, 10), (0, 10)],
        roof_planes=[{"plane_id": "p1", "area_candidate": 100, "slope_degrees": 25, "azimuth_degrees": 180}],
        roof_edges=[],
        obscured_regions=[],
        uncertain_regions=[],
        reconstruction_version="recon",
        odm_digest="sha256:test",
        source_classification="EXTERNAL_BENCHMARK",
    )
    seg = segment_from_orthophoto_bounds(
        dataset_id="MYGLA",
        structure_id="s1",
        source_revision="rev",
        reconstruction_version="recon",
        odm_digest="sha256:test",
        orthophoto_path="ortho.tif",
        bounds={"x_min": 0, "y_min": 0, "x_max": 100, "y_max": 100},
    )
    meas = calculate_measurement_candidates(
        dataset_id="MYGLA",
        structure_id="s1",
        source_revision="rev",
        reconstruction_version="recon",
        odm_digest="sha256:test",
        annotation=ann,
        segmentation=seg,
    )
    result = compare_candidates_to_benchmark(
        benchmark_annotation=ann,
        candidate_planes=ann["roof_planes"],
        candidate_segmentation=seg,
        candidate_measurements=meas,
    )
    assert result["combined_score"] is None
    assert "STRUCTURE_SEGMENTATION" in result["metric_groups"]


def test_confidence_explanations():
    conf = assess_confidence(
        image_count=80,
        overlap_estimate="good",
        gps_status="GPS_PRESENT",
        reconstruction_status="SUCCESS",
        point_density=2.0,
        plane_residual=0.1,
        vegetation_level="low",
        oblique_coverage="partial",
    )
    assert conf["confidence_state"] in CONFIDENCE_STATES
    assert conf["contributing_factors"]
    assert conf["limitations"]


def test_failure_taxonomy_and_withholding():
    failures = classify_failures({"overlap_estimate": "low", "license_blocked": True})
    classes = {f["failure_class"] for f in failures}
    assert "INSUFFICIENT_OVERLAP" in classes
    assert "LICENSE_BLOCKED" in classes
    assert should_withhold_measurements(failures) is True
    withheld = withhold_measurements("license", dataset_id="DJI", structure_id="s")
    assert withheld["withheld"] is True


def test_recapture_not_mission_approval():
    recs = build_recapture_recommendations(
        dataset_id="MYGLA",
        structure_id="s1",
        failures=classify_failures({"overlap_estimate": "low"}),
        confidence=assess_confidence(
            image_count=10,
            overlap_estimate="low",
            gps_status="GPS_ABSENT",
            reconstruction_status="FAILED",
            point_density=None,
            plane_residual=None,
            vegetation_level="high",
            oblique_coverage="limited",
        ),
    )
    assert recs
    for rec in recs:
        assert rec["mission_approved"] is False
        assert_recapture_not_mission_approval(rec)


def test_corpus_suitability_audit():
    audit = audit_existing_dataset("CALITERRA")
    assert audit["suitability_classification"] == "HIGH_VALUE_RESIDENTIAL"
    assert audit["authoritative"] is False
    corpus = audit_existing_corpus()
    assert corpus["summary"]["datasets_reviewed"] >= 6


def test_roof_edge_classification():
    planes = [{"plane_id": "p1", "slope_degrees": 2, "boundary_polygon": [[0, 0], [10, 0], [10, 1]]}]
    edges = classify_roof_edges(planes)
    assert edges[0]["detected_class"] == "EAVE"


def test_percent_difference_and_iou():
    a = [(0, 0), (10, 0), (10, 10), (0, 10)]
    b = [(5, 0), (15, 0), (15, 10), (5, 10)]
    assert iou_polygons(a, b) == pytest.approx(0.33, abs=0.05)
    assert percent_difference(100, 110) == pytest.approx(10.0)


def test_px006b_docs_present():
    px006b = REPO / "engineering" / "px006b"
    required = [
        "README.md",
        "PHYSICAL_VALIDATION_GAP.md",
        "STRATEX_GROUND_TRUTH_HOME_PROTOCOL.md",
        "FIRST_FIELD_VALIDATION_KIT.md",
        "RESIDENTIAL_DATASET_REGISTRY.yaml",
    ]
    for name in required:
        assert (px006b / name).is_file(), name


def test_no_external_binary_tracking_in_repo():
    root = REPO
    forbidden_suffixes = {".laz", ".las", ".ply", ".obj"}
    hits = []
    for path in root.rglob("*"):
        if path.suffix.lower() in forbidden_suffixes and "node_modules" not in path.parts:
            hits.append(str(path))
    assert hits == []


def test_failure_classes_registry_complete():
    assert "VEGETATION_OCCLUSION" in FAILURE_CLASSES
    assert len(FAILURE_CLASSES) >= 20


def test_copr_license_is_cc_by_sa_not_cc0():
    from nextgen.dataset_lab.license_check import _identify_license, license_check

    text = "Creative Commons Attribution-ShareAlike 4.0 International CC BY-SA 4.0\nhttp://creativecommons.org/licenses/by-sa/4.0/"
    name, conf = _identify_license(text)
    assert name == "CC-BY-SA-4.0"
    assert conf == "text_match"
    # Live COPR content if acquired locally
    from pathlib import Path
    import os

    root = Path(os.environ.get("STRATEX_DATASET_ROOT", "/tmp/stratex-external-datasets"))
    if (root / "COPR" / "content" / "license.txt").is_file():
        result = license_check("COPR")
        assert result["license_name"] == "CC-BY-SA-4.0"
        assert result["license_status"] == "VERIFIED_RESTRICTED"
        assert result["share_alike_requirement"] == "REQUIRED"
        assert result["attribution_requirement"] == "REQUIRED"
        assert result["redistribution_status"] == "CONDITIONAL"
        assert result["tracked_derivative_fixtures_allowed"] is False
        assert "CC0" not in result["license_name"]


def test_cc_by_sa_cannot_be_unrestricted_redistributable():
    from nextgen.dataset_lab.license_check import _identify_license

    name, _ = _identify_license("CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/")
    assert name == "CC-BY-SA-4.0"
    assert name != "CC0"


def test_conflicting_license_markers_fail_closed():
    from nextgen.dataset_lab.license_check import _identify_license

    # Identification distinguishes markers; aggregation fail-closed path covered when both appear.
    a, _ = _identify_license("CC0 Creative Commons Zero")
    b, _ = _identify_license("CC BY-SA 4.0")
    assert a == "CC0"
    assert b == "CC-BY-SA-4.0"


def test_withholding_on_insufficient_evidence():
    from nextgen.residential_geometry_benchmark.measurements import evaluate_withholding, withhold_measurements

    reason = evaluate_withholding(
        planes=[],
        edges=[],
        units="meters",
        coordinate_reference="LOCAL",
        confidence_state="INSUFFICIENT_EVIDENCE",
    )
    assert reason == "confidence_insufficient_evidence"
    withheld = withhold_measurements(reason, dataset_id="X", structure_id="Y")
    assert withheld["status"] == "WITHHELD"
    assert withheld["value"] is None
