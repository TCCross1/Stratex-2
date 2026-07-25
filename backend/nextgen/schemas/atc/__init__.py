"""ATC-001B schema surface — candidate vs approved separation.

Collision risk disclosure
-------------------------
This package lives at ``nextgen.schemas.atc`` and does **not** mutate
``nextgen.schemas`` package root (``schemas/__init__.py``). LANE_4 owns
habitat imports on that root; touching it risks coexistence collisions
(see ATC-001A auditor note L2 / PX-003 repair).

Aliases preserve ATC-001A shared contract names:
- ``GeometryCandidate`` → alias of ``ApprovedGeometryCandidate``
- ``AWEEvidenceCandidate`` → alias of ``AweEvidenceCandidate``

``ApprovedGeometry`` / ``ApprovedFinding`` are consumer-side markers that
ATC must not emit. See ``MIGRATION.md``.
"""
from __future__ import annotations

from .aliases import (
    AWEEvidenceCandidate,
    GeometryCandidate,
    MIGRATION_NOTES,
    alias_map,
)
from .approved_side import (
    ApprovedFinding,
    ApprovedGeometry,
    ConsumerContractForbidden,
)

__all__ = [
    "AWEEvidenceCandidate",
    "ApprovedFinding",
    "ApprovedGeometry",
    "ConsumerContractForbidden",
    "GeometryCandidate",
    "MIGRATION_NOTES",
    "alias_map",
]
