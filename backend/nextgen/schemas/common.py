"""Shared ATC-001A contract value objects.

Every shared contract declares provenance, confidence, and unknown_state.
Contract status remains PROPOSED / READY_FOR_FREEZE until Atlas freezes.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


ContractLifecycle = Literal["PROPOSED", "READY_FOR_FREEZE"]
# Never ACCEPTED / FROZEN / PRODUCTION from this lane.


class Provenance(BaseModel):
    source_type: str = Field(..., description="e.g. atc_mission, capture_package, fixture")
    source_id: str
    mission_id: Optional[str] = None
    aircraft_profile_id: Optional[str] = None
    capture_profile: Optional[str] = None
    package_hash: Optional[str] = None
    operator_id: Optional[str] = None
    device_package_id: Optional[str] = None
    publication_context: Literal[
        "contract_fixture",
        "field_candidate",
        "not_for_passport",
    ] = "contract_fixture"


class Confidence(BaseModel):
    band: Literal["unknown", "low", "medium", "high"] = "unknown"
    score_0_1: Optional[float] = Field(None, ge=0.0, le=1.0)
    rationale: str = "Contract fixture — not a production measurement claim"


class UnknownState(BaseModel):
    incomplete: bool = True
    missing_artifacts: List[str] = Field(default_factory=list)
    unresolved_surfaces: List[str] = Field(default_factory=list)
    notes: str = (
        "Unknowns must remain explicit; do not fabricate completeness "
        "or approved geometry."
    )


class ContractMeta(BaseModel):
    contract_name: str
    contract_version: str = "0.0.0"
    lifecycle_status: ContractLifecycle = "PROPOSED"
    approval_authority: Literal["Atlas"] = "Atlas"
    owning_lane: Literal["LANE_2_ATC_FIELD"] = "LANE_2_ATC_FIELD"
