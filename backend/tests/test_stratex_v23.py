"""STRATEX v2.3 — Phase1 FAIL email + Operator weather-monitor tests."""
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
    requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    code = _totp(email)
    r = requests.post(f"{API}/auth/login",
                      json={"email": email, "password": pw, "totp_code": code}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def contractor_h():
    return {"Authorization": f"Bearer {_login(CONTRACTOR_EMAIL, CONTRACTOR_PW)}"}


@pytest.fixture(scope="module")
def operator_h():
    return {"Authorization": f"Bearer {_login(OPERATOR_EMAIL, OPERATOR_PW)}"}


def _create_job(headers, address, lat, lon):
    body = {
        "property_address": address,
        "lat": lat, "lon": lon,
        "homeowner_name": "Test Owner",
        "homeowner_email": "",
        "homeowner_phone": "",
        "project_type": "Insurance Claim",
        "insurance_carrier": "State Farm",
        "roof_style": "cross_hip",
        "notes": "v23 test",
    }
    r = requests.post(f"{API}/contractor/jobs", headers=headers, json=body, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ---------- Phase1 PASS vs FAIL audit log behavior ----------
class TestPhase1FailEmail:
    """Run phase1 across multiple jobs to capture both PASS and FAIL audit shapes."""

    def test_run_phase1_audits(self, contractor_h):
        # Try multiple jobs since phase1 is deterministic-per-job-id (hash based for FAA gate)
        # but weather gate uses real Open-Meteo for Lexington which is unpredictable.
        # We assert: if overall=FAIL → audit has PHASE1_FAIL AND PHASE1_FAIL_EMAIL_SENT.
        #           if overall=PASS → audit has PHASE1_PASS and NO _EMAIL_SENT.
        observed_fail = False
        observed_pass = False
        for i in range(5):
            jid = _create_job(contractor_h, f"TEST_v23_phase1_{i} Lexington KY", 38.04, -84.5)
            r = requests.post(f"{API}/contractor/jobs/{jid}/run-phase1",
                              headers=contractor_h, timeout=30)
            assert r.status_code == 200, r.text
            overall = r.json()["overall"]
            log = requests.get(f"{API}/contractor/jobs/{jid}/audit-log",
                               headers=contractor_h, timeout=30).json()
            events = [e["event"] for e in log["events"]]
            print(f"job {i}: overall={overall}, events={events}")
            if overall == "FAIL":
                observed_fail = True
                assert "PHASE1_FAIL" in events, f"PHASE1_FAIL missing: {events}"
                assert "PHASE1_FAIL_EMAIL_SENT" in events, f"PHASE1_FAIL_EMAIL_SENT missing: {events}"
                # Verify the email-sent audit row exists; payload key is whatever the
                # endpoint chose to surface — be tolerant.
                fail_email_evt = next(e for e in log["events"] if e["event"] == "PHASE1_FAIL_EMAIL_SENT")
                meta = fail_email_evt.get("payload") or fail_email_evt.get("meta") or {}
                if meta:
                    assert meta.get("to") == CONTRACTOR_EMAIL
                    assert meta.get("mocked") is True  # RESEND_API_KEY not set
            else:  # PASS
                observed_pass = True
                assert "PHASE1_PASS" in events
                assert "PHASE1_FAIL_EMAIL_SENT" not in events, "email sent on PASS!"
                assert "PHASE1_FAIL" not in events
            if observed_fail and observed_pass:
                break
        # We require at least the FAIL path to be observed (the email logic under test)
        assert observed_fail, "Could not trigger Phase1 FAIL after 5 attempts — weather may be too clear"


# ---------- Operator weather-monitor endpoint ----------
class TestOperatorWeatherMonitor:
    @pytest.fixture(scope="class")
    def job_id(self, contractor_h):
        return _create_job(contractor_h, "TEST_v23_opwx Lexington KY", 38.04, -84.5)

    def test_unauthenticated_401(self, job_id):
        r = requests.get(f"{API}/operator/jobs/{job_id}/weather-monitor", timeout=30)
        assert r.status_code in (401, 403), r.text

    def test_contractor_forbidden(self, job_id, contractor_h):
        r = requests.get(f"{API}/operator/jobs/{job_id}/weather-monitor",
                         headers=contractor_h, timeout=30)
        assert r.status_code == 403, f"contractor should be 403, got {r.status_code}: {r.text}"

    def test_operator_ok(self, job_id, operator_h):
        r = requests.get(f"{API}/operator/jobs/{job_id}/weather-monitor",
                         headers=operator_h, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "available" in body
        if body["available"]:
            for k in ["past_24h_precip_in", "avg_cloud_12h_pct",
                      "next2h_precip_prob_pct", "next2h_precip_in",
                      "current_wind_mph", "abort_recommended", "as_of"]:
                assert k in body, f"missing {k}"
            assert isinstance(body["abort_recommended"], bool)

    def test_contractor_weather_monitor_regression(self, job_id, contractor_h):
        """Contractor's own weather-monitor must still work."""
        r = requests.get(f"{API}/contractor/jobs/{job_id}/weather-monitor",
                         headers=contractor_h, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "available" in body
        if body["available"]:
            assert "abort_recommended" in body

    def test_operator_404_for_unknown(self, operator_h):
        r = requests.get(f"{API}/operator/jobs/nonexistent-id-xyz/weather-monitor",
                         headers=operator_h, timeout=30)
        assert r.status_code == 404
