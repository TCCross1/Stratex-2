"""Shared provenance / confidence / unknown-state display contracts.

Law: confidence may be inherited or reduced, never increased above source.
Unknown / unavailable / awaiting-review must remain explicit — never collapsed
into fabricated certainty for homeowner presentation.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, Literal, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Registry-aligned; Habitat lane must not claim FROZEN / ACCEPTED.
CONTRACT_STATUS: Literal["PROPOSED"] = "PROPOSED"
CONTRACT_VERSION: Literal["0.0.0"] = "0.0.0"

UnknownAvailabilityState = Literal[
    "known",
    "unknown",
    "unavailable",
    "awaiting_review",
]

ProvenanceSourceType = Literal[
    "passport_entry",
    "property_projection",
    "approved_finding",
    "estimate_result",
    "report_publication",
    "project_opportunity",
    "habitat_projection",
]

ConfidenceBand = Literal["high", "medium", "low", "unknown"]

# Fields that must never appear on homeowner-safe Habitat projections.
FORBIDDEN_HOMEOWNER_FIELDS: FrozenSet[str] = frozenset(
    {
        "notes",
        "approval",
        "review_history",
        "author_id",
        "author_role",
        "confidence_pct",
        "confidence_source",
        "insurance_relevant",
        "passport_content_hash",
        "passport_entry_id",
        "passport_seq",
        "contractor_pricing",
        "unit_cost",
        "unit_cost_cents",
        "price_book",
        "price_book_version",
        "margin",
        "margin_pct",
        "internal_notes",
        "ai_reasoning",
        "reviewer_id",
        "reviewer_role",
        "idempotency_key",
        "expected_revision",
        "expected_head_hash",
    }
)


def assert_homeowner_safe_payload(payload: Mapping[str, Any], *, path: str = "$") -> None:
    """Reject payloads that expose contractor/internal Passport write fields."""
    for key, value in payload.items():
        here = f"{path}.{key}"
        if key in FORBIDDEN_HOMEOWNER_FIELDS:
            raise ValueError(f"Forbidden homeowner field at {here}")
        if isinstance(value, Mapping):
            assert_homeowner_safe_payload(value, path=here)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, Mapping):
                    assert_homeowner_safe_payload(item, path=f"{here}[{i}]")


class ProvenanceDisplay(BaseModel):
    """Homeowner-safe provenance display (no actor PII / write credentials)."""

    model_config = ConfigDict(extra="forbid")

    source_type: ProvenanceSourceType
    source_id: str = Field(min_length=1)
    publication_context: str = Field(min_length=1)
    passport_revision: Optional[int] = Field(default=None, ge=0)
    projected_at: str = Field(min_length=1, description="ISO-8601 UTC timestamp")
    projector: str = Field(
        default="habitat.projection",
        description="Projection builder identity — never a Passport writer",
    )


class ConfidenceDisplay(BaseModel):
    """Display-only confidence. Never inflate above source; no methodology internals."""

    model_config = ConfigDict(extra="forbid")

    band: ConfidenceBand
    inherited_from_source: bool = True
    display_label: str = Field(min_length=1)
    reduced_for_audience: bool = False

    @field_validator("band")
    @classmethod
    def _band_not_fabricated_certainty(cls, v: str) -> str:
        return v


class UnknownStateDisplay(BaseModel):
    """Explicit honesty states for incomplete or non-authoritative surfaces."""

    model_config = ConfigDict(extra="forbid")

    state: UnknownAvailabilityState
    reason: Optional[str] = None
    blocks_authoritative_presentation: bool = False

    @classmethod
    def known(cls) -> "UnknownStateDisplay":
        return cls(state="known", blocks_authoritative_presentation=False)

    @classmethod
    def unknown(cls, reason: str) -> "UnknownStateDisplay":
        return cls(
            state="unknown",
            reason=reason,
            blocks_authoritative_presentation=True,
        )

    @classmethod
    def unavailable(cls, reason: str) -> "UnknownStateDisplay":
        return cls(
            state="unavailable",
            reason=reason,
            blocks_authoritative_presentation=True,
        )

    @classmethod
    def awaiting_review(cls, reason: str) -> "UnknownStateDisplay":
        return cls(
            state="awaiting_review",
            reason=reason,
            blocks_authoritative_presentation=True,
        )


def reject_if_forbidden(data: Dict[str, Any]) -> Dict[str, Any]:
    assert_homeowner_safe_payload(data)
    return data
