"""STRATEX backend API tests - end-to-end verification."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stratex-quant.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- Root / Health ---
def test_root(session):
    r = session.get(f"{API}/")
    assert r.status_code == 200
    data = r.json()
    assert data["system"] == "STRATEX"
    assert data["status"] == "online"


# --- Project create ---
@pytest.fixture(scope="module")
def insurance_project(session):
    payload = {
        "intake": {
            "customer_name": "TEST_Insurance_Customer",
            "property_address": "1100 Test Lane, Lexington, KY",
            "insurance_carrier": "State Farm",
            "project_type": "Insurance Claim",
        },
        "scope": {
            "underlayment_brand": "Synthetic Felt",
            "drip_edge_color": "Charcoal",
            "disposal_strategy": "Automated Mobile Trailer Rig",
            "fastener_type": "Hot-Dipped Galvanized",
        },
    }
    r = session.post(f"{API}/projects", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "id" in data
    assert data["status"] == "configured"
    assert data["roof_telemetry"] is not None
    tele = data["roof_telemetry"]
    for k in ["total_sf", "squares", "eaves_lf", "rakes_lf", "ridge_lf", "valleys_lf", "hips_lf", "pitch", "pitch_num"]:
        assert k in tele
    return data


@pytest.fixture(scope="module")
def retail_project(session):
    payload = {
        "intake": {
            "customer_name": "TEST_Retail_Customer",
            "property_address": "200 Cash Pay St, Lexington, KY",
            "insurance_carrier": None,
            "project_type": "Private Cash Pay",
        },
        "scope": {
            "underlayment_brand": "Premium Synthetic Felt",
            "drip_edge_color": "Black",
            "disposal_strategy": "Commercial Roll-off Dumpster",
            "fastener_type": "Stainless Steel",
        },
    }
    r = session.post(f"{API}/projects", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_list_projects(session, insurance_project):
    r = session.get(f"{API}/projects")
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list)
    assert any(p["id"] == insurance_project["id"] for p in arr)


def test_get_project(session, insurance_project):
    r = session.get(f"{API}/projects/{insurance_project['id']}")
    assert r.status_code == 200
    p = r.json()
    assert p["id"] == insurance_project["id"]
    assert p["intake"]["customer_name"] == "TEST_Insurance_Customer"


def test_get_project_not_found(session):
    r = session.get(f"{API}/projects/non-existent-id-12345")
    assert r.status_code == 404


# --- Caliper math ---
def test_caliper_tearoff_thick(session, insurance_project):
    r = session.post(f"{API}/projects/{insurance_project['id']}/caliper",
                     json={"edge_thickness_in": 1.25})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["layers_detected"] == 2
    assert c["scope_determined"] == "Complete Tear-Off Required"
    assert c["labor_hour_multiplier"] == 1.5
    assert c["dumping_weight_allowance_multiplier"] == 1.5


def test_caliper_overlay_thin(session, retail_project):
    r = session.post(f"{API}/projects/{retail_project['id']}/caliper",
                     json={"edge_thickness_in": 0.75})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["layers_detected"] == 1
    assert c["scope_determined"] == "Overlay Permitted"
    assert c["labor_hour_multiplier"] == 1.0
    assert c["dumping_weight_allowance_multiplier"] == 1.0


def test_caliper_boundary_exactly_one(session, insurance_project):
    # edge_thickness_in == 1.0 should NOT trigger tear-off (strict >)
    # Use a new project to not affect the prior tearoff state
    pp = session.post(f"{API}/projects", json={
        "intake": {"customer_name": "TEST_Boundary", "property_address": "x", "project_type": "Insurance Claim"},
        "scope": {"underlayment_brand": "Synthetic Felt", "drip_edge_color": "White",
                  "disposal_strategy": "Commercial Roll-off Dumpster", "fastener_type": "Electro-Galvanized"},
    }).json()
    r = session.post(f"{API}/projects/{pp['id']}/caliper", json={"edge_thickness_in": 1.0})
    assert r.status_code == 200
    c = r.json()
    assert c["layers_detected"] == 1
    assert c["scope_determined"] == "Overlay Permitted"


# --- Pricing ---
def test_pricing_insurance_2025(session, insurance_project):
    # caliper applied tear-off earlier with 1.25"
    r = session.post(f"{API}/projects/{insurance_project['id']}/pricing")
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["overhead_rate"] == 0.20
    assert p["profit_rate"] == 0.25
    assert p["lock_mode"] == "INSURANCE 20/25 O&P"
    assert isinstance(p["line_items"], list) and len(p["line_items"]) >= 10
    # Verify Xactimate tags on items
    tags = {li["xactimate_tag"] for li in p["line_items"]}
    assert "RFG ASV" in tags
    assert "RFG OSB" in tags
    assert "RFG LAB" in tags
    # Verify total math
    subtotal = round(sum(li["total"] for li in p["line_items"]), 2)
    assert abs(subtotal - p["subtotal"]) < 0.5
    expected_final = round(p["subtotal"] * 1.45, 2)
    assert abs(expected_final - p["final_total"]) < 1.0
    # tear-off should be true (caliper set to 1.25)
    assert p["tear_off"] is True
    assert p["layers_detected"] == 2


def test_pricing_retail_1010(session, retail_project):
    r = session.post(f"{API}/projects/{retail_project['id']}/pricing")
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["overhead_rate"] == 0.10
    assert p["profit_rate"] == 0.10
    assert p["lock_mode"] == "RETAIL FLAT 10/10"
    assert p["tear_off"] is False
    assert p["layers_detected"] == 1


# --- Launch / preflight ---
def test_launch_rejects_bad_preflight(session, insurance_project):
    bad = {
        "trailer_hatch_secured": False,
        "drone_battery_percentage": 100,
        "rtk_gps_signal": "Centimeter-Level Locked",
        "communication_uplink": "Strong / Starlink Verified",
        "local_weather_clear": True,
    }
    r = session.post(f"{API}/projects/{insurance_project['id']}/launch", json=bad)
    assert r.status_code == 400


def test_launch_rejects_low_battery(session, insurance_project):
    bad = {
        "trailer_hatch_secured": True,
        "drone_battery_percentage": 78,
        "rtk_gps_signal": "Centimeter-Level Locked",
        "communication_uplink": "Strong / Starlink Verified",
        "local_weather_clear": True,
    }
    r = session.post(f"{API}/projects/{insurance_project['id']}/launch", json=bad)
    assert r.status_code == 400


def test_launch_success(session, insurance_project):
    good = {
        "trailer_hatch_secured": True,
        "drone_battery_percentage": 100,
        "rtk_gps_signal": "Centimeter-Level Locked",
        "communication_uplink": "Strong / Starlink Verified",
        "local_weather_clear": True,
    }
    r = session.post(f"{API}/projects/{insurance_project['id']}/launch", json=good, timeout=120)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "complete"
    mission = out["mission"]
    assert mission["status"] == "COMPLETE"
    assert isinstance(mission["anomalies"], list)
    assert mission["anomalies_count"] == len(mission["anomalies"])
    assert mission["anomalies_count"] >= 4
    # Agent reports
    ar = out["agent_reports"]
    for key in ["forensic", "validation", "reconciliation", "jurisprudential"]:
        assert key in ar, f"missing {key}"
        assert isinstance(ar[key], str)
        assert len(ar[key]) > 30, f"{key} too short: {ar[key]!r}"


def test_launch_persists_complete(session, insurance_project):
    r = session.get(f"{API}/projects/{insurance_project['id']}")
    assert r.status_code == 200
    p = r.json()
    assert p["status"] == "complete"
    assert p.get("mission") is not None
    assert p.get("agent_reports") is not None



# --- NEW: vision scan endpoint ---
def test_scan_endpoint(session, retail_project):
    r = session.post(f"{API}/projects/{retail_project['id']}/scan")
    assert r.status_code == 200, r.text
    scan = r.json()
    assert scan["mesh_status"] == "STITCHED"
    assert "telemetry" in scan and "anomalies" in scan
    assert scan["anomalies_count"] == len(scan["anomalies"])
    assert scan["anomalies_count"] >= 4
    tele = scan["telemetry"]
    for k in ["total_sf", "squares", "pitch_num"]:
        assert k in tele
    # verify persistence
    g = session.get(f"{API}/projects/{retail_project['id']}").json()
    assert g.get("scan", {}).get("mesh_status") == "STITCHED"


def test_scan_not_found(session):
    r = session.post(f"{API}/projects/no-such-id/scan")
    assert r.status_code == 404


# --- NEW: relaxed preflight (>=90) ---
def test_launch_accepts_battery_90(session):
    # Fresh project to launch
    pp = session.post(f"{API}/projects", json={
        "intake": {"customer_name": "TEST_Bat90", "property_address": "x", "project_type": "Private Cash Pay"},
        "scope": {"underlayment_brand": "Synthetic Felt", "drip_edge_color": "White",
                  "disposal_strategy": "Commercial Roll-off Dumpster", "fastener_type": "Electro-Galvanized"},
    }).json()
    good = {
        "trailer_hatch_secured": True,
        "drone_battery_percentage": 90,
        "rtk_gps_signal": "Centimeter-Level Locked",
        "communication_uplink": "Strong / Starlink Verified",
        "local_weather_clear": True,
    }
    r = session.post(f"{API}/projects/{pp['id']}/launch", json=good, timeout=180)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "complete"
    assert out["mission"]["status"] == "COMPLETE"


# --- NEW: PDF supplement endpoint ---
def test_report_pdf(session, insurance_project):
    r = session.get(f"{API}/projects/{insurance_project['id']}/report.pdf")
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/pdf")
    body = r.content
    assert len(body) > 2048, f"pdf too small: {len(body)} bytes"
    assert body[:4] == b"%PDF", f"not a PDF header: {body[:8]!r}"


def test_report_pdf_not_found(session):
    r = session.get(f"{API}/projects/no-such-id/report.pdf")
    assert r.status_code == 404
