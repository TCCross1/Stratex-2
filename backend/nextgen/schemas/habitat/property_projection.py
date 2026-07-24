"""HabitatPropertyProjection executable schema (PROPOSED).

Homeowner-safe read projection derived from approved Passport truth.
Habitat never writes canonical Passport ledger entries.
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
from .estimate_summary import HomeownerEstimateSummaryProjection
from .finding_projection import HomeownerFindingProjection
from .opportunity_status import ProjectOpportunityStatusProjection
from .report_reference import ReportPublicationReference


class HabitatAddressSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line1: str
    city: str
    region: str
    postal_code: str
    country_iso: str = "US"
    unit_label: Optional[str] = None


class HabitatPropertySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_id: str = Field(min_length=1)
    address: HabitatAddressSummary
    inspection_date: Optional[str] = None


class HabitatPropertyProjection(BaseModel):
    """Executable HabitatPropertyProjection contract (registry status PROPOSED)."""

    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["HabitatPropertyProjection"] = "HabitatPropertyProjection"
    schema_version: Literal["0.0.0"] = CONTRACT_VERSION
    contract_status: Literal["PROPOSED"] = CONTRACT_STATUS

    audience: Literal["homeowner", "public"] = "homeowner"
    property_summary: HabitatPropertySummary
    findings: List[HomeownerFindingProjection] = Field(default_factory=list)
    estimate_summary: Optional[HomeownerEstimateSummaryProjection] = None
    report_references: List[ReportPublicationReference] = Field(default_factory=list)
    project_opportunities: List[ProjectOpportunityStatusProjection] = Field(
        default_factory=list
    )
    # Opaque AWE summary when available; never invent scores under unknown_state.
    awe_available: bool = False
    awe_release_state: Optional[str] = None

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
    def _awe_honesty(self) -> "HabitatPropertyProjection":
        if not self.awe_available and self.awe_release_state is not None:
            raise ValueError("awe_release_state requires awe_available=true")
        return self
