"""Homeowner-safe Habitat property read-model consumer (HABITAT-P-002).

Consumes approved / published source bags and builds
``HabitatPropertyProjection`` plus reality-model layers.

Law: Habitat is READ-ONLY for canonical Passport truth.
This module must NEVER import Passport writer services, never invoke ledger
append/publish helpers, and never insert into passport ledger collections.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..schemas.habitat import (
    HabitatPropertyProjection,
    HomeownerEstimateSummaryProjection,
    HomeownerFindingProjection,
    ProjectOpportunityStatusProjection,
    ProvenanceDisplay,
    ReportPublicationReference,
    UnknownStateDisplay,
    assert_homeowner_safe_payload,
)
from .display_rules import (
    assert_display_rules,
    awaiting_is_not_approved,
    build_honesty_confidence,
    unknown_is_not_zero,
)
from .privacy import assert_no_private_cost_fields, redact_homeowner_secrets
from .reality_model import RealityModelBundle, build_reality_model

MODULE_IDENTITY = "nextgen.habitat.read_model"

# Report is deliverable to homeowner only when source explicitly approves delivery.
_REPORT_DELIVERY_APPROVED_STATUSES = frozenset(
    {"published", "approved_for_delivery", "customer_releasable"}
)

# Statuses that imply contracts / payments. Plain "accepted" is relationship-only
# and remains allowed; contracted/paid require explicit source support fields.
_CONTRACT_OR_PAYMENT_STATUSES = frozenset(
    {"contracted", "paid", "invoiced", "payment_pending", "under_contract"}
)
_PAYMENT_SOURCE_FLAGS = frozenset(
    {"contract_id", "payment_status", "invoice_id", "payment_id"}
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HabitatPropertyReadSource:
    """In-memory source bag for the read-model consumer (no DB writes).

    Callers supply already-loaded dicts. The consumer never opens Passport
    write paths and never fabricates property facts from silence.
    """

    property_id: str
    address: Mapping[str, Any]
    audience: str = "homeowner"
    inspection_date: Optional[str] = None
    passport_revision: Optional[int] = None
    has_scan: bool = False
    findings: Sequence[Mapping[str, Any]] = field(default_factory=list)
    estimate: Optional[Mapping[str, Any]] = None
    reports: Sequence[Mapping[str, Any]] = field(default_factory=list)
    opportunities: Sequence[Mapping[str, Any]] = field(default_factory=list)
    existing_source_ids: Sequence[str] = field(default_factory=list)
    proposed_source_ids: Sequence[str] = field(default_factory=list)
    completed_as_built_source_ids: Sequence[str] = field(default_factory=list)
    superseded: bool = False
    superseded_reason: Optional[str] = None
    awe_available: bool = False
    awe_release_state: Optional[str] = None
    projected_at: Optional[str] = None


@dataclass
class HabitatPropertyReadModel:
    """Consumer output: projection + reality model + redacted dump."""

    projection: HabitatPropertyProjection
    reality_model: RealityModelBundle
    payload: Dict[str, Any]


def _provenance(
    *,
    source_type: str,
    source_id: str,
    context: str,
    projected_at: str,
    passport_revision: Optional[int],
) -> ProvenanceDisplay:
    return ProvenanceDisplay(
        source_type=source_type,  # type: ignore[arg-type]
        source_id=source_id,
        publication_context=context,
        passport_revision=passport_revision,
        projected_at=projected_at,
        projector="habitat.read_model",
    )


def _finding_status_allowed(status: str) -> bool:
    return status in {"APPROVED", "RESOLVED"}


def project_finding(
    raw: Mapping[str, Any],
    *,
    projected_at: str,
    passport_revision: Optional[int],
) -> Optional[HomeownerFindingProjection]:
    """Project a single finding; skip non-approved / non-resolved."""
    status = str(raw.get("status") or "")
    if not _finding_status_allowed(status):
        return None

    unknown = UnknownStateDisplay.known()
    awaiting_is_not_approved(status=status, unknown_state=unknown)

    approved_at = raw.get("approved_at")
    if approved_at is None and isinstance(raw.get("approval"), Mapping):
        approved_at = raw["approval"].get("at")

    payload = redact_homeowner_secrets(
        {
            "canonical_id": raw["canonical_id"],
            "property_id": raw["property_id"],
            "taxonomy_category": raw["taxonomy_category"],
            "taxonomy_component": raw.get("taxonomy_component"),
            "severity": raw["severity"],
            "priority": raw["priority"],
            "description": raw["description"],
            "status": status,
            "approved_at": approved_at,
            "resolved_at": raw.get("resolved_at"),
            "manual_observation": bool(raw.get("manual_observation", False)),
            "provenance": _provenance(
                source_type="approved_finding",
                source_id=str(raw["canonical_id"]),
                context="habitat.finding_consumer",
                projected_at=projected_at,
                passport_revision=passport_revision,
            ).model_dump(),
            "confidence": build_honesty_confidence(
                unknown,
                display_label="Based on approved finding",
                source_band=raw.get("confidence_band"),
            ).model_dump(),
            "unknown_state": unknown.model_dump(),
        }
    )
    assert_homeowner_safe_payload(payload)
    return HomeownerFindingProjection.model_validate(payload)


def project_estimate_summary(
    raw: Optional[Mapping[str, Any]],
    *,
    property_id: str,
    projected_at: str,
    passport_revision: Optional[int],
) -> HomeownerEstimateSummaryProjection:
    """Homeowner estimate summary — never contractor margins / unit costs."""
    if raw is None:
        unknown = UnknownStateDisplay.unavailable("EstimateResult not published")
        payload = {
            "property_id": property_id,
            "estimate_ref": None,
            "availability": "unavailable",
            "currency": "USD",
            "total_range_label": None,
            "line_group_count": None,
            "includes_tax": None,
            "provenance": _provenance(
                source_type="estimate_result",
                source_id=f"{property_id}:estimate-absent",
                context="habitat.estimate_consumer",
                projected_at=projected_at,
                passport_revision=passport_revision,
            ).model_dump(),
            "confidence": build_honesty_confidence(
                unknown, display_label="Estimate not available"
            ).model_dump(),
            "unknown_state": unknown.model_dump(),
        }
        return HomeownerEstimateSummaryProjection.model_validate(payload)

    # Redact first so margins / unit costs never reach validation.
    cleaned = redact_homeowner_secrets(dict(raw))
    availability = str(cleaned.get("availability") or cleaned.get("status") or "unknown")
    if availability in {"approved", "published", "ready"}:
        availability = "available"
    if availability not in {"available", "unavailable", "awaiting_review", "unknown"}:
        availability = "unknown"

    if availability == "available":
        unknown = UnknownStateDisplay.known()
    elif availability == "awaiting_review":
        unknown = UnknownStateDisplay.awaiting_review(
            cleaned.get("reason") or "Estimate awaiting review"
        )
    elif availability == "unavailable":
        unknown = UnknownStateDisplay.unavailable(
            cleaned.get("reason") or "Estimate unavailable"
        )
    else:
        unknown = UnknownStateDisplay.unknown(
            cleaned.get("reason") or "Estimate state unknown"
        )

    # unknown≠0: do not coerce missing range / counts to 0.
    line_group_count = cleaned.get("line_group_count")
    line_group_count = unknown_is_not_zero(line_group_count, unknown_state=unknown)

    assert_display_rules(
        {"line_group_count": line_group_count},
        unknown_state=unknown,
        availability=availability,
        quantity_fields=("line_group_count",),
    )
    awaiting_is_not_approved(
        status=cleaned.get("status"),
        unknown_state=unknown,
        availability=availability,
    )

    payload = {
        "property_id": property_id,
        "estimate_ref": cleaned.get("estimate_ref") or cleaned.get("canonical_id"),
        "availability": availability,
        "currency": "USD",
        "total_range_label": cleaned.get("total_range_label"),
        "line_group_count": line_group_count,
        "includes_tax": cleaned.get("includes_tax"),
        "provenance": _provenance(
            source_type="estimate_result",
            source_id=str(
                cleaned.get("estimate_ref")
                or cleaned.get("canonical_id")
                or f"{property_id}:estimate"
            ),
            context="habitat.estimate_consumer",
            projected_at=projected_at,
            passport_revision=passport_revision,
        ).model_dump(),
        "confidence": build_honesty_confidence(
            unknown,
            display_label=(
                "Approved estimate summary"
                if availability == "available"
                else f"Estimate {availability}"
            ),
            source_band=cleaned.get("confidence_band"),
        ).model_dump(),
        "unknown_state": unknown.model_dump(),
    }
    payload = redact_homeowner_secrets(payload)
    assert_homeowner_safe_payload(payload)
    assert_no_private_cost_fields(payload)
    return HomeownerEstimateSummaryProjection.model_validate(payload)


def _report_approved_for_delivery(raw: Mapping[str, Any]) -> bool:
    status = str(raw.get("status") or "").lower()
    if status in _REPORT_DELIVERY_APPROVED_STATUSES:
        # Explicit denial wins.
        if raw.get("approved_for_delivery") is False:
            return False
        if status == "published" and raw.get("approved_for_delivery") is None:
            # published alone is insufficient unless delivery flag or template gate
            return bool(raw.get("delivery_approved") or raw.get("homeowner_deliverable"))
        return True
    return bool(raw.get("approved_for_delivery") or raw.get("delivery_approved"))


def project_report_reference(
    raw: Mapping[str, Any],
    *,
    property_id: str,
    projected_at: str,
    passport_revision: Optional[int],
) -> Optional[ReportPublicationReference]:
    """Emit report reference only when approved for homeowner delivery."""
    if not _report_approved_for_delivery(raw):
        return None

    unknown = UnknownStateDisplay.known()
    status = "published"
    publication_id = raw.get("publication_id") or raw.get("canonical_id")
    if not publication_id:
        return None

    awaiting_is_not_approved(status=status, unknown_state=unknown)

    payload = redact_homeowner_secrets(
        {
            "publication_id": publication_id,
            "property_id": property_id,
            "template": raw.get("template") or "homeowner_summary",
            "status": status,
            "published_at": raw.get("published_at"),
            "reference_uri": raw.get("reference_uri"),
            "provenance": _provenance(
                source_type="report_publication",
                source_id=str(publication_id),
                context="habitat.report_consumer",
                projected_at=projected_at,
                passport_revision=passport_revision,
            ).model_dump(),
            "confidence": build_honesty_confidence(
                unknown, display_label="Published homeowner report"
            ).model_dump(),
            "unknown_state": unknown.model_dump(),
        }
    )
    assert_homeowner_safe_payload(payload)
    return ReportPublicationReference.model_validate(payload)


def _opportunity_implies_unsupported_contract_or_payment(
    raw: Mapping[str, Any], status: str
) -> bool:
    """True when status claims contract/payment without supporting source fields."""
    if status.lower() not in _CONTRACT_OR_PAYMENT_STATUSES:
        return False
    return not any(raw.get(k) for k in _PAYMENT_SOURCE_FLAGS)


def project_opportunity_status(
    raw: Mapping[str, Any],
    *,
    property_id: str,
    projected_at: str,
    passport_revision: Optional[int],
) -> ProjectOpportunityStatusProjection:
    """Project opportunity status without inventing contracts/payments."""
    cleaned = redact_homeowner_secrets(dict(raw))
    status = str(cleaned.get("status") or "unknown")

    # Downgrade contract/payment implications when source lacks support.
    if _opportunity_implies_unsupported_contract_or_payment(cleaned, status):
        status = "shared"
        unknown = UnknownStateDisplay.awaiting_review(
            "Opportunity status does not include contract/payment source support"
        )
    elif status.lower() in _CONTRACT_OR_PAYMENT_STATUSES:
        # Supported contract/payment — still do not expose payment ids; map to accepted.
        status = "accepted"
        unknown = UnknownStateDisplay.known()
    elif status in {"unavailable", "awaiting_review", "unknown"}:
        factory = {
            "unavailable": UnknownStateDisplay.unavailable,
            "awaiting_review": UnknownStateDisplay.awaiting_review,
            "unknown": UnknownStateDisplay.unknown,
        }[status]
        unknown = factory(cleaned.get("reason") or f"Opportunity {status}")
    else:
        unknown = UnknownStateDisplay.known()

    if status not in {
        "proposed",
        "shared",
        "homeowner_reviewing",
        "accepted",
        "declined",
        "unavailable",
        "awaiting_review",
        "unknown",
    }:
        status = "unknown"
        unknown = UnknownStateDisplay.unknown("Unrecognized opportunity status")

    awaiting_is_not_approved(status=status, unknown_state=unknown)

    payload = {
        "opportunity_id": cleaned.get("opportunity_id") or cleaned.get("canonical_id"),
        "property_id": property_id,
        "status": status,
        "title_homeowner_safe": cleaned.get("title_homeowner_safe")
        or cleaned.get("title"),
        "linked_finding_ids": list(cleaned.get("linked_finding_ids") or []),
        "linked_estimate_ref": cleaned.get("linked_estimate_ref"),
        "provenance": _provenance(
            source_type="project_opportunity",
            source_id=str(
                cleaned.get("opportunity_id")
                or cleaned.get("canonical_id")
                or f"{property_id}:opportunity"
            ),
            context="habitat.opportunity_consumer",
            projected_at=projected_at,
            passport_revision=passport_revision,
        ).model_dump(),
        "confidence": build_honesty_confidence(
            unknown,
            display_label=f"Opportunity {status}",
        ).model_dump(),
        "unknown_state": unknown.model_dump(),
    }
    # Never pass through payment/contract fields into homeowner payload.
    payload = redact_homeowner_secrets(payload)
    for k in _PAYMENT_SOURCE_FLAGS:
        payload.pop(k, None)
    assert_homeowner_safe_payload(payload)
    return ProjectOpportunityStatusProjection.model_validate(payload)


class HabitatReadModelConsumer:
    """Pure in-process consumer — no Passport mutation side effects."""

    module_identity = MODULE_IDENTITY

    def build(self, source: HabitatPropertyReadSource) -> HabitatPropertyReadModel:
        projected_at = source.projected_at or _now_iso()
        addr = redact_homeowner_secrets(dict(source.address))

        findings: List[HomeownerFindingProjection] = []
        for raw in source.findings:
            projected = project_finding(
                raw,
                projected_at=projected_at,
                passport_revision=source.passport_revision,
            )
            if projected is not None:
                findings.append(projected)

        estimate = project_estimate_summary(
            source.estimate,
            property_id=source.property_id,
            projected_at=projected_at,
            passport_revision=source.passport_revision,
        )

        reports: List[ReportPublicationReference] = []
        for raw in source.reports:
            ref = project_report_reference(
                raw,
                property_id=source.property_id,
                projected_at=projected_at,
                passport_revision=source.passport_revision,
            )
            if ref is not None:
                reports.append(ref)

        opportunities = [
            project_opportunity_status(
                raw,
                property_id=source.property_id,
                projected_at=projected_at,
                passport_revision=source.passport_revision,
            )
            for raw in source.opportunities
        ]

        reality = build_reality_model(
            property_id=source.property_id,
            has_scan=source.has_scan,
            existing_source_ids=source.existing_source_ids,
            proposed_source_ids=source.proposed_source_ids,
            completed_as_built_source_ids=source.completed_as_built_source_ids,
            superseded=source.superseded,
            superseded_reason=source.superseded_reason,
            projected_at=projected_at,
            passport_revision=source.passport_revision,
        )

        # Property-level honesty: no_scan / superseded blocks authoritative presentation.
        if reality.overall_reference_state == "no_scan":
            prop_unknown = UnknownStateDisplay.unavailable("No scan for property")
        elif reality.overall_reference_state == "superseded":
            prop_unknown = UnknownStateDisplay.unavailable(
                source.superseded_reason or "Property reality model superseded"
            )
        elif reality.overall_reference_state == "scan_recorded":
            prop_unknown = UnknownStateDisplay.awaiting_review(
                "Scan recorded; projection awaiting approved truth"
            )
        else:
            prop_unknown = UnknownStateDisplay.known()

        projection = HabitatPropertyProjection.model_validate(
            {
                "audience": source.audience if source.audience in {"homeowner", "public"} else "homeowner",
                "property_summary": {
                    "property_id": source.property_id,
                    "address": {
                        "line1": addr.get("line1") or "",
                        "city": addr.get("city") or "",
                        "region": addr.get("region") or "",
                        "postal_code": addr.get("postal_code") or "",
                        "country_iso": addr.get("country_iso") or "US",
                        "unit_label": addr.get("unit_label"),
                    },
                    "inspection_date": source.inspection_date,
                },
                "findings": [f.model_dump() for f in findings],
                "estimate_summary": estimate.model_dump(),
                "report_references": [r.model_dump() for r in reports],
                "project_opportunities": [o.model_dump() for o in opportunities],
                "awe_available": bool(source.awe_available),
                "awe_release_state": source.awe_release_state
                if source.awe_available
                else None,
                "provenance": _provenance(
                    source_type="property_projection",
                    source_id=source.property_id,
                    context="habitat.property_read_model",
                    projected_at=projected_at,
                    passport_revision=source.passport_revision,
                ).model_dump(),
                "confidence": build_honesty_confidence(
                    prop_unknown,
                    display_label="Homeowner property projection",
                ).model_dump(),
                "unknown_state": prop_unknown.model_dump(),
            }
        )

        payload = redact_homeowner_secrets(
            {
                "projection": projection.model_dump(),
                "reality_model": reality.model_dump(),
                "module_identity": MODULE_IDENTITY,
                "canonical_write": "ABSENT",
            }
        )
        assert_homeowner_safe_payload(payload["projection"])
        assert_no_private_cost_fields(payload)

        return HabitatPropertyReadModel(
            projection=projection,
            reality_model=reality,
            payload=payload,
        )


def build_homeowner_property_read_model(
    source: HabitatPropertyReadSource,
) -> HabitatPropertyReadModel:
    """Functional entrypoint for the homeowner-safe property consumer."""
    return HabitatReadModelConsumer().build(source)


# Re-export for tests that probe import-side mutation attempts.
__all__ = [
    "MODULE_IDENTITY",
    "HabitatPropertyReadModel",
    "HabitatPropertyReadSource",
    "HabitatReadModelConsumer",
    "build_homeowner_property_read_model",
    "project_estimate_summary",
    "project_finding",
    "project_opportunity_status",
    "project_report_reference",
]
