"""Normalized address helpers for Passport property records (field test v1)."""

from __future__ import annotations

import hashlib
import re
from typing import Dict


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_address(address_line: str, city_state_zip: str) -> Dict[str, str]:
    """
    Produce a stable normalized address identity for Passport lookup.

    Keys properties by normalized display string hash (tenant-scoped elsewhere).
    """
    line1 = _collapse_whitespace(address_line).upper()
    city_state = _collapse_whitespace(city_state_zip).upper()
    normalized_display = f"{line1}, {city_state}"
    normalized_hash = hashlib.sha256(normalized_display.encode("utf-8")).hexdigest()[:24]
    return {
        "address_line": line1,
        "city_state_zip": city_state,
        "normalized_display": normalized_display,
        "normalized_address_hash": normalized_hash,
    }
