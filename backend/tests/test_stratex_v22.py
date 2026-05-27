"""STRATEX v2.2.0 — Model A revenue + 3-phase Risk Engine tests."""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CONTRACTOR_EMAIL = "anthony@apexroofing.com"
CONTRACTOR_PW = "Contractor!2026"
OPERATOR_EMAIL = "pilot@stratex.io"
OPERATOR_PW = "Operator!2026"


def _totp(email):
    r = requests.get(f"{API}/auth/totp-debug", params={"email": email}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["current_code"]


def _login(email, pw):
    r1 = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r1.status_code == 200, r1.text
    code = _totp(email)
    r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": pw, "totp_code": code}, timeout=30)
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"], r2.json()["user"]


@pytest.fixture(scope="module")
def contractor_auth():
    tok, u = _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)
    return {"Authorization": f"Bearer {tok}"}, u


@pytest.fixture(scope="module")
def operator_auth():
    tok, u = _login(OPERATOR_EMAIL, OPERATOR_PW)
    return {"Authorization": f"Bearer {tok}"}, u


# ---------- Billing plans Model A ----------
class TestPlansModelA:
    def test_plans_2_tiers_only(self):
        r = requests.get(f"{API}/billing/plans", timeout=30)
        assert r.status_code == 200
        tiers = r.json()["tiers"]
        assert set(tiers.keys()) == {"on_demand", "volume_builder"}, f"Got: {list(tiers.keys())}"
        assert tiers["on_demand"]["price"] == 98.00
        assert tiers["on_demand"]["included_drops"] == 0
        assert tiers["on_demand"]["extra_drop_price"] == 350.00
        assert tiers["volume_builder"]["price"] == 998.00
        assert tiers["volume_builder"]["included_drops"] == 4
        assert tiers["volume_builder"]["extra_drop_price"] == 198.00


