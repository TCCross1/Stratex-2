"""Evidence producer/consumer boundary for ATC aircraft profiles.

Profiles in scope:
- M4E_MAPPING
- M4T_AWE
- M400_P1_MAPPING
- M400_H30T_AWE

Producers emit candidates only. Consumers of approved contracts sit outside
ATC. This module encodes the boundary; it does not approve or publish.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, Mapping, Optional

from .authority import AuthorityViolation, refuse_approved_emission


PROFILE_IDS: FrozenSet[str] = frozenset(
    {
        "M4E_MAPPING",
        "M4T_AWE",
        "M400_P1_MAPPING",
        "M400_H30T_AWE",
    }
)


class ProducerOutputKind(str, Enum):
    GEOMETRY_CANDIDATE = "GeometryCandidate"
    AWE_EVIDENCE_CANDIDATE = "AWEEvidenceCandidate"
    EVIDENCE_MANIFEST = "EvidenceManifest"


class ConsumerKind(str, Enum):
    """Downstream consumers — ATC produces candidates; these consume approved forms."""

    ESTIMATOR = "estimator"  # expects ApprovedGeometry, not GeometryCandidate
    PASSPORT = "passport"  # expects ApprovedGeometry / ApprovedFinding
    HABITAT = "habitat"  # expects approved projections / findings
    ATC_PAIR_GATE = "atc_pair_gate"  # may consume candidates for pairing only


@dataclass(frozen=True)
class ProfileBoundarySpec:
    profile_id: str
    role: str
    producer_outputs: FrozenSet[ProducerOutputKind]
    may_claim_dimensions: bool
    may_claim_thermal_diagnosis: bool
    dimensional_authority: str
    consumer_approved_contracts: FrozenSet[str]
    notes: str


EVIDENCE_PROFILES: Mapping[str, ProfileBoundarySpec] = {
    "M4E_MAPPING": ProfileBoundarySpec(
        profile_id="M4E_MAPPING",
        role="daytime_precision_mapping",
        producer_outputs=frozenset(
            {
                ProducerOutputKind.GEOMETRY_CANDIDATE,
                ProducerOutputKind.EVIDENCE_MANIFEST,
            }
        ),
        may_claim_dimensions=False,  # candidates only — not approved dimensions
        may_claim_thermal_diagnosis=False,
        dimensional_authority="primary_dimensional_candidate",
        consumer_approved_contracts=frozenset({"ApprovedGeometry"}),
        notes=(
            "Produces GeometryCandidate only. Geometry is not approved merely "
            "because from 4E. Consumers require ApprovedGeometry via non-ATC authority."
        ),
    ),
    "M4T_AWE": ProfileBoundarySpec(
        profile_id="M4T_AWE",
        role="nighttime_awe_visual_thermal",
        producer_outputs=frozenset(
            {
                ProducerOutputKind.AWE_EVIDENCE_CANDIDATE,
                ProducerOutputKind.EVIDENCE_MANIFEST,
            }
        ),
        may_claim_dimensions=False,
        may_claim_thermal_diagnosis=False,
        dimensional_authority="not_dimensional_authority",
        consumer_approved_contracts=frozenset({"ApprovedFinding"}),
        notes=(
            "Produces AWEEvidenceCandidate only. Not dimensional authority; "
            "thermal does not change dimensions; no automated thermal diagnosis."
        ),
    ),
    "M400_P1_MAPPING": ProfileBoundarySpec(
        profile_id="M400_P1_MAPPING",
        role="daytime_precision_mapping",
        producer_outputs=frozenset(
            {
                ProducerOutputKind.GEOMETRY_CANDIDATE,
                ProducerOutputKind.EVIDENCE_MANIFEST,
            }
        ),
        may_claim_dimensions=False,
        may_claim_thermal_diagnosis=False,
        dimensional_authority="primary_dimensional_candidate",
        consumer_approved_contracts=frozenset({"ApprovedGeometry"}),
        notes="Future mapping profile — same producer/consumer boundary as M4E_MAPPING.",
    ),
    "M400_H30T_AWE": ProfileBoundarySpec(
        profile_id="M400_H30T_AWE",
        role="nighttime_awe_visual_thermal",
        producer_outputs=frozenset(
            {
                ProducerOutputKind.AWE_EVIDENCE_CANDIDATE,
                ProducerOutputKind.EVIDENCE_MANIFEST,
            }
        ),
        may_claim_dimensions=False,
        may_claim_thermal_diagnosis=False,
        dimensional_authority="not_dimensional_authority",
        consumer_approved_contracts=frozenset({"ApprovedFinding"}),
        notes="Future AWE profile — same producer/consumer boundary as M4T_AWE.",
    ),
}


# What each consumer kind is allowed to accept from ATC vs must obtain elsewhere.
_CONSUMER_ACCEPTS: Dict[ConsumerKind, FrozenSet[str]] = {
    ConsumerKind.ATC_PAIR_GATE: frozenset(
        {
            "GeometryCandidate",
            "ApprovedGeometryCandidate",
            "AWEEvidenceCandidate",
            "AweEvidenceCandidate",
            "EvidenceManifest",
        }
    ),
    ConsumerKind.ESTIMATOR: frozenset({"ApprovedGeometry"}),
    ConsumerKind.PASSPORT: frozenset({"ApprovedGeometry", "ApprovedFinding"}),
    ConsumerKind.HABITAT: frozenset({"ApprovedFinding", "ApprovedGeometry"}),
}


class EvidenceBoundary:
    """Executable producer/consumer boundary for one aircraft profile."""

    def __init__(self, profile_id: str) -> None:
        if profile_id not in EVIDENCE_PROFILES:
            raise KeyError(f"Unknown evidence profile for ATC-001B boundary: {profile_id}")
        self.spec = EVIDENCE_PROFILES[profile_id]

    @property
    def profile_id(self) -> str:
        return self.spec.profile_id

    def may_produce(self, kind: ProducerOutputKind) -> bool:
        return kind in self.spec.producer_outputs

    def assert_may_produce(self, kind: ProducerOutputKind) -> None:
        if not self.may_produce(kind):
            raise AuthorityViolation(
                f"Profile {self.profile_id} must not produce {kind.value}"
            )

    def consumer_may_accept(self, consumer: ConsumerKind, contract_name: str) -> bool:
        allowed = _CONSUMER_ACCEPTS[consumer]
        return contract_name in allowed

    def assert_consumer_accepts(self, consumer: ConsumerKind, contract_name: str) -> None:
        if not self.consumer_may_accept(consumer, contract_name):
            raise AuthorityViolation(
                f"Consumer {consumer.value} must not accept {contract_name} "
                f"from ATC producer path for {self.profile_id}"
            )

    def emit_approved_geometry(self) -> None:
        refuse_approved_emission("ApprovedGeometry")

    def emit_approved_finding(self) -> None:
        refuse_approved_emission("ApprovedFinding")

    def doctrine_flags(self) -> Dict[str, bool]:
        return {
            "may_claim_dimensions": self.spec.may_claim_dimensions,
            "may_claim_thermal_diagnosis": self.spec.may_claim_thermal_diagnosis,
            "thermal_changes_dimensions": False,
            "geometry_implies_approval": False,
            "is_passport_writer": False,
        }


def boundary_for(profile_id: str) -> EvidenceBoundary:
    return EvidenceBoundary(profile_id)


def all_boundaries() -> Dict[str, EvidenceBoundary]:
    return {pid: EvidenceBoundary(pid) for pid in sorted(PROFILE_IDS)}
