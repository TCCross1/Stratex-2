"""Immutable ODM image registry loading and fail-closed validation (PX-006A-R1)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from .common import repo_root

DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
APPROVED_REPOSITORY = "opendronemap/odm"
FORBIDDEN_TAGS = frozenset({"latest", "edge"})


class ODMImageError(ValueError):
    """Fail-closed ODM image governance violation."""


def odm_registry_path() -> Path:
    return repo_root() / "engineering" / "px006a" / "ODM_IMAGE_DIGEST.yaml"


def load_odm_registry() -> Dict[str, Any]:
    import yaml

    path = odm_registry_path()
    if not path.is_file():
        raise ODMImageError(f"ODM image registry missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "image" not in data:
        raise ODMImageError("invalid ODM_IMAGE_DIGEST.yaml")
    image = data["image"]
    validate_odm_image_record(image)
    return data


def validate_odm_image_record(image: Dict[str, Any]) -> None:
    repo = str(image.get("repository") or "")
    tag = str(image.get("tag") or "")
    digest = str(image.get("digest") or "")
    pinned = str(image.get("pinned_reference") or "")
    verified = image.get("verified")

    if repo != APPROVED_REPOSITORY:
        raise ODMImageError(f"repository mismatch: {repo!r}")
    if not tag or tag in FORBIDDEN_TAGS:
        raise ODMImageError(f"forbidden or missing tag: {tag!r}")
    if not digest or not DIGEST_RE.fullmatch(digest):
        raise ODMImageError(f"missing or malformed digest: {digest!r}")
    if verified is not True:
        raise ODMImageError("ODM image record not verified=true")
    expected_pin = f"{repo}@{digest}"
    if pinned != expected_pin:
        raise ODMImageError(
            f"pinned_reference mismatch: {pinned!r} != {expected_pin!r}"
        )
    # Reject mutable tag-only execution references
    if "@sha256:" not in pinned:
        raise ODMImageError("pinned_reference must include immutable digest")


def pinned_odm_reference(override: Optional[str] = None) -> str:
    """Return approved pinned reference. Reject unapproved runtime overrides."""
    reg = load_odm_registry()
    approved = str(reg["image"]["pinned_reference"])
    if override is None or override == "":
        return approved
    if override in {f"{APPROVED_REPOSITORY}:latest", "latest", "opendronemap/odm:latest"}:
        raise ODMImageError("floating tag latest rejected for execution")
    if override.startswith(f"{APPROVED_REPOSITORY}:") and "@" not in override:
        raise ODMImageError("mutable tag without digest rejected")
    if not override.startswith(f"{APPROVED_REPOSITORY}@sha256:"):
        raise ODMImageError(f"unapproved runtime image override rejected: {override!r}")
    # Digest must match registry exactly
    if override != approved:
        raise ODMImageError(
            f"digest mismatch vs registry: {override!r} != {approved!r}"
        )
    return approved


def assert_not_latest(reference: str) -> None:
    if reference.endswith(":latest") or reference == "latest" or "/latest" in reference:
        raise ODMImageError("latest execution path rejected")
