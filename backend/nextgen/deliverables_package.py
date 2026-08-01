"""
Contractor Deliverables Package — Field Test v1

Bundles the outputs a contractor needs after a successful field-test path:
- Sealed package summary
- Property Intelligence Report (structured)
- Materials takeoff
- HTML report (contractor + optional homeowner-safe)
- Publication request ready for governed publish

Does not write Passport.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .field_test_pipeline import run_single_path_pipeline, run_dual_path_pipeline
from .report_composer import compose_full_report
from .report_html import render_report_html
from .materials_takeoff import takeoff_from_geometry, labor_estimate_from_squares


def build_contractor_deliverables(
    *,
    mission_id: str,
    tenant_id: str,
    property_id: str,
    mission_type: str = "DAYTIME_PRECISION_MAPPING",
    aircraft_profile: str = "Matrice_4E",
    geometry_candidate: Optional[Dict[str, Any]] = None,
    awe_candidate: Optional[Dict[str, Any]] = None,
    media_items: Optional[list] = None,
    seal_key: Optional[bytes] = None,
    readiness_kwargs: Optional[Dict[str, Any]] = None,
    include_homeowner_html: bool = True,
) -> Dict[str, Any]:
    """
    Run single-path pipeline and package contractor-facing deliverables.
    """
    result = run_single_path_pipeline(
        mission_id=mission_id,
        tenant_id=tenant_id,
        property_id=property_id,
        mission_type=mission_type,
        aircraft_profile=aircraft_profile,
        media_items=media_items,
        geometry_candidate=geometry_candidate,
        awe_candidate=awe_candidate,
        seal_key=seal_key,
        readiness_kwargs=readiness_kwargs or {"battery_pct": 90.0},
    )

    if not result.success:
        return {
            "status": "FAILED",
            "errors": result.errors,
            "pipeline": result.to_dict(),
        }

    sealed = result.sealed_package or {}
    report = result.report or compose_full_report(sealed)
    geometry = sealed.get("geometry_candidate") or {}
    takeoff = takeoff_from_geometry(geometry)
    labor = labor_estimate_from_squares(
        (takeoff.get("basis") or {}).get("squares_with_waste") or 0
    )

    contractor_html = render_report_html(report, homeowner_safe=False)
    homeowner_html = (
        render_report_html(report, homeowner_safe=True) if include_homeowner_html else None
    )

    return {
        "status": "READY",
        "mission_id": mission_id,
        "property_id": property_id,
        "package_id": sealed.get("package_id"),
        "content_hash": sealed.get("content_hash"),
        "pipeline_state": result.state,
        "publication_request": result.publication_request,
        "report": report,
        "materials_takeoff": takeoff,
        "labor_estimate": labor,
        "html": {
            "contractor": contractor_html,
            "homeowner_safe": homeowner_html,
        },
        "next_step": "Submit publication_request via governed_publish_service (single writer path).",
        "authority": {
            "habitat_role": "read-only after projection",
            "passport_writer": "nextgen.passport_service.append_entry",
            "governed_publisher": "nextgen.governed_publish_service",
        },
    }


def build_dual_path_deliverables(
    *,
    mapping_mission_id: str,
    awe_mission_id: str,
    tenant_id: str,
    property_id: str,
    geometry_candidate: Optional[Dict[str, Any]] = None,
    awe_candidate: Optional[Dict[str, Any]] = None,
    seal_key: Optional[bytes] = None,
) -> Dict[str, Any]:
    """Dual 4E+4T path with pair gate status + mapping-side deliverables."""
    dual = run_dual_path_pipeline(
        mapping_mission_id=mapping_mission_id,
        awe_mission_id=awe_mission_id,
        tenant_id=tenant_id,
        property_id=property_id,
        geometry_candidate=geometry_candidate,
        awe_candidate=awe_candidate,
        seal_key=seal_key,
    )
    mapping_deliverables = None
    if dual.get("both_sealed"):
        # Re-run mapping path for full report package
        mapping_deliverables = build_contractor_deliverables(
            mission_id=mapping_mission_id,
            tenant_id=tenant_id,
            property_id=property_id,
            mission_type="DAYTIME_PRECISION_MAPPING",
            aircraft_profile="Matrice_4E",
            geometry_candidate=geometry_candidate,
            awe_candidate=awe_candidate,
            seal_key=seal_key,
        )
    return {
        "status": "READY" if dual.get("pair_ready") else "PARTIAL",
        "dual": dual,
        "mapping_deliverables": mapping_deliverables,
        "pair_ready_for_passport_handoff": dual.get("pair_ready", False),
    }
