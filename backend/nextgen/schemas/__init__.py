"""ATC-001A executable contract schemas (pydantic) + JSON Schema export helpers.

Statuses remain PROPOSED / READY_FOR_FREEZE. Atlas freezes; this lane does not.

LANE_2 owns ATC candidate schemas at this package root. Habitat projections are
owned by LANE_4 under ``nextgen.schemas.habitat``. Parallel-merge rule: keep ATC
exports here and preserve the optional habitat subpackage import below.
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

# Optional coexistence with LANE_4 habitat package (present after dual-lane merge).
try:
    from . import habitat as habitat
except ImportError:  # pragma: no cover - habitat lands via LANE_4
    habitat = None  # type: ignore[assignment]

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
