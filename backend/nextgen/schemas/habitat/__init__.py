"""Habitat projection contracts — PROPOSED / consumer preparation only.

Habitat remains a read-projection / relationship surface. These schemas do not
authorize Passport mutation, contractor-private pricing exposure, or fabricated
property facts.
"""
from __future__ import annotations

from .common import (
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    ConfidenceDisplay,
    FORBIDDEN_HOMEOWNER_FIELDS,
    ProvenanceDisplay,
    UnknownAvailabilityState,
    UnknownStateDisplay,
    assert_homeowner_safe_payload,
)
from .estimate_summary import HomeownerEstimateSummaryProjection
from .finding_projection import HomeownerFindingProjection
from .opportunity_status import ProjectOpportunityStatusProjection
from .property_projection import HabitatPropertyProjection
from .report_reference import ReportPublicationReference

__all__ = [
    "CONTRACT_STATUS",
    "CONTRACT_VERSION",
    "ConfidenceDisplay",
    "FORBIDDEN_HOMEOWNER_FIELDS",
    "HabitatPropertyProjection",
    "HomeownerEstimateSummaryProjection",
    "HomeownerFindingProjection",
    "ProjectOpportunityStatusProjection",
    "ProvenanceDisplay",
    "ReportPublicationReference",
    "UnknownAvailabilityState",
    "UnknownStateDisplay",
    "assert_homeowner_safe_payload",
]
