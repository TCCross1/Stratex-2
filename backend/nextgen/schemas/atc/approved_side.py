"""Consumer-side approved contracts — ATC must not produce these.

``ApprovedGeometry`` and ``ApprovedFinding`` remain shared registry names
(PROPOSED). ATC-001B defines explicit consumer markers so producers cannot
silently rename candidates into approved contracts.

Law: PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.
ATC has no Passport writer / publisher / approval authority.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from ..common import Confidence, ContractMeta, Provenance, UnknownState


class ConsumerContractForbidden(ValueError):
    """Raised when ATC code attempts to mint an approved consumer contract."""


class ApprovedGeometry(BaseModel):
    """Passport/consumer ApprovedGeometry marker — not an ATC producer output.

    Instantiation is allowed only with ``producer_lane`` outside LANE_2 and
    ``is_atc_producer_output=False``. ATC boundary code must refuse to emit this.
    """

    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="ApprovedGeometry")
    )
    geometry_id: str
    source_candidate_id: str
    producer_lane: Literal[
        "LANE_1_CORE_PASSPORT",
        "ATLAS",
        "NOT_ATC",
    ]
    is_atc_producer_output: Literal[False] = False
    is_production_approved: bool = False
    approval_authority: Literal["Atlas"] = "Atlas"
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState
    note: str = "Consumer marker only — ATC-001B does not approve geometry"

    @model_validator(mode="after")
    def _not_from_atc(self) -> "ApprovedGeometry":
        if self.is_atc_producer_output is not False:
            raise ConsumerContractForbidden(
                "ApprovedGeometry must not be marked as ATC producer output"
            )
        if self.producer_lane == "LANE_2_ATC_FIELD":  # type: ignore[comparison-overlap]
            raise ConsumerContractForbidden(
                "LANE_2 ATC must not produce ApprovedGeometry"
            )
        if self.meta.lifecycle_status not in {"PROPOSED", "READY_FOR_FREEZE"}:
            raise ValueError("ApprovedGeometry lifecycle must remain PROPOSED/READY_FOR_FREEZE")
        return self


class ApprovedFinding(BaseModel):
    """Passport/consumer ApprovedFinding marker — not an ATC producer output.

    AWE thermal candidates must not be renamed into ApprovedFinding here.
    """

    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="ApprovedFinding")
    )
    finding_id: str
    source_candidate_id: str
    producer_lane: Literal[
        "LANE_1_CORE_PASSPORT",
        "ATLAS",
        "NOT_ATC",
    ]
    is_atc_producer_output: Literal[False] = False
    is_production_approved: bool = False
    automated_thermal_diagnosis: Literal[False] = False
    approval_authority: Literal["Atlas"] = "Atlas"
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState
    dimensional_claim: Optional[str] = None
    note: str = "Consumer marker only — ATC-001B does not approve findings"

    @model_validator(mode="after")
    def _not_from_atc(self) -> "ApprovedFinding":
        if self.is_atc_producer_output is not False:
            raise ConsumerContractForbidden(
                "ApprovedFinding must not be marked as ATC producer output"
            )
        if self.producer_lane == "LANE_2_ATC_FIELD":  # type: ignore[comparison-overlap]
            raise ConsumerContractForbidden(
                "LANE_2 ATC must not produce ApprovedFinding"
            )
        if self.automated_thermal_diagnosis is not False:
            raise ValueError("ApprovedFinding marker forbids automated thermal diagnosis claim")
        if self.dimensional_claim is not None:
            raise ValueError(
                "ApprovedFinding must not carry dimensional claims from thermal/AWE path"
            )
        if self.meta.lifecycle_status not in {"PROPOSED", "READY_FOR_FREEZE"}:
            raise ValueError("ApprovedFinding lifecycle must remain PROPOSED/READY_FOR_FREEZE")
        return self
