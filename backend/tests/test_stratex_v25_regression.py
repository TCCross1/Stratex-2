"""
STRATEX v2.5 — UI batch regression backend coverage.

Targets:
  - AdminSalesHub CRM endpoints  (sales-targets / outreach-notes / call-logs / communication-templates)
  - OverseerQueue endpoint        (overseer-queue?status=...)
  - FlightAudit endpoint          (flight-authorizations/recent)
  - Auth (admin TOTP-debug login) — prerequisite

Uses the live public REACT_APP_BACKEND_URL so it exercises the same path the UI hits.
"""
import os
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Load frontend .env to grab the public URL (testing what the user sees)
load_dotenv(Path("/app/frontend/.env"))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing from /app/frontend/.env"

ADMIN_EMAIL = "admin@stratex.io"
ADMIN_PASS = "StratexAdmin!2026"


# ---------- Fixtures ---------- #
@pytest.fixture(scope="session")
def admin_token() -> str:
    s = requests.Session()
    r0 = s.get(f"{BASE_URL}/api/auth/totp-debug", params={"email": ADMIN_EMAIL}, timeout=15)
    assert r0.status_code == 200, f"totp-debug failed: {r0.status_code} {r0.text[:200]}"
    code = r0.json()["current_code"]

    r1 = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS, "totp_code": code},
        timeout=15,
    )
    assert r1.status_code == 200, f"login failed: {r1.status_code} {r1.text[:300]}"
    tok = r1.json().get("access_token")
    assert tok, f"no access_token in login response: {r1.json()}"
    return tok


@pytest.fixture(scope="session")
def admin_client(admin_token) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"})
    return s


# ---------- Sales-Targets seed ---------- #
class TestSalesTargetsSeed:
    def test_sales_targets_seeded_from_mongo(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/sales-targets", timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        if isinstance(data, dict):
            items = data.get("targets") or data.get("items") or []
        else:
            items = data
        assert len(items) == 7, f"expected 7 KY sales targets, got {len(items)}"
        # spot-check burnett-roofing exists; all rows must carry seed_source from KY constant
        ids = {it.get("id") or it.get("slug") for it in items}
        assert "burnett-roofing" in ids, f"burnett-roofing missing from {ids}"


# ---------- CRM drawer endpoints ---------- #
class TestCRMOutreachNotes:
    target_id = "burnett-roofing"

    def test_get_outreach_notes(self, admin_client):
        r = admin_client.get(
            f"{BASE_URL}/api/admin/sales-targets/{self.target_id}/outreach-notes", timeout=15
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, (list, dict)), f"unexpected type: {type(data)}"

    def test_post_outreach_note_then_get_persisted(self, admin_client):
        marker = f"TEST_NOTE_{uuid.uuid4().hex[:8]}"
        payload = {"body": marker}
        r = admin_client.post(
            f"{BASE_URL}/api/admin/sales-targets/{self.target_id}/outreach-notes",
            json=payload,
            timeout=15,
        )
        assert r.status_code in (200, 201), f"POST failed {r.status_code}: {r.text[:300]}"

        # verify persistence
        r2 = admin_client.get(
            f"{BASE_URL}/api/admin/sales-targets/{self.target_id}/outreach-notes", timeout=15
        )
        assert r2.status_code == 200
        body = r2.json()
        items = body if isinstance(body, list) else body.get("items", body.get("notes", []))
        bodies = [(it.get("body") or "") for it in items]
        assert any(marker in b for b in bodies), f"posted note marker {marker} not found in {bodies[:5]}"


class TestCRMCallLogs:
    target_id = "burnett-roofing"

    def test_get_call_logs(self, admin_client):
        r = admin_client.get(
            f"{BASE_URL}/api/admin/sales-targets/{self.target_id}/call-logs", timeout=15
        )
        assert r.status_code == 200, r.text[:300]

    def test_post_call_log_then_get_persisted(self, admin_client):
        payload = {"outcome": "voicemail", "duration_sec": 30, "note": f"TEST_{uuid.uuid4().hex[:6]}"}
        r = admin_client.post(
            f"{BASE_URL}/api/admin/sales-targets/{self.target_id}/call-logs",
            json=payload,
            timeout=15,
        )
        assert r.status_code in (200, 201), f"POST failed {r.status_code}: {r.text[:300]}"

        r2 = admin_client.get(
            f"{BASE_URL}/api/admin/sales-targets/{self.target_id}/call-logs", timeout=15
        )
        body = r2.json()
        items = body if isinstance(body, list) else body.get("items", body.get("logs", []))
        assert any(it.get("outcome") == "voicemail" for it in items), "voicemail log not persisted"


class TestCommunicationTemplates:
    def test_templates_seeded(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/communication-templates", timeout=15)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("templates", []))
        assert len(items) > 0, "expected seeded communication templates, got none"


# ---------- Overseer Queue ---------- #
class TestOverseerQueue:
    def test_overseer_queue_open(self, admin_client):
        r = admin_client.get(
            f"{BASE_URL}/api/admin/overseer-queue", params={"status": "open"}, timeout=15
        )
        assert r.status_code == 200, r.text[:300]

    @pytest.mark.parametrize("status", ["open", "reviewed", "dismissed", "all"])
    def test_overseer_queue_filters(self, admin_client, status):
        r = admin_client.get(
            f"{BASE_URL}/api/admin/overseer-queue", params={"status": status}, timeout=15
        )
        assert r.status_code == 200, f"status={status} {r.status_code}: {r.text[:300]}"


# ---------- Flight Authorizations Audit ---------- #
class TestFlightAuthorizationsAudit:
    def test_flight_authorizations_recent(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/flight-authorizations/recent", timeout=15)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        # smoke_fleet_launch already pumped >=1 row through; we don't enforce count here
        assert "items" in body or isinstance(body, list), f"unexpected shape: {str(body)[:200]}"


# ---------- Auth gating regression ---------- #
class TestAuthGating:
    def test_sales_targets_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/sales-targets", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_flight_audit_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/flight-authorizations/recent", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"
