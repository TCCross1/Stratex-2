"""Privacy redaction for Habitat homeowner-safe read models.

Strips secrets, contractor-private costs/margins, and internal Passport write
metadata before any homeowner projection leaves the consumer.
"""
from __future__ import annotations

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
        "private_cost",
        "private_cost_cents",
        "cost_cents",
        "markup",
        "markup_pct",
        "overhead",
        "overhead_pct",
        "gross_margin",
        "net_margin",
        "labor_rate",
        "labor_rate_cents",
        "price_book_id",
        "internal_unit_price",
    }
)

_REDACT_KEYS = FORBIDDEN_HOMEOWNER_FIELDS | SECRET_AND_PRIVATE_COST_KEYS


def redact_homeowner_secrets(payload: Any, *, path: str = "$") -> Any:
    """Return a deep-copied payload with secrets / private costs removed.

    Mapping keys in the redact set are dropped (not zeroed). Nested structures
    are walked. Lists are preserved with redacted elements.
    """
    if isinstance(payload, Mapping):
        out: MutableMapping[str, Any] = {}
        for key, value in payload.items():
            if key in _REDACT_KEYS:
                continue
            # Heuristic: *token* / *secret* / *password* style keys.
            lowered = key.lower()
            if any(
                needle in lowered
                for needle in ("password", "secret", "private_key", "api_key")
            ):
                continue
            out[key] = redact_homeowner_secrets(value, path=f"{path}.{key}")
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
    # Scalars — return as-is (no in-place mutation of caller structure).
    if isinstance(payload, (str, int, float, bool)) or payload is None:
        return payload
    return deepcopy(payload)


def assert_no_private_cost_fields(payload: Mapping[str, Any]) -> None:
    """Raise ValueError if private cost / secret keys remain after redaction."""
    for key, value in payload.items():
        if key in _REDACT_KEYS:
            raise ValueError(f"Private/secret field leaked at $.{key}")
        if isinstance(value, Mapping):
            assert_no_private_cost_fields(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for item in value:
                if isinstance(item, Mapping):
                    assert_no_private_cost_fields(item)
