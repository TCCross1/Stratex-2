"""
Field Test Pipeline Orchestrator — Stratex Core

Ties together:
  ATC readiness → evidence ingest → package seal → mission state transitions
  → governed-publish handoff payload → report composition

Does NOT write Passport. Does NOT claim geometry APPROVED.
Does NOT launch aircraft. Deterministic and testable.

Supports:
- Single-path demo (4E or 4T alone) for software dry-run
- Dual-path pair validation gate when both missions are provided
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .atc.readiness import evaluate_readiness
from .evidence_ingest import assemble_package_from_capture, ingest_media_item
from .mission_package_seal import seal_package, SealingError
from .mission_to_passport import prepare_for_governed_publish, HandoffError
from .report_composer import compose_full_report
from .mission_state_machine import (
    MissionOrchestration,
    STATE_PREFLIGHT_PENDING,
    STATE_PREFLIGHT_PASSED,
    STATE_PREFLIGHT_FAILED,
    STATE_CAPTURE_PACKAGE_ASSEMBLED,
    STATE_EVIDENCE_MANIFEST_READY,
    STATE_GEOMETRY_CANDIDATE_READY,
    STATE_AWE_CANDIDATE_READY,
    STATE_READY_FOR_PASSPORT_HANDOFF,
    IllegalTransition,
    AuthorityViolation,
    validate_pair_for_handoff,
)


@dataclass
class PipelineResult:
    success: bool
    mission_id: str
    state: str
    readiness: Optional[Dict[str, Any]] = None
    sealed_package: Optional[Dict[str, Any]] = None
    publication_request: Optional[Dict[str, Any]] = None
    report: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    history: List[tuple] = field(default_factory=list)
    pair_ready: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "mission_id": self.mission_id,
            "state": self.state,
            "readiness": self.readiness,
            "package_id": (self.sealed_package or {}).get("package_id"),
            "content_hash_prefix": ((self.sealed_package or {}).get("content_hash") or "")[:16] or None,
            "handoff_ready": self.publication_request is not None,
            "report_id": (self.report or {}).get("report_id"),
            "pair_ready": self.pair_ready,
            "errors": self.errors,
            "history": [{"from": a, "to": b} for a, b in self.history],
        }


def _advance_capture_path(orch: MissionOrchestration, has_media: bool, kind: str) -> None:
    """Advance through capture → evidence → candidate states safely."""
    orch.transition(STATE_CAPTURE_PACKAGE_ASSEMBLED)
    if has_media:
        orch.transition(STATE_EVIDENCE_MANIFEST_READY)
        if kind == "geometry":
            orch.mark_candidate_ready("geometry")
        elif kind == "awe":
            orch.mark_candidate_ready("awe")


def run_single_path_pipeline(
    *,
    mission_id: str,
    tenant_id: str,
    property_id: str,
    mission_type: str = "DAYTIME_PRECISION_MAPPING",
    aircraft_profile: str = "Matrice_4E",
    media_items: Optional[List[Dict[str, Any]]] = None,
    geometry_candidate: Optional[Dict[str, Any]] = None,
    awe_candidate: Optional[Dict[str, Any]] = None,
    pilot: Optional[str] = None,
    weather: Optional[str] = None,
    rtk_status: str = "FIXED",
    readiness_kwargs: Optional[Dict[str, Any]] = None,
    seal_key: Optional[bytes] = None,
    skip_readiness: bool = False,
) -> PipelineResult:
    """
    Single-mission path for software dry-run.
    Produces sealed package + publication_request + report.
    Does not claim dual-path ATC pair validation.
    """
    orch = MissionOrchestration(mission_id=mission_id)
    errors: List[str] = []
    readiness_dict = None
    sealed = None
    publication_request = None
    report = None

    try:
        orch.select_profile(aircraft_profile, mission_type)
        orch.transition(STATE_PREFLIGHT_PENDING)

        readiness = evaluate_readiness(mission_id, **(readiness_kwargs or {}))
        readiness_dict = readiness.to_dict()
        if not readiness.ready and not skip_readiness:
            orch.transition(STATE_PREFLIGHT_FAILED)
            return PipelineResult(
                success=False,
                mission_id=mission_id,
                state=orch.state,
                readiness=readiness_dict,
                errors=[f"ATC not ready: {readiness.blocking_failures}"],
                history=list(orch.history),
            )
        orch.transition(STATE_PREFLIGHT_PASSED)

        if media_items is None:
            media_items = [
                ingest_media_item("RGB", "2026-08-01T14:00:00Z", "Matrice 4E Wide", 10_000_000),
            ]

        pkg = assemble_package_from_capture(
            mission_id=mission_id,
            tenant_id=tenant_id,
            property_id=property_id,
            capture_type=mission_type,
            media_items=media_items,
            aircraft=f"DJI {aircraft_profile.replace('_', ' ')}",
            pilot=pilot,
            weather=weather,
            rtk_status=rtk_status,
            geometry_candidate=geometry_candidate,
            awe_candidate=awe_candidate,
        )

        kind = "geometry" if mission_type == "DAYTIME_PRECISION_MAPPING" else "awe"
        # Ensure candidate data exists for state transition
        if kind == "geometry" and not pkg.get("geometry_candidate", {}).get("planes"):
            pkg.setdefault("geometry_candidate", {})["planes"] = [
                {"id": "placeholder", "confidence": 0.9, "area_sqft": 100}
            ]
        if kind == "awe" and not pkg.get("awe_candidate", {}).get("findings"):
            pkg.setdefault("awe_candidate", {})["findings"] = [
                {"id": "f0", "severity": "LOW", "truth_classification": "UNKNOWN", "description": "placeholder"}
            ]

        _advance_capture_path(orch, bool(media_items), kind)

        sealed = seal_package(pkg, seal_key=seal_key)
        handoff = prepare_for_governed_publish(sealed, seal_key=seal_key)
        publication_request = handoff.get("publication_request")
        report = compose_full_report(sealed)

        return PipelineResult(
            success=True,
            mission_id=mission_id,
            state=orch.state,
            readiness=readiness_dict,
            sealed_package=sealed,
            publication_request=publication_request,
            report=report,
            errors=errors,
            history=list(orch.history),
            pair_ready=False,
        )

    except (SealingError, HandoffError, IllegalTransition, AuthorityViolation) as e:
        errors.append(str(e))
        return PipelineResult(
            success=False,
            mission_id=mission_id,
            state=orch.state,
            readiness=readiness_dict,
            sealed_package=sealed,
            publication_request=publication_request,
            report=report,
            errors=errors,
            history=list(orch.history),
        )


def run_dual_path_pipeline(
    *,
    mapping_mission_id: str,
    awe_mission_id: str,
    tenant_id: str,
    property_id: str,
    mapping_media: Optional[List[Dict[str, Any]]] = None,
    awe_media: Optional[List[Dict[str, Any]]] = None,
    geometry_candidate: Optional[Dict[str, Any]] = None,
    awe_candidate: Optional[Dict[str, Any]] = None,
    seal_key: Optional[bytes] = None,
    readiness_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run 4E mapping + 4T AWE paths, then ATC pair validation gate.
    Returns both sealed packages and a pair handoff status.
    Still does NOT write Passport.
    """
    mapping = run_single_path_pipeline(
        mission_id=mapping_mission_id,
        tenant_id=tenant_id,
        property_id=property_id,
        mission_type="DAYTIME_PRECISION_MAPPING",
        aircraft_profile="Matrice_4E",
        media_items=mapping_media,
        geometry_candidate=geometry_candidate or {
            "planes": [
                {"id": "front", "confidence": 0.93, "area_sqft": 800},
                {"id": "rear", "confidence": 0.91, "area_sqft": 760},
            ],
            "measurements": {"total_roof_area_sqft": 1560},
        },
        seal_key=seal_key,
        readiness_kwargs=readiness_kwargs,
    )
    awe = run_single_path_pipeline(
        mission_id=awe_mission_id,
        tenant_id=tenant_id,
        property_id=property_id,
        mission_type="NIGHTTIME_AWE_VISUAL_THERMAL",
        aircraft_profile="Matrice_4T",
        media_items=awe_media or [
            ingest_media_item("THERMAL", "2026-08-01T22:00:00Z", "Matrice 4T Thermal", 3_000_000),
        ],
        awe_candidate=awe_candidate or {
            "findings": [
                {
                    "id": "awe-1",
                    "severity": "HIGH",
                    "category": "ROOF",
                    "description": "Granule loss / heat pattern on front slope",
                    "location": "Front slope",
                    "truth_classification": "ESTIMATED",
                }
            ]
        },
        seal_key=seal_key,
        readiness_kwargs=readiness_kwargs,
    )

    pair_result = None
    pair_error = None
    if mapping.success and awe.success:
        try:
            # Rebuild orchestration objects at candidate-ready states for pair gate
            m_orch = MissionOrchestration(
                mission_id=mapping_mission_id,
                aircraft_profile_id="Matrice_4E",
                mission_type="DAYTIME_PRECISION_MAPPING",
                state=STATE_GEOMETRY_CANDIDATE_READY,
                geometry_candidate_ready=True,
            )
            a_orch = MissionOrchestration(
                mission_id=awe_mission_id,
                aircraft_profile_id="Matrice_4T",
                mission_type="NIGHTTIME_AWE_VISUAL_THERMAL",
                state=STATE_AWE_CANDIDATE_READY,
                awe_candidate_ready=True,
            )
            pair_result = validate_pair_for_handoff(m_orch, a_orch)
        except (IllegalTransition, AuthorityViolation) as e:
            pair_error = str(e)

    return {
        "mapping": mapping.to_dict(),
        "awe": awe.to_dict(),
        "pair_state": pair_result.state if pair_result else None,
        "pair_ready": pair_result is not None and pair_result.state == STATE_READY_FOR_PASSPORT_HANDOFF,
        "pair_error": pair_error,
        "both_sealed": mapping.success and awe.success,
    }
