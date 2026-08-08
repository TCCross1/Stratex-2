"""
AWE (Air · Water · Energy) overlays and report cards bound to the Habitat twin.
Dashboard projection merges Passport adapter output when available, else demo stub
matching approved mockups (Appalachian Way field-test shape).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def awe_index_card(
    score: int,
    label: str = "Good",
    air: Optional[int] = None,
    water: Optional[int] = None,
    energy: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "awe_index": score,
        "label": label,
        "components": {"air": air, "water": water, "energy": energy},
        "brand": "AWE™",
        "truth": "ESTIMATED",
    }


def twin_layer_set() -> List[Dict[str, Any]]:
    return [
        {"id": "finish", "label": "Finish", "default": True, "studio_default": True},
        {"id": "thermal", "label": "Thermal", "default": False, "studio_default": False},
        {"id": "moisture", "label": "Moisture", "default": False, "studio_default": False},
        {"id": "framing", "label": "Framing", "default": False, "studio_default": False},
        {"id": "energy", "label": "Energy", "default": False, "studio_default": False},
        {"id": "openings", "label": "Openings", "default": False, "studio_default": False},
        {"id": "awe", "label": "AWE", "default": False, "studio_default": False},
    ]


def awe_findings_on_twin() -> List[Dict[str, Any]]:
    return [
        {
            "id": "awe-attic-heat",
            "title": "Attic heat loss",
            "domain": "energy",
            "severity": "high",
            "summary": "Elevated thermal signature at ridge / attic plane.",
            "report_ref": "awe/energy/attic-heat",
        },
        {
            "id": "awe-window-seal",
            "title": "Window seal anomaly",
            "domain": "air",
            "severity": "medium",
            "summary": "Possible air leakage at upper-floor glazing.",
            "report_ref": "awe/air/window-seal",
        },
        {
            "id": "awe-moisture-eave",
            "title": "Eave moisture risk",
            "domain": "water",
            "severity": "medium",
            "summary": "Moisture pattern near eave / gutter line.",
            "report_ref": "awe/water/eave",
        },
    ]


def habitat_dashboard_projection_stub(
    address: str = "1234 Appalachian Way",
) -> Dict[str, Any]:
    """Mockup-locked demo projection for field UI (authoritative: false)."""
    return {
        "authoritative": False,
        "mode": "demo",
        "property": {
            "address_line": address,
            "city_state_zip": "London, KY 40741",
            "certified_score": 87,
            "score_scale": 1000,
            "rank_label": "TOP 15% of Homes in KY",
        },
        "home_health": {
            "overall": 72,
            "label": "Good",
            "systems": {
                "structure": 76,
                "roofing": 68,
                "hvac": 74,
                "plumbing": 71,
                "electrical": 78,
                "exterior": 69,
            },
        },
        "predictive_maintenance": {
            "next_12_months_usd": 2840,
            "recommended_actions": 5,
        },
        "financial": {
            "current_home_value": 285400,
            "equity": 128750,
            "investment_in_home": 96230,
            "projected_value_5yr": 342700,
        },
        "awe": awe_index_card(82, "Good"),
        "twin_layers": twin_layer_set(),
        "awe_hotspots": awe_findings_on_twin(),
        "tagline": (
            "CORE PERFORMS THE WORK. PASSPORT REMEMBERS THE HOME. "
            "HABITAT SUSTAINS THE RELATIONSHIP."
        ),
        "nav": [
            "Dashboard",
            "Property DNA",
            "Home Health",
            "Systems Studio",
            "Interior Studio",
            "Exterior Studio",
            "Renovation Studio",
            "Marketplace",
            "Projects",
            "Financial Hub",
            "Documents",
            "Timeline",
            "Reports",
            "Settings",
        ],
    }


def merge_passport_into_dashboard(
    passport_view: Dict[str, Any],
    base: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Overlay Passport field-test homeowner view onto mockup dashboard shape.
    Keeps UI contract stable while elevating truth when Passport is present.
    """
    out = base or habitat_dashboard_projection_stub()
    if not passport_view or passport_view.get("status") != "OK":
        out["passport_status"] = (passport_view or {}).get("status", "UNAVAILABLE")
        return out

    dash = passport_view.get("dashboard") or {}
    twin = passport_view.get("digital_twin") or {}
    scores = dash.get("scores") or twin.get("scores") or {}

    if scores.get("property_score") is not None:
        out["property"]["certified_score"] = int(scores["property_score"])
    if scores.get("awe") is not None:
        out["awe"] = awe_index_card(int(scores["awe"]), out["awe"].get("label", "Good"))

    # Map system-ish scores when present
    systems = out["home_health"]["systems"]
    if scores.get("roof_condition") is not None:
        systems["roofing"] = int(scores["roof_condition"])
    if scores.get("energy_score") is not None:
        systems["exterior"] = int(scores.get("energy_score") or systems["exterior"])
    if scores.get("moisture_score") is not None:
        # surface moisture as influence on overall label only
        pass

    actions = dash.get("next_actions") or dash.get("maintenance_priority") or []
    if actions:
        out["predictive_maintenance"]["recommended_actions"] = min(len(actions), 12)
        out["maintenance_priority"] = actions[:10]

    out["digital_twin"] = {
        "available": twin.get("twin_available") or (twin.get("plane_count", 0) > 0),
        "plane_count": twin.get("plane_count", 0),
        "measurements": twin.get("measurements", {}),
        "anomaly_counts": twin.get("anomaly_counts") or dash.get("anomaly_counts"),
    }
    # Official only when upstream projection says so (governed publish).
    # File handoff uses dashboard_from_contract; adapter path defaults preview.
    auth = dash.get("authoritative")
    if auth is None:
        auth = (passport_view or {}).get("authoritative")
    out["authoritative"] = bool(auth) if auth is not None else False
    out["passport_status"] = "OK" if out["authoritative"] else "PROJECTED"
    out["authority"] = dash.get("authority") or {
        "source": "passport_projection",
        "habitat_role": "read-only",
    }
    return out


def build_dashboard_projection(
    tenant_id: str = "demo",
    property_id: str = "demo-property",
) -> Dict[str, Any]:
    """
    Build dashboard JSON. Prefer HABITAT_PROJECTION_PATH when set
    (see routes._dashboard_from_file_or_build); this path is adapter/stub.
    """
    base = habitat_dashboard_projection_stub()
    try:
        from habitat_field_test_projection import get_homeowner_view

        view = get_homeowner_view(tenant_id, property_id)
        return merge_passport_into_dashboard(view, base)
    except Exception as e:
        base["passport_status"] = f"ERROR:{type(e).__name__}"
        base["passport_message"] = str(e)
        base["authoritative"] = False
        return base
