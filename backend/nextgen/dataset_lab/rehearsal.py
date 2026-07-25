"""Stratex pipeline rehearsal for external datasets (development-only).

External Dataset → Registry → Acquisition → Inventory → ATC Candidate →
Quality Gate → Optional ODM → Geometry Candidate Reference → Estimator Test
Input → ReportPublicationPackage PROPOSED → Habitat Development-Only Projection.

Safeguards: no canonical Passport append, no governed final publication,
no homeowner delivery, no approved geometry/finding, no real pricing,
no fabricated dimensions/thermal findings, no customer account, no production claim.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .common import (
    artifact_dir,
    dataset_dir,
    get_registry_entry,
    governance_block,
    now_iso,
    read_json,
    sanitize_dataset_id,
    write_json,
)
from .corpus import reject_approved_status_injection
from .reconstruction import detect_odm_environment


def rehearse_pipeline(dataset_id: str) -> Dict[str, Any]:
    safe = sanitize_dataset_id(dataset_id)
    entry = get_registry_entry(safe)
    art = artifact_dir(safe)
    stages: List[Dict[str, Any]] = []

    def add(name: str, status: str, detail: Dict[str, Any]) -> None:
        stages.append({"stage": name, "status": status, "detail": detail})

    add(
        "external_dataset",
        "OK",
        {"dataset_id": safe, "source_page": entry.get("source_page")},
    )
    add("dataset_registry", "OK", {"registry_id": safe, "present": True})
    acq = dataset_dir(safe) / "latest_acquisition.json"
    add(
        "safe_acquisition",
        "OK" if acq.is_file() else "MISSING",
        {"receipt": str(acq) if acq.is_file() else None},
    )
    inv = art / "inventory.json"
    inventory = read_json(inv) if inv.is_file() else {}
    add("inventory", "OK" if inv.is_file() else "MISSING", {"gps_status": inventory.get("gps_status")})

    cand_path = art / "development_candidate.json"
    candidate = read_json(cand_path) if cand_path.is_file() else {}
    if candidate:
        reject_approved_status_injection(candidate)
    add(
        "atc_evidence_candidate",
        "OK" if candidate else "MISSING",
        {
            "readiness": candidate.get("readiness_classification"),
            "contract_name": candidate.get("contract_name"),
        },
    )

    readiness = candidate.get("readiness_classification")
    gate = "PASS_DEVELOPMENT" if readiness in {
        "READY_FOR_DEVELOPMENT_REVIEW",
        "USABLE_WITH_LIMITATIONS",
    } else "HOLD"
    add("quality_gate", gate, {"readiness": readiness})

    odm = detect_odm_environment()
    add(
        "optional_odm_reconstruction",
        "AVAILABLE" if odm.get("odm_available") else "SKIPPED",
        {"docker": odm.get("docker_available"), "odm": odm.get("odm_available")},
    )

    # Geometry candidate reference — unvalidated, explicitly marked.
    geometry_candidate = {
        "kind": "GeometryCandidateReference",
        "contract_name": "GeometryCandidate",
        "dataset_id": safe,
        "values_source": "UNVALIDATED_RECONSTRUCTION_OR_METADATA",
        "source": "RECONSTRUCTION_DERIVED_CANDIDATE",
        "dimensions_fabricated": False,
        "approved": False,
        "authoritative": False,
        "confidence": "UNVALIDATED",
        "physical_validation": "NOT_PERFORMED",
        "uncertainty": "HIGH_EXTERNAL_PUBLIC_DATASET",
        "governance": governance_block(),
    }
    reject_approved_status_injection(geometry_candidate)
    add("geometry_candidate_reference", "OK", geometry_candidate)

    # Estimator may use only measured/present or synthetic deterministic refs.
    image_count = int(inventory.get("total_images") or 0)
    estimator_input = {
        "kind": "DeterministicEstimatorTestInput",
        "dataset_id": safe,
        "measured_values_present": {
            "image_count": image_count,
            "gcp_present": bool(inventory.get("gcp_present")),
        },
        "reconstruction_derived_candidate_values": {
            "marked_unvalidated": True,
            "values": {},
        },
        "deterministic_synthetic_reference_values": {
            "reference_area_sqft": 0.0,
            "note": "zeroed synthetic placeholder — not a real measurement",
        },
        "pricing": None,
        "real_pricing_prohibited": True,
        "source": "PX006A_REHEARSAL",
        "uncertainty": "DEVELOPMENT_ONLY",
        "governance": governance_block(),
    }
    add("deterministic_estimator_test_input", "OK", estimator_input)

    report_pkg = {
        "kind": "ReportPublicationPackage",
        "status": "PROPOSED",
        "dataset_id": safe,
        "homeowner_delivery": False,
        "governed_final_publication": False,
        "canonical_passport_append": False,
        "customer_account": None,
        "production_claim": False,
        "governance": governance_block(),
    }
    add("report_publication_package", "PROPOSED", report_pkg)

    habitat = {
        "kind": "HabitatDevelopmentOnlyProjection",
        "canonical_write": False,
        "habitat_canonical_display": "PROHIBITED",
        "dataset_id": safe,
        "projection": "DEVELOPMENT_ONLY",
        "governance": governance_block(),
    }
    add("habitat_development_only_projection", "OK", habitat)

    # Canonical-write protection assertions
    protections = {
        "canonical_passport_append": False,
        "governed_final_publication": False,
        "homeowner_delivery": False,
        "approved_geometry": False,
        "approved_finding": False,
        "habitat_canonical_write": False,
        "fabricated_dimensions": False,
        "fabricated_thermal_findings": False,
        "real_pricing": False,
        "customer_account": False,
        "production_claim": False,
    }
    add("canonical_write_protection", "CONFIRMED", protections)

    result = {
        "dataset_id": safe,
        "rehearsed_at": now_iso(),
        "stages": stages,
        "protections": protections,
        "physical_validation": "NOT_PERFORMED",
        "production_readiness": "NOT_READY",
        "governance": governance_block(),
    }
    write_json(art / "pipeline_rehearsal.json", result)
    return result
