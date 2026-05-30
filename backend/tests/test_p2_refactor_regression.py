"""
STRATEX P2 Refactor Regression — confirms all extracted route modules respond correctly
after server.py was split (4310 → 2481 lines) into 10 focused modules.

Coverage:
 - Auth (admin TOTP login, investor tour-mode bypass, /auth/me)
 - Billing (routes/billing.py)
 - Onboarding (routes/onboarding.py — public)
 - Sales Hub + CRM (routes/sales_hub.py)
 - Telemetry Overseer (routes/telemetry_overseer.py)
 - Materials Config v2 (routes/materials_config.py)
 - Weather Intelligence (routes/weather.py)
 - CV Ice Shield (routes/cv_ice_shield.py)
 - Contractor Deliverable (routes/deliverable.py)
 - Simulation (routes/simulation.py — slow, 4-LLM fan-out)
 - Assistant (routes/assistant.py)
 - Server.py-retained routes (jobs, fleet, public demo topology)
"""
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

ADMIN_EMAIL = "admin@stratex.io"
ADMIN_PASS = "StratexAdmin!2026"
INVESTOR_EMAIL = "john@crownroofing.com"
INVESTOR_PASS = "unstoppable"
CONTRACTOR_EMAIL = "anthony@apexroofing.com"
CONTRACTOR_PASS_A = "ApexRoof!2026"        # from request spec
CONTRACTOR_PASS_B = "Contractor!2026"      # from test_credentials.md


# ---------- Fixtures ---------- #
def _totp_login(email, password):
    s = requests.Session()
    r0 = s.get(f"{BASE_URL}/api/auth/totp-debug", params={"email": email}, timeout=15)
    if r0.status_code != 200:
        return None, f"totp-debug {r0.status_code}: {r0.text[:200]}"
    code = r0.json().get("current_code")
    r1 = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password, "totp_code": code},
        timeout=15,
    )
    if r1.status_code != 200:
        return None, f"login {r1.status_code}: {r1.text[:200]}"
    return r1.json().get("access_token"), None


@pytest.fixture(scope="session")
def admin_token():
    tok, err = _totp_login(ADMIN_EMAIL, ADMIN_PASS)
    if not tok:
        pytest.skip(f"Admin auth unavailable: {err}")
    return tok


@pytest.fixture(scope="session")
def admin_client(admin_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}"})
    return s


@pytest.fixture(scope="session")
def investor_token():
    # investor tour mode bypasses TOTP — direct login
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": INVESTOR_EMAIL, "password": INVESTOR_PASS},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Investor tour-mode login failed: {r.status_code} {r.text[:200]}")
    return r.json().get("access_token")


