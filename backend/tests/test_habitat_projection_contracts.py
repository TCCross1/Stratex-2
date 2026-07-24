"""Habitat projection contract consumer-preparation tests (LANE_4).

Validates PROPOSED executable schemas, homeowner-safety forbidden fields,
unknown/unavailable/awaiting-review honesty, JSON contract artifacts, and
proves Habitat routes cannot mutate canonical Passport truth.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from nextgen.schemas.habitat import (
    CONTRACT_STATUS,
    CONTRACT_VERSION,
    FORBIDDEN_HOMEOWNER_FIELDS,
    HabitatPropertyProjection,
    HomeownerEstimateSummaryProjection,
    HomeownerFindingProjection,
    ProjectOpportunityStatusProjection,
    ProvenanceDisplay,
    ReportPublicationReference,
    UnknownStateDisplay,
    assert_homeowner_safe_payload,
)

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
HABITAT_ROUTE = BACKEND / "nextgen" / "routes" / "habitat.py"
CONTRACTS = ROOT / "engineering" / "contracts" / "registry.yaml"
SCHEMA_DIR = ROOT / "engineering" / "contracts" / "schemas" / "habitat"
EXEC_DIR = BACKEND / "nextgen" / "schemas" / "habitat"

PASSPORT_WRITE_NEEDLES = (
    "append_entry",
    "governed_publish",
    "passport_entries.insert_one",
    "property_passports",
    "from ..passport_service",
    "from ..governed_publish_service",
    "from nextgen.passport_service",
    "from nextgen.governed_publish_service",
)

EXPECTED_JSON_SCHEMAS = (
    "common_display.json",
    "habitat_property_projection.json",
    "homeowner_finding_projection.json",
    "homeowner_estimate_summary_projection.json",
    "report_publication_reference.json",
    "project_opportunity_status_projection.json",
)


def _provenance(**overrides):
    base = {
        "source_type": "habitat_projection",
        "source_id": "proj-1",
        "publication_context": "habitat.consumer_prep",
        "passport_revision": 3,
        "projected_at": "2026-07-24T12:00:00+00:00",
        "projector": "habitat.projection",
    }
    base.update(overrides)
    return base


def _confidence(**overrides):
    base = {
        "band": "medium",
        "inherited_from_source": True,
        "display_label": "Based on approved inspection",
        "reduced_for_audience": True,
    }
    base.update(overrides)
    return base


def _finding(**overrides):
    base = {
        "canonical_id": "find-1",
        "property_id": "prop-1",
        "taxonomy_category": "ROOF",
        "taxonomy_component": "SHINGLES",
        "severity": "MAJOR",
        "priority": "IMPORTANT",
        "description": "Granule loss observed on south slope",
        "status": "APPROVED",
        "approved_at": "2026-07-20T10:00:00+00:00",
        "manual_observation": False,
        "provenance": _provenance(
            source_type="approved_finding",
            source_id="find-1",
        ),
        "confidence": _confidence(),
        "unknown_state": UnknownStateDisplay.known().model_dump(),
    }
    base.update(overrides)
    return base


def _estimate(**overrides):
    base = {
        "property_id": "prop-1",
        "estimate_ref": None,
        "availability": "awaiting_review",
        "currency": "USD",
        "total_range_label": None,
        "provenance": _provenance(source_type="estimate_result", source_id="est-pending"),
        "confidence": _confidence(band="unknown", display_label="Estimate not yet available"),
        "unknown_state": UnknownStateDisplay.awaiting_review(
            "EstimateResult not published"
        ).model_dump(),
    }
    base.update(overrides)
    return base


def _report_ref(**overrides):
    base = {
        "publication_id": None,
        "property_id": "prop-1",
        "template": "homeowner_summary",
        "status": "awaiting_review",
        "published_at": None,
        "reference_uri": None,
        "provenance": _provenance(
            source_type="report_publication", source_id="report-pending"
        ),
        "confidence": _confidence(band="unknown", display_label="Report pending review"),
        "unknown_state": UnknownStateDisplay.awaiting_review(
            "ReportPublicationPackage NOT_IMPLEMENTED"
        ).model_dump(),
    }
    base.update(overrides)
    return base


def _opportunity(**overrides):
    base = {
        "opportunity_id": None,
        "property_id": "prop-1",
        "status": "awaiting_review",
        "title_homeowner_safe": None,
        "linked_finding_ids": [],
        "linked_estimate_ref": None,
        "provenance": _provenance(
            source_type="project_opportunity", source_id="opp-pending"
        ),
        "confidence": _confidence(
            band="unknown", display_label="Opportunity not ready"
        ),
        "unknown_state": UnknownStateDisplay.awaiting_review(
            "ProjectOpportunityPackage NOT_IMPLEMENTED"
        ).model_dump(),
    }
    base.update(overrides)
    return base


def _property_projection(**overrides):
    base = {
        "audience": "homeowner",
        "property_summary": {
            "property_id": "prop-1",
            "address": {
                "line1": "1234 Test Command Ave",
                "city": "Denver",
                "region": "CO",
                "postal_code": "80202",
            },
            "inspection_date": "2026-07-18T15:00:00+00:00",
        },
        "findings": [_finding()],
        "estimate_summary": _estimate(),
        "report_references": [_report_ref()],
        "project_opportunities": [_opportunity()],
        "awe_available": False,
        "awe_release_state": None,
        "provenance": _provenance(
            source_type="property_projection", source_id="prop-1"
        ),
        "confidence": _confidence(),
        "unknown_state": UnknownStateDisplay.known().model_dump(),
    }
    base.update(overrides)
    return base


# ── Schema artifact presence ────────────────────────────────────────────
def test_json_contract_schemas_exist_and_parse():
    assert SCHEMA_DIR.is_dir()
    for name in EXPECTED_JSON_SCHEMAS:
        path = SCHEMA_DIR / name
        assert path.is_file(), name
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("title") or data.get("$id")
        assert data.get("$schema")


def test_executable_schema_modules_exist():
    for name in (
        "common.py",
        "property_projection.py",
        "finding_projection.py",
        "estimate_summary.py",
        "report_reference.py",
        "opportunity_status.py",
        "__init__.py",
    ):
        assert (EXEC_DIR / name).is_file(), name


def test_registry_habitat_contracts_remain_unfrozen():
    data = yaml.safe_load(CONTRACTS.read_text(encoding="utf-8"))
    by_name = {c["name"]: c for c in data["contracts"]}
    hpp = by_name["HabitatPropertyProjection"]
    assert hpp["status"] == "PROPOSED"
    assert hpp["status"] not in {"FROZEN", "ACCEPTED"}
    assert str(hpp["version"]) == "0.0.0"
    assert "schema_path" in hpp
    assert hpp["schema_path"].endswith("habitat_property_projection.json")

    pop = by_name["ProjectOpportunityPackage"]
    assert pop["status"] == "NOT_IMPLEMENTED"
    assert pop["status"] not in {"FROZEN", "ACCEPTED"}


def test_contract_constants_match_registry():
    assert CONTRACT_STATUS == "PROPOSED"
    assert CONTRACT_VERSION == "0.0.0"


# ── Executable validation ───────────────────────────────────────────────
def test_habitat_property_projection_accepts_valid_payload():
    model = HabitatPropertyProjection.model_validate(_property_projection())
    assert model.schema_name == "HabitatPropertyProjection"
    assert model.contract_status == "PROPOSED"
    assert model.audience == "homeowner"
    assert len(model.findings) == 1
    assert model.findings[0].severity == "MAJOR"


def test_homeowner_finding_projection_aligns_with_route_strip_shape():
    """Compatibility with findings._project_for_habitat field set."""
    model = HomeownerFindingProjection.model_validate(_finding())
    dumped = model.model_dump()
    for key in (
        "canonical_id",
        "property_id",
        "taxonomy_category",
        "taxonomy_component",
        "severity",
        "priority",
        "description",
        "status",
        "approved_at",
        "manual_observation",
        "resolved_at",
    ):
        assert key in dumped
    for forbidden in (
        "notes",
        "approval",
        "review_history",
        "author_id",
        "confidence_pct",
        "confidence_source",
        "insurance_relevant",
        "passport_content_hash",
    ):
        assert forbidden not in dumped


def test_forbidden_fields_rejected_on_finding():
    bad = _finding(notes="internal reviewer note")
    with pytest.raises(ValidationError):
        HomeownerFindingProjection.model_validate(bad)


def test_forbidden_contractor_pricing_rejected_on_estimate():
    bad = _estimate(
        availability="available",
        unknown_state=UnknownStateDisplay.known().model_dump(),
        confidence=_confidence(band="medium", display_label="Approved estimate summary"),
        contractor_pricing={"unit_cost_cents": 4500},
    )
    with pytest.raises((ValidationError, ValueError)):
        HomeownerEstimateSummaryProjection.model_validate(bad)


def test_assert_homeowner_safe_payload_helper():
    assert_homeowner_safe_payload({"ok": True, "nested": {"label": "x"}})
    with pytest.raises(ValueError, match="Forbidden"):
        assert_homeowner_safe_payload({"confidence_pct": 99})
    assert "unit_cost" in FORBIDDEN_HOMEOWNER_FIELDS
    assert "confidence_pct" in FORBIDDEN_HOMEOWNER_FIELDS


def test_estimate_summary_honesty_states():
    for state, availability, factory in (
        ("unavailable", "unavailable", UnknownStateDisplay.unavailable),
        ("awaiting_review", "awaiting_review", UnknownStateDisplay.awaiting_review),
        ("unknown", "unknown", UnknownStateDisplay.unknown),
    ):
        model = HomeownerEstimateSummaryProjection.model_validate(
            _estimate(
                availability=availability,
                unknown_state=factory(f"estimate {state}").model_dump(),
                confidence=_confidence(
                    band="unknown", display_label=f"Estimate {state}"
                ),
            )
        )
        assert model.unknown_state.state == state
        assert model.unknown_state.blocks_authoritative_presentation is True

    with pytest.raises(ValidationError):
        HomeownerEstimateSummaryProjection.model_validate(
            _estimate(
                availability="awaiting_review",
                unknown_state=UnknownStateDisplay.known().model_dump(),
            )
        )


def test_report_publication_reference_schema():
    pending = ReportPublicationReference.model_validate(_report_ref())
    assert pending.package_contract_status == "NOT_IMPLEMENTED"
    assert pending.status == "awaiting_review"

    published = ReportPublicationReference.model_validate(
        _report_ref(
            publication_id="pub-1",
            status="published",
            published_at="2026-07-21T00:00:00+00:00",
            reference_uri="/habitat/reports/pub-1",
            unknown_state=UnknownStateDisplay.known().model_dump(),
            confidence=_confidence(display_label="Published homeowner report"),
        )
    )
    assert published.publication_id == "pub-1"

    with pytest.raises(ValidationError):
        ReportPublicationReference.model_validate(
            _report_ref(status="published", publication_id=None)
        )


def test_project_opportunity_status_projection_schema():
    pending = ProjectOpportunityStatusProjection.model_validate(_opportunity())
    assert pending.package_contract == "ProjectOpportunityPackage"
    assert pending.package_contract_status == "NOT_IMPLEMENTED"
    assert pending.status == "awaiting_review"

    shared = ProjectOpportunityStatusProjection.model_validate(
        _opportunity(
            opportunity_id="opp-1",
            status="shared",
            title_homeowner_safe="Roof maintenance discussion",
            linked_finding_ids=["find-1"],
            unknown_state=UnknownStateDisplay.known().model_dump(),
            confidence=_confidence(display_label="Ready for conversation"),
        )
    )
    assert shared.status == "shared"

    with pytest.raises(ValidationError):
        ProjectOpportunityStatusProjection.model_validate(
            _opportunity(
                status="unavailable",
                unknown_state=UnknownStateDisplay.known().model_dump(),
            )
        )


def test_provenance_and_confidence_display_contract():
    prov = ProvenanceDisplay.model_validate(_provenance())
    assert prov.projector == "habitat.projection"
    assert prov.passport_revision == 3

    for band in ("high", "medium", "low", "unknown"):
        c = _confidence(band=band)
        assert ProvenanceDisplay.model_validate(_provenance())
        from nextgen.schemas.habitat.common import ConfidenceDisplay

        ConfidenceDisplay.model_validate(c)

    with pytest.raises(ValidationError):
        ProvenanceDisplay.model_validate({**_provenance(), "source_id": ""})


def test_unknown_unavailable_awaiting_review_factories():
    assert UnknownStateDisplay.unknown("gap").state == "unknown"
    assert UnknownStateDisplay.unavailable("down").state == "unavailable"
    assert UnknownStateDisplay.awaiting_review("pending").state == "awaiting_review"
    for state in (
        UnknownStateDisplay.unknown("x"),
        UnknownStateDisplay.unavailable("x"),
        UnknownStateDisplay.awaiting_review("x"),
    ):
        assert state.blocks_authoritative_presentation is True


def test_property_projection_rejects_awe_release_without_availability():
    with pytest.raises(ValidationError):
        HabitatPropertyProjection.model_validate(
            _property_projection(awe_available=False, awe_release_state="INTERNAL_DRAFT")
        )


# ── Habitat write-authority ABSENT proof ────────────────────────────────
def test_habitat_route_cannot_mutate_passport():
    text = HABITAT_ROUTE.read_text(encoding="utf-8")
    for needle in PASSPORT_WRITE_NEEDLES:
        assert needle not in text, f"Habitat must not contain {needle!r}"


def test_habitat_schemas_do_not_import_passport_writers():
    import_needles = (
        "from ..passport_service",
        "from ..governed_publish_service",
        "from ..approval_policy",
        "from nextgen.passport_service",
        "from nextgen.governed_publish_service",
        "from nextgen.approval_policy",
        "passport_entries.insert_one",
        "await append_entry",
        "await governed_publish",
    )
    for path in EXEC_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in import_needles:
            assert needle not in text, f"{path.name} must not contain {needle!r}"


def test_habitat_route_has_no_passport_collection_writes():
    text = HABITAT_ROUTE.read_text(encoding="utf-8")
    # Grant / audit writes are relationship UX — not Passport ledger.
    assert "passport_entries" not in text
    assert "nextgen_passport_entries" not in text
    assert ".insert_one" in text  # habitat_grants / audit_events only
    # Ensure insert targets are not passport collections by scanning lines.
    for i, line in enumerate(text.splitlines(), 1):
        if "insert_one" not in line:
            continue
        assert "passport" not in line.lower(), f"line {i}: {line}"
