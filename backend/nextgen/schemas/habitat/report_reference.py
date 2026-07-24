"""Report-publication reference schema for Habitat consumers (PROPOSED).

This is a reference stub only — not ReportPublicationPackage implementation.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import (
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    ConfidenceDisplay,
    ProvenanceDisplay,
    UnknownStateDisplay,
    assert_homeowner_safe_payload,
)

ReportReferenceStatus = Literal[
    "published",
    "unavailable",
    "awaiting_review",
    "unknown",
]


class ReportPublicationReference(BaseModel):
    """Pointer to a governed report publication suitable for Habitat linking."""

    model_config = ConfigDict(extra="forbid")

    schema_name: Literal["ReportPublicationReference"] = "ReportPublicationReference"
    schema_version: Literal["0.0.0"] = CONTRACT_VERSION
    contract_status: Literal["PROPOSED"] = CONTRACT_STATUS

    publication_id: Optional[str] = None
    property_id: str = Field(min_length=1)
    template: str = Field(min_length=1)
    status: ReportReferenceStatus
    published_at: Optional[str] = None
    reference_uri: Optional[str] = Field(
        default=None,
        description="Audience-safe URI or path; never embeds bearer JWTs",
    )
    # Explicit non-implementation of the full Estimator package.
    package_contract: Literal["ReportPublicationPackage"] = "ReportPublicationPackage"
    package_contract_status: Literal["NOT_IMPLEMENTED"] = "NOT_IMPLEMENTED"

    provenance: ProvenanceDisplay
    confidence: ConfidenceDisplay
    unknown_state: UnknownStateDisplay

    @model_validator(mode="before")
    @classmethod
    def _reject_forbidden(cls, data: object) -> object:
        if isinstance(data, dict):
            assert_homeowner_safe_payload(data)
        return data

    @model_validator(mode="after")
    def _published_requires_id(self) -> "ReportPublicationReference":
        if self.status == "published" and not self.publication_id:
            raise ValueError("published report reference requires publication_id")
        if self.status != "published" and self.unknown_state.state == "known":
            raise ValueError(
                "non-published report reference must not claim unknown_state=known"
            )
        return self