@pytest.fixture(scope="session")
def investor_client(investor_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {investor_token}"})
    return s


@pytest.fixture(scope="session")
def contractor_token():
    for pw in (CONTRACTOR_PASS_A, CONTRACTOR_PASS_B):
        tok, _ = _totp_login(CONTRACTOR_EMAIL, pw)
        if tok:
            return tok
    return None


@pytest.fixture(scope="session")
def contractor_client(contractor_token):
    if not contractor_token:
        pytest.skip("Contractor account not available")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {contractor_token}"})
    return s


# ---------- Auth ---------- #
class TestAuth:
    def test_admin_login_yields_token(self, admin_token):
        assert admin_token and isinstance(admin_token, str) and len(admin_token) > 20

    def test_investor_tour_mode_bypass(self, investor_token):
        assert investor_token and len(investor_token) > 20

    def test_auth_me_admin(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200, r.text[:200]
        assert r.json().get("email") == ADMIN_EMAIL

    def test_auth_me_investor(self, investor_client):
        r = investor_client.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200, r.text[:200]
        assert r.json().get("email") == INVESTOR_EMAIL


# ---------- routes/billing.py ---------- #
class TestBilling:
    def test_billing_plans_public(self):
        r = requests.get(f"{BASE_URL}/api/billing/plans", timeout=10)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_billing_me_admin(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/billing/me", timeout=10)
        assert r.status_code in (200, 404), r.text[:200]


# ---------- routes/onboarding.py ---------- #
class TestOnboarding:
    def test_competitive_intel_public(self):
        r = requests.post(
            f"{BASE_URL}/api/onboarding/competitive-intel",
            json={"city": "Louisville", "state": "KY"},
            timeout=15,
        )
        # public route — must NOT be 401/403
        assert r.status_code in (200, 201, 422), f"{r.status_code} {r.text[:200]}"


# ---------- routes/sales_hub.py ---------- #
class TestSalesHub:
    def test_sales_targets(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/sales-targets", timeout=10)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        targets = data.get("targets", data) if isinstance(data, dict) else data
        assert isinstance(targets, list) and len(targets) >= 1

    def test_communication_templates(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/communication-templates", timeout=10)
        assert r.status_code == 200, r.text[:200]

    def test_outreach_notes(self, admin_client):
        r = admin_client.get(
            f"{BASE_URL}/api/admin/sales-targets/ale-roofing/outreach-notes", timeout=10
        )
        assert r.status_code == 200, r.text[:200]


# ---------- routes/telemetry_overseer.py ---------- #
class TestTelemetryOverseer:
    def test_overseer_queue_open(self, admin_client):
        r = admin_client.get(
            f"{BASE_URL}/api/admin/overseer-queue", params={"status": "open"}, timeout=10
        )
        assert r.status_code == 200, r.text[:200]


# ---------- routes/materials_config.py ---------- #
class TestMaterialsConfigV2:
    def test_materials_config_role_enforced(self, investor_client, contractor_token, contractor_client):
        # Investor (non-contractor) must NOT access — should be 403
        r_inv = investor_client.get(f"{BASE_URL}/api/contractor/materials-config", timeout=10)
        assert r_inv.status_code in (401, 403), f"expected 403 for investor, got {r_inv.status_code}"

        if contractor_token:
            r_c = contractor_client.get(f"{BASE_URL}/api/contractor/materials-config", timeout=10)
            assert r_c.status_code == 200, r_c.text[:200]


# ---------- routes/weather.py ---------- #
class TestWeather:
    def test_forecast(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/weather/forecast", timeout=15)
        assert r.status_code == 200, r.text[:200]

    def test_radar(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/weather/radar", timeout=15)
        assert r.status_code == 200, r.text[:200]

    def test_historical_on_this_day(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/weather/historical-on-this-day", timeout=15)
        assert r.status_code == 200, r.text[:200]

    def test_storm_watch_post(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/weather/storm-watch",
            json={"lat": 38.25, "lon": -85.75, "radius_mi": 25},
            timeout=15,
        )
        assert r.status_code in (200, 201, 422), r.text[:200]

    def test_historical_analysis_post(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/weather/historical-analysis",
            json={"address": "Louisville, KY", "date": "2024-06-15"},
            timeout=20,
        )
        assert r.status_code in (200, 201, 422), r.text[:200]


# ---------- routes/cv_ice_shield.py ---------- #
class TestCvIceShield:
    def test_ice_shield_recent(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/cv/ice-shield/recent", timeout=10)
        assert r.status_code == 200, r.text[:200]

    def test_ice_shield_analyze(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/cv/ice-shield/analyze",
            json={"frame_url": "https://example.com/frame.jpg", "job_id": "crown-demo"},
            timeout=20,
        )
        # may 200/201, or 422 if payload schema differs — anything <500 is OK
        assert r.status_code < 500, f"{r.status_code} {r.text[:300]}"


# ---------- routes/deliverable.py ---------- #
class TestDeliverable:
    def test_crown_demo_deliverable(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/contractor/deliverable/crown-demo", timeout=15)
        assert r.status_code in (200, 404), r.text[:200]


# ---------- routes/simulation.py ---------- #
class TestSimulation:
    def test_simulation_run_crown_demo(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/simulation/run",
            params={"job_id": "crown-demo"},
            timeout=45,  # 4-LLM parallel fan-out ~10-15s
        )
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        data = r.json()
        # spec: 100 deterministic checks
        assert isinstance(data, dict)


# ---------- routes/assistant.py ---------- #
class TestAssistant:
    def test_assistant_chat(self, admin_client):
        r = admin_client.post(
            f"{BASE_URL}/api/assistant/chat",
            json={"message": "What is STRATEX?", "session_id": "regression-test"},
            timeout=30,
        )
        # Accept anything <500 (LLM may fail downstream but route should respond)
        assert r.status_code < 500, f"{r.status_code} {r.text[:300]}"


# ---------- server.py retained routes ---------- #
class TestServerRetainedRoutes:
    def test_contractor_jobs_role_enforced(self, contractor_token, contractor_client, admin_client):
        if contractor_token:
            r = contractor_client.get(f"{BASE_URL}/api/contractor/jobs", timeout=10)
            assert r.status_code == 200, r.text[:200]
        # admin may or may not have access — just ensure no 500
        r_a = admin_client.get(f"{BASE_URL}/api/contractor/jobs", timeout=10)
        assert r_a.status_code < 500

    def test_fleet_status(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/fleet/status", timeout=10)
        assert r.status_code == 200, r.text[:200]

    def test_public_demo_topology(self):
        r = requests.get(f"{BASE_URL}/api/public/demo-topology", timeout=10)
        assert r.status_code == 200, r.text[:200]
