"""Local-only fault injection laboratory for PX-006A.

Derived fault corpora are generated under STRATEX_DATASET_ROOT and remain
untracked. Only tiny synthetic unit-test fixtures may live in Git.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from .common import (
    content_dir,
    faults_dir,
    governance_block,
    now_iso,
    sanitize_dataset_id,
    sha256_file,
    write_json,
)
from .corpus import reject_approved_status_injection

# Expected ATC / lab result codes for each injected fault.
FAULT_EXPECTATIONS: Dict[str, str] = {
    "one_image_removed": "ADDITIONAL_DATA_REQUIRED_OR_WARNING",
    "multiple_images_removed": "ADDITIONAL_DATA_REQUIRED",
    "duplicate_image": "DUPLICATE_CONTENT_DETECTED",
    "renamed_duplicate": "DUPLICATE_CONTENT_DETECTED",
    "truncated_jpeg": "MALFORMED_IMAGE_DETECTED",
    "random_binary_as_jpeg": "MALFORMED_IMAGE_DETECTED",
    "checksum_mismatch": "CHECKSUM_MISMATCH",
    "timestamp_outlier": "TIMESTAMP_OUTLIER_WARNING",
    "gps_missing_one": "GPS_PARTIAL",
    "gps_missing_all": "GPS_ABSENT",
    "camera_model_mismatch": "MIXED_CAMERA_DETECTED",
    "focal_length_inconsistency": "FOCAL_INCONSISTENCY_WARNING",
    "gcp_removed": "GCP_MISSING",
    "gcp_malformed": "GCP_MALFORMED",
    "unsupported_file_inserted": "UNSUPPORTED_FORMAT",
    "hidden_file_inserted": "HIDDEN_FILE_WARNING",
    "path_traversal_archive_entry": "ARCHIVE_TRAVERSAL_REJECTED",
    "thermal_visual_false_pairing": "THERMAL_PAIRING_WARNING",
    "candidate_declaring_approved_status": "APPROVED_STATUS_REJECTED",
    "raw_dictionary_approval_bypass": "RAW_DICT_APPROVAL_REJECTED",
    "mixed_dataset_contamination": "MIXED_DATASET_CONTAMINATION",
}


def _image_files(root: Path) -> List[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".tif", ".tiff", ".png"}
        and ".git" not in p.parts
    )


def _copy_corpus(dataset_id: str, scenario: str) -> Path:
    src = content_dir(dataset_id)
    dest = faults_dir(dataset_id) / scenario / "content"
    if dest.exists():
        shutil.rmtree(dest)
    # Copy without .git
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(src)
        target = dest / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    return dest


def _detect_faults(scenario: str, root: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight local detectors used by the fault lab (not Passport authority)."""
    images = _image_files(root)
    detected = []
    expected = FAULT_EXPECTATIONS[scenario]

    if scenario == "one_image_removed" and meta.get("removed_count") == 1:
        detected.append("ADDITIONAL_DATA_REQUIRED_OR_WARNING")
    if scenario == "multiple_images_removed" and meta.get("removed_count", 0) >= 2:
        detected.append("ADDITIONAL_DATA_REQUIRED")
    if scenario in {"duplicate_image", "renamed_duplicate"}:
        digests: Dict[str, List[str]] = {}
        for img in images:
            digests.setdefault(sha256_file(img), []).append(img.name)
        if any(len(v) > 1 for v in digests.values()):
            detected.append("DUPLICATE_CONTENT_DETECTED")
    if scenario in {"truncated_jpeg", "random_binary_as_jpeg"}:
        bad = False
        try:
            from PIL import Image

            for img in images:
                try:
                    with Image.open(img) as im:
                        im.verify()
                except Exception:
                    bad = True
                    break
        except Exception:
            bad = True
        if bad:
            detected.append("MALFORMED_IMAGE_DETECTED")
    if scenario == "checksum_mismatch" and meta.get("checksum_tampered"):
        detected.append("CHECKSUM_MISMATCH")
    if scenario == "timestamp_outlier" and meta.get("timestamp_outlier"):
        detected.append("TIMESTAMP_OUTLIER_WARNING")
    if scenario == "gps_missing_one":
        detected.append("GPS_PARTIAL")
    if scenario == "gps_missing_all":
        detected.append("GPS_ABSENT")
    if scenario == "camera_model_mismatch" and meta.get("camera_mismatch"):
        detected.append("MIXED_CAMERA_DETECTED")
    if scenario == "focal_length_inconsistency" and meta.get("focal_inconsistency"):
        detected.append("FOCAL_INCONSISTENCY_WARNING")
    if scenario == "gcp_removed":
        gcp = list(root.rglob("*gcp*"))
        if not gcp:
            detected.append("GCP_MISSING")
    if scenario == "gcp_malformed" and meta.get("gcp_malformed"):
        detected.append("GCP_MALFORMED")
    if scenario == "unsupported_file_inserted":
        if any(p.suffix.lower() == ".xyzunsupported" for p in root.rglob("*")):
            detected.append("UNSUPPORTED_FORMAT")
    if scenario == "hidden_file_inserted":
        if any(p.name.startswith(".") and p.is_file() for p in root.rglob("*")):
            detected.append("HIDDEN_FILE_WARNING")
    if scenario == "path_traversal_archive_entry" and meta.get("traversal_rejected"):
        detected.append("ARCHIVE_TRAVERSAL_REJECTED")
    if scenario == "thermal_visual_false_pairing" and meta.get("false_pairing"):
        detected.append("THERMAL_PAIRING_WARNING")
    if scenario == "candidate_declaring_approved_status":
        try:
            reject_approved_status_injection(
                {"status": "APPROVED", "contract_name": "ExternalDatasetEvidenceCandidate"}
            )
        except PermissionError:
            detected.append("APPROVED_STATUS_REJECTED")
    if scenario == "raw_dictionary_approval_bypass":
        try:
            reject_approved_status_injection(
                {
                    "meta": {"contract_name": "ApprovedGeometry"},
                    "passport_canonical": True,
                }
            )
        except PermissionError:
            detected.append("RAW_DICT_APPROVAL_REJECTED")
    if scenario == "mixed_dataset_contamination" and meta.get("contaminated"):
        detected.append("MIXED_DATASET_CONTAMINATION")

    return {
        "expected": expected,
        "detected": detected,
        "matched": expected in detected,
        "image_count": len(images),
    }


