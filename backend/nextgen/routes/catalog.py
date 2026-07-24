"""NextGen catalog & session endpoints — Blueprint v1.2 §16.

Ships the three approved products (DayScan™, AWE™ Scan, Elite™) and the
minimal session/health probes required by the Phase 1a shell.
Placeholder commercial figures — final pricing set by executive review.
"""
from __future__ import annotations

from fastapi import Depends

from ..auth import NxSession, nx_session
from ._router import nextgen_r


PRODUCTS = [
    {
        "product_key": "dayscan",
        "display_name": "Stratex Core DayScan™",
        "version": "1.0",
        "capture_conditions": {
            "time_of_day": "daylight",
            "min_solar_angle_deg": 15,
            "max_wind_mph": 20,
            "min_visibility_mi": 3,
        },
        "sensor_requirements": ["rgb", "gps_rtk"],
        "processing_engines": [
            "PhotogrammetryProvider", "MeasurementProvider",
            "VisionProvider", "SegmentationProvider",
        ],
        "human_qa_tier": "tier_2_contractor_review",
        "report_template": "dayscan_v1",
        "contractor_price_cents": 24900,
        "internal_cost_estimate_cents": 8900,
        "rescan_rules": {
            "free_rescan_window_days": 14,
            "conditions": ["insufficient_evidence", "environmental_failure"],
        },
        "failed_mission_policy": {
            "environmental": "free_rescan",
            "operator": "partial_refund",
            "hardware": "free_rescan",
        },
        "habitat_entitlement": [
            "property_snapshot", "roof_measurements", "maintenance_priorities",
        ],
    },
    {
        "product_key": "awe_scan",
        "display_name": "Stratex AWE™ Scan",
        "version": "1.0",
        "capture_conditions": {
            "time_of_day": "night",
            "min_env_temp_delta_c": 5.5,
            "max_wind_mph": 12,
            "min_visibility_mi": 3,
        },
        "sensor_requirements": [
            "radiometric_thermal", "reference_rgb", "env_sensors",
        ],
        "processing_engines": [
            "ThermalAnalysisProvider", "CalibrationProvider",
            "MeasurementProvider", "RuleEngine",
        ],
        "human_qa_tier": "tier_3_high_consequence_non_engineering",
        "report_template": "awe_v1",
        "contractor_price_cents": 39900,
        "internal_cost_estimate_cents": 14900,
        "rescan_rules": {
            "free_rescan_window_days": 14,
            "conditions": [
                "env_delta_failure", "registration_failure",
                "insufficient_evidence",
            ],
        },
        "failed_mission_policy": {
            "env_delta_failure": "free_rescan",
            "operator": "partial_refund",
            "hardware": "free_rescan",
        },
        "habitat_entitlement": [
            "awe_findings", "energy_indicators",
            "moisture_indicators", "air_indicators",
        ],
    },
    {
        "product_key": "elite",
        "display_name": "Stratex Elite™ Property Intelligence",
        "version": "1.0",
        "capture_conditions": {
            "requires_missions": ["dayscan", "awe_scan"],
            "same_property_identity": True,
        },
        "sensor_requirements": [
            "rgb", "gps_rtk", "radiometric_thermal",
            "reference_rgb", "env_sensors",
        ],
        "processing_engines": [
            "PhotogrammetryProvider", "MeasurementProvider",
            "VisionProvider", "SegmentationProvider",
            "ThermalAnalysisProvider", "CalibrationProvider",
            "RuleEngine",
        ],
        "human_qa_tier": "tier_3_high_consequence_non_engineering",
        "report_template": "elite_v1",
        "contractor_price_cents": 59900,
        "internal_cost_estimate_cents": 22900,
        "rescan_rules": {
            "free_rescan_window_days": 14,
            "conditions": [
                "insufficient_evidence", "environmental_failure",
                "registration_failure", "contradiction_unresolvable",
            ],
        },
        "failed_mission_policy": {
            "environmental": "free_rescan",
            "operator": "partial_refund",
            "hardware": "free_rescan",
        },
        "habitat_entitlement": [
            "property_snapshot", "roof_measurements", "maintenance_priorities",
            "awe_findings", "energy_indicators", "moisture_indicators",
            "air_indicators", "cross_evidence_findings",
            "awe_composite_index",
        ],
    },
]


def _product_by_key(key: str):
    for p in PRODUCTS:
        if p["product_key"] == key:
            return p
    return None


@nextgen_r.get("/health")
async def nextgen_health():
    from ..passport_indexes import get_index_readiness

    readiness = get_index_readiness()
    passport_ready = readiness.get("state") == "READY"
    return {
        "status": "ok" if passport_ready else "degraded",
        "phase": "1a",
        "passport_indexes": {
            "state": readiness.get("state"),
            "checked_at": readiness.get("checked_at"),
            "failed_index": readiness.get("failed_index"),
            "error_classification": readiness.get("error_classification"),
            "critical_failed": readiness.get("critical_failed"),
            # Safe metadata only — no credentials or connection strings.
        },
        "authorized_scope": [
            "phase_1a_legacy_freeze_and_foundation",
            "phase_1b_application_shell",
            "phase_1c_workspaces",
            "phase_1d_integrated_review_build",
        ],
        "requires_executive_approval": [
            "deploy_to_stratexdrone_com",
            "destructive_migration",
            "legacy_deletion",
            "passport_authority_change",
            "new_recurring_vendor_expense_gt_250usd_mo",
            "publish_unvalidated_claims",
        ],
    }


@nextgen_r.get("/catalog/products")
async def list_products():
    return {"products": PRODUCTS}


@nextgen_r.get("/me")
async def me(session: NxSession = Depends(nx_session)):
    return {
        "user_id": session.user_id,
        "email": session.user.get("email"),
        "legal_name": session.user.get("legal_name"),
        "role": session.role,
        "tenant": session.tenant,
    }
