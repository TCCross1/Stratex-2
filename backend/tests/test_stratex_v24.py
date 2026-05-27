"""STRATEX v2.4 — Multi-agent expert panel validation + Caliper OCR endpoint tests.

Covers:
  1. /api/public/demo-topology returns `validation` object with 6 gates, score_pct=100
  2. Each validation gate has required keys: id, label, agent, pass, message, rule_ref
  3. POST /api/contractor/caliper-ocr requires contractor auth (401/403 without token)
  4. POST /api/contractor/caliper-ocr with valid token + tiny png returns clean JSON
     shape (ok, thickness_mm, thickness_in, confidence, fallback) — NOT a 500 error.
     Fallback=true is acceptable for a 1x1 transparent PNG.
  5. GET /api/contractor/materials includes `measured_thickness_mm` field (default 0.0)
  6. PUT /api/contractor/materials accepts and persists `measured_thickness_mm: 4.95`
"""
import base64
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CONTRACTOR_EMAIL = "anthony@apexroofing.com"
CONTRACTOR_PW = "Contractor!2026"

# 1x1 transparent PNG (smallest valid PNG)
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def _totp(email):
    r = requests.get(f"{API}/auth/totp-debug", params={"email": email}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["current_code"]


def _login(email, pw):
    # step 1 (primes the secret)
    requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    code = _totp(email)
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": pw, "totp_code": code},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def contractor_token():
    return _login(CONTRACTOR_EMAIL, CONTRACTOR_PW)


@pytest.fixture(scope="module")
def contractor_h(contractor_token):
    return {"Authorization": f"Bearer {contractor_token}"}


# ---------------------------------------------------------------
# 1+2. /public/demo-topology validation gates
# ---------------------------------------------------------------
class TestDemoTopologyValidation:
    def test_demo_topology_returns_validation_block(self):
        r = requests.get(f"{API}/public/demo-topology", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "validation" in body, "Expected `validation` key in /public/demo-topology"
        v = body["validation"]
        assert v is not None
        # 6 gates required
        assert "gates" in v
        assert isinstance(v["gates"], list)
        assert len(v["gates"]) == 6, f"Expected 6 gates, got {len(v['gates'])}"
        # totals
        assert v["total"] == 6
        assert v["passed"] == 6, f"Expected all 6 gates to pass, got passed={v['passed']}; gates={v['gates']}"
        assert v["all_pass"] is True
        assert v["score_pct"] == 100 or v["score_pct"] == 100.0

    def test_each_gate_has_required_keys(self):
        r = requests.get(f"{API}/public/demo-topology", timeout=30)
        body = r.json()
        gates = body["validation"]["gates"]
        REQUIRED = {"id", "label", "agent", "pass", "message", "rule_ref"}
        for g in gates:
            missing = REQUIRED - set(g.keys())
            assert not missing, f"Gate {g.get('id')} missing keys: {missing}"
            assert isinstance(g["pass"], bool), f"gate {g['id']} pass must be bool"
            assert isinstance(g["label"], str) and len(g["label"]) > 0
            assert isinstance(g["agent"], str) and len(g["agent"]) > 0
            assert isinstance(g["message"], str) and len(g["message"]) > 0
            assert isinstance(g["rule_ref"], str) and len(g["rule_ref"]) > 0

    def test_gate_ids_are_unique_and_expected(self):
        r = requests.get(f"{API}/public/demo-topology", timeout=30)
        body = r.json()
        gate_ids = [g["id"] for g in body["validation"]["gates"]]
        assert len(gate_ids) == len(set(gate_ids)), "Gate IDs must be unique"
        expected = {
            "slope_basis", "gutter_coverage", "rafter_count",
            "sub_fascia", "material_direction", "edge_hierarchy",
        }
        assert set(gate_ids) == expected, f"Gate IDs mismatch: {set(gate_ids)} vs {expected}"


# ---------------------------------------------------------------
# 3+4. Caliper OCR endpoint
# ---------------------------------------------------------------
class TestCaliperOCR:
    def test_caliper_ocr_requires_auth(self):
        """Without bearer token -> 401 or 403."""
        r = requests.post(
            f"{API}/contractor/caliper-ocr",
            json={"image_base64": TINY_PNG_B64, "mime_type": "image/png"},
            timeout=30,
        )
        assert r.status_code in (401, 403), \
            f"Expected 401/403 for unauth caliper-ocr, got {r.status_code}: {r.text}"

    def test_caliper_ocr_with_valid_token_returns_clean_shape(self, contractor_h):
        """Real test: should NEVER 500. May return fallback=true for tiny PNG."""
        r = requests.post(
            f"{API}/contractor/caliper-ocr",
            headers=contractor_h,
            json={"image_base64": TINY_PNG_B64, "mime_type": "image/png"},
            timeout=120,  # LLM call can be slow
        )
        # Must NOT be a 500
        assert r.status_code != 500, f"caliper-ocr 500 error: {r.text}"
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        body = r.json()
        # Required keys
        for key in ("ok", "thickness_mm", "thickness_in", "confidence", "fallback"):
            assert key in body, f"caliper-ocr response missing '{key}': {body}"
        # ok must be a bool
        assert isinstance(body["ok"], bool)
        assert isinstance(body["fallback"], bool)
        # confidence must be a known string
        assert body["confidence"] in ("high", "medium", "low", "none"), \
            f"Unexpected confidence value: {body['confidence']}"
        # If ok=true, must have non-null thickness; if ok=false, fallback should be true
        if body["ok"]:
            assert body["thickness_mm"] is not None
            assert body["thickness_in"] is not None
        else:
            # Acceptable for a 1x1 transparent PNG
            assert body["fallback"] is True, \
                f"ok=false should imply fallback=true; got {body}"


# ---------------------------------------------------------------
# 5+6. Materials measured_thickness_mm field
# ---------------------------------------------------------------
class TestMaterialsMeasuredThickness:
    def test_get_materials_includes_measured_thickness_mm(self, contractor_h):
        r = requests.get(f"{API}/contractor/materials", headers=contractor_h, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "measured_thickness_mm" in body, \
            f"materials missing measured_thickness_mm; keys={list(body.keys())}"
        # Should be a number (0.0 default OR previously persisted value)
        assert isinstance(body["measured_thickness_mm"], (int, float))

    def test_put_materials_persists_measured_thickness_mm(self, contractor_h):
        # First GET current full config to send full body back (avoid wiping fields)
        cur = requests.get(f"{API}/contractor/materials", headers=contractor_h, timeout=30).json()
        cur["measured_thickness_mm"] = 4.95

        r = requests.put(
            f"{API}/contractor/materials",
            headers=contractor_h,
            json=cur,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True, f"Expected ok=true, got {body}"

        # Verify persistence via GET
        r2 = requests.get(f"{API}/contractor/materials", headers=contractor_h, timeout=30)
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2["measured_thickness_mm"] == 4.95, \
            f"Expected measured_thickness_mm=4.95 persisted; got {body2.get('measured_thickness_mm')}"

    def test_put_materials_reset_measured_thickness_mm(self, contractor_h):
        """Reset to 0.0 so subsequent tests / app state remains clean."""
        cur = requests.get(f"{API}/contractor/materials", headers=contractor_h, timeout=30).json()
        cur["measured_thickness_mm"] = 0.0
        r = requests.put(f"{API}/contractor/materials", headers=contractor_h, json=cur, timeout=30)
        assert r.status_code == 200
