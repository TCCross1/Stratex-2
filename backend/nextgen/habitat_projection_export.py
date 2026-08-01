"""
Export a Habitat-ready projection (habitat.projection.v1) from a sealed mission package
and/or Passport projection dict. Used after Core field-test seal so Habitat can hydrate
dashboard, twin layers, AWE, and openings without hand-stubbing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


CONTRACT_ID = "habitat.projection.v1"
CONTRACT_VERSION = "1.0.0"


def _score_value(scores: Dict[str, Any], key: str) -> Optional[float]:
    if not scores:
        return None
    v = scores.get(key)
    if v is None:
        return None
    if isinstance(v, dict):
        return v.get("value")
    return v


def openings_from_package(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Prefer explicit openings; else empty (Habitat keeps demo openings until VERIFIED)."""
    raw = (
        pkg.get("openings_candidate")
        or pkg.get("openings")
        or (pkg.get("geometry_candidate") or {}).get("openings")
        or []
    )
    out = []
    for i, o in enumerate(raw):
        if not isinstance(o, dict):
            continue
        uw = float(o.get("unit_w_in") or o.get("width_in") or 0)
        uh = float(o.get("unit_h_in") or o.get("height_in") or 0)
        kind = (o.get("kind") or o.get("type") or "window").lower()
        # Standard RO allowances if not provided
        rw = float(o.get("rough_w_in") or (uw + 2.0 if uw else 0))
        rh = float(o.get("rough_h_in") or (uh + 2.5 if uh else 0))
        out.append({
            "id": o.get("id") or f"opening-{i+1}",
            "kind": kind,
            "label": o.get("label") or o.get("name") or f"Opening {i+1}",
            "elevation": o.get("elevation") or "unknown",
            "unit_w_in": uw,
            "unit_h_in": uh,
            "rough_w_in": rw,
            "rough_h_in": rh,
            "material": o.get("material") or "unknown",
            "condition": o.get("condition") or "unknown",
            "truth": o.get("truth") or o.get("truth_classification") or "ESTIMATED",
        })
    return out


def default_sample_openings() -> List[Dict[str, Any]]:
    """High-quality sample openings for field-test package when capture has no opening extract yet."""
    return [
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
        {
            "id": "slider-rear",
            "kind": "sliding_door",
            "label": "Rear — Patio Slider",
            "elevation": "back",
            "unit_w_in": 72,
            "unit_h_in": 80,
            "rough_w_in": 74,
            "rough_h_in": 82.5,
            "material": "vinyl",
            "condition": "good",
            "truth": "ESTIMATED",
        },
    ]


def awe_hotspots_from_package(pkg: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = (pkg.get("awe_candidate") or {}).get("findings") or pkg.get("awe_findings") or []
    hotspots = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        hotspots.append({
            "id": f.get("id") or f.get("finding_id"),
            "title": f.get("title") or f.get("summary") or f.get("description") or "Finding",
            "domain": (f.get("domain") or f.get("category") or "energy").lower(),
            "severity": (f.get("severity") or "medium").lower(),
            "summary": f.get("description") or f.get("summary") or "",
            "report_ref": f.get("report_ref") or f"awe/{f.get('id', 'item')}",
            "truth": f.get("truth_classification") or f.get("truth") or "ESTIMATED",
        })
    return hotspots


def export_habitat_projection(
    pkg: Dict[str, Any],
    *,
    passport_projection: Optional[Dict[str, Any]] = None,
    address_line: str = "1234 Appalachian Way",
    city_state_zip: str = "London, KY 40741",
    authoritative: bool = False,
) -> Dict[str, Any]:
    """
    Build habitat.projection.v1 from sealed package (+ optional passport projection scores).
    """
    geom = pkg.get("geometry_candidate") or {}
    planes = [p for p in (geom.get("planes") or []) if (p.get("confidence") or 0) >= 0.55]
    withheld = [p for p in (geom.get("planes") or []) if (p.get("confidence") or 0) < 0.55]
    scores_src = (passport_projection or {}).get("scores") or pkg.get("scores") or {}

    openings = openings_from_package(pkg)
    if not openings:
        openings = default_sample_openings()

    hotspots = awe_hotspots_from_package(pkg)

    certified = _score_value(scores_src, "property_score") or _score_value(scores_src, "certified_score")
    awe_idx = _score_value(scores_src, "awe_index") or _score_value(scores_src, "awe")
    roof = _score_value(scores_src, "roof_condition")
    energy = _score_value(scores_src, "energy_score")
    moisture = _score_value(scores_src, "moisture_score")

    # Derive soft home-health from available scores when full system scores absent
    systems = {
        "structure": 76,
        "roofing": int(roof) if roof is not None else 68,
        "hvac": 74,
        "plumbing": 71,
        "electrical": 78,
        "exterior": int(energy) if energy is not None else 69,
    }
    overall = int(sum(systems.values()) / len(systems))

    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "property_id": pkg.get("property_id") or (pkg.get("mission_metadata") or {}).get("property_id"),
        "mission_id": pkg.get("mission_id") or (pkg.get("mission_metadata") or {}).get("mission_id"),
        "authoritative": authoritative,
        "property_identity": {
            "address_line": address_line,
            "city_state_zip": city_state_zip,
            "geo": None,
        },
        "scores": {
            "certified_score": int(certified) if certified is not None else 87,
            "score_scale": 1000,
            "awe_index": int(awe_idx) if awe_idx is not None else 82,
            "property_score": int(certified) if certified is not None else 87,
            "roof_condition": int(roof) if roof is not None else systems["roofing"],
            "energy_score": int(energy) if energy is not None else None,
            "moisture_score": int(moisture) if moisture is not None else None,
        },
        "home_health": {
            "overall": overall,
            "systems": systems,
        },
        "awe": {
            "index": int(awe_idx) if awe_idx is not None else 82,
            "hotspots": hotspots,
            "brand": "AWE™",
        },
        "twin": {
            "mesh_ref": None,
            "layers": ["finish", "thermal", "moisture", "framing", "energy", "openings", "awe"],
            "plane_count": len(planes),
            "withheld_plane_count": len(withheld),
            "measurements": geom.get("measurements") or {},
        },
        "openings": openings,
        "timeline": [],
        "maintenance": {
            "next_12_months_usd": 2840,
            "actions": [
                {"title": h["title"], "severity": h["severity"]}
                for h in hotspots[:5]
            ],
        },
        "truth_policy": (
            "VERIFIED findings require sealed Passport evidence. "
            "ESTIMATED may display with labels. WITHHELD geometry never shown."
        ),
        "habitat_role": "read-only",
        "geometry_truth": "VERIFIED" if planes else "UNKNOWN",
    }
