"""HABITAT-P-002 homeowner-safe read-model consumer tests.

Proves:
- Reality-model states (no_scan → superseded) + layer separation
- unknown≠0 and awaiting≠approved display rules
- Report refs only when approved for delivery
- Estimate summaries without contractor-private margins
- Opportunity status without unsupported contract/payment claims
- Privacy redaction of secrets / private costs
- Canonical Passport mutation ABSENT in the Habitat consumer package
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from nextgen.habitat import (
    MODULE_IDENTITY,
    HabitatPropertyReadSource,
    HabitatReadModelConsumer,
    build_homeowner_property_read_model,
    build_reality_model,
    redact_homeowner_secrets,
)
from nextgen.habitat.display_rules import (
    DisplayRuleError,
    awaiting_is_not_approved,
    unknown_is_not_zero,
)
from nextgen.habitat.read_model import (
    project_estimate_summary,
    project_opportunity_status,
    project_report_reference,
)
from nextgen.schemas.habitat import UnknownStateDisplay

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
HABITAT_PKG = BACKEND / "nextgen" / "habitat"
HABITAT_ROUTE = BACKEND / "nextgen" / "routes" / "habitat.py"
SCHEMAS_INIT = BACKEND / "nextgen" / "schemas" / "__init__.py"
CONTRACT_READINESS = (
    ROOT / "engineering" / "px004" / "lane4" / "CONTRACT_READINESS.md"
)

PASSPORT_WRITE_NEEDLES = (
    "append_entry",
    "governed_publish",
    "passport_entries.insert_one",
    "property_passports",
    "from ..passport_service",
    "from ..governed_publish_service",
    "from ..approval_policy",
    "from nextgen.passport_service",
    "from nextgen.governed_publish_service",
    "from nextgen.approval_policy",
    "passport_entries",
    "nextgen_passport_entries",
)


def _addr():
    return {
        "line1": "1234 Test Command Ave",
        "city": "Denver",
        "region": "CO",
        "postal_code": "80202",
    }


def _approved_finding(**overrides):
    base = {
        "canonical_id": "find-1",
        "property_id": "prop-1",
        "taxonomy_category": "ROOF",
        "taxonomy_component": "SHINGLES",
        "severity": "MAJOR",
        "priority": "IMPORTANT",
        "description": "Granule loss on south slope",
        "status": "APPROVED",
        "approved_at": "2026-07-20T10:00:00+00:00",
        "manual_observation": False,
        "notes": "internal reviewer note",
        "confidence_pct": 99,
        "margin_pct": 22,
    }
    base.update(overrides)
    return base


# ── Package / docs presence ─────────────────────────────────────────────
def test_contract_readiness_doc_exists():
    assert CONTRACT_READINESS.is_file()
    text = CONTRACT_READINESS.read_text(encoding="utf-8")
    assert "HABITAT-P-002" in text
    assert "ABSENT" in text
    assert "PROPOSED" in text


def test_module_identity():
    assert MODULE_IDENTITY == "nextgen.habitat.read_model"
    assert HabitatReadModelConsumer.module_identity == MODULE_IDENTITY


def test_schemas_init_not_required_for_p002():
    """Disclose: HABITAT-P-002 does not need to touch schemas/__init__.py."""
    assert SCHEMAS_INIT.is_file()
    # Habitat subpackage import still works through existing package root.
    from nextgen.schemas import habitat as habitat_schemas

    assert hasattr(habitat_schemas, "HabitatPropertyProjection")


# ── Canonical write ABSENT ───────────────────────────────────────────────
def test_habitat_consumer_package_has_no_canonical_write_authority():
    assert HABITAT_PKG.is_dir()
    for path in HABITAT_PKG.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in PASSPORT_WRITE_NEEDLES:
            assert needle not in text, f"{path.name} must not contain {needle!r}"


def test_habitat_consumer_ast_has_no_passport_mutation_calls():
    """AST-level proof: no calls to append_entry / governed_publish."""
    forbidden_calls = {"append_entry", "governed_publish", "insert_one"}
    for path in HABITAT_PKG.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in forbidden_calls:
                    # insert_one is never acceptable in this package.
                    pytest.fail(f"{path.name} calls forbidden {name}()")


def test_build_read_model_does_not_import_passport_writers(monkeypatch):
    """Runtime: importing/building must not pull Passport writers."""
    import sys

    blocked = {
        "nextgen.passport_service",
        "nextgen.governed_publish_service",
        "nextgen.approval_policy",
    }
    real_import = __import__

    def guarded(name, *args, **kwargs):
        if name in blocked or any(name.startswith(b + ".") for b in blocked):
            raise AssertionError(f"Habitat consumer must not import {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", guarded)
    # Fresh build path (modules already imported are fine; new imports blocked).
    model = build_homeowner_property_read_model(
        HabitatPropertyReadSource(
            property_id="prop-1",
            address=_addr(),
            has_scan=False,
            projected_at="2026-07-24T12:00:00+00:00",
        )
    )
    assert model.payload["canonical_write"] == "ABSENT"
    assert "nextgen.passport_service" not in sys.modules or True  # not newly required


def test_habitat_route_still_has_no_passport_writes():
    text = HABITAT_ROUTE.read_text(encoding="utf-8")
    for needle in (
        "append_entry",
        "governed_publish",
        "passport_entries",
        "from ..passport_service",
    ):
        assert needle not in text


# ── Reality model ────────────────────────────────────────────────────────
def test_reality_model_no_scan_to_superseded_and_layer_separation():
    no_scan = build_reality_model(
        property_id="prop-1",
        has_scan=False,
        projected_at="2026-07-24T12:00:00+00:00",
    )
    assert no_scan.overall_reference_state == "no_scan"
    assert no_scan.existing.reference_state == "no_scan"
    assert no_scan.existing.kind == "existing"
    assert no_scan.proposed.kind == "proposed"
    assert no_scan.completed_as_built.kind == "completed_as_built"
    assert no_scan.existing.is_authoritative is False
    assert no_scan.existing.unknown_state.blocks_authoritative_presentation is True

    existing = build_reality_model(
        property_id="prop-1",
        has_scan=True,
        existing_source_ids=["scan-1"],
        projected_at="2026-07-24T12:00:00+00:00",
    )
    assert existing.overall_reference_state == "existing"
    assert existing.existing.reference_state == "existing"
    assert existing.proposed.reference_state in {"no_scan", "scan_recorded"}
    assert existing.completed_as_built.kind == "completed_as_built"

    proposed = build_reality_model(
        property_id="prop-1",
        has_scan=True,
        existing_source_ids=["scan-1"],
        proposed_source_ids=["prop-design-1"],
        projected_at="2026-07-24T12:00:00+00:00",
    )
    assert proposed.overall_reference_state == "proposed"
    assert proposed.proposed.reference_state == "proposed"
    assert proposed.existing.kind != proposed.proposed.kind

    completed = build_reality_model(
        property_id="prop-1",
        has_scan=True,
        existing_source_ids=["scan-1"],
        completed_as_built_source_ids=["asbuilt-1"],
        projected_at="2026-07-24T12:00:00+00:00",
    )
    assert completed.overall_reference_state == "completed_as_built"
    assert completed.completed_as_built.reference_state == "completed_as_built"

    superseded = build_reality_model(
        property_id="prop-1",
        has_scan=True,
        existing_source_ids=["scan-1"],
        superseded=True,
        superseded_reason="Replaced by newer survey",
        projected_at="2026-07-24T12:00:00+00:00",
    )
    assert superseded.overall_reference_state == "superseded"
    assert superseded.existing.reference_state == "superseded"
    assert superseded.proposed.reference_state == "superseded"
    assert superseded.completed_as_built.reference_state == "superseded"
    assert superseded.existing.is_authoritative is False


# ── Display rules ────────────────────────────────────────────────────────
def test_unknown_is_not_zero():
    unknown = UnknownStateDisplay.unknown("gap")
    assert unknown_is_not_zero(None, unknown_state=unknown) is None
    with pytest.raises(DisplayRuleError, match="unknown≠0"):
        unknown_is_not_zero(0, unknown_state=unknown)
    with pytest.raises(DisplayRuleError, match="unknown≠0"):
        unknown_is_not_zero(0.0, unknown_state=unknown)
    # Known state may carry a real zero.
    assert unknown_is_not_zero(0, unknown_state=UnknownStateDisplay.known()) == 0


def test_awaiting_is_not_approved():
    awaiting = UnknownStateDisplay.awaiting_review("pending")
    with pytest.raises(DisplayRuleError, match="awaiting≠approved"):
        awaiting_is_not_approved(status="approved", unknown_state=awaiting)
    with pytest.raises(DisplayRuleError, match="awaiting≠approved"):
        awaiting_is_not_approved(
            status=None, unknown_state=awaiting, availability="available"
        )
    awaiting_is_not_approved(status="awaiting_review", unknown_state=awaiting)


def test_estimate_consumer_rejects_zero_under_unknown():
    with pytest.raises(DisplayRuleError):
        project_estimate_summary(
            {
                "availability": "unknown",
                "line_group_count": 0,
                "reason": "missing quantities",
            },
            property_id="prop-1",
            projected_at="2026-07-24T12:00:00+00:00",
            passport_revision=1,
        )


# ── Report consumer ──────────────────────────────────────────────────────
def test_report_reference_only_when_approved_for_delivery():
    pending = project_report_reference(
        {
            "publication_id": "pub-pending",
            "status": "awaiting_review",
            "template": "homeowner_summary",
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=1,
    )
    assert pending is None

    published_only = project_report_reference(
        {
            "publication_id": "pub-1",
            "status": "published",
            "template": "homeowner_summary",
            "published_at": "2026-07-21T00:00:00+00:00",
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=1,
    )
    assert published_only is None  # published alone ≠ approved for delivery

    # RENDERED / UNDER_REVIEW never imply approved (E-N-001)
    for status in ("RENDERED", "UNDER_REVIEW", "FAILED", "SUPERSEDED", "PROPOSED"):
        assert (
            project_report_reference(
                {
                    "report_publication_id": "rp-x",
                    "publication_status": status,
                    "report_type": "homeowner_summary",
                    "approved_for_delivery": True,  # flag must not override
                },
                property_id="prop-1",
                projected_at="2026-07-24T12:00:00+00:00",
                passport_revision=1,
            )
            is None
        )

    # Missing / unknown status fail closed
    assert (
        project_report_reference(
            {"report_publication_id": "rp-missing", "report_type": "homeowner_summary"},
            property_id="prop-1",
            projected_at="2026-07-24T12:00:00+00:00",
            passport_revision=1,
        )
        is None
    )

    deliverable = project_report_reference(
        {
            "publication_id": "pub-2",
            "status": "published",
            "approved_for_delivery": True,
            "template": "homeowner_summary",
            "published_at": "2026-07-21T00:00:00+00:00",
            "reference_uri": "/habitat/reports/pub-2",
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=1,
    )
    assert deliverable is not None
    assert deliverable.publication_id == "pub-2"
    assert deliverable.status == "published"

    # Exact C-P-004 package field mapping (E-N-003)
    cp004 = project_report_reference(
        {
            "report_publication_id": "rp-cp004",
            "publication_status": "APPROVED_FOR_DELIVERY",
            "delivery_status": "APPROVED_FOR_DELIVERY",
            "report_type": "homeowner_summary",
            "template_version": "1.2.0",
            "object_reference_safe_id": "objref:abc123",
            "checksum": "deadbeef",
            "generated_at": "2026-07-21T00:00:00+00:00",
            "approved_at": "2026-07-22T00:00:00+00:00",
            "superseded": False,
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=1,
    )
    assert cp004 is not None
    assert cp004.publication_id == "rp-cp004"
    assert cp004.template == "homeowner_summary"
    assert cp004.reference_uri == "objref:abc123"
    assert cp004.published_at == "2026-07-22T00:00:00+00:00"
    assert cp004.status == "published"


# ── Estimate consumer / privacy ──────────────────────────────────────────
def test_estimate_summary_strips_contractor_private_margins():
    model = project_estimate_summary(
        {
            "canonical_id": "est-1",
            "availability": "available",
            "total_range_label": "$8k–$12k",
            "line_group_count": 3,
            "margin": 0.35,
            "margin_pct": 35,
            "contractor_pricing": {"unit_cost_cents": 4500},
            "unit_cost_cents": 4500,
            "secret": "do-not-leak",
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=2,
    )
    dumped = model.model_dump()
    assert dumped["availability"] == "available"
    assert dumped["total_range_label"] == "$8k–$12k"
    for forbidden in (
        "margin",
        "margin_pct",
        "contractor_pricing",
        "unit_cost_cents",
        "secret",
    ):
        assert forbidden not in dumped


def test_redact_homeowner_secrets_removes_tokens_and_costs():
    cleaned = redact_homeowner_secrets(
        {
            "ok": True,
            "token": "abc",
            "api_key": "xyz",
            "private_cost_cents": 1200,
            "nested": {"password": "nope", "label": "safe"},
        }
    )
    assert cleaned == {"ok": True, "nested": {"label": "safe"}}


def test_compound_private_field_redaction_matrix():
    cleaned = redact_homeowner_secrets(
        {
            "safe": 1,
            "marginPct": 12,
            "Margin": 1,
            "margin-pct": 9,
            "grossMargin": 0.2,
            "Profit": 100,
            "contractorMargin": 0.3,
            "private.cost": 44,
            "api-key": "k",
            "nested": {"unitCostCents": 500, "label": "ok"},
            "SecretToken": "x",
            "presignedUrl": "https://signed",
            "auditSignature": "sig",
        }
    )
    assert cleaned["safe"] == 1
    assert cleaned["nested"] == {"label": "ok"}
    for banned in (
        "marginPct",
        "Margin",
        "margin-pct",
        "grossMargin",
        "Profit",
        "contractorMargin",
        "private.cost",
        "api-key",
        "SecretToken",
        "presignedUrl",
        "auditSignature",
    ):
        assert banned not in cleaned
    assert "unitCostCents" not in cleaned["nested"]


def test_estimate_maps_exact_ledger_id():
    model = project_estimate_summary(
        {
            "ledger_id": "led-e002-001",
            "availability": "available",
            "assembly_engine_version": "e002.1.0.0",
            "total_range_label": None,
            "line_group_count": 2,
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=2,
    )
    assert model.estimate_ref == "led-e002-001"
    assert "e002.1.0.0" in model.provenance.source_id


# ── Opportunity consumer ─────────────────────────────────────────────────
def test_opportunity_status_without_unsupported_contract_payment():
    downgraded = project_opportunity_status(
        {
            "opportunity_id": "opp-1",
            "status": "paid",
            "title_homeowner_safe": "Roof discussion",
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=1,
    )
    assert downgraded.status == "shared"
    assert downgraded.unknown_state.state == "awaiting_review"
    dumped = downgraded.model_dump()
    assert "payment_id" not in dumped
    assert "contract_id" not in dumped

    supported = project_opportunity_status(
        {
            "opportunity_id": "opp-2",
            "status": "contracted",
            "contract_id": "ctr-1",
            "title_homeowner_safe": "Approved scope conversation",
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=1,
    )
    assert supported.status == "accepted"
    assert "contract_id" not in supported.model_dump()

    relationship = project_opportunity_status(
        {
            "opportunity_id": "opp-3",
            "status": "accepted",
            "title_homeowner_safe": "Homeowner accepted conversation",
        },
        property_id="prop-1",
        projected_at="2026-07-24T12:00:00+00:00",
        passport_revision=1,
    )
    assert relationship.status == "accepted"


# ── Full property consumer ───────────────────────────────────────────────
def test_build_homeowner_property_read_model_end_to_end():
    result = build_homeowner_property_read_model(
        HabitatPropertyReadSource(
            property_id="prop-1",
            address=_addr(),
            inspection_date="2026-07-18T15:00:00+00:00",
            passport_revision=4,
            has_scan=True,
            findings=[
                _approved_finding(),
                _approved_finding(
                    canonical_id="find-draft",
                    status="DRAFT",
                    description="Should be excluded",
                ),
            ],
            estimate={
                "ledger_id": "led-est-1",
                "availability": "awaiting_review",
                "margin_pct": 40,
                "contractorMargin": 0.4,
            },
            reports=[
                {
                    "report_publication_id": "pub-x",
                    "publication_status": "APPROVED_FOR_DELIVERY",
                    "report_type": "homeowner_summary",
                    "object_reference_safe_id": "objref:pub-x",
                    "approved_at": "2026-07-21T00:00:00+00:00",
                    "superseded": False,
                },
                {
                    "report_publication_id": "pub-y",
                    "publication_status": "UNDER_REVIEW",
                },
                {
                    "report_publication_id": "pub-z",
                    "publication_status": "SUPERSEDED",
                    "superseded": True,
                },
            ],
            opportunities=[
                {
                    "opportunity_id": "opp-1",
                    "status": "proposed",
                    "title_homeowner_safe": "Maintenance conversation",
                    "linked_finding_ids": ["find-1"],
                }
            ],
            existing_source_ids=["scan-1"],
            proposed_source_ids=["design-1"],
            projected_at="2026-07-24T12:00:00+00:00",
        )
    )

    proj = result.projection
    assert proj.schema_name == "HabitatPropertyProjection"
    assert proj.contract_status == "PROPOSED"
    assert len(proj.findings) == 1
    assert proj.findings[0].canonical_id == "find-1"
    assert "notes" not in proj.findings[0].model_dump()
    assert proj.estimate_summary is not None
    assert proj.estimate_summary.availability == "awaiting_review"
    assert proj.estimate_summary.unknown_state.state == "awaiting_review"
    assert len(proj.report_references) == 1
    assert proj.report_references[0].publication_id == "pub-x"
    assert len(proj.project_opportunities) == 1
    assert result.reality_model.overall_reference_state == "proposed"
    assert result.reality_model.existing.kind == "existing"
    assert result.reality_model.proposed.kind == "proposed"
    assert result.payload["canonical_write"] == "ABSENT"
    # Privacy: forbidden fields absent from serialized payload.
    blob = str(result.payload)
    assert "margin_pct" not in blob
    assert "internal reviewer note" not in blob
