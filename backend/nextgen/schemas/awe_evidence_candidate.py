"""AWE evidence CANDIDATE schema — ATC-001A.

4T is not primary dimensional authority. Thermal does not change dimensions.
No automated thermal diagnosis claim. Candidates only.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .common import Confidence, ContractMeta, Provenance, UnknownState


class ThermalObservationRef(BaseModel):
    observation_id: str
    artifact_id: str
    # Descriptive fixture fields only — not a diagnosis engine output
    label: str = "unreviewed_thermal_region"
    delta_c_fixture: Optional[float] = None
    automated_diagnosis: Literal[False] = False


class AweEvidenceCandidate(BaseModel):
    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="AweEvidenceCandidate")
    )
    candidate_id: str
    mission_id: str
    aircraft_profile_id: Literal["M4T_AWE", "M400_H30T_AWE"] = "M4T_AWE"
    source_evidence_manifest_id: str
    approval_status: Literal[
        "CANDIDATE",
        "NOT_APPROVED",
        "REJECTED_CANDIDATE",
    ] = "CANDIDATE"
    is_dimensional_authority: Literal[False] = False
    thermal_changes_dimensions: Literal[False] = False
    automated_thermal_diagnosis: Literal[False] = False
    is_production_approved: Literal[False] = False
    observations: List[ThermalObservationRef] = Field(default_factory=list)
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState

    @model_validator(mode="after")
    def _doctrine(self) -> "AweEvidenceCandidate":
        if self.is_dimensional_authority is not False:
            raise ValueError("4T is not primary dimensional authority")
        if self.thermal_changes_dimensions is not False:
            raise ValueError("thermal does not change dimensions")
        if self.automated_thermal_diagnosis is not False:
            raise ValueError("ATC-001A must not claim automated thermal diagnosis")
        if self.is_production_approved is not False:
            raise ValueError("AWE evidence candidate is not production-approved")
        for obs in self.observations:
            if obs.automated_diagnosis is not False:
                raise ValueError("observation must not claim automated diagnosis")
        if self.meta.lifecycle_status not in {"PROPOSED", "READY_FOR_FREEZE"}:
            raise ValueError("AWE candidate lifecycle must remain PROPOSED/READY_FOR_FREEZE")
        return self
