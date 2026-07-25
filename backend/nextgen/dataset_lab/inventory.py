"""Dataset inventory and privacy-safe metadata extraction for PX-006A."""

from __future__ import annotations

import json
import mimetypes
from collections import Counter
from typing import Any, Dict, List, Tuple

from .common import (
    GOVERNANCE_LABELS,
    artifact_dir,
    content_dir,
    get_registry_entry,
    governance_block,
    now_iso,
    redacted_summary_gps,
    sanitize_dataset_id,
    sha256_bytes,
    sha256_file,
    write_json,
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".dng"}
GCP_NAMES = {"gcp_list.txt", "gcp.txt", "gcps.txt", "gcp_list.csv"}
RECON_HINTS = ("odm_", "orthophoto", "dsm", "dtm", "opensfm", "reconstruction")


def _safe_exif(path) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "width": None,
        "height": None,
        "camera_make": None,
        "camera_model": None,
        "focal_length": None,
        "orientation": None,
        "timestamp": None,
        "gps_present": False,
        "dji_fields_present": False,
        "thermal_indicator": False,
    }
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except Exception:
        return out
    try:
        with Image.open(path) as img:
            out["width"], out["height"] = img.size
            exif = img.getexif()
            if not exif:
                return out
            tagged = {TAGS.get(k, str(k)): v for k, v in exif.items()}
            out["camera_make"] = str(tagged.get("Make") or "") or None
            out["camera_model"] = str(tagged.get("Model") or "") or None
            out["orientation"] = tagged.get("Orientation")
            out["timestamp"] = (
                str(tagged.get("DateTime") or tagged.get("DateTimeOriginal") or "")
                or None
            )
            fl = tagged.get("FocalLength")
            if fl is not None:
                try:
                    out["focal_length"] = float(fl)
                except Exception:
                    out["focal_length"] = str(fl)
            # GPS presence only — never emit coordinates into reports.
            out["gps_present"] = bool(tagged.get("GPSInfo"))
            make = (out["camera_make"] or "").upper()
            model = (out["camera_model"] or "").upper()
            out["dji_fields_present"] = "DJI" in make or "DJI" in model
            name_u = path.name.upper()
            out["thermal_indicator"] = any(
                x in name_u for x in ("_T.", "THERMAL", "IR_")
            ) or "R-JPEG" in model
    except Exception as exc:  # noqa: BLE001
        out["error"] = type(exc).__name__
    return out


