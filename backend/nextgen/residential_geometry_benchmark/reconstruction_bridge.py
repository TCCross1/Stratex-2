"""Reconstruction bridge for PX-006B using digest-pinned ODM from dataset_lab."""
from __future__ import annotations

from typing import Any, Dict, Optional

from nextgen.dataset_lab.license_check import license_check
from nextgen.dataset_lab.reconstruction import PROFILES, run_odm_reconstruction

PX006B_PROFILES: Dict[str, Dict[str, Any]] = {
    "roof-detail": {
        "extra_args": [
            "--pc-quality",
            "medium",
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
    "roof-smoke": {
        "extra_args": [
            "--fast-orthophoto",
            "--skip-3dmodel",
            "--max-concurrency",
            "2",
        ],
        "timeout_sec": 5400,
        "memory": "6g",
        "cpus": "2",
        "cpu_affinity": "0,1",
        "pids_limit": "256",
        "gcp_mode": "not_used_by_profile",
    },
}


def ensure_px006b_profiles_registered() -> None:
    for name, profile in PX006B_PROFILES.items():
        PROFILES.setdefault(name, profile)


def run_benchmark_reconstruction(
    dataset_id: str,
    *,
    profile: str = "roof-detail",
    output_dirname: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_px006b_profiles_registered()
    lic = license_check(dataset_id)
    if lic.get("license_status") == "REJECTED":
        return {
            "dataset_id": dataset_id,
            "status": "LICENSE_BLOCKED",
            "promoted": False,
            "authoritative": False,
        }
    if lic.get("redistribution_status") == "PROHIBITED":
        return {
            "dataset_id": dataset_id,
            "status": "LICENSE_BLOCKED",
            "promoted": False,
            "authoritative": False,
            "reason": "redistribution_prohibited",
        }
    return run_odm_reconstruction(dataset_id, profile=profile, output_dirname=output_dirname)
