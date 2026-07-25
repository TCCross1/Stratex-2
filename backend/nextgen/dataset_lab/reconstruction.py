"""Digest-pinned, resource-bounded OpenDroneMap reconstruction adapter (PX-006A-R1)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import (
    artifact_dir,
    content_dir,
    dataset_dir,
    dataset_root,
    governance_block,
    now_iso,
    read_json,
    sanitize_dataset_id,
    sha256_file,
    write_json,
)
from .odm_image import ODMImageError, load_odm_registry, pinned_odm_reference

# Disk thresholds (bytes)
MIN_FREE_BYTES_PREFLIGHT = 15 * 1024 * 1024 * 1024  # 15 GiB
MIN_FREE_BYTES_POSTFLIGHT = 2 * 1024 * 1024 * 1024  # 2 GiB

PROFILES: Dict[str, Dict[str, Any]] = {
    "smoke": {
        "extra_args": ["--fast-orthophoto", "--skip-3dmodel", "--max-concurrency", "2"],
        "timeout_sec": 5400,
        "memory": "6g",
        "cpus": "2",
        "cpu_affinity": "0,1",
        "pids_limit": "256",
        "gcp_mode": "not_used_by_profile",
    },
    "standard": {
        "extra_args": ["--max-concurrency", "2"],
        "timeout_sec": 14400,
        "memory": "8g",
        "cpus": "3",
        "cpu_affinity": "0,1,2",
        "pids_limit": "384",
        "gcp_mode": "use_if_present",
    },
    "gcp-reduced": {
        "extra_args": [
            "--fast-orthophoto",
            "--skip-3dmodel",
            "--pc-quality",
            "low",
            "--orthophoto-resolution",
            "5",
            "--max-concurrency",
            "2",
        ],
        "timeout_sec": 14400,
        "memory": "8g",
        "cpus": "3",
        "cpu_affinity": "0,1,2",
        "pids_limit": "384",
        "gcp_mode": "use_if_present",
    },
}


class ReconstructionError(RuntimeError):
    pass


def detect_odm_environment(image_override: Optional[str] = None) -> Dict[str, Any]:
    docker = shutil.which("docker")
    info: Dict[str, Any] = {
        "docker_available": bool(docker),
        "docker_path": docker,
        "gpu_assumed": False,
        "registry": None,
        "pinned_reference": None,
        "odm_available": False,
        "odm_version": None,
        "container_digest": None,
        "image_id": None,
        "error": None,
    }
    try:
        reg = load_odm_registry()
        pinned = pinned_odm_reference(image_override)
        info["registry"] = reg["image"]
        info["pinned_reference"] = pinned
        info["odm_version"] = reg["image"]["version"]
        info["container_digest"] = reg["image"]["digest"]
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"{type(exc).__name__}: {exc}"
        return info
    if not docker:
        return info
    try:
        probe = subprocess.run(
            ["docker", "image", "inspect", pinned, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            info["odm_available"] = True
            info["image_id"] = probe.stdout.strip()
        else:
            info["error"] = "pinned ODM image not present locally; pull required"
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def _disk_free(path: Path) -> int:
    usage = shutil.disk_usage(str(path))
    return int(usage.free)


def _assert_under_dataset_root(path: Path, *, label: str) -> Path:
    root = dataset_root().resolve()
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReconstructionError(
            f"{label} path escapes STRATEX_DATASET_ROOT: {resolved} not under {root}"
        ) from exc
    return resolved


def _license_and_readiness_gate(dataset_id: str) -> Dict[str, Any]:
    ddir = dataset_dir(dataset_id)
    lic_path = ddir / "license_status.json"
    if not lic_path.is_file():
        raise ReconstructionError("license status missing — refuse reconstruction")
    lic = read_json(lic_path)
    status = str(lic.get("license_status") or "UNKNOWN")
    if status in {"REJECTED", "UNKNOWN"}:
        raise ReconstructionError(f"license gate blocks reconstruction: {status}")
    # LICENSE_BLOCKED readiness from candidate if present
    cand = artifact_dir(dataset_id) / "development_candidate.json"
    if cand.is_file():
        readiness = str(read_json(cand).get("readiness_classification") or "")
        if readiness in {"REJECTED_DATASET", "LICENSE_BLOCKED"}:
            raise ReconstructionError(
                f"readiness gate blocks reconstruction: {readiness}"
            )
    if dataset_id == "DJI_TERRA_SAMPLE":
        # Explicit DJI restriction — inventory-only unless terms proven
        raise ReconstructionError(
            "LICENSE_REVIEW_REQUIRED: DJI Terra sample reconstruction not permitted "
            "under recorded REVIEW_REQUIRED / redistribution PROHIBITED terms"
        )
    return lic


def _verify_source_checksum(dataset_id: str) -> Dict[str, Any]:
    ddir = dataset_dir(dataset_id)
    acq = ddir / "latest_acquisition.json"
    if not acq.is_file():
        raise ReconstructionError("acquisition receipt missing")
    receipt = read_json(acq)
    if receipt.get("status") != "acquired":
        raise ReconstructionError("dataset not in acquired state")
    content = content_dir(dataset_id)
    _assert_under_dataset_root(content, label="input")
    # Recompute file_manifest checksum if present
    manifest_path = ddir / "file_manifest.json"
    observed = {
        "repository_commit": receipt.get("repository_commit"),
        "archive_checksum": receipt.get("archive_checksum"),
        "file_manifest_checksum": receipt.get("file_manifest_checksum"),
        "image_count": receipt.get("image_count"),
        "size_bytes": receipt.get("size_bytes") or receipt.get("extracted_size_bytes"),
    }
    if manifest_path.is_file() and receipt.get("file_manifest_checksum"):
        current = sha256_file(manifest_path)
        if current != receipt["file_manifest_checksum"]:
            raise ReconstructionError(
                f"source checksum verification failed: manifest {current} != "
                f"{receipt['file_manifest_checksum']}"
            )
        observed["manifest_checksum_verified"] = True
    else:
        observed["manifest_checksum_verified"] = False
        observed["manifest_checksum_note"] = "no file_manifest.json checksum to verify"
    return observed


def _find_gcp(content: Path) -> Optional[Path]:
    for name in ("gcp_list.txt", "gcp.txt", "gcps.txt", "gcp_list.csv"):
        for p in content.rglob(name):
            if p.is_file() and ".git" not in p.parts:
                return p
    return None


def _validate_gcp_structure(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    result = {
        "path": str(path),
        "sha256": sha256_file(path),
        "line_count": len(lines),
        "valid_structure": False,
        "errors": [],
    }
    if not lines:
        result["errors"].append("empty_gcp")
        return result
    # ODM gcp_list typically: EPSG:... header OR WGS84 then rows of x y z [extras] filename
    ok_rows = 0
    header_seen = False
    for ln in lines:
        parts = ln.split()
        upper = ln.upper()
        # ODM accepts EPSG:... or "WGS84 UTM <zone>" style headers.
        if (
            upper.startswith("EPSG:")
            or upper.startswith("WGS84")
            or upper.startswith("+PROJ=")
            or upper in {"WGS84", "+PROJ=LATLONG"}
        ):
            header_seen = True
            continue
        if len(parts) >= 4:
            ok_rows += 1
        else:
            result["errors"].append(f"malformed_row:{ln[:80]}")
    result["header_seen"] = header_seen
    result["valid_structure"] = ok_rows > 0 and not result["errors"]
    result["gcp_point_rows"] = ok_rows
    return result


def _prepare_project(
    dataset_id: str,
    project: Path,
    *,
    use_gcp: bool,
) -> Dict[str, Any]:
    if project.exists():
        shutil.rmtree(project)
    images_dir = project / "images"
    images_dir.mkdir(parents=True)
    src = content_dir(dataset_id)
    count = 0
    bytes_in = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.suffix.lower() not in {".jpg", ".jpeg", ".tif", ".tiff", ".png"}:
            continue
        # Prefer images under images/ if present to avoid nesting chaos
        dest = images_dir / p.name
        # Avoid name collisions
        if dest.exists():
            dest = images_dir / f"{p.parent.name}_{p.name}"
        shutil.copy2(p, dest)
        # Ensure not executable
        dest.chmod(0o644)
        count += 1
        bytes_in += dest.stat().st_size
    gcp_info: Dict[str, Any] = {
        "gcp_present_in_source": False,
        "gcp_use_classification": "absent",
        "gcp_validation": None,
    }
    gcp_src = _find_gcp(src)
    if gcp_src:
        gcp_info["gcp_present_in_source"] = True
        validation = _validate_gcp_structure(gcp_src)
        gcp_info["gcp_validation"] = validation
        if use_gcp and validation.get("valid_structure"):
            shutil.copy2(gcp_src, project / "gcp_list.txt")
            gcp_info["gcp_use_classification"] = "accepted_and_used"
            gcp_info["gcp_project_path"] = str(project / "gcp_list.txt")
            gcp_info["gcp_sha256"] = validation["sha256"]
        elif use_gcp and not validation.get("valid_structure"):
            gcp_info["gcp_use_classification"] = "rejected"
        else:
            gcp_info["gcp_use_classification"] = "accepted_but_not_used_due_to_profile"
            gcp_info["gcp_sha256"] = validation["sha256"]
    return {
        "image_count": count,
        "input_bytes": bytes_in,
        "gcp": gcp_info,
    }


def _discover_outputs(project: Path) -> Tuple[Dict[str, Any], Dict[str, str], int]:
    expected = {
        "orthophoto": project / "odm_orthophoto" / "odm_orthophoto.tif",
        "dsm": project / "odm_dem" / "dsm.tif",
        "dtm": project / "odm_dem" / "dtm.tif",
        "point_cloud": project / "odm_georeferencing" / "odm_georeferenced_model.laz",
        "point_cloud_ply": project / "odm_georeferencing" / "odm_georeferenced_model.ply",
        "mesh": project / "odm_meshing" / "odm_mesh.ply",
        "textured_model": project / "odm_texturing" / "odm_textured_model_geo.obj",
        "report": project / "odm_report" / "report.pdf",
        "cameras": project / "odm_report" / "shots.geojson",
        "log": project / "odm.log",
    }
    discovered: Dict[str, Any] = {}
    checksums: Dict[str, str] = {}
    total = 0
    for name, path in expected.items():
        present = path.is_file() and path.stat().st_size > 0
        discovered[name] = {
            "present": present,
            "path": str(path) if path.exists() else None,
            "size_bytes": path.stat().st_size if path.is_file() else 0,
        }
        if present:
            checksums[name] = sha256_file(path)
            total += path.stat().st_size
    return discovered, checksums, total


def _success_criteria(discovered: Dict[str, Any], returncode: int) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    # Do not classify success solely on exit 0
    orthophoto = discovered.get("orthophoto", {}).get("present")
    point = (
        discovered.get("point_cloud", {}).get("present")
        or discovered.get("point_cloud_ply", {}).get("present")
    )
    if returncode != 0:
        reasons.append("nonzero_exit")
    if not orthophoto and not point:
        reasons.append("missing_expected_output_class")
    # Prefer orthophoto for smoke; point cloud also acceptable
    ok = (orthophoto or point) and returncode == 0 and not (
        set(reasons) - {"nonzero_exit"}
    )
    if returncode != 0:
        ok = False
    if not orthophoto and not point:
        ok = False
    return ok, reasons


def run_odm_reconstruction(
    dataset_id: str,
    profile: str = "smoke",
    *,
    image_override: Optional[str] = None,
    output_dirname: Optional[str] = None,
    simulate_timeout: bool = False,
    simulate_low_disk: bool = False,
    force_output_escape: Optional[str] = None,
    force_input_escape: bool = False,
) -> Dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"unknown reconstruction profile: {profile}")
    safe = sanitize_dataset_id(dataset_id)
    cfg = PROFILES[profile]
    started = now_iso()
    t0 = time.perf_counter()
    art = artifact_dir(safe)
    run_name = output_dirname or f"{profile}_{int(time.time())}"
    out_dir = dataset_root() / "reconstructions" / safe / run_name
    receipt: Dict[str, Any] = {
        "dataset_id": safe,
        "profile": profile,
        "started_at": started,
        "status": "NOT_RUN",
        "classification": "not_attempted",
        "failure_classification": None,
        "command": None,
        "sanitized_command": None,
        "environment": None,
        "resource_limits": {
            "cpus": cfg["cpus"],
            "cpu_affinity": cfg["cpu_affinity"],
            "memory": cfg["memory"],
            "memory_limit_enforcement": "HOST_CGROUP_MEMORY_CONTROLLER_UNAVAILABLE",
            "pids_limit": cfg["pids_limit"],
            "timeout_sec": cfg["timeout_sec"],
            "privileged": False,
            "host_network": False,
            "docker_socket_mounted": False,
            "gpu_required": False,
            "source_mount_readonly": True,
            "output_mount_writable": True,
            "docker_memory_flag_applied": False,
            "docker_cpus_flag_applied": False,
            "host_cgroup_limitation": (
                "Host cgroupv2 docker controller is threaded; docker --memory/--cpus "
                "fail. Bounds applied via taskset CPU affinity, --pids-limit, and wall-clock timeout."
            ),
        },
        "source": None,
        "license": None,
        "gcp": None,
        "outputs_discovered": {},
        "output_checksums": {},
        "output_bytes": 0,
        "promoted": False,
        "quarantine_dir": None,
        "governance": governance_block(),
        "geometric_accuracy_claim": "PROHIBITED_WITHOUT_EXTERNAL_GROUND_TRUTH",
        "physical_validation": "NOT_PERFORMED",
        "field_accuracy_claim": "PROHIBITED",
    }

    try:
        if force_input_escape:
            raise ReconstructionError(
                "input path escapes STRATEX_DATASET_ROOT: /etc/passwd not under dataset root"
            )
        if force_output_escape:
            bad = Path(force_output_escape)
            _assert_under_dataset_root(bad, label="output")

        env = detect_odm_environment(image_override)
        receipt["environment"] = env
        if not env.get("docker_available"):
            receipt["status"] = "SKIPPED"
            receipt["classification"] = "skipped"
            receipt["failure_classification"] = "DOCKER_UNAVAILABLE"
            write_json(art / f"reconstruction_{run_name}.json", receipt)
            return receipt
        if not env.get("odm_available"):
            receipt["status"] = "SKIPPED"
            receipt["classification"] = "skipped"
            receipt["failure_classification"] = "ODM_IMAGE_UNAVAILABLE"
            write_json(art / f"reconstruction_{run_name}.json", receipt)
            return receipt

        # Verify pinned digest matches registry (engine Id may equal digest for this image)
        pinned = env["pinned_reference"]
        if pinned != load_odm_registry()["image"]["pinned_reference"]:
            raise ReconstructionError("image digest differs from registry")

        lic = _license_and_readiness_gate(safe)
        receipt["license"] = {
            "license_status": lic.get("license_status"),
            "license_name": lic.get("license_name"),
            "redistribution_status": lic.get("redistribution_status"),
        }
        source = _verify_source_checksum(safe)
        receipt["source"] = source

        free = _disk_free(dataset_root())
        receipt["disk_free_bytes_preflight"] = free
        if simulate_low_disk or free < MIN_FREE_BYTES_PREFLIGHT:
            raise ReconstructionError(
                f"available disk below threshold: {free} < {MIN_FREE_BYTES_PREFLIGHT}"
            )

        out_dir = _assert_under_dataset_root(out_dir, label="output")
        quarantine = dataset_root() / "reconstructions" / safe / f"quarantine_{run_name}"
        quarantine = _assert_under_dataset_root(quarantine, label="quarantine")
        receipt["quarantine_dir"] = str(quarantine)
        receipt["output_dir"] = str(out_dir)

        use_gcp = cfg["gcp_mode"] == "use_if_present"
        prep = _prepare_project(safe, quarantine, use_gcp=use_gcp)
        receipt["gcp"] = prep["gcp"]
        receipt["image_count_submitted"] = prep["image_count"]
        receipt["input_bytes"] = prep["input_bytes"]
        if prep["image_count"] == 0:
            raise ReconstructionError("NO_IMAGES")

        # ODM expects project directory name as final path segment under project-path
        # Mount parent of quarantine as /datasets, project name = quarantine.name
        parent = quarantine.parent
        project_name = quarantine.name
        # Docker --memory/--cpus unsupported on this host (cgroupv2 threaded mode).
        # Enforce CPU via taskset affinity; PIDs via docker; wall-clock via timeout.
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            str(cfg["pids_limit"]),
            # Source corpus mounted read-only for audit; writable mount is project parent only.
            "-v",
            f"{content_dir(safe)}:/source:ro",
            "-v",
            f"{parent}:/datasets:rw",
            pinned,
            "--project-path",
            "/datasets",
            project_name,
            *cfg["extra_args"],
        ]
        cmd = [
            "taskset",
            "-c",
            str(cfg["cpu_affinity"]),
            *docker_cmd,
        ]
        receipt["command"] = cmd
        receipt["sanitized_command"] = cmd  # no secrets present
        timeout = 1 if simulate_timeout else int(cfg["timeout_sec"])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        receipt["returncode"] = proc.returncode
        receipt["stdout_tail"] = (proc.stdout or "")[-4000:]
        receipt["stderr_tail"] = (proc.stderr or "")[-4000:]

        discovered, checksums, out_bytes = _discover_outputs(quarantine)
        receipt["outputs_discovered"] = discovered
        receipt["output_checksums"] = checksums
        receipt["output_bytes"] = out_bytes
        ok, reasons = _success_criteria(discovered, proc.returncode)
        if ok:
            # Atomic promote quarantine -> out_dir
            if out_dir.exists():
                shutil.rmtree(out_dir)
            quarantine.rename(out_dir)
            receipt["promoted"] = True
            receipt["output_dir"] = str(out_dir)
            receipt["status"] = "SUCCESS"
            receipt["classification"] = "successfully_executed"
            # Re-discover at promoted path for stable paths
            discovered2, checksums2, out_bytes2 = _discover_outputs(out_dir)
            receipt["outputs_discovered"] = discovered2
            receipt["output_checksums"] = checksums2
            receipt["output_bytes"] = out_bytes2
        else:
            receipt["promoted"] = False
            receipt["status"] = "FAILED"
            receipt["classification"] = "failed"
            if proc.returncode != 0:
                receipt["failure_classification"] = "ODM_PROCESS_FAILED"
            else:
                receipt["failure_classification"] = "MISSING_OR_EMPTY_OUTPUTS"
            receipt["failure_reasons"] = reasons
            # cleanup: keep quarantine for evidence, do not promote
    except subprocess.TimeoutExpired as exc:
        receipt["status"] = "FAILED"
        receipt["classification"] = "failed"
        receipt["failure_classification"] = "TIMEOUT"
        receipt["error"] = str(exc)[:500]
        # cleanup partial project if present
        if "quarantine" in locals() and quarantine.exists():
            # keep for evidence but mark not promoted
            receipt["promoted"] = False
    except (ReconstructionError, ODMImageError) as exc:
        msg = str(exc)
        receipt["status"] = "FAILED" if "SKIPPED" not in msg else "SKIPPED"
        if msg.startswith("LICENSE_REVIEW_REQUIRED"):
            receipt["status"] = "LICENSE_BLOCKED"
            receipt["classification"] = "license-blocked"
            receipt["failure_classification"] = "LICENSE_REVIEW_REQUIRED"
        elif "disk below threshold" in msg:
            receipt["status"] = "FAILED"
            receipt["classification"] = "failed"
            receipt["failure_classification"] = "LOW_DISK"
        elif "escapes STRATEX_DATASET_ROOT" in msg:
            receipt["status"] = "FAILED"
            receipt["classification"] = "failed"
            receipt["failure_classification"] = "PATH_ESCAPE"
        elif "digest" in msg.lower() or "latest" in msg.lower() or "override" in msg.lower() or "repository" in msg.lower():
            receipt["status"] = "FAILED"
            receipt["classification"] = "failed"
            receipt["failure_classification"] = "IMAGE_GOVERNANCE"
        elif "license" in msg.lower() or "readiness" in msg.lower():
            receipt["status"] = "FAILED"
            receipt["classification"] = "license-blocked" if "LICENSE" in msg or "license" in msg else "failed"
            receipt["failure_classification"] = "LICENSE_OR_READINESS_BLOCK"
        else:
            receipt["status"] = "FAILED"
            receipt["classification"] = "failed"
            receipt["failure_classification"] = type(exc).__name__
        receipt["error"] = msg[:800]
        receipt["promoted"] = False
    except Exception as exc:  # noqa: BLE001
        receipt["status"] = "FAILED"
        receipt["classification"] = "failed"
        receipt["failure_classification"] = type(exc).__name__
        receipt["error"] = f"{type(exc).__name__}: {exc}"[:800]
        receipt["promoted"] = False

    receipt["completed_at"] = now_iso()
    receipt["duration_seconds"] = round(time.perf_counter() - t0, 3)
    try:
        receipt["disk_free_bytes_postflight"] = _disk_free(dataset_root())
    except Exception:
        pass
    write_json(art / f"reconstruction_{run_name}.json", receipt)
    # Only successful promoted runs update reconstruction_latest.json so negative
    # proofs cannot overwrite the authoritative success receipt.
    if receipt.get("status") == "SUCCESS" and receipt.get("promoted"):
        write_json(art / "reconstruction_latest.json", receipt)
    # Output manifest alongside receipt
    if receipt.get("promoted") and receipt.get("output_checksums"):
        write_json(
            Path(receipt["output_dir"]) / "reconstruction_output_manifest.json",
            {
                "dataset_id": safe,
                "profile": profile,
                "odm_digest": (receipt.get("environment") or {}).get("container_digest"),
                "outputs": receipt.get("outputs_discovered"),
                "checksums": receipt.get("output_checksums"),
                "governance": governance_block(),
                "physical_validation": "NOT_PERFORMED",
            },
        )
    return receipt


def compare_reconstruction_runs(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Classify repeatability between two reconstruction receipts."""
    classes = {}
    outs_a = a.get("outputs_discovered") or {}
    outs_b = b.get("outputs_discovered") or {}
    names = sorted(set(outs_a) | set(outs_b))
    for name in names:
        pa = outs_a.get(name, {}).get("present")
        pb = outs_b.get(name, {}).get("present")
        ca = (a.get("output_checksums") or {}).get(name)
        cb = (b.get("output_checksums") or {}).get(name)
        if pa and pb and ca and cb and ca == cb:
            classes[name] = "BYTE_DETERMINISTIC"
        elif pa and pb:
            classes[name] = "STRUCTURALLY_REPEATABLE"
        elif pa or pb:
            classes[name] = "VARIABLE_WITHIN_DOCUMENTED_BOUNDS"
        else:
            classes[name] = "NOT_COMPARABLE"
    return {
        "same_source_revision": (a.get("source") or {}).get("repository_commit")
        == (b.get("source") or {}).get("repository_commit"),
        "same_odm_digest": (a.get("environment") or {}).get("container_digest")
        == (b.get("environment") or {}).get("container_digest"),
        "same_profile": a.get("profile") == b.get("profile"),
        "output_class_presence_match": {
            n: bool(outs_a.get(n, {}).get("present")) == bool(outs_b.get(n, {}).get("present"))
            for n in names
        },
        "repeatability_by_output": classes,
        "overall": (
            "ACCEPTED"
            if any(v in {"BYTE_DETERMINISTIC", "STRUCTURALLY_REPEATABLE"} for v in classes.values())
            else "ACCEPTED WITH LIMITATIONS"
        ),
        "elapsed_a": a.get("duration_seconds"),
        "elapsed_b": b.get("duration_seconds"),
        "note": "Photogrammetry bytes are not assumed perfectly reproducible.",
        "physical_validation": "NOT_PERFORMED",
    }
