"""
Pre-seal ATC readiness checklist — Field Test v1 (Matrice 4E / 4T).

Runs immediately before `seal_package` inside `field_test_pipeline` only.
Validates mission profile, day RGB vs night thermal evidence, and required
stub artifacts. Seal is blocked when any blocking check fails.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .readiness import CheckResult, ReadinessReport


# Matrice field-test profiles (deterministic, no live SDK).
MATRICE_4E = "Matrice_4E"
MATRICE_4T = "Matrice_4T"

DAYTIME_MAPPING = "DAYTIME_PRECISION_MAPPING"
NIGHTTIME_AWE = "NIGHTTIME_AWE_VISUAL_THERMAL"

PROFILE_EXPECTATIONS: Dict[str, Dict[str, Any]] = {
    MATRICE_4E: {
        "mission_type": DAYTIME_MAPPING,
        "capture_label": "daytime RGB mapping",
        "required_media_types": {"RGB"},
        "min_media_items": 1,
        "candidate_section": "geometry_candidate",
        "candidate_list_key": "planes",
        "candidate_label": "geometry planes",
    },
    MATRICE_4T: {
        "mission_type": NIGHTTIME_AWE,
        "capture_label": "nighttime thermal AWE",
        "required_media_types": {"THERMAL", "RADIOMETRIC"},
        "min_media_items": 1,
        "candidate_section": "awe_candidate",
        "candidate_list_key": "findings",
        "candidate_label": "AWE findings",
    },
}


def _media_types(manifest_items: List[Dict[str, Any]]) -> Set[str]:
    return {
        str(item.get("media_type", "")).upper()
        for item in manifest_items
        if isinstance(item, dict)
    }


def evaluate_seal_readiness(
    package: Dict[str, Any],
    *,
    aircraft_profile: str,
    mission_type: str,
    mission_id: Optional[str] = None,
) -> ReadinessReport:
    """
    Minimum Matrice 4E / 4T checklist before seal.

    Blocking checks:
    - Supported aircraft profile (4E or 4T)
    - Mission type matches profile (day RGB mapping vs night thermal AWE)
    - Required evidence media types present in manifest (stub OK)
    - Required candidate section populated (geometry planes or AWE findings)
    """
    mid = mission_id or package.get("mission_id") or "unknown"
    checks: List[CheckResult] = []
    expectations = PROFILE_EXPECTATIONS.get(aircraft_profile)

    if not expectations:
        checks.append(
            CheckResult(
                "aircraft_profile",
                False,
                f"Unsupported profile {aircraft_profile!r}; expected Matrice_4E or Matrice_4T",
            )
        )
        blocking = [c.name for c in checks if c.blocking and not c.passed]
        return ReadinessReport(
            mission_id=mid,
            ready=False,
            checks=checks,
            blocking_failures=blocking,
        )

    checks.append(
        CheckResult(
            "aircraft_profile",
            True,
            f"{aircraft_profile} selected",
        )
    )

    expected_type = expectations["mission_type"]
    type_ok = mission_type == expected_type
    checks.append(
        CheckResult(
            "mission_type_profile",
            type_ok,
            (
                f"{mission_type} matches {aircraft_profile} ({expectations['capture_label']})"
                if type_ok
                else f"{mission_type} does not match {aircraft_profile}; expected {expected_type}"
            ),
        )
    )

    capture_type = (package.get("mission_metadata") or {}).get("capture_type")
    capture_ok = capture_type == expected_type
    checks.append(
        CheckResult(
            "capture_type",
            capture_ok,
            (
                f"Package capture_type is {capture_type}"
                if capture_ok
                else f"Package capture_type {capture_type!r} != expected {expected_type}"
            ),
        )
    )

    items = (package.get("evidence_manifest") or {}).get("items") or []
    media_types = _media_types(items)
    required_types: Set[str] = expectations["required_media_types"]
    present_required = media_types & required_types
    media_ok = len(items) >= expectations["min_media_items"] and bool(present_required)
    checks.append(
        CheckResult(
            "required_evidence_media",
            media_ok,
            (
                f"Found {sorted(present_required)} media ({len(items)} item(s))"
                if media_ok
                else f"Missing required {sorted(required_types)} evidence; have {sorted(media_types) or ['none']}"
            ),
        )
    )

    section = package.get(expectations["candidate_section"]) or {}
    entries = section.get(expectations["candidate_list_key"]) or []
    candidate_ok = bool(entries)
    checks.append(
        CheckResult(
            "required_candidate",
            candidate_ok,
            (
                f"{len(entries)} {expectations['candidate_label']} present"
                if candidate_ok
                else f"No {expectations['candidate_label']} in {expectations['candidate_section']}"
            ),
        )
    )

    blocking_failures = [c.name for c in checks if c.blocking and not c.passed]
    return ReadinessReport(
        mission_id=mid,
        ready=len(blocking_failures) == 0,
        checks=checks,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        blocking_failures=blocking_failures,
    )
