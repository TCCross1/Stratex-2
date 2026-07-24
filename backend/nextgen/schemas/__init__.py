"""NextGen executable contract schemas — PX-003 reconciled package root.

LANE_2 owns ATC candidate schemas at this package root.
LANE_4 owns homeowner-safe projections under ``nextgen.schemas.habitat``.

Statuses remain PROPOSED / READY_FOR_FREEZE. Atlas freezes; this wave does not.
Law: PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.
"""
from __future__ import annotations

from .approved_geometry_candidate import ApprovedGeometryCandidate, GeometryExtents
from .awe_evidence_candidate import AweEvidenceCandidate, ThermalObservationRef
from .common import Confidence, ContractMeta, Provenance, UnknownState
from .evidence_manifest import (
    EvidenceArtifactRef,
    EvidenceManifest,
    MissionTypeContract,
)
from .preflight import CapturePackageFile, CapturePackageManifest, PreflightCheckItem, PreflightResult

# Habitat subpackage provided by LANE_4 (present after PX-003 serialized merge).
from . import habitat as habitat

__all__ = [
    "ApprovedGeometryCandidate",
    "AweEvidenceCandidate",
    "CapturePackageFile",
    "CapturePackageManifest",
    "Confidence",
    "ContractMeta",
    "EvidenceArtifactRef",
    "EvidenceManifest",
    "GeometryExtents",
    "MissionTypeContract",
    "PreflightCheckItem",
    "PreflightResult",
    "Provenance",
    "ThermalObservationRef",
    "UnknownState",
    "habitat",
]
