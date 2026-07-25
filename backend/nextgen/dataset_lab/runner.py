"""Repeatable experiment runner for PX-006A."""

from __future__ import annotations

import hashlib
import platform
import sys
from typing import Any, Dict, List, Optional

from .acquire import acquire_dataset
from .common import (
    LAB_VERSION,
    MODULE_IDENTITY,
    experiments_dir,
    governance_block,
    now_iso,
    sanitize_dataset_id,
    sha256_json,
    write_json,
)
from .corpus import build_candidate_package
from .faults import generate_fault_matrix
from .inventory import inventory_dataset
from .license_check import license_check
from .reconstruction import detect_odm_environment, run_odm_reconstruction
from .rehearsal import rehearse_pipeline

PROFILES = {
    "smoke": ["acquire_verify", "license", "inventory", "candidate"],
    "inventory": ["license", "inventory"],
    "atc-validation": ["license", "inventory", "candidate", "rehearsal"],
    "reconstruction": ["license", "inventory", "reconstruction"],
    "fault-matrix": ["license", "inventory", "faults"],
    "full-development": [
        "acquire_verify",
        "license",
        "inventory",
        "candidate",
        "faults",
        "rehearsal",
        "reconstruction",
    ],
}


def _software_commit() -> str:
    import subprocess
    from .common import repo_root

    try:
        return subprocess.run(
            ["git", "-C", str(repo_root()), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except Exception:
        return "UNKNOWN"


def experiment_identity(
    dataset_id: str,
    profile: str,
    source_revision: Optional[str],
    software_commit: str,
    configuration: Dict[str, Any],
) -> str:
    """Deterministic experiment id — not solely a random timestamp."""
    material = {
        "dataset_id": dataset_id,
        "profile": profile,
        "source_revision": source_revision or "NONE",
        "software_commit": software_commit,
        "lab_version": LAB_VERSION,
        "configuration": configuration,
    }
    digest = sha256_json(material)[:16]
    return f"exp_{dataset_id.lower()}_{profile}_{digest}"


def run_experiment(dataset_id: str, profile: str = "smoke") -> Dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    safe = sanitize_dataset_id(dataset_id)
    stages = list(PROFILES[profile])
    software_commit = _software_commit()
    configuration = {
        "profile": profile,
        "stages": stages,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "module": MODULE_IDENTITY,
        "lab_version": LAB_VERSION,
    }
    # Seed source revision from prior acquisition if present.
    from .common import dataset_dir, read_json

    acq = dataset_dir(safe) / "latest_acquisition.json"
    source_revision = None
    if acq.is_file():
        prev = read_json(acq)
        source_revision = prev.get("repository_commit") or prev.get("archive_checksum")

    experiment_id = experiment_identity(
        safe, profile, source_revision, software_commit, configuration
    )
    receipt: Dict[str, Any] = {
        "experiment_id": experiment_id,
        "dataset_id": safe,
        "source_revision": source_revision,
        "software_commit": software_commit,
        "configuration": configuration,
        "parser_versions": {"lab": LAB_VERSION, "python": sys.version.split()[0]},
        "odm": detect_odm_environment(),
        "started_at": now_iso(),
        "completed_at": None,
        "duration_seconds": None,
        "stages_executed": [],
        "stage_results": {},
        "warnings": [],
        "failures": [],
        "generated_artifact_checksums": {},
        "truth_limitations": [
            "EXTERNAL_PUBLIC_DATASET",
            "NON_CANONICAL_TEST_DATA",
            "NOT_PHYSICAL_VALIDATION",
        ],
        "physical_validation": "NOT_PERFORMED",
        "governance": governance_block(),
        "production_readiness": "NOT_READY",
    }

    import time

    t0 = time.perf_counter()
    for stage in stages:
        receipt["stages_executed"].append(stage)
        try:
            if stage == "acquire_verify":
                out = acquire_dataset(safe, verify_only=True)
            elif stage == "license":
                out = license_check(safe)
            elif stage == "inventory":
                out = inventory_dataset(safe)
            elif stage == "candidate":
                out = build_candidate_package(safe)
            elif stage == "faults":
                out = generate_fault_matrix(safe)
            elif stage == "rehearsal":
                out = rehearse_pipeline(safe)
            elif stage == "reconstruction":
                out = run_odm_reconstruction(safe, profile="smoke")
                if out.get("status") == "SKIPPED":
                    receipt["warnings"].append(
                        f"reconstruction_skipped:{out.get('failure_classification')}"
                    )
            else:
                raise ValueError(f"unknown stage {stage}")
            receipt["stage_results"][stage] = {
                "status": "OK",
                "summary_keys": sorted(list(out.keys()))[:30]
                if isinstance(out, dict)
                else [],
            }
            if isinstance(out, dict):
                receipt["generated_artifact_checksums"][stage] = hashlib.sha256(
                    repr(sorted(out.keys())).encode("utf-8")
                ).hexdigest()[:16]
        except Exception as exc:  # noqa: BLE001
            receipt["stage_results"][stage] = {
                "status": "FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            }
            receipt["failures"].append({"stage": stage, "error": str(exc)[:500]})

    receipt["completed_at"] = now_iso()
    receipt["duration_seconds"] = round(time.perf_counter() - t0, 3)
    write_json(experiments_dir(safe) / f"{experiment_id}.json", receipt)
    write_json(experiments_dir(safe) / "latest_experiment.json", receipt)
    return receipt
