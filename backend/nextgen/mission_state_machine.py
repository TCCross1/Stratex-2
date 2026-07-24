"""ATC-001A deterministic mission orchestration state machine.

No real device, no DJI SDK, no production flight authority.
Transitions are pure and fixture-driven for contract tests.

Doctrine gates encoded here:
- ATC must validate BOTH 4E mapping and 4T AWE evidence paths before
  either package is considered eligible for Passport acceptance handoff.
- This machine NEVER writes Passport, NEVER marks geometry APPROVED,
  and NEVER claims physical capture occurred.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# Deterministic ATC orchestration states (contract layer; not live ops).
ATCMissionState = str

STATE_DRAFT = "DRAFT"
STATE_PROFILE_SELECTED = "PROFILE_SELECTED"
STATE_PREFLIGHT_PENDING = "PREFLIGHT_PENDING"
STATE_PREFLIGHT_FAILED = "PREFLIGHT_FAILED"
STATE_PREFLIGHT_PASSED = "PREFLIGHT_PASSED"
STATE_CAPTURE_PACKAGE_ASSEMBLED = "CAPTURE_PACKAGE_ASSEMBLED"
STATE_EVIDENCE_MANIFEST_READY = "EVIDENCE_MANIFEST_READY"
STATE_GEOMETRY_CANDIDATE_READY = "GEOMETRY_CANDIDATE_READY"
STATE_AWE_CANDIDATE_READY = "AWE_CANDIDATE_READY"
STATE_ATC_PAIR_VALIDATED = "ATC_PAIR_VALIDATED"
STATE_READY_FOR_PASSPORT_HANDOFF = "READY_FOR_PASSPORT_HANDOFF"
STATE_BLOCKED = "BLOCKED"
STATE_CANCELED = "CANCELED"
STATE_FAILED = "FAILED"

ALL_STATES: FrozenSet[str] = frozenset(
    {
        STATE_DRAFT,
        STATE_PROFILE_SELECTED,
        STATE_PREFLIGHT_PENDING,
        STATE_PREFLIGHT_FAILED,
        STATE_PREFLIGHT_PASSED,
        STATE_CAPTURE_PACKAGE_ASSEMBLED,
        STATE_EVIDENCE_MANIFEST_READY,
        STATE_GEOMETRY_CANDIDATE_READY,
        STATE_AWE_CANDIDATE_READY,
        STATE_ATC_PAIR_VALIDATED,
        STATE_READY_FOR_PASSPORT_HANDOFF,
        STATE_BLOCKED,
        STATE_CANCELED,
        STATE_FAILED,
    }
)

# Allowed directed edges. Terminal-ish failure/cancel edges from most active states.
_BASE_TRANSITIONS: Dict[str, Set[str]] = {
    STATE_DRAFT: {STATE_PROFILE_SELECTED, STATE_CANCELED},
    STATE_PROFILE_SELECTED: {STATE_PREFLIGHT_PENDING, STATE_CANCELED, STATE_BLOCKED},
    STATE_PREFLIGHT_PENDING: {
        STATE_PREFLIGHT_PASSED,
        STATE_PREFLIGHT_FAILED,
        STATE_CANCELED,
        STATE_BLOCKED,
    },
    STATE_PREFLIGHT_FAILED: {STATE_PREFLIGHT_PENDING, STATE_CANCELED, STATE_FAILED},
    STATE_PREFLIGHT_PASSED: {
        STATE_CAPTURE_PACKAGE_ASSEMBLED,
        STATE_CANCELED,
        STATE_BLOCKED,
    },
    STATE_CAPTURE_PACKAGE_ASSEMBLED: {
        STATE_EVIDENCE_MANIFEST_READY,
        STATE_CANCELED,
        STATE_FAILED,
    },
    STATE_EVIDENCE_MANIFEST_READY: {
        STATE_GEOMETRY_CANDIDATE_READY,
        STATE_AWE_CANDIDATE_READY,
        STATE_BLOCKED,
        STATE_FAILED,
    },
    # Single-mission candidate readiness; pairing is a separate orchestration record.
    STATE_GEOMETRY_CANDIDATE_READY: {
        STATE_ATC_PAIR_VALIDATED,
        STATE_BLOCKED,
        STATE_FAILED,
    },
    STATE_AWE_CANDIDATE_READY: {
        STATE_ATC_PAIR_VALIDATED,
        STATE_BLOCKED,
        STATE_FAILED,
    },
    STATE_ATC_PAIR_VALIDATED: {
        STATE_READY_FOR_PASSPORT_HANDOFF,
        STATE_BLOCKED,
    },
    STATE_READY_FOR_PASSPORT_HANDOFF: {STATE_BLOCKED},
    STATE_BLOCKED: {STATE_CANCELED, STATE_FAILED},
    STATE_CANCELED: set(),
    STATE_FAILED: set(),
}


class IllegalTransition(ValueError):
    """Raised when a transition is not allowed by the deterministic table."""


class AuthorityViolation(RuntimeError):
    """Raised when code attempts Passport write or fabricated approval claims."""


@dataclass
class MissionOrchestration:
    """In-memory ATC mission record for deterministic contract tests."""

    mission_id: str
    aircraft_profile_id: Optional[str] = None
    mission_type: Optional[str] = None
    state: str = STATE_DRAFT
    paired_mission_id: Optional[str] = None
    geometry_candidate_ready: bool = False
    awe_candidate_ready: bool = False
    atc_validated_4e: bool = False
    atc_validated_4t: bool = False
    history: List[Tuple[str, str]] = field(default_factory=list)

    def transition(self, to_state: str) -> None:
        if to_state not in ALL_STATES:
            raise IllegalTransition(f"Unknown state: {to_state}")
        allowed = _BASE_TRANSITIONS.get(self.state, set())
        if to_state not in allowed:
            raise IllegalTransition(
                f"Illegal transition {self.state} -> {to_state}"
            )
        self.history.append((self.state, to_state))
        self.state = to_state

    def select_profile(self, profile_id: str, mission_type: str) -> None:
        if self.state != STATE_DRAFT:
            raise IllegalTransition("select_profile only from DRAFT")
        self.aircraft_profile_id = profile_id
        self.mission_type = mission_type
        self.transition(STATE_PROFILE_SELECTED)

    def mark_candidate_ready(self, kind: str) -> None:
        """Mark geometry or AWE candidate ready — never APPROVED."""
        if kind == "geometry":
            if self.state != STATE_EVIDENCE_MANIFEST_READY:
                raise IllegalTransition(
                    "geometry candidate requires EVIDENCE_MANIFEST_READY"
                )
            self.geometry_candidate_ready = True
            self.transition(STATE_GEOMETRY_CANDIDATE_READY)
        elif kind == "awe":
            if self.state != STATE_EVIDENCE_MANIFEST_READY:
                raise IllegalTransition(
                    "awe candidate requires EVIDENCE_MANIFEST_READY"
                )
            self.awe_candidate_ready = True
            self.transition(STATE_AWE_CANDIDATE_READY)
        else:
            raise ValueError(f"Unknown candidate kind: {kind}")

    def claim_approved_geometry(self) -> None:
        """Hard guard — ATC-001A must never fabricate approved geometry."""
        raise AuthorityViolation(
            "ATC-001A produces ApprovedGeometry CANDIDATES only; "
            "geometry is not approved merely because it came from 4E"
        )

    def write_passport(self) -> None:
        """Hard guard — Passport publication is LANE_1 only."""
        raise AuthorityViolation(
            "ATC lane must not write Passport; handoff only after ATC pair validation"
        )


def can_passport_accept_either(
    mapping_mission: MissionOrchestration,
    awe_mission: MissionOrchestration,
) -> bool:
    """Passport may accept either package only after ATC validates BOTH.

    This function does not publish; it only encodes the acceptance gate.
    """
    if not (
        mapping_mission.atc_validated_4e
        and awe_mission.atc_validated_4t
        and mapping_mission.geometry_candidate_ready
        and awe_mission.awe_candidate_ready
    ):
        return False
    return (
        mapping_mission.state in {
            STATE_ATC_PAIR_VALIDATED,
            STATE_READY_FOR_PASSPORT_HANDOFF,
            STATE_GEOMETRY_CANDIDATE_READY,
        }
        and awe_mission.state in {
            STATE_ATC_PAIR_VALIDATED,
            STATE_READY_FOR_PASSPORT_HANDOFF,
            STATE_AWE_CANDIDATE_READY,
        }
    )


def validate_pair_for_handoff(
    mapping_mission: MissionOrchestration,
    awe_mission: MissionOrchestration,
) -> MissionOrchestration:
    """Mark both missions ATC-validated and advance to pair-validated handoff gate.

    Returns a synthetic orchestration record representing the pair gate.
    Does NOT call Passport writers.
    """
    if mapping_mission.mission_type != "DAYTIME_PRECISION_MAPPING":
        raise IllegalTransition("mapping mission must be DAYTIME_PRECISION_MAPPING")
    if awe_mission.mission_type != "NIGHTTIME_AWE_VISUAL_THERMAL":
        raise IllegalTransition("awe mission must be NIGHTTIME_AWE_VISUAL_THERMAL")
    if not mapping_mission.geometry_candidate_ready:
        raise IllegalTransition("4E geometry candidate not ready")
    if not awe_mission.awe_candidate_ready:
        raise IllegalTransition("4T AWE candidate not ready")

    mapping_mission.atc_validated_4e = True
    awe_mission.atc_validated_4t = True
    mapping_mission.paired_mission_id = awe_mission.mission_id
    awe_mission.paired_mission_id = mapping_mission.mission_id

    if mapping_mission.state == STATE_GEOMETRY_CANDIDATE_READY:
        mapping_mission.transition(STATE_ATC_PAIR_VALIDATED)
    if awe_mission.state == STATE_AWE_CANDIDATE_READY:
        awe_mission.transition(STATE_ATC_PAIR_VALIDATED)

    mapping_mission.transition(STATE_READY_FOR_PASSPORT_HANDOFF)
    awe_mission.transition(STATE_READY_FOR_PASSPORT_HANDOFF)

    return MissionOrchestration(
        mission_id=f"pair:{mapping_mission.mission_id}+{awe_mission.mission_id}",
        state=STATE_READY_FOR_PASSPORT_HANDOFF,
        paired_mission_id=mapping_mission.mission_id,
        geometry_candidate_ready=True,
        awe_candidate_ready=True,
        atc_validated_4e=True,
        atc_validated_4t=True,
    )


def allowed_transitions(state: str) -> Set[str]:
    return set(_BASE_TRANSITIONS.get(state, set()))
