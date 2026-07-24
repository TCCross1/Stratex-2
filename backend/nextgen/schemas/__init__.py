"""NextGen schemas package root.

LANE_4 owns the ``habitat`` subpackage only (homeowner-safe projections).
ATC / EvidenceManifest executable schemas are owned by LANE_2 and must not be
wiped by this package marker during parallel merges.

Import Habitat contracts via::

    from nextgen.schemas import habitat
    # or
    from nextgen.schemas.habitat import HabitatPropertyProjection

Statuses remain PROPOSED — Atlas freezes; this lane does not.
"""
from __future__ import annotations

from . import habitat

__all__ = ["habitat"]
