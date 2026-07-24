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
    "Do not treat GeometryCandidate as ApprovedGeometry. "
    "Do not treat AWEEvidenceCandidate as ApprovedFinding. "
    "Promotion to approved contracts is outside LANE_2 ATC authority."
)


def alias_map() -> Dict[str, Type]:
    """Stable alias registry for compatibility validators and docs."""
    return {
        "GeometryCandidate": GeometryCandidate,
        "ApprovedGeometryCandidate": ApprovedGeometryCandidate,
        "AWEEvidenceCandidate": AWEEvidenceCandidate,
        "AweEvidenceCandidate": AweEvidenceCandidate,
    }
