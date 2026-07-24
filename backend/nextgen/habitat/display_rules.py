"""Provenance + unknown display rules for Habitat consumers.

Hard laws:
- ``unknown ≠ 0`` — unknown / unavailable quantities must never be coerced to zero
- ``awaiting ≠ approved`` — awaiting_review must never be presented as approved
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Union

from ..schemas.habitat.common import (
    ConfidenceDisplay,
    UnknownStateDisplay,
)

APPROVED_CLAIM_STATUSES = frozenset(
    {
        "approved",
        "APPROVED",
        "published",
        "available",
        "passport_committed",
        "accepted",
    }
)

NON_AUTHORITATIVE_STATES = frozenset(
    {"unknown", "unavailable", "awaiting_review"}
)


class DisplayRuleError(ValueError):
    """Raised when a consumer would violate honesty display rules."""


def unknown_is_not_zero(value: Any, *, unknown_state: UnknownStateDisplay) -> Any:
    """Refuse to treat unknown quantities as numeric zero.

    Returns ``None`` when state is non-authoritative and value is missing/zero-like
    so callers cannot silently publish ``0`` as a known quantity.
    """
    if unknown_state.state in NON_AUTHORITATIVE_STATES:
        if value is None:
            return None
        if value == 0 or value == 0.0:
            raise DisplayRuleError(
                "unknown≠0: cannot present 0 while unknown_state is "
                f"{unknown_state.state}"
            )
        if value == "0":
            raise DisplayRuleError(
                "unknown≠0: cannot present '0' while unknown_state is "
                f"{unknown_state.state}"
            )
    return value


def awaiting_is_not_approved(
    *,
    status: Optional[str],
    unknown_state: UnknownStateDisplay,
    availability: Optional[str] = None,
) -> None:
    """Raise if awaiting_review (or similar) is labeled as approved/published."""
    if unknown_state.state == "awaiting_review":
        if status in APPROVED_CLAIM_STATUSES:
            raise DisplayRuleError(
                "awaiting≠approved: status cannot be "
                f"{status!r} while unknown_state=awaiting_review"
            )
        if availability in APPROVED_CLAIM_STATUSES:
            raise DisplayRuleError(
                "awaiting≠approved: availability cannot be "
                f"{availability!r} while unknown_state=awaiting_review"
            )
    if status in {"awaiting_review", "AWAITING_REVIEW"} and (
        unknown_state.state == "known" and unknown_state.blocks_authoritative_presentation is False
    ):
        # Status says awaiting but display claims known/authoritative.
        raise DisplayRuleError(
            "awaiting≠approved: status=awaiting_review cannot claim "
            "authoritative known presentation"
        )


def confidence_band_for_unknown(unknown_state: UnknownStateDisplay) -> str:
    """Map honesty state to a non-inflated confidence band."""
    if unknown_state.state in NON_AUTHORITATIVE_STATES:
        return "unknown"
    return "medium"


def build_honesty_confidence(
    unknown_state: UnknownStateDisplay,
    *,
    display_label: str,
    source_band: Optional[str] = None,
) -> ConfidenceDisplay:
    """Confidence may be inherited or reduced — never inflated above source."""
    band = confidence_band_for_unknown(unknown_state)
    if source_band == "unknown":
        band = "unknown"
    elif source_band in {"low", "medium", "high"} and band != "unknown":
        # Never inflate: take the more conservative band.
        order = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
        band = source_band if order[source_band] <= order[band] else band
    return ConfidenceDisplay(
        band=band,  # type: ignore[arg-type]
        inherited_from_source=True,
        display_label=display_label,
        reduced_for_audience=True,
    )


def assert_display_rules(
    payload: Mapping[str, Any],
    *,
    unknown_state: UnknownStateDisplay,
    status: Optional[str] = None,
    availability: Optional[str] = None,
    quantity_fields: Optional[tuple[str, ...]] = None,
) -> None:
    """Apply unknown≠0 and awaiting≠approved to a consumer payload fragment."""
    awaiting_is_not_approved(
        status=status,
        unknown_state=unknown_state,
        availability=availability,
    )
    for field in quantity_fields or ():
        if field in payload:
            unknown_is_not_zero(payload[field], unknown_state=unknown_state)
