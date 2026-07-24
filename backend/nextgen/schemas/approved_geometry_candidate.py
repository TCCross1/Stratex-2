"""ApprovedGeometry CANDIDATE schema — ATC-001A.

Geometry is NOT approved merely because it originated from a 4E package.
This schema intentionally forbids approval_status values other than CANDIDATE /
NOT_APPROVED / REJECTED_CANDIDATE. Production approval remains outside ATC.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .common import Confidence, ContractMeta, Provenance, UnknownState


class GeometryExtents(BaseModel):
    units: Literal["meters", "feet"] = "meters"
    bbox_min: List[float] = Field(..., min_length=2, max_length=3)
    bbox_max: List[float] = Field(..., min_length=2, max_length=3)
    area_estimate: Optional[float] = None
    # Explicitly not claimed as surveyed truth:
    measurement_claim: Literal["fixture_estimate_only"] = "fixture_estimate_only"


class ApprovedGeometryCandidate(BaseModel):
    """Candidate only — never a production ApprovedGeometry acceptance."""

    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="ApprovedGeometry")
    )
    candidate_id: str
    mission_id: str
    aircraft_profile_id: Literal["M4E_MAPPING", "M400_P1_MAPPING"] = "M4E_MAPPING"
    source_evidence_manifest_id: str
    approval_status: Literal[
        "CANDIDATE",
        "NOT_APPROVED",
        "REJECTED_CANDIDATE",
    ] = "CANDIDATE"
    # Hard doctrine flags
    approved_because_from_4e: Literal[False] = False
    is_production_approved: Literal[False] = False
    rtk_accuracy_claimed: Literal[False] = False
    extents: Optional[GeometryExtents] = None
    control_points_unknown: List[str] = Field(default_factory=list)
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState

    @model_validator(mode="after")
    def _candidate_only(self) -> "ApprovedGeometryCandidate":
        if self.approval_status == "APPROVED":  # type: ignore[comparison-overlap]
            raise ValueError("ApprovedGeometryCandidate must not be APPROVED in ATC-001A")
        if self.approved_because_from_4e is not False:
            raise ValueError("Geometry not approved merely because from 4E")
        if self.is_production_approved is not False:
            raise ValueError("ATC must not mark production-approved geometry")
        if self.rtk_accuracy_claimed is not False:
            raise ValueError("ATC-001A must not claim RTK accuracy")
        if self.meta.lifecycle_status not in {"PROPOSED", "READY_FOR_FREEZE"}:
            raise ValueError("ApprovedGeometry lifecycle must remain PROPOSED/READY_FOR_FREEZE")
        if not self.unknown_state.incomplete and self.approval_status == "CANDIDATE":
            # Candidates should retain explicit unknowns until Atlas/Passport path
            self.unknown_state = UnknownState(
                incomplete=True,
                missing_artifacts=self.unknown_state.missing_artifacts,
                unresolved_surfaces=self.unknown_state.unresolved_surfaces
                or ["approval_pending_atlas_passport_path"],
                notes=(
                    "Candidate geometry retains unknown_state until governed "
                    "approval outside ATC lane"
                ),
            )
        return self
