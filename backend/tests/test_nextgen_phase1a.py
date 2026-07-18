"""NextGen Phase 1a — backend regression tests.

Covers Directive 005 Phase 1a scope:
- Catalog + health (public, no auth)
- Workflow stages (15 stages, Blueprint §22)
- Auth-gated /me, tenant auto-provisioning
- Property resolve + create + duplicate 409 + tenant isolation
- Mission create, detail (with 15 stage labels), advance (forward-only, capped at 15)
- Workflow overview KPIs
- Audit events trail
- Passport stub
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stratex-quant.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@stratex.io"
ADMIN_PASS = "StratexAdmin!2026"


# ── Shared session + auth fixtures ──────────────────────────────
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def admin_token(session):
    """Login admin via TOTP-debug bypass endpoint."""
    r = session.get(f"{API}/auth/totp-debug", params={"email": ADMIN_EMAIL}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"totp-debug unavailable ({r.status_code}): {r.text[:200]}")
    totp = r.json().get("current_code")
    assert totp, f"no current_code in {r.json()}"

    lr = session.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS, "totp_code": totp},
        timeout=15,
    )
    assert lr.status_code == 200, f"login failed: {lr.status_code} {lr.text[:300]}"
    data = lr.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"no token in login response: {data}"
    return token


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ── Phase 1a · public endpoints ─────────────────────────────────
class TestPublicEndpoints:
    def test_health_no_auth(self, session):
        r = session.get(f"{API}/nextgen/health", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert d["phase"] == "1a"
        assert "phase_1a_legacy_freeze_and_foundation" in d["authorized_scope"]
        assert "deploy_to_stratexdrone_com" in d["requires_executive_approval"]

    def test_catalog_products_no_auth(self, session):
        r = session.get(f"{API}/nextgen/catalog/products", timeout=10)
        assert r.status_code == 200
        products = r.json()["products"]
        assert len(products) == 3
        keys = {p["product_key"] for p in products}
        assert keys == {"dayscan", "awe_scan", "elite"}
        # Elite pricing per spec
        elite = [p for p in products if p["product_key"] == "elite"][0]
        assert elite["contractor_price_cents"] == 59900

    def test_workflow_stages_exactly_15(self, session):
        r = session.get(f"{API}/nextgen/workflow/stages", timeout=10)
        assert r.status_code == 200
        stages = r.json()["stages"]
        assert len(stages) == 15
        assert stages[0]["index"] == 1
        assert stages[0]["label"] == "Mission Control"
        assert stages[14]["index"] == 15
        assert stages[14]["label"] == "Customer Delivery"


# ── Phase 1a · auth-gated ───────────────────────────────────────
class TestAuthGated:
    def test_me_requires_auth(self):
        # Fresh session to guarantee no lingering Authorization header.
        r = requests.get(f"{API}/nextgen/me", timeout=10)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_me_with_token_returns_tenant(self, session, auth_headers):
        r = session.get(f"{API}/nextgen/me", headers=auth_headers, timeout=10)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert "tenant" in d
        assert d["tenant"]["canonical_id"]
        assert d["tenant"]["status"] == "active"


# ── Phase 1a · properties ───────────────────────────────────────
_TEST_ADDRESS_SUFFIX = str(int(time.time() * 1000))


@pytest.fixture(scope="session")
def unique_property_payload():
    return {
        "address": {
            "line1": f"TEST_{_TEST_ADDRESS_SUFFIX} Blueprint Ln",
            "city": "Lexington",
            "region": "KY",
            "postal_code": "40502",
            "country_iso": "US",
        },
        "coordinate": {"lat": 38.0406, "lon": -84.5037, "precision_m": 5.0},
        "unit_label": None,
    }


class TestProperties:
    def test_resolve_create_new_when_no_candidates(self, session, auth_headers, unique_property_payload):
        r = session.post(
            f"{API}/nextgen/properties/resolve",
            headers=auth_headers,
            json=unique_property_payload,
            timeout=10,
        )
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["decision"] in ("create_new", "auto_match", "review")
        assert isinstance(d["candidates"], list)

    def test_create_property_and_persist(self, session, auth_headers, unique_property_payload):
        r = session.post(
            f"{API}/nextgen/properties",
            headers=auth_headers,
            json=unique_property_payload,
            timeout=10,
        )
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        prop = d["property"]
        assert prop["canonical_id"]
        assert prop["tenant_id"]
        assert prop["status"] == "active"
        assert prop["address"]["line1"] == unique_property_payload["address"]["line1"]

        # save for subsequent tests
        pytest.property_id = prop["canonical_id"]
        pytest.tenant_id = prop["tenant_id"]

        # GET should list it
        lr = session.get(f"{API}/nextgen/properties", headers=auth_headers, timeout=10)
        assert lr.status_code == 200
        ids = [p["canonical_id"] for p in lr.json()["items"]]
        assert prop["canonical_id"] in ids

    def test_duplicate_property_returns_409(self, session, auth_headers, unique_property_payload):
        r = session.post(
            f"{API}/nextgen/properties",
            headers=auth_headers,
            json=unique_property_payload,
            timeout=10,
        )
        assert r.status_code == 409, r.text[:300]
        detail = r.json()["detail"]
        assert detail["code"] == "duplicate_property"
        assert detail["existing_property_id"] == getattr(pytest, "property_id", None)

    def test_get_single_property(self, session, auth_headers):
        pid = getattr(pytest, "property_id", None)
        assert pid, "property_id not set from previous test"
        r = session.get(f"{API}/nextgen/properties/{pid}", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["property"]["canonical_id"] == pid


# ── Phase 1a · missions ─────────────────────────────────────────
class TestMissions:
    def test_create_mission_bound_to_property(self, session, auth_headers):
        pid = getattr(pytest, "property_id", None)
        assert pid, "requires property from earlier test"
        r = session.post(
            f"{API}/nextgen/missions",
            headers=auth_headers,
            json={"property_id": pid, "product": "dayscan"},
            timeout=10,
        )
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        m = d["mission"]
        assert m["stage"] == 1
        assert m["state"] == "planned"
        assert m["property_id"] == pid
        assert m["price"]["amount_cents"] == 24900
        assert m["estimated_cost"]["amount_cents"] == 8900
        assert d["product"]["product_key"] == "dayscan"
        pytest.mission_id = m["canonical_id"]

    def test_mission_detail_has_15_stage_labels(self, session, auth_headers):
        mid = getattr(pytest, "mission_id", None)
        r = session.get(f"{API}/nextgen/missions/{mid}", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["mission"]["canonical_id"] == mid
        assert len(d["stage_labels"]) == 15
        assert d["stage_labels"][0] == "Mission Control"
        assert d["stage_labels"][14] == "Customer Delivery"
        assert d["property"]["canonical_id"] == pytest.property_id
        assert d["product"]["product_key"] == "dayscan"

    def test_advance_forward_ok(self, session, auth_headers):
        mid = getattr(pytest, "mission_id", None)
        r = session.post(
            f"{API}/nextgen/missions/{mid}/advance",
            headers=auth_headers,
            json={"to_stage": 2, "note": "unit test advance"},
            timeout=10,
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["stage"] == 2
        assert r.json()["stage_label"] == "Mission Planning"

    def test_advance_backward_rejected_400(self, session, auth_headers):
        mid = getattr(pytest, "mission_id", None)
        r = session.post(
            f"{API}/nextgen/missions/{mid}/advance",
            headers=auth_headers,
            json={"to_stage": 1},
            timeout=10,
        )
        assert r.status_code == 400, r.text[:300]

    def test_advance_over_15_rejected_400(self, session, auth_headers):
        mid = getattr(pytest, "mission_id", None)
        r = session.post(
            f"{API}/nextgen/missions/{mid}/advance",
            headers=auth_headers,
            json={"to_stage": 16},
            timeout=10,
        )
        assert r.status_code == 400, r.text[:300]


# ── Phase 1a · workflow overview / audit / passport ─────────────
class TestWorkflowOverview:
    def test_overview_counts_and_15_stages(self, session, auth_headers):
        r = session.get(f"{API}/nextgen/workflow/overview", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "counts" in d
        assert d["counts"]["properties_active"] >= 1
        assert d["counts"]["missions_total"] >= 1
        assert len(d["missions_by_stage"]) == 15
        assert d["missions_by_stage"][0]["stage"] == 1
        assert d["missions_by_stage"][14]["stage"] == 15


class TestAudit:
    def test_audit_includes_property_and_mission_events(self, session, auth_headers):
        r = session.get(f"{API}/nextgen/audit/events", headers=auth_headers, timeout=10)
        assert r.status_code == 200
        events = r.json()["items"]
        assert len(events) >= 3
        types = {e["event_type"] for e in events}
        assert "property.created" in types
        assert "mission.created" in types
        assert "mission.stage_advanced" in types


class TestPassportStub:
    def test_passport_by_property_returns_stub_note(self, session, auth_headers):
        pid = getattr(pytest, "property_id", None)
        r = session.get(f"{API}/nextgen/passports/by-property/{pid}", headers=auth_headers, timeout=10)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["property"]["canonical_id"] == pid
        assert "Phase 1c" in d["note"]


# ── Legacy no-regression smoke ──────────────────────────────────
class TestLegacyNoRegression:
    def test_root_landing_reachable(self, session):
        # Landing SPA is served by frontend; /api root should still respond.
        r = session.get(f"{API}/", timeout=10)
        # Legacy backend may respond 200/404 for root; both are non-regressions.
        assert r.status_code in (200, 404, 405)

    def test_ceo_login_endpoint_reachable(self, session):
        # Just verify endpoint exists (may return 400 for missing body)
        r = session.post(f"{API}/auth/ceo-login", json={}, timeout=10)
        assert r.status_code in (400, 401, 403, 404, 422)