# ---------- Billing meter ----------
class TestBillingMeter:
    def test_meter_shape(self, contractor_auth):
        H, _ = contractor_auth
        r = requests.get(f"{API}/contractor/billing/meter", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        m = r.json()
        for k in ["bucket", "tier_key", "tier_name", "monthly_retainer",
                  "drops_used", "drops_included", "overage_drops",
                  "overage_drop_price", "overage_charges_usd",
                  "dry_run_count", "dry_run_charges_usd", "estimated_invoice_total"]:
            assert k in m, f"missing key: {k}"
        assert m["tier_key"] in ("on_demand", "volume_builder")


# ---------- Job creation w/ empty email ----------
class TestJobCreation:
    def test_create_job_empty_email_pending_phase1(self, contractor_auth):
        H, _ = contractor_auth
        body = {
            "property_address": "TEST_v22_42 Pheasant Run, Lexington, KY",
            "lat": 38.0406, "lon": -84.5037,
            "homeowner_name": "Test Homeowner",
            "homeowner_email": "",
            "homeowner_phone": "",
            "project_type": "Insurance Claim",
            "insurance_carrier": "State Farm",
            "roof_style": "cross_hip",
            "notes": "v22 test",
        }
        r = requests.post(f"{API}/contractor/jobs", headers=H, json=body, timeout=30)
        assert r.status_code == 200, r.text
        job = r.json()
        assert job["status"] == "PENDING_PHASE1"
        assert job["phase1_status"] is None
        pytest.v22_job_id = job["id"]


# ---------- Phase 1 ----------
class TestPhase1:
    def test_run_phase1(self, contractor_auth):
        H, _ = contractor_auth
        job_id = pytest.v22_job_id
        r = requests.post(f"{API}/contractor/jobs/{job_id}/run-phase1", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["overall"] in ("PASS", "FAIL")
        assert len(body["checks"]) >= 3  # v2.3 now emits 6 (FAA + 4 ASTM weather sub-gates + GIS)
        names = [c["name"] for c in body["checks"]]
        assert any("FAA" in n for n in names)
        assert any("Weather" in n for n in names)
        assert any("GIS" in n or "Utility" in n for n in names)
        # Verify job status updated
        r2 = requests.get(f"{API}/contractor/jobs/{job_id}", headers=H, timeout=30)
        if body["overall"] == "PASS":
            assert r2.json()["status"] == "PENDING_FIELD_CAPTURE"
        else:
            assert r2.json()["status"] == "PHASE1_BLOCKED"
        pytest.v22_phase1_overall = body["overall"]


# ---------- Operator launch gates ----------
class TestLaunchGates:
    def _preflight(self, **overrides):
        p = {
            "homeowner_verified": True,
            "vertical_obstruction_clear": True,
            "k9_and_child_clear_zone": True,
            "trailer_hatch_secured": True,
            "drone_battery_percentage": 100,
            "battery_cell_variance_v": 0.015,
            "rtk_gps_signal": "Centimeter-Level Locked",
            "communication_uplink": "Strong / Starlink Verified",
            "local_weather_clear": True,
            "personnel_clear": True,
        }
        p.update(overrides)
        return p

    def test_phase2_gate_block(self, operator_auth):
        if getattr(pytest, "v22_phase1_overall", None) != "PASS":
            pytest.skip("phase1 didn't pass")
        H, _ = operator_auth
        r = requests.post(f"{API}/operator/jobs/{pytest.v22_job_id}/launch",
                          headers=H, json=self._preflight(homeowner_verified=False), timeout=30)
        assert r.status_code == 400
        assert "Phase 2" in r.text

    def test_phase3_battery_variance_block(self, operator_auth):
        if getattr(pytest, "v22_phase1_overall", None) != "PASS":
            pytest.skip("phase1 didn't pass")
        H, _ = operator_auth
        r = requests.post(f"{API}/operator/jobs/{pytest.v22_job_id}/launch",
                          headers=H, json=self._preflight(battery_cell_variance_v=0.025), timeout=30)
        assert r.status_code == 400
        assert "Phase 3" in r.text

    def test_phase3_low_battery_block(self, operator_auth):
        if getattr(pytest, "v22_phase1_overall", None) != "PASS":
            pytest.skip("phase1 didn't pass")
        H, _ = operator_auth
        r = requests.post(f"{API}/operator/jobs/{pytest.v22_job_id}/launch",
                          headers=H, json=self._preflight(drone_battery_percentage=80), timeout=30)
        assert r.status_code == 400

    def test_launch_success(self, operator_auth, contractor_auth):
        if getattr(pytest, "v22_phase1_overall", None) != "PASS":
            pytest.skip("phase1 didn't pass")
        H, _ = operator_auth
        Hc, _ = contractor_auth
        # Pre-launch drops count
        m0 = requests.get(f"{API}/contractor/billing/meter", headers=Hc, timeout=30).json()
        pre_drops = m0["drops_used"]
        r = requests.post(f"{API}/operator/jobs/{pytest.v22_job_id}/launch",
                          headers=H, json=self._preflight(), timeout=60)
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["status"] == "DATA_CAPTURE_COMPLETE"
        # Verify drop counter incremented
        m1 = requests.get(f"{API}/contractor/billing/meter", headers=Hc, timeout=30).json()
        assert m1["drops_used"] == pre_drops + 1
        # Audit log
        log = requests.get(f"{API}/contractor/jobs/{pytest.v22_job_id}/audit-log",
                           headers=Hc, timeout=30).json()
        events = [e["event"] for e in log["events"]]
        assert "LAUNCH_AUTHORIZED" in events
        # Ascending timestamps
        ts = [e["ts"] for e in log["events"]]
        assert ts == sorted(ts)


# ---------- Dry-run ----------
class TestDryRun:
    @pytest.fixture(scope="class")
    def dryrun_job(self, contractor_auth):
        H, _ = contractor_auth
        body = {
            "property_address": "TEST_v22_DRYRUN 9 Locked Gate Ln, Louisville, KY",
            "lat": 38.2527, "lon": -85.7585,
            "homeowner_name": "Locked Gate",
            "homeowner_email": "",
            "homeowner_phone": "",
            "project_type": "Insurance Claim",
            "insurance_carrier": "Allstate",
            "roof_style": "cross_hip",
            "notes": "dry-run test",
        }
        r = requests.post(f"{API}/contractor/jobs", headers=H, json=body, timeout=30)
        assert r.status_code == 200
        return r.json()["id"]

    def test_invalid_reason(self, dryrun_job, operator_auth):
        H, _ = operator_auth
        r = requests.post(f"{API}/operator/jobs/{dryrun_job}/dry-run",
                          headers=H, json={"reason": "alien_invasion"}, timeout=30)
        assert r.status_code == 400

    def test_dryrun_flag_locked_gate(self, dryrun_job, operator_auth, contractor_auth):
        Ho, _ = operator_auth
        Hc, _ = contractor_auth
        m0 = requests.get(f"{API}/contractor/billing/meter", headers=Hc, timeout=30).json()
        pre = m0["dry_run_charges_usd"]
        pre_count = m0["dry_run_count"]
        r = requests.post(f"{API}/operator/jobs/{dryrun_job}/dry-run",
                          headers=Ho, json={"reason": "locked_gate", "notes": "Gate locked, no answer"}, timeout=30)
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["status"] == "DRY_RUN_PENALTY"
        m1 = requests.get(f"{API}/contractor/billing/meter", headers=Hc, timeout=30).json()
        assert m1["dry_run_charges_usd"] == pre + 150.0
        assert m1["dry_run_count"] == pre_count + 1
        # audit
        log = requests.get(f"{API}/contractor/jobs/{dryrun_job}/audit-log",
                           headers=Hc, timeout=30).json()
        assert any(e["event"] == "DRY_RUN_FLAGGED" for e in log["events"])


# ---------- Audit log auth ----------
class TestAuditAuth:
    def test_other_contractor_cant_read(self, operator_auth):
        Ho, _ = operator_auth
        # Operator is not a contractor — should 403 (role gate) or 404
        r = requests.get(f"{API}/contractor/jobs/{pytest.v22_job_id}/audit-log",
                         headers=Ho, timeout=30)
        assert r.status_code in (403, 404)


# ---------- Phase1 gate on launch ----------
class TestLaunchRequiresPhase1:
    def test_launch_without_phase1(self, contractor_auth, operator_auth):
        Hc, _ = contractor_auth
        Ho, _ = operator_auth
        # Create job, do NOT run phase1, try to launch
        body = {
            "property_address": "TEST_v22_NOPH1 5 Skip Phase1 St",
            "lat": 38.0, "lon": -84.5,
            "homeowner_name": "Skip",
            "homeowner_email": "",
            "project_type": "Insurance Claim",
            "roof_style": "cross_hip",
        }
        r = requests.post(f"{API}/contractor/jobs", headers=Hc, json=body, timeout=30)
        assert r.status_code == 200
        jid = r.json()["id"]
        # job is in PENDING_PHASE1 — launch must reject (status check OR phase1 check)
        preflight = {
            "homeowner_verified": True, "vertical_obstruction_clear": True,
            "k9_and_child_clear_zone": True, "trailer_hatch_secured": True,
            "drone_battery_percentage": 100, "battery_cell_variance_v": 0.015,
            "rtk_gps_signal": "Centimeter-Level Locked",
            "communication_uplink": "Strong / Starlink Verified",
            "local_weather_clear": True, "personnel_clear": True,
        }
        r2 = requests.post(f"{API}/operator/jobs/{jid}/launch", headers=Ho, json=preflight, timeout=30)
        assert r2.status_code == 400
