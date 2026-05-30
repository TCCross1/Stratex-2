"""STRATEX iteration 17 - Backend regression for new features.

Coverage:
  - Auth login (admin + contractor) via TOTP debug
  - /api/contractor/deliverable/crown-demo full payload structure
  - Demo bypass: contractor (anthony) can access crown-demo job
  - /api/admin/ops/sku-forecast
  - Quote builder: create + promote-to-job flow
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stratex-quant.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@stratex.io"
ADMIN_PASSWORD = "StratexAdmin!2026"
CONTRACTOR_EMAIL = "anthony@apexroofing.com"
CONTRACTOR_PASSWORD = "Contractor!2026"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------
def _fetch_totp(email: str) -> str:
    r = requests.get(f"{API}/auth/totp-debug", params={"email": email}, timeout=15)
    assert r.status_code == 200, f"totp-debug failed: {r.status_code} {r.text}"
    code = r.json().get("current_code")
    assert code and len(code) == 6, f"bad totp code: {r.json()}"
    return code


def _login(email: str, password: str) -> str:
    code = _fetch_totp(email)
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password, "totp_code": code},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token in login response: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def admin_token() -> str:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def contractor_token() -> str:
    return _login(CONTRACTOR_EMAIL, CONTRACTOR_PASSWORD)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def contractor_headers(contractor_token):
    return {"Authorization": f"Bearer {contractor_token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# 1. Auth — both roles
# ---------------------------------------------------------------------------
class TestAuth:
    def test_admin_login(self, admin_token):
        assert isinstance(admin_token, str) and len(admin_token) > 20

    def test_contractor_login(self, contractor_token):
        assert isinstance(contractor_token, str) and len(contractor_token) > 20


# ---------------------------------------------------------------------------
# 2. Deliverable — full payload + demo bypass
# ---------------------------------------------------------------------------
class TestDeliverableCrownDemo:
    REQUIRED_TOP_KEYS = [
        "deliverable_id", "client", "flight", "roof",
        "geometrics_extended", "moisture_diagnostics", "anomalies",
        "financial_phases", "pricing", "disposal_logistics",
    ]

    def test_contractor_bypass_can_load_crown_demo(self, contractor_headers):
        """Anthony (contractor) does NOT own crown-demo (Crown Roofing job) but
        the is_demo whitelist in routes/deliverable.py line ~30 should allow it."""
        r = requests.get(f"{API}/contractor/deliverable/crown-demo", headers=contractor_headers, timeout=20)
        assert r.status_code == 200, f"demo bypass broken: {r.status_code} {r.text}"
        data = r.json()
        for k in self.REQUIRED_TOP_KEYS:
            assert k in data, f"missing key {k} in deliverable payload"
        assert data["deliverable_id"].startswith("STRATEX-"), data["deliverable_id"]

    def test_admin_loads_crown_demo(self, admin_headers):
        r = requests.get(f"{API}/contractor/deliverable/crown-demo", headers=admin_headers, timeout=20)
        assert r.status_code == 200
        data = r.json()
        # Ensure top-level keys are populated, not just present
        assert data["client"].get("name") and data["client"]["name"] != "—"
        assert data["roof"].get("total_squares") is not None
        assert data["pricing"]["total_usd"] > 0

    def test_pricing_total_estimate(self, admin_headers):
        r = requests.get(f"{API}/contractor/deliverable/crown-demo", headers=admin_headers, timeout=20)
        data = r.json()
        # Spec expects ~ $51,854.60 total
        total = data["pricing"]["total_usd"]
        assert abs(total - 51854.60) < 1.0, f"total {total} not within $1 of $51,854.60"

    def test_anomalies_and_moisture_populated(self, admin_headers):
        r = requests.get(f"{API}/contractor/deliverable/crown-demo", headers=admin_headers, timeout=20)
        data = r.json()
        assert isinstance(data["anomalies"], list) and len(data["anomalies"]) > 0, "anomalies empty"
        assert isinstance(data["moisture_diagnostics"], list) and len(data["moisture_diagnostics"]) > 0, "moisture empty"
        assert isinstance(data["geometrics_extended"], dict) and data["geometrics_extended"]
        assert isinstance(data["financial_phases"], dict) and data["financial_phases"]
        assert isinstance(data["disposal_logistics"], dict) and data["disposal_logistics"]


# ---------------------------------------------------------------------------
# 3. SKU Forecast
# ---------------------------------------------------------------------------
class TestSkuForecast:
    def test_admin_sku_forecast(self, admin_headers):
        r = requests.get(f"{API}/admin/ops/sku-forecast", headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "rows" in data and isinstance(data["rows"], list)
        assert "summary" in data
        for key in ("total_skus", "skus_with_demand", "reorder_alerts", "total_forecast_value_usd"):
            assert key in data["summary"], key
        # Validate row shape if there are any
        if data["rows"]:
            row = data["rows"][0]
            for k in ("material_id", "sku", "name", "qty_demanded", "tier_breakdown", "reorder_signal"):
                assert k in row, f"row missing {k}"

    def test_contractor_cannot_access_sku_forecast(self, contractor_headers):
        r = requests.get(f"{API}/admin/ops/sku-forecast", headers=contractor_headers, timeout=15)
        assert r.status_code in (401, 403), f"contractor should be forbidden, got {r.status_code}"


# ---------------------------------------------------------------------------
# 4. Quote Builder — create + promote-to-job
# ---------------------------------------------------------------------------
class TestQuoteBuilderPromote:
    def test_full_promote_flow(self, contractor_headers):
        # a. catalog
        r = requests.get(f"{API}/contractor/quote-builder/catalog", headers=contractor_headers, timeout=15)
        assert r.status_code == 200, r.text
        catalog = r.json()
        assert catalog.get("materials"), "empty catalog"
        material = catalog["materials"][0]

        # b. create quote
        body = {
            "title": "TEST_promote_iter17",
            "markup_pct": 0.25,
            "lines": [{"material_id": material["id"], "quantity": 10}],
            "notes": "TEST",
        }
        r = requests.post(f"{API}/contractor/quote-builder/quotes", headers=contractor_headers, json=body, timeout=15)
        assert r.status_code == 200, r.text
        quote = r.json()
        assert quote["status"] == "draft"
        assert quote["total_usd"] > 0
        quote_id = quote["id"]

        # c. eligible jobs
        r = requests.get(f"{API}/contractor/quote-builder/eligible-jobs", headers=contractor_headers, timeout=15)
        assert r.status_code == 200, r.text
        jobs = r.json().get("jobs", [])
        if not jobs:
            pytest.skip("Contractor has no eligible jobs to promote to — non-blocking")
        job_id = jobs[0]["job_id"]

        # d. promote
        r = requests.post(
            f"{API}/contractor/quote-builder/quotes/{quote_id}/promote",
            headers=contractor_headers,
            json={"job_id": job_id},
            timeout=15,
        )
        assert r.status_code == 200, f"promote failed: {r.status_code} {r.text}"
        result = r.json()
        assert result["ok"] is True
        assert result["job_id"] == job_id
        assert result["quote_id"] == quote_id
        assert result["total_usd"] == quote["total_usd"]

        # e. verify quote is now promoted
        r = requests.get(f"{API}/contractor/quote-builder/quotes", headers=contractor_headers, timeout=15)
        assert r.status_code == 200
        listing = r.json()
        match = next((q for q in listing["quotes"] if q["id"] == quote_id), None)
        assert match is not None, "promoted quote not in listing"
        assert match["status"] == "promoted"
        assert match["job_id"] == job_id

    def test_promote_unknown_quote_404(self, contractor_headers):
        r = requests.post(
            f"{API}/contractor/quote-builder/quotes/quote-doesnotexist/promote",
            headers=contractor_headers,
            json={"job_id": "any"},
            timeout=15,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 5. Deck route reachability (frontend route, but verify the demo endpoint
#    powering it is still healthy)
# ---------------------------------------------------------------------------
class TestDeckBackend:
    def test_deck_uses_same_deliverable_endpoint(self, contractor_headers):
        # The /deck/demo page in frontend simply calls /api/contractor/deliverable/crown-demo
        r = requests.get(f"{API}/contractor/deliverable/crown-demo", headers=contractor_headers, timeout=20)
        assert r.status_code == 200
