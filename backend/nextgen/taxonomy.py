"""NextGen canonical taxonomy — building systems, severity, risk, AWE, timeline.

Every enum lives here so downstream services, reports, and future AI agents
read from ONE source of truth. Do not scatter these strings across route
files.
"""
from __future__ import annotations

from typing import Dict, List


# ── Building system taxonomy (Directive 007) ─────────────────────────────
# Structured as { category → components }. `category` is the top-level
# system a homeowner or contractor recognizes; `component` is the specific
# element an inspector observes.
BUILDING_SYSTEMS: Dict[str, List[str]] = {
    "ROOF": [
        "ROOF_DECK", "UNDERLAYMENT", "SHINGLES", "METAL_ROOFING", "TILE_ROOFING",
        "FLAT_MEMBRANE", "FLASHING", "VALLEYS", "RIDGES", "DRIP_EDGE",
        "PENETRATIONS", "SKYLIGHTS", "VENTS",
    ],
    "DRAINAGE": ["GUTTERS", "DOWNSPOUTS", "SPLASH_BLOCKS", "GRADING", "FRENCH_DRAIN"],
    "FASCIA_SOFFIT": ["FASCIA", "SOFFIT", "VENTED_SOFFIT"],
    "EXTERIOR_WALLS": [
        "SIDING_VINYL", "SIDING_FIBER_CEMENT", "SIDING_WOOD", "BRICK", "STONE",
        "STUCCO", "EIFS", "PAINT_FINISH",
    ],
    "OPENINGS": ["WINDOWS", "DOORS", "GARAGE_DOOR", "STORM_DOOR", "SKYLIGHT_SEAL"],
    "FOUNDATION": ["FOUNDATION_WALL", "SLAB", "CRAWLSPACE", "BASEMENT_WALL", "PIER"],
    "CHIMNEY": ["CHIMNEY_CROWN", "CHIMNEY_CAP", "CHIMNEY_FLASHING", "MASONRY", "LINER"],
    "SOLAR": ["PANELS", "RACKING", "INVERTER_EXT", "SOLAR_PENETRATIONS"],
    "HVAC_EXTERIOR": ["CONDENSER", "HEAT_PUMP", "MINI_SPLIT", "PACKAGED_UNIT"],
    "VENTILATION": ["RIDGE_VENT", "SOFFIT_VENT", "GABLE_VENT", "BATH_VENT_EXHAUST"],
    "INSULATION_EXTERIOR": ["ATTIC_ACCESS", "WALL_INSULATION_EXTERIOR"],
    "ELECTRICAL_EXTERIOR": ["SERVICE_ENTRANCE", "METER", "EXTERIOR_OUTLETS", "EXTERIOR_LIGHTING"],
    "PLUMBING_EXTERIOR": ["HOSE_BIBBS", "IRRIGATION_VALVE", "SEWER_CLEANOUT"],
    "LANDSCAPING": ["TREE_CANOPY", "OVERGROWTH", "TREE_LIMB_RISK"],
    "ACCESSORY_STRUCTURES": ["DETACHED_GARAGE", "SHED", "ADU", "DECK", "PATIO", "FENCE"],
    "GARAGE": ["GARAGE_DOOR", "GARAGE_ROOF", "GARAGE_SIDING"],
    "ATTIC_INTERIOR": ["ATTIC_MOISTURE", "ATTIC_INSULATION", "ATTIC_VENTILATION"],
    "OTHER": ["OTHER"],
}


def flatten_taxonomy() -> List[Dict[str, str]]:
    out = []
    for system, comps in BUILDING_SYSTEMS.items():
        for c in comps:
            out.append({"system": system, "component": c})
    return out


# ── Severity, risk, priority, remaining life ─────────────────────────────
SEVERITY = ["INFORMATIONAL", "MINOR", "MODERATE", "MAJOR", "CRITICAL"]
PRIORITY = ["MONITOR", "SCHEDULE", "IMPORTANT", "URGENT", "IMMEDIATE"]
RISK_LEVEL = ["LOW", "ELEVATED", "HIGH", "SEVERE"]

# ── Risk tier drives QA authority (Blueprint §10) ────────────────────────
RISK_TIER = [
    "tier_1_automated_informational",
    "tier_2_contractor_review",
    "tier_3_high_consequence_non_engineering",
    "tier_4_engineering_controlled",
]


def tier_for_severity(severity: str) -> str:
    return {
        "INFORMATIONAL": "tier_1_automated_informational",
        "MINOR": "tier_2_contractor_review",
        "MODERATE": "tier_2_contractor_review",
        "MAJOR": "tier_3_high_consequence_non_engineering",
        "CRITICAL": "tier_3_high_consequence_non_engineering",
    }.get(severity, "tier_2_contractor_review")


def allowed_reviewer_roles_for_tier(tier: str) -> List[str]:
    """Roles authorized to approve at each tier (Phase 2B config).

    Tier 4 requires an engineer license — reviewers must have
    `user_attributes.engineer_license_active = true`. That check happens in
    the review endpoint.
    """
    return {
        "tier_1_automated_informational": ["admin", "ceo", "contractor", "inspector",
                                             "tier2_qa", "tier3_qa", "engineer_reviewer"],
        "tier_2_contractor_review": ["admin", "ceo", "contractor", "inspector",
                                       "tier2_qa", "tier3_qa", "engineer_reviewer"],
        "tier_3_high_consequence_non_engineering": ["admin", "ceo", "tier3_qa",
                                                       "engineer_reviewer"],
        "tier_4_engineering_controlled": ["engineer_reviewer"],
    }.get(tier, ["admin", "ceo"])


# ── AWE categories ───────────────────────────────────────────────────────
# Every intelligence object must classify AWE impact even if zero.
AWE_CATEGORIES = ["AIR", "WATER", "ENERGY"]


# ── Timeline entry kinds (Directive 007 "Property Timeline") ─────────────
TIMELINE_KINDS = [
    "INSPECTION",
    "INTELLIGENCE_APPROVED",
    "REPAIR",
    "MAINTENANCE",
    "REPLACEMENT",
    "STORM_EVENT",
    "WARRANTY",
    "INSURANCE_CLAIM",
    "ENERGY_UPGRADE",
    "CONTRACTOR_QUOTE",
    "PASSPORT_APPEND",
    "HABITAT_ACTION",
]


# ── Passport entry types (Blueprint §11.3) ───────────────────────────────
PASSPORT_ENTRY_TYPES = [
    "INTELLIGENCE_APPROVED",
    "INSPECTION_DELTA",
    "SUPERSEDE_FINDING",
    "IDENTITY_LINK",
    "IDENTITY_UNLINK",
    "IDENTITY_MERGE",
    "IDENTITY_SPLIT",
    "ADDRESS_CORRECTION",
    "PARCEL_CORRECTION",
    "OWNERSHIP_TRANSFER",
    "COSIGN",
    "HABITAT_ACK",
    "LEGAL_HOLD",
]


# ── Report templates (projections, not sources of truth) ─────────────────
REPORT_TEMPLATES = [
    "contractor_full", "homeowner_summary", "insurance_claim",
    "hoa_summary", "energy_focused", "executive_summary", "property_health",
]


# ── Projection visibility scopes (per PIO) ───────────────────────────────
VISIBILITY_SCOPES = ["contractor", "homeowner", "adjuster", "insurer",
                      "internal", "public"]
