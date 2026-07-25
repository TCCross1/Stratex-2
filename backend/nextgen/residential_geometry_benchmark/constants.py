"""Classification constants for PX-006B residential geometry benchmark."""
from __future__ import annotations

from typing import FrozenSet

MODULE_IDENTITY = "nextgen.residential_geometry_benchmark"
BENCHMARK_VERSION = "px006b.1.0.0"
PRODUCTION_READINESS = "NOT_READY"
CONTRACT_STATUS = "PROPOSED"

SUITABILITY_CLASSES = frozenset(
    {
        "HIGH_VALUE_RESIDENTIAL",
        "USEFUL_SMALL_BUILDING",
        "GENERAL_GEOMETRY_ONLY",
        "CAPTURE_QUALITY_ONLY",
        "LICENSE_RESTRICTED_INVENTORY_ONLY",
        "UNSUITABLE",
    }
)

TRUTH_CLASSIFICATIONS = frozenset(
    {
        "MANUAL_IMAGE_ANNOTATION",
        "MANUAL_POINT_CLOUD_ANNOTATION",
        "MANUAL_MESH_ANNOTATION",
        "SOURCE_PROVIDED_CONTROL",
        "RECONSTRUCTION_DERIVED_CANDIDATE",
        "SYNTHETIC_REFERENCE",
    }
)

PROHIBITED_TRUTH_CLASSIFICATIONS = frozenset({"CANONICAL_PROPERTY_TRUTH"})

ANNOTATION_REVIEW_STATES = frozenset(
    {
        "DRAFT",
        "SECOND_REVIEW_REQUIRED",
        "BENCHMARK_ACCEPTED",
        "DISPUTED",
        "REJECTED",
    }
)

SEGMENTATION_STATES = frozenset(
    {
        "PROPOSED",
        "REVIEW_REQUIRED",
        "BENCHMARK_ACCEPTED",
        "REJECTED",
    }
)

ROOF_EDGE_CLASSES = frozenset(
    {
        "EAVE",
        "RAKE",
        "RIDGE",
        "HIP",
        "VALLEY",
        "STEP",
        "UNKNOWN",
    }
)

CONFIDENCE_STATES = frozenset(
    {
        "HIGH_DEVELOPMENT_CONFIDENCE",
        "MODERATE_DEVELOPMENT_CONFIDENCE",
        "LOW_DEVELOPMENT_CONFIDENCE",
        "INSUFFICIENT_EVIDENCE",
        "UNVALIDATED",
    }
)

FAILURE_CLASSES = frozenset(
    {
        "INSUFFICIENT_OVERLAP",
        "NADIR_ONLY_ROOF_LIMITATION",
        "MISSING_OBLIQUE_WALL_COVERAGE",
        "VEGETATION_OCCLUSION",
        "TREE_CANOPY_CONTAMINATION",
        "REFLECTIVE_ROOF",
        "LOW_TEXTURE_ROOF",
        "DARK_ROOF_SHADOW",
        "WHITE_ROOF_OVEREXPOSURE",
        "REPETITIVE_SHINGLE_PATTERN",
        "SOLAR_PANEL_OCCLUSION",
        "CHIMNEY_OR_PENETRATION_CONFUSION",
        "DORMER_SPLIT_FAILURE",
        "HIP_GABLE_CLASSIFICATION_CONFLICT",
        "VALLEY_NOT_VISIBLE",
        "ATTACHED_GARAGE_MERGED",
        "ACCESSORY_STRUCTURE_MERGED",
        "NEIGHBORING_HOME_CONTAMINATION",
        "POINT_CLOUD_HOLE",
        "MESH_ARTIFACT",
        "DSM_SMOOTHING_ERROR",
        "GPS_PARTIAL",
        "GCP_MISSING",
        "CONTROL_REFERENCE_UNKNOWN",
        "LICENSE_BLOCKED",
        "PRIVACY_BLOCKED",
    }
)

RECAPTURE_STATES = frozenset({"PROPOSED_CAPTURE_ADJUSTMENT"})

BENCHMARK_DISPOSITIONS = frozenset(
    {
        "BENCHMARK_ACCEPTED",
        "ACCEPTED_WITH_LIMITATIONS",
        "INSUFFICIENT_EVIDENCE",
        "RECONSTRUCTION_FAILED",
        "ANNOTATION_DISPUTED",
        "LICENSE_BLOCKED",
        "PRIVACY_BLOCKED",
    }
)

METRIC_GROUPS = frozenset(
    {
        "STRUCTURE_SEGMENTATION",
        "ROOF_BOUNDARY",
        "ROOF_PLANES",
        "ROOF_EDGES",
        "ROOF_SLOPE",
        "AREA_CANDIDATES",
        "LINEAR_MEASUREMENTS",
        "OPENINGS_AND_PENETRATIONS",
        "OCCLUSION_HANDLING",
    }
)

ACQUISITION_DECISIONS = frozenset(
    {
        "APPROVED_FOR_LOCAL_DEVELOPMENT",
        "APPROVED_WITH_ATTRIBUTION",
        "INVENTORY_ONLY",
        "LICENSE_REVIEW_REQUIRED",
        "PRIVACY_REVIEW_REQUIRED",
        "REJECTED",
    }
)

GOVERNANCE_LABELS = {
    "data_origin": "EXTERNAL_PUBLIC_DATASET",
    "truth_status": "NON_CANONICAL_TEST_DATA",
    "physical_validation": "NOT_PERFORMED",
    "property_use": "DEVELOPMENT_ONLY",
    "customer_use": "PROHIBITED",
    "passport_publication": "PROHIBITED",
    "habitat_canonical_display": "PROHIBITED",
    "field_accuracy_claim": "PROHIBITED",
    "authoritative": "false",
}

ALGORITHM_VERSION = "rgb_benchmark_v1"
ANNOTATION_VERSION = "manual_v1"
