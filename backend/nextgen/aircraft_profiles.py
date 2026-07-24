"""ATC-001A aircraft profile registry — contract foundation only.

Doctrine (encode, do not claim production flight authority):
- Matrice 4E: daytime precision mapping (primary dimensional capture path).
- Matrice 4T: nighttime AWE visual/thermal (condition evidence path).
- ATC validates both packages before Passport may accept either.
- 4T is NOT primary dimensional authority; thermal does NOT change dimensions.
- Geometry is NOT approved merely because it originated from a 4E package.
- Future profiles (registry stubs only): M400_P1_MAPPING, M400_H30T_AWE.

Law: PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.
This module does NOT claim a real DJI SDK, physical capture, RTK accuracy,
approved real geometry, automated thermal diagnosis, or production flight
authority. Passport publication remains LANE_1 only.
"""
from __future__ import annotations

from typing import Dict, List, Literal, TypedDict


AircraftRole = Literal[
    "daytime_precision_mapping",
    "nighttime_awe_visual_thermal",
]
DimensionalAuthority = Literal[
    "primary_dimensional_candidate",  # may produce geometry CANDIDATES only
    "not_dimensional_authority",      # thermal/visual condition evidence only
]
ProfileStatus = Literal[
    "ACTIVE_CONTRACT",   # in-scope for ATC-001A contract work
    "FUTURE_STUB",       # registered for forward compatibility; not executable yet
]


class AircraftProfile(TypedDict, total=False):
    profile_id: str
    display_name: str
    airframe: str
    payload: str
    role: AircraftRole
    mission_types: List[str]
    dimensional_authority: DimensionalAuthority
    thermal_changes_dimensions: bool
    produces_geometry_candidate: bool
    produces_awe_evidence_candidate: bool
    evidence_product_keys: List[str]
    status: ProfileStatus
    contract_status: str
    notes: str


# Official ATC-001A profiles + future stubs. No live device binding.
AIRCRAFT_PROFILES: Dict[str, AircraftProfile] = {
    "M4E_MAPPING": {
        "profile_id": "M4E_MAPPING",
        "display_name": "Matrice 4E — Daytime Precision Mapping",
        "airframe": "DJI Matrice 4E",
        "payload": "RGB mapping camera (contract profile; no live SDK claim)",
        "role": "daytime_precision_mapping",
        "mission_types": ["DAYTIME_PRECISION_MAPPING"],
        "dimensional_authority": "primary_dimensional_candidate",
        "thermal_changes_dimensions": False,
        "produces_geometry_candidate": True,
        "produces_awe_evidence_candidate": False,
        "evidence_product_keys": ["dayscan"],
        "status": "ACTIVE_CONTRACT",
        "contract_status": "PROPOSED",
        "notes": (
            "4E packages may yield ApprovedGeometry CANDIDATES only. "
            "Geometry is not approved merely because it came from 4E. "
            "ATC validation required before Passport acceptance."
        ),
    },
    "M4T_AWE": {
        "profile_id": "M4T_AWE",
        "display_name": "Matrice 4T — Nighttime AWE Visual/Thermal",
        "airframe": "DJI Matrice 4T",
        "payload": "Visual + radiometric thermal (contract profile; no live SDK claim)",
        "role": "nighttime_awe_visual_thermal",
        "mission_types": ["NIGHTTIME_AWE_VISUAL_THERMAL"],
        "dimensional_authority": "not_dimensional_authority",
        "thermal_changes_dimensions": False,
        "produces_geometry_candidate": False,
        "produces_awe_evidence_candidate": True,
        "evidence_product_keys": ["awe_scan"],
        "status": "ACTIVE_CONTRACT",
        "contract_status": "PROPOSED",
        "notes": (
            "4T is not primary dimensional authority. Thermal does not change "
            "dimensions. Produces AWE evidence CANDIDATES only — not automated "
            "thermal diagnosis and not Passport publication."
        ),
    },
    "M400_P1_MAPPING": {
        "profile_id": "M400_P1_MAPPING",
        "display_name": "Matrice 400 + P1 — Future Mapping",
        "airframe": "DJI Matrice 400",
        "payload": "P1 (future stub)",
        "role": "daytime_precision_mapping",
        "mission_types": ["DAYTIME_PRECISION_MAPPING"],
        "dimensional_authority": "primary_dimensional_candidate",
        "thermal_changes_dimensions": False,
        "produces_geometry_candidate": True,
        "produces_awe_evidence_candidate": False,
        "evidence_product_keys": ["dayscan"],
        "status": "FUTURE_STUB",
        "contract_status": "PROPOSED",
        "notes": "Future profile stub. Not executable in ATC-001A checkpoint.",
    },
    "M400_H30T_AWE": {
        "profile_id": "M400_H30T_AWE",
        "display_name": "Matrice 400 + H30T — Future AWE",
        "airframe": "DJI Matrice 400",
        "payload": "H30T (future stub)",
        "role": "nighttime_awe_visual_thermal",
        "mission_types": ["NIGHTTIME_AWE_VISUAL_THERMAL"],
        "dimensional_authority": "not_dimensional_authority",
        "thermal_changes_dimensions": False,
        "produces_geometry_candidate": False,
        "produces_awe_evidence_candidate": True,
        "evidence_product_keys": ["awe_scan"],
        "status": "FUTURE_STUB",
        "contract_status": "PROPOSED",
        "notes": "Future profile stub. Not executable in ATC-001A checkpoint.",
    },
}


ACTIVE_PROFILE_IDS = frozenset(
    pid for pid, p in AIRCRAFT_PROFILES.items() if p["status"] == "ACTIVE_CONTRACT"
)


def get_profile(profile_id: str) -> AircraftProfile:
    if profile_id not in AIRCRAFT_PROFILES:
        raise KeyError(f"Unknown aircraft profile: {profile_id}")
    return AIRCRAFT_PROFILES[profile_id]


def list_active_profiles() -> List[AircraftProfile]:
    return [AIRCRAFT_PROFILES[pid] for pid in sorted(ACTIVE_PROFILE_IDS)]


def asserts_not_dimensional_authority(profile_id: str) -> bool:
    """Return True when the profile must never assert dimensional approval."""
    profile = get_profile(profile_id)
    return profile["dimensional_authority"] == "not_dimensional_authority"


def thermal_may_change_dimensions(profile_id: str) -> bool:
    """Always False under ATC doctrine; exposed for explicit contract tests."""
    return bool(get_profile(profile_id).get("thermal_changes_dimensions", False))
