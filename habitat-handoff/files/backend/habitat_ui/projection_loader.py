"""
Load habitat.projection.v1 JSON for field-test handoff.

Core exports → Passport stores → Habitat reads only.
Priority: HABITAT_PROJECTION_PATH file, else caller falls back to adapter/stub.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("habitat.projection_loader")

CONTRACT_ID = "habitat.projection.v1"


def projection_path_from_env() -> Optional[Path]:
    raw = (os.environ.get("HABITAT_PROJECTION_PATH") or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def load_projection_from_env() -> Optional[Dict[str, Any]]:
    """
    Read habitat.projection.v1 JSON from HABITAT_PROJECTION_PATH if set.
    Returns None when unset / missing / invalid so callers keep demo fallback.
    Never writes Passport or Core.
    """
    path = projection_path_from_env()
    if path is None:
        return None
    if not path.is_file():
        logger.warning(
            "HABITAT_PROJECTION_PATH set but file not found: %s", path
        )
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        logger.exception(
            "Failed to load habitat projection from %s: %s", path, exc
        )
        return None
    if not isinstance(payload, dict):
        logger.warning(
            "HABITAT_PROJECTION_PATH payload is not an object: %s", path
        )
        return None
    cid = payload.get("contract_id")
    if cid and cid != CONTRACT_ID:
        logger.warning(
            "Unexpected contract_id=%s (expected %s) at %s — still hydrating",
            cid,
            CONTRACT_ID,
            path,
        )
    logger.info(
        "Loaded habitat projection from file path=%s authoritative=%s property_id=%s",
        path,
        payload.get("authoritative"),
        payload.get("property_id"),
    )
    return payload
