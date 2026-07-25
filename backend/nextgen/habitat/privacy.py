"""Privacy redaction for Habitat homeowner-safe read models.

Strips secrets, contractor-private costs/margins, and internal Passport write
metadata before any homeowner projection leaves the consumer.

E-N-002: compound private-field detection across snake_case, camelCase,
PascalCase, kebab-case, dotted paths, and nested objects.
"""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Mapping, MutableMapping, Sequence

from ..schemas.habitat.common import FORBIDDEN_HOMEOWNER_FIELDS

# Extra secret / credential / private-cost keys beyond the schema forbid-list.
SECRET_AND_PRIVATE_COST_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "api_secret",
        "private_key",
        "seal_secret",
        "signing_key",
        "authorization",
        "bearer",
        "contractor_cost",
        "contractor_cost_cents",
        "contractor_margin",
        "private_cost",
        "private_cost_cents",
        "cost_cents",
        "markup",
        "markup_pct",
        "overhead",
        "overhead_pct",
        "gross_margin",
        "net_margin",
        "profit",
        "commission",
        "wholesale_cost",
        "internal_cost",
        "labor_rate",
        "labor_rate_cents",
        "price_book_id",
        "internal_unit_price",
        "presigned_url",
        "signed_url",
        "worker_lease",
        "audit_signature",
        "storage_secret",
        "hmac_key",
    }
)

_PRIVATE_CONCEPT_MARKERS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "private_key",
    "api_key",
    "apikey",
    "presigned",
    "signed_url",
    "worker_lease",
    "audit_signature",
    "contractor_margin",
    "contractor_cost",
    "wholesale_cost",
    "internal_cost",
    "unit_cost",
    "margin",
    "markup",
    "profit",
    "commission",
    "overhead",
)

_REDACT_KEYS = FORBIDDEN_HOMEOWNER_FIELDS | SECRET_AND_PRIVATE_COST_KEYS


def normalize_field_key(key: Any) -> str:
    """Normalize compound naming styles to snake_case for private matching."""
    text = str(key).strip()
    # dotted / path segments → join last meaningful segment + full path
    text = text.replace(".", "_").replace("-", "_").replace(" ", "_")
    # camelCase / PascalCase → snake
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    return text.lower().strip("_")


def is_private_field_key(key: Any) -> bool:
    """True when a key (any naming style) denotes a private/secret concept."""
    if key in _REDACT_KEYS:
        return True
    norm = normalize_field_key(key)
    if norm in _REDACT_KEYS:
        return True
    # Compact form (marginpct, apikey)
    compact = norm.replace("_", "")
    for banned in _REDACT_KEYS:
        if banned.replace("_", "") == compact:
            return True
    return any(marker in norm or marker.replace("_", "") in compact for marker in _PRIVATE_CONCEPT_MARKERS)


def redact_homeowner_secrets(payload: Any, *, path: str = "$") -> Any:
    """Return a deep-copied payload with secrets / private costs removed.

    Mapping keys matching private concepts (any compound naming style) are
    dropped. Nested structures and dotted-path keys are walked.
    """
    if isinstance(payload, Mapping):
        out: MutableMapping[str, Any] = {}
        for key, value in payload.items():
            if is_private_field_key(key):
                continue
            out[str(key)] = redact_homeowner_secrets(value, path=f"{path}.{key}")
        return out
    if isinstance(payload, list):
        return [
            redact_homeowner_secrets(item, path=f"{path}[{i}]")
            for i, item in enumerate(payload)
        ]
    if isinstance(payload, tuple):
        return tuple(
            redact_homeowner_secrets(item, path=f"{path}[{i}]")
            for i, item in enumerate(payload)
        )
    if isinstance(payload, (str, int, float, bool)) or payload is None:
        return payload
    return deepcopy(payload)


def assert_no_private_cost_fields(payload: Mapping[str, Any]) -> None:
    """Raise ValueError if private cost / secret keys remain after redaction."""
    for key, value in payload.items():
        if is_private_field_key(key):
            raise ValueError(f"Private/secret field leaked at $.{key}")
        if isinstance(value, Mapping):
            assert_no_private_cost_fields(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                if isinstance(item, Mapping):
                    assert_no_private_cost_fields(item)
