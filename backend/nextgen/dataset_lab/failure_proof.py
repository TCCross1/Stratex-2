"""Controlled negative reconstruction tests (PX-006A-R1)."""

from __future__ import annotations

from typing import Any, Dict

from .odm_image import ODMImageError, pinned_odm_reference
from .reconstruction import ReconstructionError, run_odm_reconstruction


def run_failure_proofs() -> Dict[str, Any]:
    results: Dict[str, Any] = {"cases": {}, "physical_validation": "NOT_PERFORMED"}

    # wrong digest / latest
    for name, override in [
        ("wrong_digest", "opendronemap/odm@sha256:" + ("0" * 64)),
        ("latest_tag", "opendronemap/odm:latest"),
        ("mutable_tag", "opendronemap/odm:3.5.6"),
    ]:
        try:
            pinned_odm_reference(override)
            results["cases"][name] = {"ok": False, "error": "did_not_reject"}
        except ODMImageError as exc:
            results["cases"][name] = {"ok": True, "error": str(exc)}

    # path escapes
    r = run_odm_reconstruction("MYGLA", profile="smoke", force_input_escape=True, output_dirname="fail_input_escape")
    results["cases"]["input_path_escape"] = {
        "ok": r.get("failure_classification") == "PATH_ESCAPE",
        "status": r.get("status"),
        "promoted": r.get("promoted"),
        "classification": r.get("failure_classification"),
    }
    r = run_odm_reconstruction(
        "MYGLA",
        profile="smoke",
        force_output_escape="/tmp/evil-out",
        output_dirname="fail_output_escape",
    )
    results["cases"]["output_path_escape"] = {
        "ok": r.get("failure_classification") == "PATH_ESCAPE",
        "status": r.get("status"),
        "promoted": r.get("promoted"),
        "classification": r.get("failure_classification"),
    }

    # low disk simulation
    r = run_odm_reconstruction("MYGLA", profile="smoke", simulate_low_disk=True, output_dirname="fail_low_disk")
    results["cases"]["low_disk"] = {
        "ok": r.get("failure_classification") == "LOW_DISK",
        "promoted": r.get("promoted"),
        "status": r.get("status"),
    }

    # timeout simulation
    r = run_odm_reconstruction("MYGLA", profile="smoke", simulate_timeout=True, output_dirname="fail_timeout")
    results["cases"]["timeout"] = {
        "ok": r.get("failure_classification") == "TIMEOUT",
        "promoted": r.get("promoted"),
        "status": r.get("status"),
    }

    # license-blocked DJI
    r = run_odm_reconstruction("DJI_TERRA_SAMPLE", profile="smoke", output_dirname="fail_dji_license")
    results["cases"]["license_blocked_dji"] = {
        "ok": r.get("classification") == "license-blocked" or r.get("status") == "LICENSE_BLOCKED",
        "promoted": r.get("promoted"),
        "status": r.get("status"),
        "failure_classification": r.get("failure_classification"),
    }

    # Ensure no case promoted partial success
    results["partial_output_promotion_protection"] = all(
        not (c.get("promoted") is True) for c in results["cases"].values() if isinstance(c, dict)
    )
    return results
