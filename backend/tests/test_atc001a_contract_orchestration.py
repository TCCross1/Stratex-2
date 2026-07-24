"""ATC-001A contract orchestration — deterministic fixture tests + architecture guards.

Checkpoint: mission/evidence contract foundation only.
Does not claim DJI SDK, physical capture, RTK accuracy, approved geometry,
automated thermal diagnosis, or production flight authority.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from nextgen.aircraft_profiles import (
    ACTIVE_PROFILE_IDS,
    AIRCRAFT_PROFILES,
    asserts_not_dimensional_authority,
    get_profile,
    thermal_may_change_dimensions,
)
from nextgen.mission_state_machine import (
    STATE_CAPTURE_PACKAGE_ASSEMBLED,
    STATE_EVIDENCE_MANIFEST_READY,
    STATE_GEOMETRY_CANDIDATE_READY,
    STATE_PREFLIGHT_PASSED,
    STATE_PREFLIGHT_PENDING,
    STATE_READY_FOR_PASSPORT_HANDOFF,
    AuthorityViolation,
    IllegalTransition,
    MissionOrchestration,
    can_passport_accept_either,
    validate_pair_for_handoff,
)
from nextgen.schemas import (
    ApprovedGeometryCandidate,
    AweEvidenceCandidate,
    CapturePackageManifest,
    Confidence,
    EvidenceArtifactRef,
    EvidenceManifest,
    MissionTypeContract,
    PreflightCheckItem,
    PreflightResult,
    Provenance,
    ThermalObservationRef,
    UnknownState,
)


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CONTRACTS = ROOT / "engineering" / "contracts"
SCHEMAS = CONTRACTS / "schemas"
REGISTRY = CONTRACTS / "registry.yaml"
MISSION_RECORD = ROOT / "engineering" / "px001" / "missions" / "LANE_2_ATC001A.md"

ATC_MODULES = [
    BACKEND / "nextgen" / "aircraft_profiles.py",
    BACKEND / "nextgen" / "mission_state_machine.py",
    BACKEND / "nextgen" / "schemas" / "evidence_manifest.py",
    BACKEND / "nextgen" / "schemas" / "approved_geometry_candidate.py",
    BACKEND / "nextgen" / "schemas" / "awe_evidence_candidate.py",
    BACKEND / "nextgen" / "schemas" / "preflight.py",
]


def _prov(**kwargs) -> Provenance:
    base = dict(
        source_type="contract_fixture",
        source_id="atc001a-fixture",
        publication_context="contract_fixture",
    )
    base.update(kwargs)
    return Provenance(**base)


def _conf(**kwargs) -> Confidence:
    return Confidence(**kwargs)


def _unk(**kwargs) -> UnknownState:
    return UnknownState(**kwargs)


# ── Aircraft profile registry ───────────────────────────────────────────


def test_aircraft_profiles_encode_doctrine():
    m4e = get_profile("M4E_MAPPING")
    m4t = get_profile("M4T_AWE")
    assert m4e["role"] == "daytime_precision_mapping"
    assert m4t["role"] == "nighttime_awe_visual_thermal"
    assert m4e["dimensional_authority"] == "primary_dimensional_candidate"
    assert asserts_not_dimensional_authority("M4T_AWE")
    assert thermal_may_change_dimensions("M4T_AWE") is False
    assert thermal_may_change_dimensions("M4E_MAPPING") is False
    assert m4e["contract_status"] == "PROPOSED"
    assert m4t["contract_status"] == "PROPOSED"
    # Future stubs present but not active
    assert "M400_P1_MAPPING" in AIRCRAFT_PROFILES
    assert "M400_H30T_AWE" in AIRCRAFT_PROFILES
    assert AIRCRAFT_PROFILES["M400_P1_MAPPING"]["status"] == "FUTURE_STUB"
    assert ACTIVE_PROFILE_IDS == frozenset({"M4E_MAPPING", "M4T_AWE"})


# ── Mission type + EvidenceManifest ─────────────────────────────────────


def test_mission_type_contracts_4e_and_4t():
    mapping = MissionTypeContract(
        mission_type="DAYTIME_PRECISION_MAPPING",
        aircraft_profile_id="M4E_MAPPING",
        evidence_product_key="dayscan",
        dimensional_role="primary_dimensional_candidate",
        thermal_changes_dimensions=False,
        requires_paired_mission_type="NIGHTTIME_AWE_VISUAL_THERMAL",
        provenance=_prov(mission_id="m-4e", aircraft_profile_id="M4E_MAPPING"),
        confidence=_conf(band="medium", rationale="fixture mission-type binding"),
        unknown_state=_unk(incomplete=True, notes="pairing pending"),
    )
    awe = MissionTypeContract(
        mission_type="NIGHTTIME_AWE_VISUAL_THERMAL",
        aircraft_profile_id="M4T_AWE",
        evidence_product_key="awe_scan",
        dimensional_role="not_dimensional_authority",
        thermal_changes_dimensions=False,
        requires_paired_mission_type="DAYTIME_PRECISION_MAPPING",
        provenance=_prov(mission_id="m-4t", aircraft_profile_id="M4T_AWE"),
        confidence=_conf(band="medium", rationale="fixture mission-type binding"),
        unknown_state=_unk(incomplete=True, notes="pairing pending"),
    )
    assert mapping.meta.lifecycle_status == "PROPOSED"
    assert awe.dimensional_role == "not_dimensional_authority"


def test_mission_type_rejects_4t_as_dimensional_authority():
    with pytest.raises(ValidationError):
        MissionTypeContract(
            mission_type="NIGHTTIME_AWE_VISUAL_THERMAL",
            aircraft_profile_id="M4T_AWE",
            evidence_product_key="awe_scan",
            dimensional_role="primary_dimensional_candidate",
            provenance=_prov(),
            confidence=_conf(),
            unknown_state=_unk(),
        )


def test_evidence_manifest_fixture_completeness():
    artifacts = [
        EvidenceArtifactRef(
            artifact_id="rgb-1",
            category="RGB_IMAGE",
            relative_path="rgb/001.jpg",
            required=True,
            present=True,
        ),
        EvidenceArtifactRef(
            artifact_id="flog",
            category="FLIGHT_LOG",
            relative_path="logs/flight.json",
            required=True,
            present=True,
        ),
    ]
    manifest = EvidenceManifest(
        mission_id="m-4e",
        mission_type="DAYTIME_PRECISION_MAPPING",
        aircraft_profile_id="M4E_MAPPING",
        package_hash="sha256:fixturedeadbeef01",
        artifacts=artifacts,
        provenance=_prov(
            mission_id="m-4e",
            aircraft_profile_id="M4E_MAPPING",
            package_hash="sha256:fixturedeadbeef01",
        ),
        confidence=_conf(band="low", rationale="fixture completeness only"),
        unknown_state=_unk(incomplete=True),
    )
    assert manifest.recompute_completeness() is True
    assert manifest.passport_accepted is False
    assert manifest.atc_validation_status == "NOT_VALIDATED"
    assert manifest.meta.lifecycle_status in {"PROPOSED", "READY_FOR_FREEZE"}


def test_evidence_manifest_tracks_missing_without_fabricating():
    manifest = EvidenceManifest(
        mission_id="m-gap",
        mission_type="NIGHTTIME_AWE_VISUAL_THERMAL",
        aircraft_profile_id="M4T_AWE",
        package_hash="sha256:fixturedeadbeef02",
        artifacts=[
            EvidenceArtifactRef(
                artifact_id="thermal-1",
                category="THERMAL_RADIOMETRIC",
                relative_path="thermal/001.rjpg",
                required=True,
                present=False,
            )
        ],
        provenance=_prov(mission_id="m-gap"),
        confidence=_conf(),
        unknown_state=_unk(),
    )
    assert manifest.recompute_completeness() is False
    assert "thermal-1" in manifest.unknown_state.missing_artifacts


# ── Geometry + AWE candidates ───────────────────────────────────────────


def test_approved_geometry_candidate_only():
    cand = ApprovedGeometryCandidate(
        candidate_id="geo-cand-1",
        mission_id="m-4e",
        aircraft_profile_id="M4E_MAPPING",
        source_evidence_manifest_id="em-4e",
        approval_status="CANDIDATE",
        approved_because_from_4e=False,
        is_production_approved=False,
        rtk_accuracy_claimed=False,
        control_points_unknown=["cp-north", "cp-south"],
        provenance=_prov(mission_id="m-4e", aircraft_profile_id="M4E_MAPPING"),
        confidence=_conf(band="unknown", rationale="candidate only"),
        unknown_state=_unk(
            incomplete=True,
            unresolved_surfaces=["east_elevation"],
            notes="not approved merely because from 4E",
        ),
    )
    assert cand.approval_status == "CANDIDATE"
    assert cand.is_production_approved is False


def test_geometry_rejects_production_approval_flags():
    with pytest.raises(ValidationError):
        ApprovedGeometryCandidate(
            candidate_id="bad",
            mission_id="m",
            source_evidence_manifest_id="em",
            approved_because_from_4e=True,  # type: ignore[arg-type]
            provenance=_prov(),
            confidence=_conf(),
            unknown_state=_unk(),
        )


def test_awe_evidence_candidate_doctrine():
    awe = AweEvidenceCandidate(
        candidate_id="awe-cand-1",
        mission_id="m-4t",
        aircraft_profile_id="M4T_AWE",
        source_evidence_manifest_id="em-4t",
        observations=[
            ThermalObservationRef(
                observation_id="obs-1",
                artifact_id="thermal-1",
                label="fixture_region",
                delta_c_fixture=4.2,
                automated_diagnosis=False,
            )
        ],
        provenance=_prov(mission_id="m-4t", aircraft_profile_id="M4T_AWE"),
        confidence=_conf(band="low"),
        unknown_state=_unk(incomplete=True, notes="no automated diagnosis"),
    )
    assert awe.is_dimensional_authority is False
    assert awe.thermal_changes_dimensions is False
    assert awe.automated_thermal_diagnosis is False


# ── Preflight + capture package ─────────────────────────────────────────


def test_preflight_and_capture_package_fixtures():
    pre = PreflightResult(
        mission_id="m-4e",
        aircraft_profile_id="M4E_MAPPING",
        overall="passed",
        checks=[
            PreflightCheckItem(
                check_id="pf-battery",
                label="Battery threshold (fixture)",
                severity="hard",
                result="pass",
            ),
            PreflightCheckItem(
                check_id="pf-airspace",
                label="Airspace record present (fixture)",
                severity="hard",
                result="pass",
            ),
        ],
        real_device_exercised=False,
        production_flight_authority=False,
        dji_sdk_invoked=False,
        provenance=_prov(mission_id="m-4e"),
        confidence=_conf(band="medium", rationale="deterministic fixture gate"),
        unknown_state=_unk(incomplete=False, notes="fixture preflight only"),
    )
    assert pre.overall == "passed"

    pkg = CapturePackageManifest(
        package_id="pkg-4e-1",
        mission_id="m-4e",
        aircraft_profile_id="M4E_MAPPING",
        mission_type="DAYTIME_PRECISION_MAPPING",
        package_hash="sha256:fixturedeadbeef01",
        files=[],
        assembled_from_fixture=True,
        physical_capture_claimed=False,
        provenance=_prov(mission_id="m-4e", package_hash="sha256:fixturedeadbeef01"),
        confidence=_conf(),
        unknown_state=_unk(incomplete=True, missing_artifacts=["live_capture"]),
    )
    assert pkg.physical_capture_claimed is False


def test_preflight_rejects_hard_fail_with_passed_overall():
    with pytest.raises(ValidationError):
        PreflightResult(
            mission_id="m",
            aircraft_profile_id="M4E_MAPPING",
            overall="passed",
            checks=[
                PreflightCheckItem(
                    check_id="x",
                    label="x",
                    severity="hard",
                    result="fail",
                )
            ],
            provenance=_prov(),
            confidence=_conf(),
            unknown_state=_unk(),
        )


# ── Mission state machine ───────────────────────────────────────────────


def _advance_to_evidence(mission: MissionOrchestration, profile: str, mtype: str) -> None:
    mission.select_profile(profile, mtype)
    mission.transition(STATE_PREFLIGHT_PENDING)
    mission.transition(STATE_PREFLIGHT_PASSED)
    mission.transition(STATE_CAPTURE_PACKAGE_ASSEMBLED)
    mission.transition(STATE_EVIDENCE_MANIFEST_READY)


def test_mission_state_machine_happy_path_pair_gate():
    m4e = MissionOrchestration(mission_id="m-4e")
    m4t = MissionOrchestration(mission_id="m-4t")
    _advance_to_evidence(m4e, "M4E_MAPPING", "DAYTIME_PRECISION_MAPPING")
    _advance_to_evidence(m4t, "M4T_AWE", "NIGHTTIME_AWE_VISUAL_THERMAL")

    assert can_passport_accept_either(m4e, m4t) is False

    m4e.mark_candidate_ready("geometry")
    m4t.mark_candidate_ready("awe")
    assert m4e.state == STATE_GEOMETRY_CANDIDATE_READY
    assert can_passport_accept_either(m4e, m4t) is False  # ATC not yet validated both

    pair = validate_pair_for_handoff(m4e, m4t)
    assert pair.state == STATE_READY_FOR_PASSPORT_HANDOFF
    assert m4e.atc_validated_4e and m4t.atc_validated_4t
    assert m4e.state == STATE_READY_FOR_PASSPORT_HANDOFF
    assert can_passport_accept_either(m4e, m4t) is True


def test_illegal_transition_and_authority_guards():
    m = MissionOrchestration(mission_id="m1")
    with pytest.raises(IllegalTransition):
        m.transition(STATE_PREFLIGHT_PASSED)
    with pytest.raises(AuthorityViolation):
        m.claim_approved_geometry()
    with pytest.raises(AuthorityViolation):
        m.write_passport()


def test_passport_cannot_accept_one_side_only():
    m4e = MissionOrchestration(mission_id="m-4e")
    m4t = MissionOrchestration(mission_id="m-4t")
    _advance_to_evidence(m4e, "M4E_MAPPING", "DAYTIME_PRECISION_MAPPING")
    _advance_to_evidence(m4t, "M4T_AWE", "NIGHTTIME_AWE_VISUAL_THERMAL")
    m4e.mark_candidate_ready("geometry")
    m4e.atc_validated_4e = True
    # 4T not ready / not validated
    assert can_passport_accept_either(m4e, m4t) is False


# ── Architecture guards ─────────────────────────────────────────────────


def test_architecture_guard_no_passport_writer_in_atc_modules():
    forbidden = (
        "passport_entries.insert_one",
        "await append_entry(",
        "await governed_publish(",
        "from ..passport_service import append_entry",
        "from .passport_service import append_entry",
        "from ..governed_publish_service import governed_publish",
        "from .governed_publish_service import governed_publish",
    )
    for path in ATC_MODULES:
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            assert needle not in text, f"{path.name} must not contain {needle}"


def test_architecture_guard_no_fabricated_approved_geometry_claims():
    for path in ATC_MODULES:
        text = path.read_text(encoding="utf-8")
        # Soft-ban production approval claims in ATC contract modules
        assert "is_production_approved=True" not in text
        assert 'approval_status="APPROVED"' not in text
        assert "approval_status='APPROVED'" not in text
    # Doctrine comments present
    profiles = (BACKEND / "nextgen" / "aircraft_profiles.py").read_text(encoding="utf-8")
    assert "thermal does NOT change dimensions" in profiles or "thermal does not change" in profiles.lower()
    assert "not approved merely because" in profiles.lower()


def test_json_schema_files_exist_and_forbid_frozen():
    expected = [
        "evidence_manifest.schema.json",
        "approved_geometry_candidate.schema.json",
        "awe_evidence_candidate.schema.json",
        "mission_type.schema.json",
        "preflight_result.schema.json",
        "capture_package_manifest.schema.json",
    ]
    for name in expected:
        path = SCHEMAS / name
        assert path.is_file(), name
        blob = path.read_text(encoding="utf-8")
        assert "FROZEN" not in blob or '"FROZEN"' not in blob
        assert "PROPOSED" in blob or "READY_FOR_FREEZE" in blob


def test_registry_keeps_proposed_and_points_at_schemas():
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    by_name = {c["name"]: c for c in data["contracts"]}
    for name in ("EvidenceManifest", "ApprovedGeometry"):
        c = by_name[name]
        assert c["status"] == "PROPOSED"
        assert c["status"] not in {"FROZEN", "ACCEPTED", "PRODUCTION"}
        assert c.get("schema_location") or c.get("schema_notes")
        if c.get("schema_location"):
            loc = ROOT / c["schema_location"]
            assert loc.exists(), c["schema_location"]
    # Global readiness unchanged
    assert data["production_readiness"] == "NOT_READY"


def test_mission_record_exists():
    assert MISSION_RECORD.is_file()
    text = MISSION_RECORD.read_text(encoding="utf-8")
    assert "ATC-001A" in text
    assert "LANE_2_ATC_FIELD" in text
    assert "PROPOSED" in text
    assert "Passport" in text
    assert "Matrice 4E" in text
    assert "Matrice 4T" in text
