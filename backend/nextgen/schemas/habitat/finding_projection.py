"""Homeowner-safe finding projection schema (PROPOSED)."""
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

Severity = Literal[
    "CRITICAL",
    "MAJOR",
    "MODERATE",
    "MINOR",
    "INFORMATIONAL",
]

Priority = Literal[
    "IMMEDIATE",
    "URGENT",
    "IMPORTANT",
    "SCHEDULE",
    "MONITOR",
]

FindingStatus = Literal["APPROVED", "RESOLVED"]


class HomeownerFindingProjection(BaseModel):
    """Approved finding fields safe for Habitat / homeowner audience.

    Aligns with findings._project_for_habitat plus required provenance /
    confidence / unknown_state display contracts.
    """

    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["HomeownerFindingProjection"] = "HomeownerFindingProjection"
    schema_version: Literal["0.0.0"] = CONTRACT_VERSION
    contract_status: Literal["PROPOSED"] = CONTRACT_STATUS

    canonical_id: str = Field(min_length=1)
    property_id: str = Field(min_length=1)
    taxonomy_category: str = Field(min_length=1)
    taxonomy_component: Optional[str] = None
    severity: Severity
    priority: Priority
    description: str = Field(min_length=1)
    status: FindingStatus
    approved_at: Optional[str] = None
    resolved_at: Optional[str] = None
    manual_observation: bool = False

    provenance: ProvenanceDisplay
    confidence: ConfidenceDisplay
    unknown_state: UnknownStateDisplay

    @model_validator(mode="before")
    @classmethod
    def _reject_forbidden(cls, data: object) -> object:
        if isinstance(data, dict):
            assert_homeowner_safe_payload(data)
        return data
