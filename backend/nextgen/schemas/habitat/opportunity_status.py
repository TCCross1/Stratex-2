"""Project-opportunity status projection schema (PROPOSED).

Status surface only. Does not implement ProjectOpportunityPackage feature UX
and must not present fabricated scope as settled fact.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    ConfidenceDisplay,
    ProvenanceDisplay,
    UnknownStateDisplay,
    assert_homeowner_safe_payload,
)

OpportunityStatus = Literal[
    "proposed",
    "shared",
    "homeowner_reviewing",
    "accepted",
    "declined",
    "unavailable",
    "awaiting_review",
    "unknown",
]


class ProjectOpportunityStatusProjection(BaseModel):
    """Homeowner relationship status for a project opportunity."""

    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["ProjectOpportunityStatusProjection"] = (
        "ProjectOpportunityStatusProjection"
    )
    schema_version: Literal["0.0.0"] = CONTRACT_VERSION
    contract_status: Literal["PROPOSED"] = CONTRACT_STATUS

    opportunity_id: Optional[str] = None
    property_id: str = Field(min_length=1)
    status: OpportunityStatus
    title_homeowner_safe: Optional[str] = None
    linked_finding_ids: List[str] = Field(default_factory=list)
    linked_estimate_ref: Optional[str] = None
    # Full package remains NOT_IMPLEMENTED until Atlas freeze.
    package_contract: Literal["ProjectOpportunityPackage"] = "ProjectOpportunityPackage"
    package_contract_status: Literal["NOT_IMPLEMENTED"] = "NOT_IMPLEMENTED"

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
    def _no_fabricated_settled_scope(self) -> "ProjectOpportunityStatusProjection":
        unsettled = {
            "unavailable",
            "awaiting_review",
            "unknown",
            "proposed",
        }
        if self.status in unsettled:
            if (
                self.unknown_state.state == "known"
                and self.status in {"unavailable", "awaiting_review", "unknown"}
            ):
                raise ValueError(
                    "unsettled opportunity must not claim unknown_state=known"
                )
            if (
                self.status in {"unavailable", "awaiting_review", "unknown"}
                and not self.unknown_state.blocks_authoritative_presentation
            ):
                raise ValueError(
                    "unsettled opportunity must block authoritative presentation"
                )
        return self
