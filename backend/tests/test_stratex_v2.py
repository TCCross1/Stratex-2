"""STRATEX v2.0.0 dual-portal regression tests (auth + role + NDA + materials + jobs lifecycle)."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stratex-quant.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CONTRACTOR_EMAIL = "anthony@apexroofing.com"
CONTRACTOR_PW = "Contractor!2026"
OPERATOR_EMAIL = "pilot@stratex.io"
OPERATOR_PW = "Operator!2026"


def _totp(email):
    r = requests.get(f"{API}/auth/totp-debug", params={"email": email}, timeout=15)
    assert r.status_code == 200, f"totp-debug failed: {r.text}"
    return r.json()["current_code"]


def _login(email, pw):
    # step 1
    r1 = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r1.status_code == 200, f"step1 failed: {r1.text}"
    assert r1.json().get("mfa_required") is True
    # step 2
    code = _totp(email)
    r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": pw, "totp_code": code}, timeout=15)
    assert r2.status_code == 200, f"step2 failed: {r2.text}"
    data = r2.json()
    assert "access_token" in data
    return data["access_token"], data["user"]


# ---------------- AUTH ----------------
class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert r.json()["system"] == "STRATEX"

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": CONTRACTOR_EMAIL, "password": "wrong"}, timeout=10)
        assert r.status_code == 401

    def test_login_two_step_contractor(self):
        r1 = requests.post(f"{API}/auth/login", json={"email": CONTRACTOR_EMAIL, "password": CONTRACTOR_PW}, timeout=10)
        assert r1.status_code == 200
        assert r1.json().get("mfa_required") is True
        code = _totp(CONTRACTOR_EMAIL)
        r2 = requests.post(f"{API}/auth/login", json={"email": CONTRACTOR_EMAIL, "password": CONTRACTOR_PW, "totp_code": code}, timeout=10)
        assert r2.status_code == 200
        body = r2.json()
        assert "access_token" in body
        assert body["user"]["role"] == "contractor"
        assert body["user"]["nda_accepted"] is True

    def test_login_bad_totp(self):
        r = requests.post(f"{API}/auth/login", json={"email": CONTRACTOR_EMAIL, "password": CONTRACTOR_PW, "totp_code": "000000"}, timeout=10)
        assert r.status_code == 401

    def test_me(self):
        token, user = _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == CONTRACTOR_EMAIL

    def test_me_no_token(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_signup_creates_user_with_totp(self):
        email = f"TEST_signup_{uuid.uuid4().hex[:8]}@test.io"
        r = requests.post(f"{API}/auth/signup", json={
            "email": email, "password": "StratexTest!2026",
            "legal_name": "Test User", "company_name": "Test Co", "role": "contractor"
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"].lower() == email.lower()
        assert d["user"]["nda_accepted"] is False
        assert "secret" in d["totp_setup"]
        assert "uri" in d["totp_setup"]


# ---------------- NDA ----------------
class TestNDA:
    def test_nda_preview(self):
        token, _ = _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)
        r = requests.get(f"{API}/auth/nda-preview", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        assert r.status_code == 200
        text = r.json()["rendered_text"]
        assert "MUTUAL NON-DISCLOSURE" in text
        assert "Anthony Cross" in text

    def test_nda_mismatch(self):
        token, _ = _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)
        r = requests.post(f"{API}/auth/accept-nda", headers={"Authorization": f"Bearer {token}"},
                          json={"typed_name": "Wrong Person"}, timeout=10)
        assert r.status_code == 400

    def test_nda_signup_then_accept(self):
        """New contractor signup → accept-nda flips flag."""
        email = f"TEST_nda_{uuid.uuid4().hex[:8]}@test.io"
        pw = "StratexTest!2026"
        legal = "Test Legal Name"
        r = requests.post(f"{API}/auth/signup", json={
            "email": email, "password": pw, "legal_name": legal,
            "company_name": "X", "role": "contractor"}, timeout=15)
        assert r.status_code == 200
        # login to get token (TOTP for new user)
        code = _totp(email)
        rl = requests.post(f"{API}/auth/login", json={"email": email, "password": pw, "totp_code": code}, timeout=10)
        assert rl.status_code == 200
        token = rl.json()["access_token"]
        assert rl.json()["user"]["nda_accepted"] is False
        # accept NDA
        r2 = requests.post(f"{API}/auth/accept-nda", headers={"Authorization": f"Bearer {token}"},
                           json={"typed_name": legal}, timeout=10)
        assert r2.status_code == 200, r2.text
        # me reflects flip
        rm = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        assert rm.status_code == 200
        assert rm.json()["nda_accepted"] is True


# ---------------- ROLES ----------------
class TestRoleEnforcement:
    def test_contractor_cannot_access_operator(self):
        token, _ = _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)
        r = requests.get(f"{API}/operator/jobs", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        assert r.status_code == 403

    def test_operator_cannot_access_contractor(self):
        token, _ = _login(OPERATOR_EMAIL, OPERATOR_PW)
        r = requests.get(f"{API}/contractor/jobs", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        assert r.status_code == 403
        r2 = requests.get(f"{API}/contractor/materials", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        assert r2.status_code == 403


# ---------------- MATERIALS ----------------
class TestMaterials:
    def test_materials_round_trip_encrypted(self):
        token, _ = _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)
        H = {"Authorization": f"Bearer {token}"}
        # GET (defaults if absent)
        r = requests.get(f"{API}/contractor/materials", headers=H, timeout=10)
        assert r.status_code == 200
        # PUT
        payload = {
            "shingle_brand": "GAF Timberline HDZ",
            "underlayment_brand": "GAF FeltBuster Synthetic",
            "ice_water_brand": "GAF StormGuard",
            "ridge_vent_brand": "GAF Cobra Ridge Vent",
            "starter_brand": "GAF Pro-Start",
            "drip_edge_color": "Charcoal",
            "fastener_type": "Hot-Dipped Galvanized",
            "shingle_bundle_price": 41.25,
            "underlayment_square_price": 80.0,
            "ice_water_roll_price": 95.0,
            "ridge_cap_bundle_price": 60.0,
            "starter_bundle_price": 65.0,
            "drip_edge_lf_price": 2.25,
            "fastener_square_price": 13.0,
            "osb_sheet_price": 40.0,
            "overhead_pct": 22.5,
            "profit_margin_pct": 27.5,
            "labor_rate_per_hour": 82.0,
            "labor_rate_per_square": 0.0,
            "insurance_supplement_multiplier_pct": 12.0,
        }
        r2 = requests.put(f"{API}/contractor/materials", headers=H, json=payload, timeout=10)
        assert r2.status_code == 200, r2.text
        assert r2.json()["ok"] is True
        # GET round-trip decrypted
        r3 = requests.get(f"{API}/contractor/materials", headers=H, timeout=10)
        assert r3.status_code == 200
        got = r3.json()
        assert abs(got["shingle_bundle_price"] - 41.25) < 0.01
        assert abs(got["overhead_pct"] - 22.5) < 0.01
        assert abs(got["profit_margin_pct"] - 27.5) < 0.01
        assert got["shingle_brand"] == "GAF Timberline HDZ"
        assert "_encrypted" not in got


# ---------------- JOB LIFECYCLE ----------------
class TestJobLifecycle:
    @pytest.fixture(scope="class")
    def tokens(self):
        ct, _ = _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)
        ot, _ = _login(OPERATOR_EMAIL, OPERATOR_PW)
        return ct, ot

    def test_create_then_operator_strips_pricing(self, tokens):
        ct, ot = tokens
        H = {"Authorization": f"Bearer {ct}"}
        payload = {
            "property_address": "TEST 100 Sandhill Crane Ln, Austin, TX 78745",
            "lat": 30.2672, "lon": -97.7431,
            "homeowner_name": "TEST Homeowner",
            "homeowner_email": "homeowner@test.io",
            "homeowner_phone": "555-0100",
            "project_type": "Insurance Claim",
            "insurance_carrier": "State Farm",
            "roof_style": "cross_hip",
            "notes": "test job",
        }
        rc = requests.post(f"{API}/contractor/jobs", headers=H, json=payload, timeout=15)
        assert rc.status_code == 200, rc.text
        job = rc.json()
        job_id = job["id"]
        assert job["status"] == "PENDING_FIELD_CAPTURE"

        # operator board sees job, no pricing or homeowner contact
        ho = {"Authorization": f"Bearer {ot}"}
        rb = requests.get(f"{API}/operator/jobs", headers=ho, timeout=15)
        assert rb.status_code == 200
        seen = [j for j in rb.json() if j["id"] == job_id]
        assert len(seen) == 1
        opj = seen[0]
        assert "pricing" not in opj
        assert "homeowner_email" not in opj
        assert "homeowner_phone" not in opj
        assert opj["homeowner_name"] == "TEST Homeowner"

        # operator GET single job
        rg = requests.get(f"{API}/operator/jobs/{job_id}", headers=ho, timeout=10)
        assert rg.status_code == 200
        single = rg.json()
        assert "pricing" not in single
        assert "homeowner_email" not in single
        assert "homeowner_phone" not in single

        # store for next tests
        pytest.job_id = job_id

    def test_operator_launch_transitions_state(self, tokens):
        _, ot = tokens
        job_id = pytest.job_id
        ho = {"Authorization": f"Bearer {ot}"}
        preflight = {
            "trailer_hatch_secured": True,
            "drone_battery_percentage": 100,
            "rtk_gps_signal": "Centimeter-Level Locked",
            "communication_uplink": "Strong / Starlink Verified",
            "local_weather_clear": True,
            "personnel_clear": True,
        }
        rl = requests.post(f"{API}/operator/jobs/{job_id}/launch", headers=ho, json=preflight, timeout=60)
        assert rl.status_code == 200, rl.text
        out = rl.json()
        assert out["status"] == "DATA_CAPTURE_COMPLETE"
        assert out.get("roof_telemetry") is not None
        assert isinstance(out.get("anomalies"), list)
        # operator must still NOT see pricing
        assert "pricing" not in out

    def test_operator_launch_invalid_preflight(self, tokens):
        ct, ot = tokens
        # create another job
        H = {"Authorization": f"Bearer {ct}"}
        rc = requests.post(f"{API}/contractor/jobs", headers=H, json={
            "property_address": "TEST 200 Bad Preflight",
            "lat": 30.3, "lon": -97.7,
            "homeowner_name": "TEST",
            "project_type": "Private Cash Pay",
            "roof_style": "gable",
        }, timeout=15)
        assert rc.status_code == 200
        jid = rc.json()["id"]
        bad = {"trailer_hatch_secured": False, "drone_battery_percentage": 50,
               "rtk_gps_signal": "Lost", "communication_uplink": "Weak",
               "local_weather_clear": False, "personnel_clear": False}
        rl = requests.post(f"{API}/operator/jobs/{jid}/launch", headers={"Authorization": f"Bearer {ot}"},
                           json=bad, timeout=15)
        assert rl.status_code == 400

    def test_compute_proposal_yields_pricing(self, tokens):
        ct, _ = tokens
        H = {"Authorization": f"Bearer {ct}"}
        rp = requests.post(f"{API}/contractor/jobs/{pytest.job_id}/compute-proposal", headers=H, timeout=20)
        assert rp.status_code == 200, rp.text
        job = rp.json()
        assert job["status"] == "PROPOSAL_READY"
        pricing = job["pricing"]
        assert pricing["line_items"]
        assert pricing["final_total"] > 0
        assert pricing["subtotal"] > 0

    def test_audit_then_mark_sent(self, tokens):
        ct, _ = tokens
        H = {"Authorization": f"Bearer {ct}"}
        r1 = requests.post(f"{API}/contractor/jobs/{pytest.job_id}/audit-approve", headers=H, timeout=10)
        assert r1.status_code == 200
        assert r1.json()["status"] == "AUDIT_APPROVED"
        r2 = requests.post(f"{API}/contractor/jobs/{pytest.job_id}/mark-sent", headers=H, timeout=10)
        assert r2.status_code == 200
        assert r2.json()["status"] == "SENT_TO_HOMEOWNER"

    def test_pdf_download(self, tokens):
        ct, _ = tokens
        H = {"Authorization": f"Bearer {ct}"}
        r = requests.get(f"{API}/contractor/jobs/{pytest.job_id}/report.pdf", headers=H, timeout=30)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert len(r.content) > 1000
