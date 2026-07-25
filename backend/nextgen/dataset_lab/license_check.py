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
    "license",
    "license.md",
    "license.txt",
    "license.html",
    "LICENSE.html",
    "COPYING",
    "COPYING.txt",
    "LICENCE",
    "LICENCE.md",
)

# Conservative known markers — identification only, not legal advice.
_KNOWN_MARKERS = (
    ("CC0", re.compile(r"\bCC0\b|Creative Commons Zero|cc0-1\.0", re.I)),
    ("CC-BY-SA-4.0", re.compile(
        r"creativecommons\.org/licenses/by-sa/4\.0|CC BY-SA 4\.0|CC-BY-SA\b",
        re.I,
    )),
    ("CC-BY-3.0", re.compile(r"creativecommons\.org/licenses/by/3\.0|CC BY 3\.0", re.I)),
    ("CC-BY-4.0", re.compile(r"creativecommons\.org/licenses/by/4\.0|CC BY 4\.0", re.I)),
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
    identified: List[str] = []
    if not files:
        result["notes"].append(
            "No LICENSE file found in standard locations. "
            "Will inspect README for explicit license markers only; "
            "never guess permissive status from repository visibility."
        )
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

    # Conservative aggregation — never upgrade UNKNOWN to permissive without text.
    # Authoritative license files outrank registry assumptions and README summaries.
    known = {
        "CC0",
        "CC-BY-3.0",
        "CC-BY-4.0",
        "CC-BY-SA-4.0",
        "MIT",
        "Apache-2.0",
        "BSD-3-Clause",
    }
    unique_ids = sorted(set(identified))
    has_cc0 = "CC0" in unique_ids
    has_by_sa = any(n.startswith("CC-BY-SA") for n in unique_ids)
    has_by = any(n.startswith("CC-BY") and "SA" not in n for n in unique_ids)
    conflicting = (has_cc0 and (has_by or has_by_sa)) or (has_by and has_by_sa and len(unique_ids) > 1)

    result["share_alike_requirement"] = "NOT_APPLICABLE"
    result["tracked_third_party_fixture_status"] = "PROHIBITED_UNLESS_REVIEWED"
    result["raw_data_git_status"] = "PROHIBITED"
    result["commercial_development_status"] = "UNKNOWN"

    if conflicting:
        result["license_name"] = ",".join(unique_ids)
        result["license_status"] = "REVIEW_REQUIRED"
        result["redistribution_status"] = "BLOCKED_UNTIL_VERIFIED"
        result["commercial_reuse_status"] = "UNKNOWN"
        result["commercial_development_status"] = "LICENSE_TERMS_UNCLEAR"
        result["attribution_requirement"] = "REQUIRED"
        result["share_alike_requirement"] = "UNCLEAR"
        result["tracked_derivative_fixtures_allowed"] = False
        result["tracked_third_party_fixture_status"] = "PROHIBITED_UNLESS_REVIEWED"
        result["notes"].append(
            "Conflicting license markers present — fail closed. "
            "Authoritative license file must be reconciled before any redistribution claim."
        )
    elif identified and all(n == "CC0" for n in identified):
        result["license_name"] = "CC0-1.0"
        result["license_status"] = "VERIFIED_PERMISSIVE"
        result["redistribution_status"] = "PERMITTED_WITH_SOURCE_ATTRIBUTION"
        result["commercial_reuse_status"] = "PERMITTED_UNDER_CC0"
        result["commercial_development_status"] = "PERMITTED_UNDER_CC0"
        result["attribution_requirement"] = "RECORD_SOURCE"
        result["share_alike_requirement"] = "NOT_REQUIRED"
        result["tracked_derivative_fixtures_allowed"] = True
        result["tracked_third_party_fixture_status"] = "TINY_SYNTHETIC_DERIVATIVES_ONLY"
        result["notes"].append(
            "CC0 text matched. Tiny synthetic derived fixtures may be tracked; "
            "raw third-party imagery still must not be committed."
        )
    elif identified and all(n in known for n in identified) and has_by_sa:
        result["license_name"] = ",".join(unique_ids)
        result["license_status"] = "VERIFIED_RESTRICTED"
        result["redistribution_status"] = "CONDITIONAL"
        result["commercial_reuse_status"] = "LICENSE_TERMS_APPLY"
        result["commercial_development_status"] = "LICENSE_TERMS_APPLY"
        result["attribution_requirement"] = "REQUIRED"
        result["share_alike_requirement"] = "REQUIRED"
        result["tracked_derivative_fixtures_allowed"] = False
        result["tracked_third_party_fixture_status"] = "PROHIBITED_UNLESS_REVIEWED"
        result["raw_data_git_status"] = "PROHIBITED"
        result["notes"].append(
            "CC-BY-SA marker matched from authoritative license file. Attribution and "
            "share-alike required. Imagery binaries must not be committed; commercial "
            "development remains subject to license terms."
        )
    elif identified and all(n in known for n in identified) and any(
        n.startswith("CC-BY") for n in identified
    ):
        result["license_name"] = ",".join(unique_ids)
        result["license_status"] = "VERIFIED_RESTRICTED"
        result["redistribution_status"] = "CONDITIONAL"
        result["commercial_reuse_status"] = "REVIEW_REQUIRED"
        result["commercial_development_status"] = "LICENSE_TERMS_APPLY"
        result["attribution_requirement"] = "REQUIRED"
        result["share_alike_requirement"] = "NOT_REQUIRED"
        result["tracked_derivative_fixtures_allowed"] = False
        result["tracked_third_party_fixture_status"] = "PROHIBITED_UNLESS_REVIEWED"
        result["notes"].append(
            "CC-BY marker matched. Attribution required. Third-party imagery "
            "binaries must not be committed; commercial reuse requires separate review."
        )
    elif any(n == "UNKNOWN" for n in identified) or not identified:
        result["license_name"] = identified[0] if identified else "UNKNOWN"
        result["license_status"] = "REVIEW_REQUIRED"
        result["redistribution_status"] = "BLOCKED_UNTIL_VERIFIED"
        result["tracked_derivative_fixtures_allowed"] = False
        result["notes"].append("Ambiguous or unknown license text — manual review required.")
    else:
        # Known open-source license markers but not CC0 — block tracked imagery fixtures.
        result["license_name"] = ",".join(unique_ids)
        result["license_status"] = "VERIFIED_RESTRICTED"
        result["redistribution_status"] = "CONDITIONAL"
        result["commercial_reuse_status"] = "REVIEW_REQUIRED"
        result["commercial_development_status"] = "LICENSE_TERMS_APPLY"
        result["tracked_derivative_fixtures_allowed"] = False
        result["notes"].append(
            "Known open-source license markers found, but redistribution of imagery "
            "binaries remains blocked pending explicit dataset terms review."
        )

    # Registry conflict: authoritative file outranks prior registry assumption.
    registry_name = str(entry.get("license_name") or "")
    if (
        result["license_status"] in {"VERIFIED_RESTRICTED", "VERIFIED_PERMISSIVE"}
        and registry_name
        and registry_name != result["license_name"]
        and registry_name not in result["license_name"]
    ):
        result["notes"].append(
            f"Registry license_name={registry_name!r} differs from authoritative "
            f"file classification={result['license_name']!r}; file wins."
        )
        if "CC0" in registry_name and "CC-BY-SA" in result["license_name"]:
            result["errors"].append("registry_cc0_assumption_rejected_by_license_file")

    # MYGLA: if still unknown, inspect README for CC-BY (conservative restricted).
    if result["license_status"] == "REVIEW_REQUIRED":
        readme = content / "README.md"
        if readme.is_file():
            rtext = readme.read_text(encoding="utf-8", errors="replace")[:200_000]
            name, conf = _identify_license(rtext)
            if name.startswith("CC-BY"):
                result["license_name"] = name
                result["license_status"] = "VERIFIED_RESTRICTED"
                result["redistribution_status"] = "ATTRIBUTION_REQUIRED_NO_TRACKED_IMAGERY"
                result["commercial_reuse_status"] = "REVIEW_REQUIRED"
                result["attribution_requirement"] = "REQUIRED"
                result["tracked_derivative_fixtures_allowed"] = False
                result["license_files"].append(
                    {
                        "path": "README.md",
                        "sha256": sha256_file(readme),
                        "identified_as": name,
                        "confidence": conf,
                    }
                )
                result["notes"].append(
                    "License inferred conservatively from README CC-BY reference only; "
                    "imagery still not redistributable via Git."
                )

    write_json(receipt_dir(safe) / "license-check-latest.json", result)
    write_json(dataset_dir(safe) / "license_status.json", result)
    return result
