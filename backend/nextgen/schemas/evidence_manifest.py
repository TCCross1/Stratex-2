"""Mission-type + EvidenceManifest executable schemas (ATC-001A).

PROPOSED / READY_FOR_FREEZE only. No Passport writer. No fabricated device evidence.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .common import Confidence, ContractMeta, Provenance, UnknownState


MissionType = Literal[
    "DAYTIME_PRECISION_MAPPING",
    "NIGHTTIME_AWE_VISUAL_THERMAL",
]

EvidenceCategory = Literal[
    "RGB_IMAGE",
    "THERMAL_RADIOMETRIC",
    "THERMAL_DERIVATIVE",
    "FLIGHT_LOG",
    "TELEMETRY",
    "CAMERA_METADATA",
    "CALIBRATION_FILE",
    "WEATHER_RECORD",
    "AIRSPACE_RECORD",
    "OPERATOR_NOTE",
    "PHOTOGRAMMETRY_OUTPUT",
    "OTHER",
]


class MissionTypeContract(BaseModel):
    """Binds a mission type to an aircraft profile and evidence expectations."""

    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="MissionTypeContract")
    )
    mission_type: MissionType
    aircraft_profile_id: str
    evidence_product_key: Literal["dayscan", "awe_scan", "elite"]
    dimensional_role: Literal[
        "primary_dimensional_candidate",
        "not_dimensional_authority",
    ]
    thermal_changes_dimensions: Literal[False] = False
    requires_paired_mission_type: Optional[MissionType] = None
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState

    @model_validator(mode="after")
    def _doctrine(self) -> "MissionTypeContract":
        if self.mission_type == "DAYTIME_PRECISION_MAPPING":
            if self.dimensional_role != "primary_dimensional_candidate":
                raise ValueError("4E mapping must be primary_dimensional_candidate")
            if self.aircraft_profile_id not in {"M4E_MAPPING", "M400_P1_MAPPING"}:
                raise ValueError("mapping mission requires mapping aircraft profile")
        if self.mission_type == "NIGHTTIME_AWE_VISUAL_THERMAL":
            if self.dimensional_role != "not_dimensional_authority":
                raise ValueError("4T AWE is not dimensional authority")
            if self.thermal_changes_dimensions is not False:
                raise ValueError("thermal does not change dimensions")
            if self.aircraft_profile_id not in {"M4T_AWE", "M400_H30T_AWE"}:
                raise ValueError("AWE mission requires AWE aircraft profile")
        return self


class EvidenceArtifactRef(BaseModel):
    artifact_id: str
    category: EvidenceCategory
    relative_path: str
    content_sha256: Optional[str] = None
    required: bool = True
    present: bool = False  # fixtures may mark present without claiming live capture


class EvidenceManifest(BaseModel):
    """Field-capture evidence inventory — executable schema, candidates/fixtures only."""

    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="EvidenceManifest")
    )
    mission_id: str
    mission_type: MissionType
    aircraft_profile_id: str
    package_hash: str
    artifacts: List[EvidenceArtifactRef] = Field(default_factory=list)
    completeness_ok: bool = False
    atc_validation_status: Literal[
        "NOT_VALIDATED",
        "VALIDATED_CANDIDATE",
        "BLOCKED",
    ] = "NOT_VALIDATED"
    passport_accepted: Literal[False] = False  # ATC never sets Passport acceptance
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState

    @model_validator(mode="after")
    def _no_passport_claim(self) -> "EvidenceManifest":
        if self.passport_accepted is not False:
            raise ValueError("EvidenceManifest must not claim Passport acceptance")
        if self.meta.lifecycle_status not in {"PROPOSED", "READY_FOR_FREEZE"}:
            raise ValueError("EvidenceManifest lifecycle must remain PROPOSED/READY_FOR_FREEZE")
        return self

    def recompute_completeness(self) -> bool:
        required = [a for a in self.artifacts if a.required]
        self.completeness_ok = bool(required) and all(a.present for a in required)
        if not self.completeness_ok:
            missing = [a.artifact_id for a in required if not a.present]
            self.unknown_state = UnknownState(
                incomplete=True,
                missing_artifacts=missing,
                notes="Required artifacts missing; do not fabricate presence",
            )
        return self.completeness_ok
