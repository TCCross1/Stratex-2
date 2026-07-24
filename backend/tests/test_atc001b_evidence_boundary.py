"""ATC-001B evidence producer/consumer boundary — synthetic fixture tests.

Checkpoint: evidence boundary, compatibility validation, DJI parser foundation,
quality gates. Does not claim live DJI SDK, physical capture, RTK accuracy,
approved geometry/findings, automated thermal diagnosis, or Passport authority.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from nextgen.atc import (
    AuthorityViolation,
    ConsumerKind,
    EVIDENCE_PROFILES,
    PROFILE_IDS,
    PackageQualityGate,
    ProducerOutputKind,
    boundary_for,
    evaluate_package_quality,
    refuse_approved_emission,
    refuse_passport_write,
    validate_compatibility,
)
from nextgen.atc.dji import (
    SyntheticDJIPackageParser,
    WarningCode,
    load_synthetic_fixture,
)
from nextgen.atc.pipeline import assess_synthetic_package
from nextgen.schemas.atc import (
    AWEEvidenceCandidate,
    ApprovedFinding,
    ApprovedGeometry,
    ConsumerContractForbidden,
    GeometryCandidate,
    MIGRATION_NOTES,
    alias_map,
)
from nextgen.schemas.common import Confidence, Provenance, UnknownState


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
ATC_ROOT = BACKEND / "nextgen" / "atc"
SCHEMAS_ATC = BACKEND / "nextgen" / "schemas" / "atc"
CONTRACT_READINESS = ROOT / "engineering" / "px004" / "lane2" / "CONTRACT_READINESS.md"
SCHEMAS_INIT = BACKEND / "nextgen" / "schemas" / "__init__.py"

ATC_MODULES = [
    ATC_ROOT / "authority.py",
    ATC_ROOT / "boundary.py",
    ATC_ROOT / "compatibility.py",
    ATC_ROOT / "quality_gates.py",
    ATC_ROOT / "pipeline.py",
    ATC_ROOT / "dji" / "interfaces.py",
    ATC_ROOT / "dji" / "synthetic.py",
    ATC_ROOT / "dji" / "checksums.py",
    ATC_ROOT / "dji" / "pairing.py",
    ATC_ROOT / "dji" / "warnings.py",
    SCHEMAS_ATC / "aliases.py",
    SCHEMAS_ATC / "approved_side.py",
]


def _prov(**kwargs) -> Provenance:
    base = dict(
        source_type="contract_fixture",
        source_id="atc001b-fixture",
        publication_context="contract_fixture",
    )
    base.update(kwargs)
    return Provenance(**base)


def _conf(**kwargs) -> Confidence:
    return Confidence(**kwargs)


def _unk(**kwargs) -> UnknownState:
    return UnknownState(**kwargs)


# ── Profiles + producer/consumer boundary ────────────────────────────────


def test_all_four_profiles_have_boundaries():
    assert PROFILE_IDS == frozenset(
        {"M4E_MAPPING", "M4T_AWE", "M400_P1_MAPPING", "M400_H30T_AWE"}
    )
    for pid in PROFILE_IDS:
        b = boundary_for(pid)
        assert b.profile_id == pid
        assert b.doctrine_flags()["thermal_changes_dimensions"] is False
        assert b.doctrine_flags()["geometry_implies_approval"] is False
        assert b.doctrine_flags()["is_passport_writer"] is False


def test_mapping_profiles_produce_geometry_candidate_only():
    for pid in ("M4E_MAPPING", "M400_P1_MAPPING"):
        b = boundary_for(pid)
        b.assert_may_produce(ProducerOutputKind.GEOMETRY_CANDIDATE)
        b.assert_may_produce(ProducerOutputKind.EVIDENCE_MANIFEST)
        with pytest.raises(AuthorityViolation):
            b.assert_may_produce(ProducerOutputKind.AWE_EVIDENCE_CANDIDATE)
        # Estimator must not accept candidate as approved
        with pytest.raises(AuthorityViolation):
            b.assert_consumer_accepts(ConsumerKind.ESTIMATOR, "GeometryCandidate")
        b.assert_consumer_accepts(ConsumerKind.ESTIMATOR, "ApprovedGeometry")
        b.assert_consumer_accepts(ConsumerKind.ATC_PAIR_GATE, "GeometryCandidate")


def test_awe_profiles_produce_awe_candidate_not_dimensions():
    for pid in ("M4T_AWE", "M400_H30T_AWE"):
        b = boundary_for(pid)
        b.assert_may_produce(ProducerOutputKind.AWE_EVIDENCE_CANDIDATE)
        with pytest.raises(AuthorityViolation):
            b.assert_may_produce(ProducerOutputKind.GEOMETRY_CANDIDATE)
        assert b.spec.may_claim_dimensions is False
        assert b.spec.may_claim_thermal_diagnosis is False
        assert b.spec.dimensional_authority == "not_dimensional_authority"
        with pytest.raises(AuthorityViolation):
            b.assert_consumer_accepts(ConsumerKind.PASSPORT, "AWEEvidenceCandidate")
        b.assert_consumer_accepts(ConsumerKind.PASSPORT, "ApprovedFinding")


def test_boundary_refuses_approved_emission():
    b = boundary_for("M4E_MAPPING")
    with pytest.raises(AuthorityViolation):
        b.emit_approved_geometry()
    with pytest.raises(AuthorityViolation):
        b.emit_approved_finding()
    with pytest.raises(AuthorityViolation):
        refuse_passport_write()
    with pytest.raises(AuthorityViolation):
        refuse_approved_emission("ApprovedGeometry")


# ── Alias separation (no silent rename) ──────────────────────────────────


def test_geometry_candidate_alias_is_not_approved_geometry():
    assert GeometryCandidate is alias_map()["ApprovedGeometryCandidate"]
    assert "GeometryCandidate" in MIGRATION_NOTES
    assert "ApprovedGeometry" in MIGRATION_NOTES
    cand = GeometryCandidate(
        candidate_id="geo-1",
        mission_id="m-4e",
        aircraft_profile_id="M4E_MAPPING",
        source_evidence_manifest_id="em-1",
        provenance=_prov(mission_id="m-4e", aircraft_profile_id="M4E_MAPPING"),
        confidence=_conf(),
        unknown_state=_unk(incomplete=True),
    )
    assert cand.is_production_approved is False
    assert cand.approval_status == "CANDIDATE"
    # Distinct consumer type
    assert GeometryCandidate is not ApprovedGeometry


def test_awe_evidence_candidate_alias_is_not_approved_finding():
    assert AWEEvidenceCandidate is alias_map()["AweEvidenceCandidate"]
    awe = AWEEvidenceCandidate(
        candidate_id="awe-1",
        mission_id="m-4t",
        aircraft_profile_id="M4T_AWE",
        source_evidence_manifest_id="em-4t",
        provenance=_prov(mission_id="m-4t", aircraft_profile_id="M4T_AWE"),
        confidence=_conf(),
        unknown_state=_unk(incomplete=True),
    )
    assert awe.is_dimensional_authority is False
    assert awe.thermal_changes_dimensions is False
    assert AWEEvidenceCandidate is not ApprovedFinding


def test_approved_side_markers_forbid_atc_producer_lane():
    with pytest.raises((ValidationError, ConsumerContractForbidden)):
        ApprovedGeometry(
            geometry_id="g1",
            source_candidate_id="c1",
            producer_lane="LANE_2_ATC_FIELD",  # type: ignore[arg-type]
            provenance=_prov(),
            confidence=_conf(),
            unknown_state=_unk(),
        )
    ok = ApprovedGeometry(
        geometry_id="g1",
        source_candidate_id="c1",
        producer_lane="LANE_1_CORE_PASSPORT",
        provenance=_prov(publication_context="not_for_passport"),
        confidence=_conf(),
        unknown_state=_unk(),
    )
    assert ok.is_atc_producer_output is False


# ── Compatibility validation ─────────────────────────────────────────────


def test_compatibility_accepts_geometry_candidate_fixture():
    cand = GeometryCandidate(
        candidate_id="geo-1",
        mission_id="m-4e",
        aircraft_profile_id="M4E_MAPPING",
        source_evidence_manifest_id="em-1",
        provenance=_prov(mission_id="m-4e", aircraft_profile_id="M4E_MAPPING"),
        confidence=_conf(),
        unknown_state=_unk(incomplete=True),
    )
    result = validate_compatibility(cand, expected_contract="GeometryCandidate")
    assert result.ok is True
    assert result.contract_version == "0.0.0"


def test_compatibility_flags_unknown_fields_and_missing_provenance():
    payload = {
        "meta": {"contract_name": "GeometryCandidate", "contract_version": "0.0.0"},
        "candidate_id": "x",
        "mission_id": "m",
        "aircraft_profile_id": "M4E_MAPPING",
        "source_evidence_manifest_id": "em",
        "approval_status": "CANDIDATE",
        "approved_because_from_4e": False,
        "is_production_approved": False,
        "rtk_accuracy_claimed": False,
        "extra_future_field": 1,
        "confidence": {"band": "unknown"},
        "unknown_state": {"incomplete": True},
    }
    warn = validate_compatibility(payload, expected_contract="GeometryCandidate")
    assert "extra_future_field" in warn.unknown_fields
    assert warn.ok is False  # missing provenance is an error
    assert any(i.code == "MISSING_PROVENANCE" for i in warn.errors)

    strict = validate_compatibility(
        {**payload, "provenance": {"source_type": "fixture", "source_id": "s1"}},
        expected_contract="GeometryCandidate",
        allow_unknown_fields=False,
    )
    assert any(i.code == "UNKNOWN_FIELDS" for i in strict.errors)


def test_compatibility_thermal_not_dimensions_and_geometry_not_thermal():
    thermal_bad = {
        "meta": {"contract_name": "AWEEvidenceCandidate", "contract_version": "0.0.0"},
        "candidate_id": "a1",
        "mission_id": "m",
        "aircraft_profile_id": "M4T_AWE",
        "source_evidence_manifest_id": "em",
        "is_dimensional_authority": True,
        "thermal_changes_dimensions": True,
        "automated_thermal_diagnosis": True,
        "provenance": {"source_type": "fixture", "source_id": "s"},
        "confidence": {"band": "low"},
        "unknown_state": {"incomplete": True},
    }
    r = validate_compatibility(thermal_bad, expected_contract="AWEEvidenceCandidate")
    assert r.ok is False
    codes = {i.code for i in r.errors}
    assert "THERMAL_DIMENSION_VIOLATION" in codes
    assert "THERMAL_DIAGNOSIS_VIOLATION" in codes

    geom_bad = {
        "meta": {"contract_name": "GeometryCandidate", "contract_version": "0.0.0"},
        "candidate_id": "g1",
        "mission_id": "m",
        "aircraft_profile_id": "M4E_MAPPING",
        "source_evidence_manifest_id": "em",
        "automated_thermal_diagnosis": True,
        "observations": [{"x": 1}],
        "provenance": {"source_type": "fixture", "source_id": "s"},
        "confidence": {"band": "low"},
        "unknown_state": {"incomplete": True},
    }
    g = validate_compatibility(geom_bad, expected_contract="GeometryCandidate")
    assert g.ok is False
    assert any(i.code == "THERMAL_ON_GEOMETRY" for i in g.errors)


def test_compatibility_rejects_unsupported_version():
    payload = {
        "meta": {"contract_name": "EvidenceManifest", "contract_version": "9.9.9"},
        "mission_id": "m",
        "mission_type": "DAYTIME_PRECISION_MAPPING",
        "aircraft_profile_id": "M4E_MAPPING",
        "package_hash": "sha256:x",
        "artifacts": [],
        "provenance": {"source_type": "fixture", "source_id": "s"},
        "confidence": {"band": "unknown"},
        "unknown_state": {"incomplete": True},
    }
    r = validate_compatibility(payload, expected_contract="EvidenceManifest")
    assert r.ok is False
    assert any(i.code == "UNSUPPORTED_VERSION" for i in r.errors)


# ── DJI parser foundation (synthetic) ───────────────────────────────────


@pytest.mark.parametrize(
    "profile_id",
    ["M4E_MAPPING", "M4T_AWE", "M400_P1_MAPPING", "M400_H30T_AWE"],
)
def test_synthetic_dji_parser_for_all_profiles(profile_id):
    parser = SyntheticDJIPackageParser()
    fixture = load_synthetic_fixture(profile_id)
    assert fixture["manifest"]["synthetic"] is True
    assert fixture["manifest"]["live_dji_sdk"] is False
    assert fixture["manifest"]["physical_capture_claimed"] is False

    manifest = parser.parse_manifest(profile_id)
    assert manifest.profile_id == profile_id
    assert manifest.synthetic is True
    assert manifest.live_dji_sdk is False
    assert manifest.physical_capture_claimed is False
    assert manifest.rtk_accuracy_claimed is False

    inventory = parser.inventory(profile_id)
    assert inventory.items
    checksums = parser.verify_checksums(inventory)
    assert checksums.ok is True

    warnings = parser.collect_warnings(manifest, inventory)
    codes = {w.code for w in warnings}
    assert WarningCode.SYNTHETIC_FIXTURE in codes
    assert WarningCode.NO_LIVE_DJI_SDK in codes
    assert WarningCode.NO_PHYSICAL_CAPTURE in codes


def test_rjpg_metadata_interface_synthetic_only():
    parser = SyntheticDJIPackageParser()
    meta = parser.extract_rjpg_metadata("M4T_AWE", "thermal-001")
    assert meta.radiometric is True
    assert meta.synthetic is True
    assert meta.automated_diagnosis is False


def test_pairing_and_checksum_mismatch_paths():
    parser = SyntheticDJIPackageParser()
    inv = parser.inventory("M4T_AWE")
    pairing = parser.pair_visual_thermal(inv)
    assert pairing.ok is True
    assert pairing.pairs

    # Force mismatch
    inv.items[0].sha256 = "sha256:deadbeef"
    # expected still from item after mutation — set diverge via expected map
    from nextgen.atc.dji.checksums import verify_checksums

    report = verify_checksums(
        inv,
        expected_by_artifact={inv.items[0].artifact_id: "sha256:" + "ab" * 32},
    )
    assert report.ok is False
    assert inv.items[0].artifact_id in report.mismatched


# ── Quality gates ────────────────────────────────────────────────────────


def test_quality_gate_enum_complete():
    values = {g.value for g in PackageQualityGate}
    assert values == {
        "READY_FOR_REVIEW",
        "USABLE_WITH_LIMITATIONS",
        "ADDITIONAL_CAPTURE_REQUIRED",
        "REJECTED_PACKAGE",
        "UNSUPPORTED_FORMAT",
    }


def test_quality_gate_evaluation_matrix():
    assert (
        evaluate_package_quality(
            profile_id="M4E_MAPPING",
            format_supported=False,
            checksums_ok=True,
            required_artifacts_present=True,
        ).gate
        == PackageQualityGate.UNSUPPORTED_FORMAT
    )
    assert (
        evaluate_package_quality(
            profile_id="M4E_MAPPING",
            format_supported=True,
            checksums_ok=False,
            required_artifacts_present=True,
        ).gate
        == PackageQualityGate.REJECTED_PACKAGE
    )
    assert (
        evaluate_package_quality(
            profile_id="M4T_AWE",
            format_supported=True,
            checksums_ok=True,
            required_artifacts_present=False,
        ).gate
        == PackageQualityGate.ADDITIONAL_CAPTURE_REQUIRED
    )
    assert (
        evaluate_package_quality(
            profile_id="M4E_MAPPING",
            format_supported=True,
            checksums_ok=True,
            required_artifacts_present=True,
            limitations=["partial_overlap_fixture"],
        ).gate
        == PackageQualityGate.USABLE_WITH_LIMITATIONS
    )
    assert (
        evaluate_package_quality(
            profile_id="M4E_MAPPING",
            format_supported=True,
            checksums_ok=True,
            required_artifacts_present=True,
        ).gate
        == PackageQualityGate.READY_FOR_REVIEW
    )


@pytest.mark.parametrize(
    "profile_id",
    ["M4E_MAPPING", "M4T_AWE", "M400_P1_MAPPING", "M400_H30T_AWE"],
)
def test_pipeline_assessment_ready_for_review(profile_id):
    assessment = assess_synthetic_package(profile_id)
    assert assessment.format_supported is True
    assert assessment.checksums_ok is True
    assert assessment.quality.gate == PackageQualityGate.READY_FOR_REVIEW
    assert assessment.quality.physical_capture_claimed is False
    assert assessment.quality.live_dji_sdk is False


def test_pipeline_with_limitations():
    assessment = assess_synthetic_package(
        "M4E_MAPPING",
        limitations=["fixture_coverage_incomplete"],
    )
    assert assessment.quality.gate == PackageQualityGate.USABLE_WITH_LIMITATIONS


# ── Docs + architecture guards ───────────────────────────────────────────


def test_contract_readiness_doc_exists():
    assert CONTRACT_READINESS.is_file()
    text = CONTRACT_READINESS.read_text(encoding="utf-8")
    assert "ATC-001B" in text
    assert "PROPOSED" in text
    assert "READY_FOR_FREEZE" in text
    assert "GeometryCandidate" in text
    assert "ApprovedGeometry" in text
    assert "AWEEvidenceCandidate" in text
    assert "ApprovedFinding" in text
    assert "Passport" in text
    assert "synthetic" in text.lower() or "Synthetic" in text
    assert "append_entry" in text or "Passport writer" in text


def test_migration_notes_file_exists():
    mig = SCHEMAS_ATC / "MIGRATION.md"
    assert mig.is_file()
    text = mig.read_text(encoding="utf-8")
    assert "GeometryCandidate" in text
    assert "do not silently rename" in text.lower() or "Do not silently rename" in text


def test_schemas_init_untouched_for_collision_safety():
    """Disclose collision risk: ATC-001B must not edit schemas/__init__.py."""
    text = SCHEMAS_INIT.read_text(encoding="utf-8")
    assert "schemas.atc" not in text
    assert "from .atc" not in text
    assert "AWEEvidenceCandidate" not in text
    assert "habitat" in text  # LANE_4 coexistence preserved


def test_architecture_guard_no_passport_writer_in_atc001b_modules():
    forbidden = (
        "passport_entries.insert_one",
        "await append_entry(",
        "await governed_publish(",
        "from ..passport_service import append_entry",
        "from .passport_service import append_entry",
        "from ..governed_publish_service import governed_publish",
        "from .governed_publish_service import governed_publish",
        "evaluate_approval_policy(",
        "is_production_approved=True",
        'approval_status="APPROVED"',
    )
    for path in ATC_MODULES:
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path} must not contain {needle}"


def test_evidence_profiles_mapping_complete():
    assert set(EVIDENCE_PROFILES) == set(PROFILE_IDS)
