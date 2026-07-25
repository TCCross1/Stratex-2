"""ATC-001B naming aliases — do not silently rename shared contracts.

ATC-001A shipped:
- ``ApprovedGeometryCandidate`` (producer candidate for geometry)
- ``AweEvidenceCandidate`` (producer candidate for AWE/thermal)

ATC-001B introduces clearer producer names as **aliases** only:
- ``GeometryCandidate``
- ``AWEEvidenceCandidate`` (capitalization-normalized)

Shared registry contracts ``ApprovedGeometry`` and ``ApprovedFinding`` remain
separate consumer/Passport-side names — see ``approved_side.py``.
"""
from __future__ import annotations

from typing import Dict, Type

from ..approved_geometry_candidate import ApprovedGeometryCandidate
from ..awe_evidence_candidate import AweEvidenceCandidate

# Producer-side aliases (ATC-001B). Identical types; no schema fork.
GeometryCandidate = ApprovedGeometryCandidate
AWEEvidenceCandidate = AweEvidenceCandidate

MIGRATION_NOTES = (
    "ATC-001B aliases: GeometryCandidate == ApprovedGeometryCandidate (ATC-001A); "
    "AWEEvidenceCandidate == AweEvidenceCandidate (ATC-001A spelling). "
    "Candidate meta.contract_name must be ApprovedGeometryCandidate or "
    "GeometryCandidate — never ApprovedGeometry for unapproved data. "
    "Deprecated alias: historical payloads that used meta.contract_name="
    "ApprovedGeometry for candidates are rejected as MISLABELED_APPROVED "
    "(versioned 0.0.0 migration; consumers must not infer approval from the "
    "legacy name). "
    "Do not treat GeometryCandidate as ApprovedGeometry. "
    "Do not treat AWEEvidenceCandidate as ApprovedFinding. "
    "Promotion to approved contracts is outside LANE_2 ATC authority."
)

# Explicit deprecated alias — documented, versioned, not silently accepted.
DEPRECATED_CANDIDATE_CONTRACT_NAMES = frozenset({"ApprovedGeometry"})


def alias_map() -> Dict[str, Type]:
    """Stable alias registry for compatibility validators and docs."""
    return {
        "GeometryCandidate": GeometryCandidate,
        "ApprovedGeometryCandidate": ApprovedGeometryCandidate,
        "AWEEvidenceCandidate": AWEEvidenceCandidate,
        "AweEvidenceCandidate": AweEvidenceCandidate,
    }