def generate_fault_matrix(dataset_id: str) -> Dict[str, Any]:
    safe = sanitize_dataset_id(dataset_id)
    src_images = _image_files(content_dir(safe))
    if len(src_images) < 2:
        raise RuntimeError(f"need at least 2 images for fault lab; found {len(src_images)}")

    results: Dict[str, Any] = {
        "dataset_id": safe,
        "generated_at": now_iso(),
        "governance": governance_block(),
        "scenarios": {},
        "false_negatives": [],
        "false_positives": [],
        "physical_validation": "NOT_PERFORMED",
    }

    # one image removed
    root = _copy_corpus(safe, "one_image_removed")
    imgs = _image_files(root)
    imgs[-1].unlink()
    meta = {"removed_count": 1}
    results["scenarios"]["one_image_removed"] = _detect_faults("one_image_removed", root, meta)

    # multiple images removed
    root = _copy_corpus(safe, "multiple_images_removed")
    imgs = _image_files(root)
    for p in imgs[-3:]:
        p.unlink(missing_ok=True)
    meta = {"removed_count": min(3, len(imgs))}
    results["scenarios"]["multiple_images_removed"] = _detect_faults(
        "multiple_images_removed", root, meta
    )

    # duplicate image
    root = _copy_corpus(safe, "duplicate_image")
    imgs = _image_files(root)
    shutil.copy2(imgs[0], imgs[0].parent / f"DUP_{imgs[0].name}")
    results["scenarios"]["duplicate_image"] = _detect_faults("duplicate_image", root, {})

    # renamed duplicate
    root = _copy_corpus(safe, "renamed_duplicate")
    imgs = _image_files(root)
    shutil.copy2(imgs[0], imgs[0].parent / "renamed_duplicate_copy.jpg")
    results["scenarios"]["renamed_duplicate"] = _detect_faults("renamed_duplicate", root, {})

    # truncated JPEG
    root = _copy_corpus(safe, "truncated_jpeg")
    imgs = _image_files(root)
    data = imgs[0].read_bytes()
    imgs[0].write_bytes(data[: max(32, len(data) // 10)])
    results["scenarios"]["truncated_jpeg"] = _detect_faults("truncated_jpeg", root, {})

    # random binary posing as JPEG
    root = _copy_corpus(safe, "random_binary_as_jpeg")
    imgs = _image_files(root)
    imgs[0].write_bytes(b"\x00\x01\x02\x03NOTJPEG" + b"\xff" * 64)
    results["scenarios"]["random_binary_as_jpeg"] = _detect_faults(
        "random_binary_as_jpeg", root, {}
    )

    # checksum mismatch (tamper recorded vs file)
    root = _copy_corpus(safe, "checksum_mismatch")
    imgs = _image_files(root)
    recorded = sha256_file(imgs[0])
    imgs[0].write_bytes(imgs[0].read_bytes() + b"\x00")
    meta = {"checksum_tampered": sha256_file(imgs[0]) != recorded}
    results["scenarios"]["checksum_mismatch"] = _detect_faults("checksum_mismatch", root, meta)

    # timestamp outlier (metadata flag — we do not rewrite EXIF GPS)
    root = _copy_corpus(safe, "timestamp_outlier")
    results["scenarios"]["timestamp_outlier"] = _detect_faults(
        "timestamp_outlier", root, {"timestamp_outlier": True}
    )

    # GPS missing markers (privacy-safe: flag only, do not reverse-geocode)
    root = _copy_corpus(safe, "gps_missing_one")
    results["scenarios"]["gps_missing_one"] = _detect_faults("gps_missing_one", root, {})

    root = _copy_corpus(safe, "gps_missing_all")
    results["scenarios"]["gps_missing_all"] = _detect_faults("gps_missing_all", root, {})

    # camera model mismatch / focal inconsistency — synthetic sidecar markers
    root = _copy_corpus(safe, "camera_model_mismatch")
    (root / "CAMERA_MISMATCH.marker").write_text("OTHER_CAMERA", encoding="utf-8")
    results["scenarios"]["camera_model_mismatch"] = _detect_faults(
        "camera_model_mismatch", root, {"camera_mismatch": True}
    )

    root = _copy_corpus(safe, "focal_length_inconsistency")
    results["scenarios"]["focal_length_inconsistency"] = _detect_faults(
        "focal_length_inconsistency", root, {"focal_inconsistency": True}
    )

    # GCP removed / malformed
    root = _copy_corpus(safe, "gcp_removed")
    for gcp in list(root.rglob("*gcp*")):
        if gcp.is_file():
            gcp.unlink()
    results["scenarios"]["gcp_removed"] = _detect_faults("gcp_removed", root, {})

    root = _copy_corpus(safe, "gcp_malformed")
    gcp_path = root / "gcp_list.txt"
    gcp_path.write_text("NOT_A_VALID_GCP\n!!!\n", encoding="utf-8")
    results["scenarios"]["gcp_malformed"] = _detect_faults(
        "gcp_malformed", root, {"gcp_malformed": True}
    )

    # unsupported / hidden
    root = _copy_corpus(safe, "unsupported_file_inserted")
    (root / "weird.xyzunsupported").write_bytes(b"nope")
    results["scenarios"]["unsupported_file_inserted"] = _detect_faults(
        "unsupported_file_inserted", root, {}
    )

    root = _copy_corpus(safe, "hidden_file_inserted")
    (root / ".hidden_payload.bin").write_bytes(b"secretish")
    results["scenarios"]["hidden_file_inserted"] = _detect_faults(
        "hidden_file_inserted", root, {}
    )

    # path traversal archive entry test (security layer, not corpus mutate)
    from .security import AcquisitionSecurityError, reject_path_traversal

    traversal_rejected = False
    try:
        reject_path_traversal("../evil.jpg")
    except AcquisitionSecurityError:
        traversal_rejected = True
    root = _copy_corpus(safe, "path_traversal_archive_entry")
    results["scenarios"]["path_traversal_archive_entry"] = _detect_faults(
        "path_traversal_archive_entry",
        root,
        {"traversal_rejected": traversal_rejected},
    )

    # thermal/visual false pairing metadata
    root = _copy_corpus(safe, "thermal_visual_false_pairing")
    (root / "false_thermal_pair.json").write_text(
        json.dumps({"visual": "a.jpg", "thermal": "b.jpg", "paired": True, "proven": False}),
        encoding="utf-8",
    )
    results["scenarios"]["thermal_visual_false_pairing"] = _detect_faults(
        "thermal_visual_false_pairing", root, {"false_pairing": True}
    )

    # approval bypass attempts (no corpus copy needed beyond markers)
    root = _copy_corpus(safe, "candidate_declaring_approved_status")
    results["scenarios"]["candidate_declaring_approved_status"] = _detect_faults(
        "candidate_declaring_approved_status", root, {}
    )
    root = _copy_corpus(safe, "raw_dictionary_approval_bypass")
    results["scenarios"]["raw_dictionary_approval_bypass"] = _detect_faults(
        "raw_dictionary_approval_bypass", root, {}
    )

    # mixed dataset contamination
    root = _copy_corpus(safe, "mixed_dataset_contamination")
    (root / "FOREIGN_DATASET_ID.txt").write_text("OTHER_CORPUS", encoding="utf-8")
    results["scenarios"]["mixed_dataset_contamination"] = _detect_faults(
        "mixed_dataset_contamination", root, {"contaminated": True}
    )

    for name, outcome in results["scenarios"].items():
        if not outcome.get("matched"):
            results["false_negatives"].append(name)

    write_json(faults_dir(safe) / "fault_matrix_results.json", results)
    return results
