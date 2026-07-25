"""Conservative license gate — never guess permissive from public visibility."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common import (
    content_dir,
    dataset_dir,
    get_registry_entry,
    governance_block,
    now_iso,
    receipt_dir,
    sanitize_dataset_id,
    sha256_file,
    write_json,
)

LICENSE_CANDIDATE_NAMES = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "COPYING",
    "COPYING.txt",
    "LICENCE",
    "LICENCE.md",
)

# Conservative known markers — identification only, not legal advice.
_KNOWN_MARKERS = (
    ("CC0", re.compile(r"\bCC0\b|Creative Commons Zero|cc0-1\.0", re.I)),
    ("MIT", re.compile(r"\bMIT License\b", re.I)),
    ("Apache-2.0", re.compile(r"Apache License.*Version 2\.0", re.I | re.S)),
    ("BSD-3-Clause", re.compile(r"BSD 3-Clause|Redistribution and use in source", re.I)),
)


def _find_license_files(root: Path) -> List[Path]:
    found: List[Path] = []
    for name in LICENSE_CANDIDATE_NAMES:
        for p in root.rglob(name):
            if p.is_file():
                found.append(p)
    # Also look for LICENSE* at repo root only depth-limited
    for p in root.glob("LICENSE*"):
        if p.is_file() and p not in found:
            found.append(p)
    return sorted(set(found))


def _identify_license(text: str) -> Tuple[str, str]:
    """Return (license_name, confidence). Never upgrades UNKNOWN to permissive without text."""
    for name, pattern in _KNOWN_MARKERS:
        if pattern.search(text):
            return name, "text_match"
    return "UNKNOWN", "no_known_marker"


def license_check(dataset_id: str) -> Dict[str, Any]:
    safe = sanitize_dataset_id(dataset_id)
    entry = get_registry_entry(safe)
    content = content_dir(safe)
    result: Dict[str, Any] = {
        "dataset_id": safe,
        "checked_at": now_iso(),
        "governance": governance_block(),
        "source_page": entry.get("source_page"),
        "public_does_not_imply_redistributable": True,
        "license_files": [],
        "license_status": "UNKNOWN",
        "license_name": "UNKNOWN",
        "redistribution_status": "BLOCKED_UNTIL_VERIFIED",
        "commercial_reuse_status": "UNKNOWN",
        "attribution_requirement": "REQUIRED_IF_PRESENT",
        "tracked_derivative_fixtures_allowed": False,
        "notes": [],
        "errors": [],
    }

    if not content.exists() or not any(content.iterdir()):
        result["license_status"] = "REVIEW_REQUIRED"
        result["errors"].append("content_missing_acquire_first")
        result["notes"].append(
            "Cannot verify license without acquired content. "
            "Public visibility never implies free redistribution."
        )
        write_json(receipt_dir(safe) / "license-check-latest.json", result)
        return result

    # DJI sample: hard REVIEW_REQUIRED / no redistribution.
    if safe == "DJI_TERRA_SAMPLE":
        result.update(
            {
                "license_status": "REVIEW_REQUIRED",
                "license_name": "DJI_TERMS_REVIEW_REQUIRED",
                "redistribution_status": "PROHIBITED",
                "commercial_reuse_status": "UNKNOWN",
                "tracked_derivative_fixtures_allowed": False,
                "notes": [
                    "DJI Terra sample acquired for local evaluation only.",
                    "Do not assume CC0 or redistributable.",
                    "redistribution_allowed=false unless explicitly proven otherwise.",
                    "Source page and download URL must remain attributed.",
                ],
            }
        )
        write_json(receipt_dir(safe) / "license-check-latest.json", result)
        write_json(dataset_dir(safe) / "license_status.json", result)
        return result

    files = _find_license_files(content)
    if not files:
        result["license_status"] = "REVIEW_REQUIRED"
        result["notes"].append(
            "No LICENSE file found. Manual review required. "
            "Never guess permissive status from repository visibility."
        )
        write_json(receipt_dir(safe) / "license-check-latest.json", result)
        write_json(dataset_dir(safe) / "license_status.json", result)
        return result

    identified: List[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
        name, confidence = _identify_license(text)
        identified.append(name)
        result["license_files"].append(
            {
                "path": str(path.relative_to(content)),
                "sha256": sha256_file(path),
                "identified_as": name,
                "confidence": confidence,
            }
        )

    # Conservative aggregation
    if all(n == "CC0" for n in identified):
        result["license_name"] = "CC0-1.0"
        result["license_status"] = "VERIFIED_PERMISSIVE"
        result["redistribution_status"] = "PERMITTED_WITH_SOURCE_ATTRIBUTION"
        result["commercial_reuse_status"] = "PERMITTED_UNDER_CC0"
        result["tracked_derivative_fixtures_allowed"] = True
        result["notes"].append(
            "CC0 text matched. Tiny synthetic derived fixtures may be tracked; "
            "raw third-party imagery still must not be committed."
        )
    elif any(n == "UNKNOWN" for n in identified) and not all(
        n in {"MIT", "Apache-2.0", "BSD-3-Clause", "CC0"} for n in identified
    ):
        result["license_name"] = identified[0]
        result["license_status"] = "REVIEW_REQUIRED"
        result["tracked_derivative_fixtures_allowed"] = False
        result["notes"].append("Ambiguous or unknown license text — manual review required.")
    else:
        # Known permissive family but not CC0 — still block tracked imagery fixtures.
        result["license_name"] = ",".join(sorted(set(identified)))
        result["license_status"] = "VERIFIED_RESTRICTED"
        result["redistribution_status"] = "RESTRICTED_REVIEW_ATTRIBUTION"
        result["commercial_reuse_status"] = "REVIEW_REQUIRED"
        result["tracked_derivative_fixtures_allowed"] = False
        result["notes"].append(
            "Known open-source license markers found, but redistribution of imagery "
            "binaries remains blocked pending explicit dataset terms review."
        )

    write_json(receipt_dir(safe) / "license-check-latest.json", result)
    write_json(dataset_dir(safe) / "license_status.json", result)
    return result
