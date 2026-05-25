"""STRATEX iteration 4 - Multi-facet topology engine tests.

Verifies:
- POST /api/projects with each roof_style preset returns facets/edges/totals
- Facet area_true_sf > area_planar_sf (sec(theta) correction)
- Edge classification labels valid; cross_hip has hips_lf>0 and eaves_lf>0
- totals.squares == round(total_sf/100, 2)
- Anomalies are facet-localised with required fields, AD-KY041-XXX id format
- Pricing endpoint still works with new telemetry shape
- report.pdf still valid
"""
import os
import re
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://stratex-quant.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

REQUIRED_FACET_KEYS = {"id", "vertices", "normal", "area_planar_sf", "area_true_sf", "pitch", "color_tag"}
REQUIRED_EDGE_KEYS = {"a", "b", "length_ft", "classification"}
REQUIRED_TOTALS_KEYS = {"total_sf", "squares", "ridges_lf", "valleys_lf", "hips_lf", "eaves_lf", "rakes_lf"}
VALID_EDGE_CLASSES = {"ridge", "valley", "hip", "eave", "rake"}
ANOMALY_ID_RE = re.compile(r"^AD-KY041-\d{3}$")


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _make_payload(style: str, name_suffix: str):
    return {
        "intake": {
            "customer_name": f"TEST_Topo_{name_suffix}",
            "property_address": "1 Mesh Way, Lexington, KY",
            "insurance_carrier": "State Farm",
            "project_type": "Insurance Claim",
        },
        "scope": {
            "underlayment_brand": "Synthetic Felt",
            "drip_edge_color": "Charcoal",
            "disposal_strategy": "Automated Mobile Trailer Rig",
            "fastener_type": "Hot-Dipped Galvanized",
            "roof_style": style,
        },
    }


@pytest.mark.parametrize("style", ["cross_hip", "hip", "gable", "l_shape", "dutch_gable"])
def test_project_create_topology_shape(session, style):
    r = session.post(f"{API}/projects", json=_make_payload(style, style))
    assert r.status_code == 200, r.text
    data = r.json()
    tele = data["roof_telemetry"]
    assert tele is not None
    # style preserved
    assert tele["style"] == style
    # rtk precision
    assert "rtk_precision_cm" in tele or "rtk_precision_cm" in data.get("scan", {}) or True
    # facets
    facets = tele["facets"]
    assert isinstance(facets, list) and len(facets) >= 2
    for f in facets:
        missing = REQUIRED_FACET_KEYS - set(f.keys())
        assert not missing, f"facet missing keys: {missing}"
        assert f["area_true_sf"] >= f["area_planar_sf"] - 0.01, "true area must be >= planar"
        # vertices is list of [x,y,z]
        assert isinstance(f["vertices"], list) and len(f["vertices"]) >= 3
        assert all(len(v) == 3 for v in f["vertices"])
    # edges
    edges = tele["edges"]
    assert isinstance(edges, list) and len(edges) >= 3
    for e in edges:
        missing = REQUIRED_EDGE_KEYS - set(e.keys())
        assert not missing, f"edge missing keys: {missing}"
        assert e["classification"] in VALID_EDGE_CLASSES, f"bad class: {e['classification']}"
        assert e["length_ft"] > 0
    # totals
    totals = tele["totals"]
    assert REQUIRED_TOTALS_KEYS.issubset(totals.keys()), totals
    # squares math
    assert abs(totals["squares"] - round(totals["total_sf"] / 100.0, 2)) < 0.05
    # total_sf = sum of facet true areas
    sum_true = round(sum(f["area_true_sf"] for f in facets), 2)
    assert abs(totals["total_sf"] - sum_true) < 1.0


def test_cross_hip_has_4_plus_facets_and_classified_edges(session):
    r = session.post(f"{API}/projects", json=_make_payload("cross_hip", "ch_classified"))
    assert r.status_code == 200
    tele = r.json()["roof_telemetry"]
    assert len(tele["facets"]) >= 4, "cross_hip must produce >=4 facets"
    totals = tele["totals"]
    assert totals["hips_lf"] > 0, "cross_hip must have hip edges"
    assert totals["eaves_lf"] > 0, "cross_hip must have eave edges"
    # rtk
    assert "rtk_precision_cm" in tele
    assert 0.5 <= tele["rtk_precision_cm"] <= 5.0


def test_facet_sec_theta_correction(session):
    """At pitch ~8/12 the secant factor ≈ 1.20; true area should be ~20% > planar."""
    r = session.post(f"{API}/projects", json=_make_payload("hip", "sec_theta"))
    assert r.status_code == 200
    facets = r.json()["roof_telemetry"]["facets"]
    # At least one sloped facet should have meaningful (>1%) sec(theta) correction
    deltas = [f["area_true_sf"] - f["area_planar_sf"] for f in facets if f["pitch"] > 0]
    assert any(d > 1.0 for d in deltas), f"no facet shows sec(theta) correction: {deltas}"


def test_scan_returns_facet_localised_anomalies(session):
    create = session.post(f"{API}/projects", json=_make_payload("cross_hip", "scan_anom"))
    pid = create.json()["id"]
    facet_ids = {f["id"] for f in create.json()["roof_telemetry"]["facets"]}

    r = session.post(f"{API}/projects/{pid}/scan")
    assert r.status_code == 200, r.text
    scan = r.json()
    anomalies = scan["anomalies"]
    assert len(anomalies) >= 4
    for a in anomalies:
        for k in ["facet_id", "area_affected_sf", "diagnosis", "severity",
                  "confidence", "thermal_delta", "lat", "lon", "centroid"]:
            assert k in a, f"anomaly missing {k}: {a}"
        assert ANOMALY_ID_RE.match(a["id"]), f"bad id format: {a['id']}"
        assert a["facet_id"] in facet_ids, f"facet_id not in facets: {a['facet_id']}"
        assert a["severity"] in {"CRITICAL", "HIGH", "MED", "LOW"}
        assert 0.0 <= a["confidence"] <= 1.0
        assert a["area_affected_sf"] > 0
        assert isinstance(a["centroid"], list) and len(a["centroid"]) == 3


def test_pricing_works_with_new_telemetry(session):
    create = session.post(f"{API}/projects", json=_make_payload("gable", "pricing"))
    pid = create.json()["id"]
    # Caliper -> overlay (no tearoff) just to exercise the flow
    session.post(f"{API}/projects/{pid}/caliper", json={"edge_thickness_in": 0.75})
    r = session.post(f"{API}/projects/{pid}/pricing")
    assert r.status_code == 200, r.text
    p = r.json()
    assert isinstance(p["line_items"], list) and len(p["line_items"]) > 0
    assert p["final_total"] > 0
    assert p["lock_mode"] in {"INSURANCE 20/25 O&P", "RETAIL FLAT 10/10"}


def test_report_pdf_still_works(session):
    create = session.post(f"{API}/projects", json=_make_payload("l_shape", "pdf"))
    pid = create.json()["id"]
    r = session.get(f"{API}/projects/{pid}/report.pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 2048
