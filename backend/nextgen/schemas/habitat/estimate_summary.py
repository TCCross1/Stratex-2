"""Homeowner-safe estimate-summary projection schema (PROPOSED).

Exposes summary readiness only. Contractor-private pricing, unit costs,
margins, and price-book internals are forbidden.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    ConfidenceDisplay,
    ProvenanceDisplay,
    UnknownStateDisplay,
    assert_homeowner_safe_payload,
)

EstimateSummaryAvailability = Literal[
    "available",
    "unavailable",
    "awaiting_review",
    "unknown",
]


class HomeownerEstimateSummaryProjection(BaseModel):
    """Homeowner-facing estimate summary — never a contractor rate sheet."""

    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["HomeownerEstimateSummaryProjection"] = (
        "HomeownerEstimateSummaryProjection"
    )
    schema_version: Literal["0.0.0"] = CONTRACT_VERSION
    contract_status: Literal["PROPOSED"] = CONTRACT_STATUS

    property_id: str = Field(min_length=1)
    estimate_ref: Optional[str] = Field(
        default=None,
        description="Opaque reference to EstimateResult when available",
    )
    availability: EstimateSummaryAvailability
    currency: Literal["USD"] = "USD"
    # Homeowner-safe range labels only — not line-item amounts or unit costs.
    total_range_label: Optional[str] = Field(
        default=None,
        description="Audience-safe range label, e.g. 'Approximate range pending review'",
    )
    line_group_count: Optional[int] = Field(default=None, ge=0)
    includes_tax: Optional[bool] = None

    provenance: ProvenanceDisplay
    confidence: ConfidenceDisplay
    unknown_state: UnknownStateDisplay

    @model_validator(mode="before")
    @classmethod
    def _reject_forbidden(cls, data: object) -> object:
        if isinstance(data, dict):
            assert_homeowner_safe_payload(data)
        return data

    @model_validator(mode="after")
    def _honesty_when_not_available(self) -> "HomeownerEstimateSummaryProjection":
        if self.availability in {"unavailable", "awaiting_review", "unknown"}:
            if self.unknown_state.state == "known":
                raise ValueError(
                    "non-available estimate summary must not claim unknown_state=known"
                )
            if self.unknown_state.blocks_authoritative_presentation is False:
                raise ValueError(
                    "non-available estimate summary must block authoritative presentation"
                )
        return self
