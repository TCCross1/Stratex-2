"""Stratex corpus adapter — development-only ATC candidate packages (PX-006A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .common import (
    READINESS_RESULTS,
    artifact_dir,
    dataset_dir,
    get_registry_entry,
    governance_block,
    now_iso,
    read_json,
    sanitize_dataset_id,
    write_json,
)

FORBIDDEN_CONTRACTS = {"ApprovedGeometry", "ApprovedFinding"}
FORBIDDEN_STATUS = {"APPROVED", "DELIVERED", "ApprovedGeometry", "ApprovedFinding"}


def build_candidate_package(dataset_id: str) -> Dict[str, Any]:
    safe = sanitize_dataset_id(dataset_id)
    entry = get_registry_entry(safe)
    art = artifact_dir(safe)
    inv_path = art / "inventory.json"
    if not inv_path.is_file():
        raise FileNotFoundError("inventory required before corpus adapter")
    inventory = read_json(inv_path)

    lic_path = dataset_dir(safe) / "license_status.json"
    if not lic_path.is_file():
        lic_path = dataset_dir(safe) / "receipts" / "license-check-latest.json"
    license_doc = (
        read_json(lic_path)
        if lic_path.is_file()
        else {
            "license_status": "UNKNOWN",
            "tracked_derivative_fixtures_allowed": False,
        }
    )

    lic_status = str(license_doc.get("license_status") or "UNKNOWN")
    images = int(inventory.get("total_images") or 0)

    if lic_status == "REJECTED" or (lic_status == "UNKNOWN" and images == 0):
        readiness = "LICENSE_BLOCKED"
    elif images == 0:
        readiness = "REJECTED_DATASET"
    elif inventory.get("unsupported_files"):
        readiness = "UNSUPPORTED_FORMAT"
    elif lic_status in {"REVIEW_REQUIRED", "UNKNOWN", "VERIFIED_RESTRICTED"}:
        readiness = "USABLE_WITH_LIMITATIONS"
    elif inventory.get("gps_status") == "GPS_ABSENT" and not inventory.get("gcp_present"):
        readiness = "ADDITIONAL_DATA_REQUIRED"
    else:
        readiness = "READY_FOR_DEVELOPMENT_REVIEW"

    if readiness not in READINESS_RESULTS:
        raise ValueError(f"invalid readiness: {readiness}")

    acq_path = dataset_dir(safe) / "latest_acquisition.json"
    immutable = None
    if acq_path.is_file():
        acq = read_json(acq_path)
        immutable = acq.get("repository_commit") or acq.get("archive_checksum")

    man_path = art / "manifest.json"
    manifest_checksum = None
    if man_path.is_file():
        manifest_checksum = read_json(man_path).get("file_manifest_checksum")

    candidate = {
        "package_kind": "EXTERNAL_DATASET_DEVELOPMENT_CANDIDATE",
        "contract_name": "ExternalDatasetEvidenceCandidate",
        "dataset_id": safe,
        "display_name": entry.get("display_name"),
        "immutable_source_revision": immutable,
        "file_manifest_checksum": manifest_checksum,
        "image_count": images,
        "camera_sensor_summary": inventory.get("cameras_observed"),
        "capture_timestamps_present": any(
            i.get("timestamp") for i in inventory.get("images") or []
        ),
        "metadata_completeness": {
            "gps_status": inventory.get("gps_status"),
            "gcp_present": inventory.get("gcp_present"),
            "rtk_claimed_by_source": inventory.get("rtk_claimed_by_source"),
            "thermal_present": inventory.get("thermal_present"),
            "lidar_present": inventory.get("lidar_present"),
        },
        "unsupported_format_warnings": inventory.get("unsupported_files") or [],
        "source_license_status": lic_status,
        "readiness_classification": readiness,
        "authority_boundary": {
            "emits_approved_geometry": False,
            "emits_approved_finding": False,
            "emits_canonical_passport": False,
            "emits_delivered_homeowner_report": False,
            "stops_at": "candidate_and_development_readiness",
        },
        "generated_at": now_iso(),
        "governance": governance_block(),
        **governance_block(),
    }

    reject_approved_status_injection(candidate)
    write_json(art / "development_candidate.json", candidate)
    return candidate


def reject_approved_status_injection(payload: Dict[str, Any]) -> None:
    """Guard used by tests and fault lab — candidate-only authority."""
    status = str(payload.get("status") or payload.get("readiness_classification") or "")
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    contract = str(payload.get("contract_name") or meta.get("contract_name") or "")
    if status in FORBIDDEN_STATUS:
        raise PermissionError(
            "approved-status injection rejected — candidate-only authority"
        )
    if contract in FORBIDDEN_CONTRACTS:
        raise PermissionError("approved contract injection rejected")
    if payload.get("passport_canonical") is True:
        raise PermissionError("canonical Passport write rejected")
    if payload.get("habitat_canonical_write") is True:
        raise PermissionError("Habitat canonical write rejected")
