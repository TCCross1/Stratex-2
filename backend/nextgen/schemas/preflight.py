"""Preflight result + capture-package manifest contracts (ATC-001A).

Deterministic fixtures only. No real device preflight, no production flight authority.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .common import Confidence, ContractMeta, Provenance, UnknownState


class PreflightCheckItem(BaseModel):
    check_id: str
    label: str
    severity: Literal["hard", "warn", "info"] = "hard"
    result: Literal["pass", "fail", "warn", "skipped"]
    detail: str = ""


class PreflightResult(BaseModel):
    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="PreflightResult")
    )
    mission_id: str
    aircraft_profile_id: str
    overall: Literal["passed", "failed", "warned"]
    checks: List[PreflightCheckItem] = Field(default_factory=list)
    # Explicit non-claims
    real_device_exercised: Literal[False] = False
    production_flight_authority: Literal[False] = False
    dji_sdk_invoked: Literal[False] = False
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState

    @model_validator(mode="after")
    def _no_live_claims(self) -> "PreflightResult":
        if self.real_device_exercised or self.production_flight_authority or self.dji_sdk_invoked:
            raise ValueError("PreflightResult must not claim live device/SDK/flight authority")
        if self.overall == "passed":
            hard_fails = [
                c for c in self.checks
                if c.severity == "hard" and c.result == "fail"
            ]
            if hard_fails:
                raise ValueError("overall=passed incompatible with hard failures")
        return self


class CapturePackageFile(BaseModel):
    file_id: str
    relative_path: str
    category: str
    bytes_claimed: Optional[int] = None
    sha256: Optional[str] = None
    present_in_fixture: bool = True


class CapturePackageManifest(BaseModel):
    meta: ContractMeta = Field(
        default_factory=lambda: ContractMeta(contract_name="CapturePackageManifest")
    )
    package_id: str
    mission_id: str
    aircraft_profile_id: str
    mission_type: Literal[
        "DAYTIME_PRECISION_MAPPING",
        "NIGHTTIME_AWE_VISUAL_THERMAL",
    ]
    package_hash: str
    files: List[CapturePackageFile] = Field(default_factory=list)
    assembled_from_fixture: Literal[True] = True
    physical_capture_claimed: Literal[False] = False
    provenance: Provenance
    confidence: Confidence
    unknown_state: UnknownState

    @model_validator(mode="after")
    def _fixture_only(self) -> "CapturePackageManifest":
        if self.physical_capture_claimed is not False:
            raise ValueError("CapturePackageManifest must not claim physical capture")
        if self.assembled_from_fixture is not True:
            raise ValueError("ATC-001A capture packages are fixture-assembled only")
        return self
