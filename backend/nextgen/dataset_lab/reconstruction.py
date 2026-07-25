"""Optional OpenDroneMap reconstruction adapter (PX-006A)."""

from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict

from .common import (
    artifact_dir,
    content_dir,
    dataset_root,
    governance_block,
    now_iso,
    sanitize_dataset_id,
    sha256_file,
    write_json,
)

PROFILES = {
    "smoke": {
        "extra_args": ["--fast-orthophoto", "--skip-3dmodel"],
        "timeout_sec": 1800,
        "memory": "4g",
        "cpus": "2",
    },
    "standard": {
        "extra_args": [],
        "timeout_sec": 7200,
        "memory": "8g",
        "cpus": "4",
    },
    "high-detail": {
        "extra_args": ["--pc-quality", "high"],
        "timeout_sec": 14400,
        "memory": "16g",
        "cpus": "8",
    },
}


def detect_odm_environment() -> Dict[str, Any]:
    docker = shutil.which("docker")
    info: Dict[str, Any] = {
        "docker_available": bool(docker),
        "docker_path": docker,
        "odm_image": "opendronemap/odm:latest",
        "odm_available": False,
        "odm_version": None,
        "container_digest": None,
        "gpu_assumed": False,
    }
    if not docker:
        return info
    try:
        probe = subprocess.run(
            [
                "docker",
                "image",
                "inspect",
                info["odm_image"],
                "--format",
                "{{.Id}}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            info["odm_available"] = True
            info["container_digest"] = probe.stdout.strip()
        else:
            info["note"] = (
                "ODM image not present locally; pull required before reconstruction"
            )
    except Exception as exc:  # noqa: BLE001
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


def run_odm_reconstruction(dataset_id: str, profile: str = "smoke") -> Dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"unknown reconstruction profile: {profile}")
    safe = sanitize_dataset_id(dataset_id)
    env = detect_odm_environment()
    art = artifact_dir(safe)
    out_dir = dataset_root() / "reconstructions" / safe / profile
    receipt: Dict[str, Any] = {
        "dataset_id": safe,
        "profile": profile,
        "started_at": now_iso(),
        "environment": env,
        "output_dir": str(out_dir),
        "status": "NOT_RUN",
        "failure_classification": None,
        "command": None,
        "outputs_discovered": {},
        "output_checksums": {},
        "governance": governance_block(),
        "geometric_accuracy_claim": "PROHIBITED_WITHOUT_EXTERNAL_GROUND_TRUTH",
        "physical_validation": "NOT_PERFORMED",
    }
    if not env["docker_available"]:
        receipt["status"] = "SKIPPED"
        receipt["failure_classification"] = "DOCKER_UNAVAILABLE"
        write_json(art / f"reconstruction_{profile}.json", receipt)
        return receipt
    if not env["odm_available"]:
        receipt["status"] = "SKIPPED"
        receipt["failure_classification"] = "ODM_IMAGE_UNAVAILABLE"
        write_json(art / f"reconstruction_{profile}.json", receipt)
        return receipt

    project = out_dir
    images = project / "images"
    project.mkdir(parents=True, exist_ok=True)
    if images.exists():
        shutil.rmtree(images)
    images.mkdir(parents=True)
    src = content_dir(safe)
    count = 0
    for p in src.rglob("*"):
        if (
            p.is_file()
            and p.suffix.lower() in {".jpg", ".jpeg", ".tif", ".tiff", ".png"}
            and ".git" not in p.parts
        ):
            shutil.copy2(p, images / p.name)
            count += 1
    if count == 0:
        receipt["status"] = "FAILED"
        receipt["failure_classification"] = "NO_IMAGES"
        write_json(art / f"reconstruction_{profile}.json", receipt)
        return receipt

    cfg = PROFILES[profile]
    cmd = [
        "docker",
        "run",
        "--rm",
        "--memory",
        cfg["memory"],
        "--cpus",
        cfg["cpus"],
        "-v",
        f"{project}:/datasets/code",
        env["odm_image"],
        "--project-path",
        "/datasets",
        *cfg["extra_args"],
    ]
    receipt["command"] = cmd
    receipt["image_count_submitted"] = count
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=cfg["timeout_sec"], check=False
        )
        receipt["returncode"] = proc.returncode
        receipt["stdout_tail"] = (proc.stdout or "")[-2000:]
        receipt["stderr_tail"] = (proc.stderr or "")[-2000:]
        receipt["status"] = "SUCCESS" if proc.returncode == 0 else "FAILED"
        if proc.returncode != 0:
            receipt["failure_classification"] = "ODM_PROCESS_FAILED"
    except subprocess.TimeoutExpired:
        receipt["status"] = "FAILED"
        receipt["failure_classification"] = "TIMEOUT"
    except Exception as exc:  # noqa: BLE001
        receipt["status"] = "FAILED"
        receipt["failure_classification"] = type(exc).__name__

    expected = {
        "orthophoto": project / "odm_orthophoto" / "odm_orthophoto.tif",
        "dsm": project / "odm_dem" / "dsm.tif",
        "dtm": project / "odm_dem" / "dtm.tif",
        "point_cloud": project / "odm_georeferencing" / "odm_georeferenced_model.laz",
        "mesh": project / "odm_meshing" / "odm_mesh.ply",
        "textured_model": project / "odm_texturing" / "odm_textured_model_geo.obj",
        "report": project / "odm_report" / "report.pdf",
    }
    for name, path in expected.items():
        receipt["outputs_discovered"][name] = path.is_file()
        if path.is_file():
            receipt["output_checksums"][name] = sha256_file(path)

    receipt["completed_at"] = now_iso()
    write_json(art / f"reconstruction_{profile}.json", receipt)
    return receipt