def inventory_dataset(dataset_id: str) -> Dict[str, Any]:
    safe = sanitize_dataset_id(dataset_id)
    entry = get_registry_entry(safe)
    root = content_dir(safe)
    if not root.is_dir() or not any(root.iterdir()):
        raise FileNotFoundError(f"dataset not acquired: {safe}")

    files: List[Dict[str, Any]] = []
    image_records: List[Dict[str, Any]] = []
    duplicates: Dict[str, List[str]] = {}
    cameras: Counter[str] = Counter()
    aircraft: Counter[str] = Counter()
    gps_flags: List[bool] = []
    gcp_files: List[str] = []
    recon_files: List[str] = []
    unsupported: List[str] = []
    near_dup_names: List[Tuple[str, str]] = []
    name_index: Dict[str, str] = {}

    all_paths = sorted(
        p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts
    )

    for path in all_paths:
        rel = str(path.relative_to(root)).replace("\\", "/")
        digest = sha256_file(path)
        size = path.stat().st_size
        mime, _ = mimetypes.guess_type(path.name)
        suffix = path.suffix.lower()
        files.append(
            {
                "path": rel,
                "size_bytes": size,
                "mime": mime or "application/octet-stream",
                "sha256": digest,
                "suffix": suffix,
            }
        )
        duplicates.setdefault(digest, []).append(rel)
        lower_name = path.name.lower()
        if lower_name in name_index and name_index[lower_name] != rel:
            near_dup_names.append((name_index[lower_name], rel))
        else:
            name_index[lower_name] = rel

        if lower_name in GCP_NAMES or (
            "gcp" in lower_name and suffix in {".txt", ".csv"}
        ):
            gcp_files.append(rel)

        if suffix in {".las", ".laz", ".ply", ".obj", ".mtl", ".tif", ".tiff"} and any(
            h in rel.lower() for h in RECON_HINTS
        ):
            recon_files.append(rel)

        if suffix in IMAGE_SUFFIXES:
            meta = _safe_exif(path)
            gps_flags.append(bool(meta.get("gps_present")))
            cam = f"{meta.get('camera_make') or 'UNKNOWN'}/{meta.get('camera_model') or 'UNKNOWN'}"
            cameras[cam] += 1
            if meta.get("dji_fields_present"):
                aircraft["DJI"] += 1
            image_records.append(
                {
                    "path": rel,
                    "size_bytes": size,
                    "sha256": digest,
                    "width": meta.get("width"),
                    "height": meta.get("height"),
                    "camera_make": meta.get("camera_make"),
                    "camera_model": meta.get("camera_model"),
                    "focal_length": meta.get("focal_length"),
                    "orientation": meta.get("orientation"),
                    "timestamp": meta.get("timestamp"),
                    "gps_present": bool(meta.get("gps_present")),
                    "dji_fields_present": bool(meta.get("dji_fields_present")),
                    "thermal_indicator": bool(meta.get("thermal_indicator")),
                }
            )
        elif suffix in {".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1"}:
            unsupported.append(rel)

    dup_content = {k: v for k, v in duplicates.items() if len(v) > 1}
    if not gps_flags:
        gps_status = "GPS_ABSENT"
    elif all(gps_flags):
        gps_status = "GPS_PRESENT"
    elif any(gps_flags):
        gps_status = "GPS_PARTIAL"
    else:
        gps_status = "GPS_ABSENT"
    gps_status = redacted_summary_gps(gps_status)

    lidar = any(p.suffix.lower() in {".las", ".laz"} for p in all_paths)
    thermal = any(r.get("thermal_indicator") for r in image_records)

    manifest = {
        "dataset_id": safe,
        "display_name": entry.get("display_name"),
        "file_count": len(files),
        "files": [
            {"path": f["path"], "size_bytes": f["size_bytes"], "sha256": f["sha256"]}
            for f in files
        ],
        "file_manifest_checksum": sha256_bytes(
            json.dumps(
                [{"path": f["path"], "sha256": f["sha256"]} for f in files],
                sort_keys=True,
            ).encode("utf-8")
        ),
        "governance": governance_block(),
    }
    inventory = {
        "dataset_id": safe,
        "generated_at": now_iso(),
        "total_files": len(files),
        "total_images": len(image_records),
        "total_bytes": sum(f["size_bytes"] for f in files),
        "cameras_observed": dict(cameras),
        "aircraft_observed": dict(aircraft),
        "gps_status": gps_status,
        "gcp_present": bool(gcp_files),
        "gcp_files": gcp_files,
        "rtk_claimed_by_source": bool(entry.get("RTK_claimed_by_source")),
        "thermal_present": thermal,
        "lidar_present": lidar,
        "reconstruction_outputs_present": bool(recon_files),
        "reconstruction_files": recon_files[:50],
        "duplicate_content_groups": len(dup_content),
        "duplicate_examples": list(dup_content.values())[:10],
        "near_duplicate_names": near_dup_names[:20],
        "unsupported_files": unsupported,
        "images": image_records,
        "privacy_note": "EXIF GPS coordinates intentionally omitted from inventory reports",
        "governance": governance_block(),
        **{k: v for k, v in GOVERNANCE_LABELS.items()},
    }
    validation = {
        "dataset_id": safe,
        "ok": len(image_records) > 0,
        "image_count": len(image_records),
        "expected_image_count": entry.get("expected_image_count"),
        "gps_status": gps_status,
        "gcp_present": bool(gcp_files),
        "warnings": [],
        "errors": [],
        "governance": governance_block(),
    }
    expected = entry.get("expected_image_count")
    if expected and abs(len(image_records) - int(expected)) > 5:
        validation["warnings"].append("image_count_differs_from_registry_expectation")
    if not image_records:
        validation["ok"] = False
        validation["errors"].append("no_images_found")

    art = artifact_dir(safe)
    write_json(art / "manifest.json", manifest)
    write_json(art / "inventory.json", inventory)
    write_json(art / "validation.json", validation)
    summary = (
        f"# Inventory — {safe}\n\n"
        f"- files: {len(files)}\n"
        f"- images: {len(image_records)}\n"
        f"- bytes: {inventory['total_bytes']}\n"
        f"- GPS: {gps_status}\n"
        f"- GCP: {'PRESENT' if gcp_files else 'ABSENT'}\n"
        f"- thermal: {thermal}\n"
        f"- LiDAR: {lidar}\n"
        f"- cameras: {dict(cameras)}\n"
        f"- truth_status: {GOVERNANCE_LABELS['truth_status']}\n"
        f"- physical_validation: {GOVERNANCE_LABELS['physical_validation']}\n"
        f"- NOTE: no EXIF GPS coordinates are recorded in this summary\n"
    )
    (art / "summary.md").write_text(summary, encoding="utf-8")
    return {
        "manifest": manifest,
        "inventory": inventory,
        "validation": validation,
        "artifact_dir": str(art),
    }
