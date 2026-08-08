"""API: Habitat dashboard projection, openings, AWE twin layers (mockup-locked).

Read-only field-test surface. Passport owns official ledger writes and claim codes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from habitat_ui.openings import demo_openings_for_property
from habitat_ui.awe_twin import (
    build_dashboard_projection,
    habitat_dashboard_projection_stub,
    twin_layer_set,
    awe_findings_on_twin,
)
from habitat_ui.projection_loader import load_projection_from_env
from habitat_ui.hydrate_from_contract import (
    dashboard_from_contract,
    openings_ui_from_contract,
)

logger = logging.getLogger("habitat.ui.routes")

router = APIRouter(prefix="/habitat", tags=["habitat-ui"])


def _dashboard_from_file_or_build(
    tenant_id: str,
    property_id: str,
    stub_only: bool,
) -> Dict[str, Any]:
    """Prefer HABITAT_PROJECTION_PATH JSON; else Passport adapter / demo stub."""
    if stub_only:
        return habitat_dashboard_projection_stub()

    file_proj = load_projection_from_env()
    if file_proj is not None:
        try:
            dash = dashboard_from_contract(file_proj)
            dash["source"] = "HABITAT_PROJECTION_PATH"
            dash["habitat_role"] = "read-only"
            # Preserve contract authoritative bit (official vs preview)
            dash["authoritative"] = bool(file_proj.get("authoritative"))
            dash["passport_status"] = (
                "OK" if dash["authoritative"] else "PROJECTED"
            )
            logger.info(
                "dashboard/projection served from HABITAT_PROJECTION_PATH "
                "authoritative=%s property_id=%s",
                dash["authoritative"],
                file_proj.get("property_id"),
            )
            return dash
        except Exception as exc:
            logger.exception(
                "Failed hydrating HABITAT_PROJECTION_PATH; falling back: %s",
                exc,
            )

    return build_dashboard_projection(tenant_id, property_id)


@router.get("/dashboard/projection")
def dashboard_projection(
    tenant_id: str = Query("demo"),
    property_id: str = Query("demo-property"),
    stub_only: bool = Query(False),
):
    """
    Passport-shaped projection for Habitat dashboard (JSON).
    Tries HABITAT_PROJECTION_PATH, then Passport adapter merge, else demo stub.
    """
    return _dashboard_from_file_or_build(tenant_id, property_id, stub_only)


@router.get("/twin/layers")
def layers():
    return {"layers": twin_layer_set()}


@router.get("/twin/awe-hotspots")
def awe_hotspots():
    return {"hotspots": awe_findings_on_twin(), "brand": "AWE™"}


@router.get("/openings")
def list_openings():
    file_proj = load_projection_from_env()
    if file_proj is not None and "openings" in file_proj:
        try:
            return {
                "openings": openings_ui_from_contract(file_proj.get("openings") or []),
                "source": "HABITAT_PROJECTION_PATH",
                "authoritative": bool(file_proj.get("authoritative")),
            }
        except Exception as exc:
            logger.exception(
                "Failed openings from HABITAT_PROJECTION_PATH; demo fallback: %s",
                exc,
            )
    return {"openings": demo_openings_for_property()}


@router.get("/openings/{opening_id}")
def get_opening(opening_id: str):
    items = list_openings().get("openings") or []
    for o in items:
        if o["id"] == opening_id:
            return o
    return items[0] if items else {"error": "not_found"}


@router.get("/projection/contract")
def projection_contract():
    """Field-ready Passport→Habitat contract schema for Core publishers."""
    from habitat_ui.projection_contract import (
        empty_field_ready_projection,
        validate_projection,
        CONTRACT_ID,
        CONTRACT_VERSION,
    )

    sample = empty_field_ready_projection("example")
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "sample": sample,
        "validation_example": validate_projection(sample),
    }


@router.get("/projection/from_sample_mission")
def projection_from_sample_mission():
    """
    Field-test: build habitat.projection.v1-shaped dashboard using the same
    rules Core will use after seal (local sample geometry/AWE/openings).
    Does not call Core; mirrors export_habitat_projection defaults.
    """
    from habitat_ui.projection_contract import empty_field_ready_projection

    # Local mirror of Core sample export (no cross-repo import at runtime)
    sample = empty_field_ready_projection("prop-field-test-ky")
    sample["authoritative"] = False
    sample["property_identity"] = {
        "address_line": "1234 Appalachian Way",
        "city_state_zip": "London, KY 40741",
        "geo": None,
    }
    sample["scores"] = {
        "certified_score": 87,
        "score_scale": 1000,
        "awe_index": 82,
        "property_score": 87,
        "roof_condition": 68,
        "energy_score": 71,
        "moisture_score": 70,
    }
    sample["home_health"] = {
        "overall": 72,
        "systems": {
            "structure": 76,
            "roofing": 68,
            "hvac": 74,
            "plumbing": 71,
            "electrical": 78,
            "exterior": 69,
        },
    }
    sample["awe"] = {
        "index": 82,
        "brand": "AWE™",
        "hotspots": [
            {
                "id": "awe-attic-heat",
                "title": "Attic heat loss",
                "domain": "energy",
                "severity": "high",
                "summary": "Elevated thermal signature at ridge / attic plane.",
                "report_ref": "awe/energy/attic-heat",
                "truth": "ESTIMATED",
            }
        ],
    }
    sample["twin"] = {
        "mesh_ref": None,
        "layers": ["finish", "thermal", "moisture", "framing", "energy", "openings", "awe"],
        "plane_count": 4,
        "withheld_plane_count": 1,
        "measurements": {
            "total_roof_area_sqft": 2015,
            "pitch_primary": "6/12",
        },
    }
    sample["openings"] = [
        {
            "id": "win-front-lr",
            "kind": "window",
            "label": "Front — Living Room Picture",
            "elevation": "front",
            "unit_w_in": 72,
            "unit_h_in": 48,
            "rough_w_in": 74,
            "rough_h_in": 50.5,
            "material": "vinyl",
            "condition": "fair",
            "truth": "ESTIMATED",
        },
        {
            "id": "door-front",
            "kind": "door",
            "label": "Front Entry",
            "elevation": "front",
            "unit_w_in": 36,
            "unit_h_in": 80,
            "rough_w_in": 38,
            "rough_h_in": 82.5,
            "material": "fiberglass",
            "condition": "good",
            "truth": "ESTIMATED",
        },
    ]
    sample["maintenance"] = {
        "next_12_months_usd": 2840,
        "actions": [{"title": "Attic heat loss", "severity": "high"}],
    }
    dash = dashboard_from_contract(sample)
    return {
        "dashboard": dash,
        "openings": openings_ui_from_contract(sample["openings"]),
        "contract": sample,
    }


class ClaimRedeemRequest(BaseModel):
    """Read-only claim lookup. Habitat does not mint codes or write Passport."""

    claim_code: str = Field(..., min_length=1, description="Homeowner claim code")
    email: Optional[str] = Field(None, description="Optional claimant email for lookup")


@router.post("/v1/claim/redeem")
def claim_redeem(body: ClaimRedeemRequest):
    """
    Minimal read-only claim redeem stub for field-test handoff.

    - Does NOT mint claim codes
    - Does NOT write Passport / official ledger
    - Does NOT call Core publish
    - Lookup only: match against HABITAT_PROJECTION_PATH property when present
    """
    code = (body.claim_code or "").strip()
    logger.info(
        "claim/redeem read-only lookup code_len=%s email_present=%s",
        len(code),
        bool(body.email),
    )

    file_proj = load_projection_from_env()
    property_identity: Optional[Dict[str, Any]] = None
    property_id: Optional[str] = None
    authoritative = False
    matched = False

    if file_proj is not None:
        property_id = file_proj.get("property_id")
        property_identity = file_proj.get("property_identity")
        authoritative = bool(file_proj.get("authoritative"))
        # Stub match: any non-empty code resolves to the loaded projection property
        matched = bool(code)
        logger.info(
            "claim/redeem matched=%s property_id=%s authoritative=%s (file projection)",
            matched,
            property_id,
            authoritative,
        )
    else:
        logger.info(
            "claim/redeem no HABITAT_PROJECTION_PATH; returning lookup-unavailable stub"
        )

    return {
        "ok": True,
        "mode": "lookup",
        "habitat_role": "read-only",
        "minted": False,
        "ledger_write": False,
        "core_publish": False,
        "matched": matched,
        "claim_code": code,
        "email": body.email,
        "authoritative": authoritative,
        "property_id": property_id,
        "property_identity": property_identity,
        "message": (
            "Read-only claim lookup. Passport owns official claim codes and ledger writes; "
            "Habitat never mints codes or publishes to Core."
        ),
    }
