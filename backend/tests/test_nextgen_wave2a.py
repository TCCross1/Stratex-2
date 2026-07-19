"""NextGen Wave 2A — Evidence Ingest + Canonical Mission Package.

Covers Directive 006 Wave 2A endpoints under /api/nextgen/v1/*:
- Evidence profiles (dayscan / awe_scan / elite)
- Upload with dedup, blocked exts, unknown category, OPERATIONAL 403
- Tenant isolation (mission-from-another-tenant 404)
- List / detail / download (X-Content-SHA256 header + streamed bytes)
- Delete pending, delete finalized (409)
- Package validate (FAIL / PASS)
- Package finalize (422 unmet, PASS creates row, second finalize v2)
- Outbox row (idempotency), audit events, manifest.json
"""
import io
import os
import time
import hashlib
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stratex-quant.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
V1 = f"{API}/nextgen/v1"

ADMIN_EMAIL = "admin@stratex.io"
ADMIN_PASS = "StratexAdmin!2026"
CONTRACTOR_EMAIL = "anthony@apexroofing.com"
CONTRACTOR_PASS = "Contractor!2026"


# ── Auth helpers ───────────────────────────────────────────────
def _login(session, email, password):
    r = session.get(f"{API}/auth/totp-debug", params={"email": email}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"totp-debug unavailable ({r.status_code}): {r.text[:200]}")
    totp = r.json().get("current_code")
    assert totp, r.text
    lr = session.post(
        f"{API}/auth/login",
        json={"email": email, "password": password, "totp_code": totp},
        timeout=15,
    )
    assert lr.status_code == 200, f"login {email} failed: {lr.status_code} {lr.text[:200]}"
    tok = lr.json().get("access_token") or lr.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    token = _login(s, ADMIN_EMAIL, ADMIN_PASS)
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def contractor_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    token = _login(s, CONTRACTOR_EMAIL, CONTRACTOR_PASS)
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ── Mission fixtures (admin tenant) ────────────────────────────
_TEST_SUFFIX = str(int(time.time() * 1000))


@pytest.fixture(scope="session")
def admin_mission_id(admin_session):
    payload = {
        "address": {
            "line1": f"TEST_W2A_{_TEST_SUFFIX} Evidence Way",
            "city": "Lexington", "region": "KY", "postal_code": "40502",
            "country_iso": "US",
        },
        "coordinate": {"lat": 38.0406, "lon": -84.5037, "precision_m": 5.0},
    }
    r = admin_session.post(f"{API}/nextgen/properties", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["property"]["canonical_id"]
    r = admin_session.post(
        f"{API}/nextgen/missions",
        json={"property_id": pid, "product": "dayscan"}, timeout=15,
    )
    assert r.status_code == 200, r.text
    mid = r.json()["mission"]["canonical_id"]
    return mid


@pytest.fixture(scope="session")
def admin_awe_mission_id(admin_session):
    payload = {
        "address": {
            "line1": f"TEST_W2A_{_TEST_SUFFIX} AWE Court",
            "city": "Lexington", "region": "KY", "postal_code": "40503",
            "country_iso": "US",
        },
        "coordinate": {"lat": 38.05, "lon": -84.5, "precision_m": 5.0},
    }
    r = admin_session.post(f"{API}/nextgen/properties", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["property"]["canonical_id"]
    r = admin_session.post(
        f"{API}/nextgen/missions",
        json={"property_id": pid, "product": "awe_scan"}, timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["mission"]["canonical_id"]


@pytest.fixture(scope="session")
def contractor_mission_id(contractor_session):
    payload = {
        "address": {
            "line1": f"TEST_W2A_{_TEST_SUFFIX} Contractor Rd",
            "city": "Lexington", "region": "KY", "postal_code": "40504",
            "country_iso": "US",
        },
        "coordinate": {"lat": 38.06, "lon": -84.49, "precision_m": 5.0},
    }
    r = contractor_session.post(f"{API}/nextgen/properties", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["property"]["canonical_id"]
    r = contractor_session.post(
        f"{API}/nextgen/missions",
        json={"property_id": pid, "product": "dayscan"}, timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["mission"]["canonical_id"]


# ── File builders ──────────────────────────────────────────────
def _png_bytes(seed: int = 0, w: int = 32, h: int = 32) -> bytes:
    """Deterministic within a test run, unique across test runs.

    Derives a full 32-byte SHA-256 salt from ``_TEST_SUFFIX + seed`` and
    paints those bytes across a strip of pixels — so every unique
    ``_TEST_SUFFIX`` produces a unique PNG SHA-256 without any salt-cycle
    truncation. Same seed within the same run still produces the same
    bytes (so ``test_duplicate_returns_409`` continues to work).
    Production duplicate protection is not weakened; only the test payload
    is per-run unique.
    """
    salt_bytes = hashlib.sha256(f"{_TEST_SUFFIX}:{seed}".encode()).digest()  # 32 bytes
    # Human-readable base color from seed (test still checks pixel dimensions).
    img = Image.new(
        "RGB", (w, h),
        color=(
            (seed * 7) % 255,
            (seed * 13) % 255,
            (seed * 29) % 255,
        ),
    )
    for x in range(w):
        img.putpixel((x, seed % h), (255, 0, 0))
    # Paint the full 32-byte session-unique salt across the top row so
    # every distinct ``_TEST_SUFFIX`` produces a distinct PNG SHA-256.
    for i in range(min(w, len(salt_bytes) // 3)):
        b = i * 3
        img.putpixel((i, 0), (salt_bytes[b], salt_bytes[b + 1], salt_bytes[b + 2]))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _upload(session, mission_id, filename, data, category, mime="image/png",
            is_original=True, intended_duplicate=False, mode="DEMO"):
    files = {"file": (filename, data, mime)}
    form = {
        "category": category,
        "is_original": str(is_original).lower(),
        "intended_duplicate": str(intended_duplicate).lower(),
        "mode": mode,
    }
    # Don't send Content-Type: application/json header for multipart
    headers = {k: v for k, v in session.headers.items() if k.lower() != "content-type"}
    return requests.post(
        f"{V1}/missions/{mission_id}/evidence",
        files=files, data=form, headers=headers, timeout=30,
    )


# ── Profiles ───────────────────────────────────────────────────
class TestEvidenceProfiles:
    def test_dayscan_profile(self, admin_session):
        r = admin_session.get(f"{V1}/evidence-profiles/dayscan", timeout=10)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["product_key"] == "dayscan"
        assert len(p["requirements"]) == 6
        by = {x["category"]: x for x in p["requirements"]}
        assert by["RGB_IMAGE"]["min_count"] == 12 and by["RGB_IMAGE"]["required"] is True
        assert by["FLIGHT_LOG"]["min_count"] == 1 and by["FLIGHT_LOG"]["required"] is True
        assert by["CAMERA_METADATA"]["required"] is False
        assert by["OPERATOR_NOTE"]["required"] is False
        assert by["VIDEO"]["required"] is False
        assert by["MANUAL_MEASUREMENT"]["required"] is False

    def test_awe_scan_profile(self, admin_session):
        r = admin_session.get(f"{V1}/evidence-profiles/awe_scan", timeout=10)
        assert r.status_code == 200
        cats = {x["category"] for x in r.json()["requirements"]}
        assert "THERMAL_RADIOMETRIC" in cats
        assert "WEATHER_RECORD" in cats

    def test_elite_profile(self, admin_session):
        r = admin_session.get(f"{V1}/evidence-profiles/elite", timeout=10)
        assert r.status_code == 200
        assert r.json()["product_key"] == "elite"

    def test_unknown_profile_404(self, admin_session):
        r = admin_session.get(f"{V1}/evidence-profiles/nope", timeout=10)
        assert r.status_code == 404


# ── Upload happy path + hash + metadata ────────────────────────
class TestUploadBasics:
    def test_upload_rgb_returns_hash_and_key(self, admin_session, admin_mission_id):
        data = _png_bytes(seed=1)
        expected_sha = hashlib.sha256(data).hexdigest()
        r = _upload(admin_session, admin_mission_id, "TEST_upload1.png", data, "RGB_IMAGE")
        assert r.status_code == 200, r.text
        body = r.json()
        ev = body["evidence"]
        assert ev["content_sha256"] == expected_sha
        assert ev["object_key"].startswith("nextgen://")
        assert ev["size_bytes"] == len(data)
        assert ev["role"] == "original"
        assert ev["mode"] == "DEMO"
        # best-effort metadata blob present
        assert "metadata" in body
        assert body["metadata"].get("dimensions") == {"width": 32, "height": 32}
        pytest.first_evidence_id = ev["canonical_id"]
        pytest.first_evidence_sha = expected_sha
        pytest.first_evidence_bytes = data

    def test_duplicate_returns_409(self, admin_session, admin_mission_id):
        data = _png_bytes(seed=1)  # same as previous
        r = _upload(admin_session, admin_mission_id, "TEST_upload1.png", data, "RGB_IMAGE")
        assert r.status_code == 409, r.text
        detail = r.json()["detail"]
        assert detail["code"] == "duplicate_detected"
        assert detail["existing_evidence_id"] == pytest.first_evidence_id

    def test_intended_duplicate_ok_creates_link(self, admin_session, admin_mission_id):
        data = _png_bytes(seed=1)
        r = _upload(admin_session, admin_mission_id, "TEST_upload1_dup.png", data,
                    "RGB_IMAGE", intended_duplicate=True)
        assert r.status_code == 200, r.text
        ev_id = r.json()["evidence"]["canonical_id"]
        # Fetch detail: relationships should include intentional_duplicate_of
        d = admin_session.get(f"{V1}/evidence/{ev_id}", timeout=10).json()
        rels = d["relationships"]
        assert any(x["relationship"] == "intentional_duplicate_of" for x in rels), rels

    def test_blocked_extension_415(self, admin_session, admin_mission_id):
        r = _upload(admin_session, admin_mission_id, "TEST_bad.exe", b"MZ\x00\x00", "OTHER",
                    mime="application/octet-stream")
        assert r.status_code == 415, r.text

    def test_unknown_category_400(self, admin_session, admin_mission_id):
        r = _upload(admin_session, admin_mission_id, "TEST_x.png", _png_bytes(seed=99),
                    "NOT_A_CATEGORY")
        assert r.status_code == 400, r.text

    def test_operational_mode_403(self, admin_session, admin_mission_id):
        r = _upload(admin_session, admin_mission_id, "TEST_op.png", _png_bytes(seed=98),
                    "RGB_IMAGE", mode="OPERATIONAL")
        assert r.status_code == 403, r.text

    def test_tenant_isolation_404(self, admin_session, contractor_mission_id):
        # admin tries to upload into contractor's mission → 404 (not-found on this tenant)
        r = _upload(admin_session, contractor_mission_id, "TEST_x.png", _png_bytes(seed=97),
                    "RGB_IMAGE")
        assert r.status_code == 404, r.text


# ── List / Detail / Download ───────────────────────────────────
class TestListDetailDownload:
    def test_list_evidence(self, admin_session, admin_mission_id):
        r = admin_session.get(f"{V1}/missions/{admin_mission_id}/evidence", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["count"] >= 2
        assert all("content_sha256" in it for it in d["items"])

    def test_detail_includes_meta_and_rels(self, admin_session):
        eid = pytest.first_evidence_id
        r = admin_session.get(f"{V1}/evidence/{eid}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["evidence"]["canonical_id"] == eid
        assert "metadata" in d
        assert isinstance(d["relationships"], list)

    def test_download_streams_bytes_and_header_matches(self, admin_session):
        eid = pytest.first_evidence_id
        r = admin_session.get(f"{V1}/evidence/{eid}/download", timeout=30, stream=True)
        assert r.status_code == 200
        content = r.content
        assert content == pytest.first_evidence_bytes
        assert r.headers.get("X-Content-SHA256") == pytest.first_evidence_sha


# ── Validate + Finalize ────────────────────────────────────────
class TestValidateFinalize:
    def test_validate_fail_when_unmet(self, admin_session, admin_mission_id):
        r = admin_session.post(
            f"{V1}/missions/{admin_mission_id}/package/validate", timeout=15,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["overall"] == "FAIL"
        # each requirement result present
        keys = {x["key"] for x in d["results"]}
        assert "required:RGB_IMAGE" in keys
        assert "required:FLIGHT_LOG" in keys

    def test_finalize_unmet_returns_422(self, admin_session, admin_mission_id):
        r = admin_session.post(
            f"{V1}/missions/{admin_mission_id}/package/finalize",
            json={"operator_notes": "premature"}, timeout=15,
        )
        assert r.status_code == 422, r.text
        detail = r.json()["detail"]
        assert detail["code"] == "package_validation_failed"
        assert "validation" in detail

    def test_meet_reqs_validate_pass_and_finalize(self, admin_session, admin_mission_id):
        # Upload more RGB to hit 12 unique (already 2 unique originals -> add 10 more).
        # Then a FLIGHT_LOG.
        for i in range(2, 13):
            r = _upload(admin_session, admin_mission_id, f"TEST_rgb_{i}.png",
                        _png_bytes(seed=i + 200), "RGB_IMAGE")
            assert r.status_code == 200, f"seed {i}: {r.status_code} {r.text[:180]}"
        # FLIGHT_LOG (per-run salted so we don't collide with a previous run's SHA in shared DBs)
        fl = _upload(admin_session, admin_mission_id, "TEST_flight.log",
                     f"# test_run={_TEST_SUFFIX}\ntime,lat,lon,alt\n0,38.04,-84.50,120\n".encode(),
                     "FLIGHT_LOG", mime="text/plain")
        assert fl.status_code == 200, fl.text

        v = admin_session.post(
            f"{V1}/missions/{admin_mission_id}/package/validate", timeout=15,
        ).json()
        assert v["overall"] == "PASS", v

        r = admin_session.post(
            f"{V1}/missions/{admin_mission_id}/package/finalize",
            json={"operator_notes": "ok"}, timeout=15,
        )
        assert r.status_code == 200, r.text
        pkg = r.json()["package"]
        assert pkg["package_version"] == 1
        assert pkg["status"] == "finalized"
        assert len(pkg["manifest_digest"]) == 64
        int(pkg["manifest_digest"], 16)  # sha-256 hex
        pytest.pkg1_id = pkg["canonical_id"]

    def test_mission_advanced_to_stage_7(self, admin_session, admin_mission_id):
        r = admin_session.get(f"{API}/nextgen/missions/{admin_mission_id}", timeout=15)
        assert r.status_code == 200
        assert r.json()["mission"]["stage"] >= 7

    def test_delete_of_finalized_evidence_409(self, admin_session):
        eid = pytest.first_evidence_id
        r = admin_session.delete(f"{V1}/evidence/{eid}", timeout=15)
        assert r.status_code == 409, r.text

    def test_second_finalize_creates_v2(self, admin_session, admin_mission_id):
        # Add another original (unique) then finalize again → v2
        extra = _upload(admin_session, admin_mission_id, "TEST_rgb_extra.png",
                        _png_bytes(seed=999), "RGB_IMAGE")
        assert extra.status_code == 200, extra.text
        r = admin_session.post(
            f"{V1}/missions/{admin_mission_id}/package/finalize",
            json={"operator_notes": "amended"}, timeout=15,
        )
        assert r.status_code == 200, r.text
        pkg = r.json()["package"]
        assert pkg["package_version"] == 2
        assert pkg["canonical_id"] != pytest.pkg1_id
        pytest.pkg2_id = pkg["canonical_id"]

    def test_list_packages_desc_by_version(self, admin_session, admin_mission_id):
        r = admin_session.get(f"{V1}/missions/{admin_mission_id}/packages", timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 2
        versions = [i["package_version"] for i in items]
        assert versions == sorted(versions, reverse=True)

    def test_manifest_json_full(self, admin_session):
        r = admin_session.get(
            f"{V1}/packages/{pytest.pkg1_id}/manifest.json", timeout=15,
        )
        assert r.status_code == 200
        m = r.json()
        assert "originals" in m and isinstance(m["originals"], list)
        assert "derivatives" in m
        assert "validation" in m
        assert m["finalized_by"]
        assert m["finalized_at"]
        assert m["package_version"] == 1


# ── Delete pending + Audit + Outbox ────────────────────────────
class TestDeletePendingAndAudit:
    def test_delete_pending_ok(self, admin_session, admin_awe_mission_id):
        # Upload one item to AWE mission (no finalized pkg) → deletion allowed.
        r = _upload(admin_session, admin_awe_mission_id, "TEST_pending.png",
                    _png_bytes(seed=333), "RGB_IMAGE")
        assert r.status_code == 200, r.text
        eid = r.json()["evidence"]["canonical_id"]
        d = admin_session.delete(f"{V1}/evidence/{eid}", timeout=15)
        assert d.status_code == 200, d.text
        # Now GET returns 404
        g = admin_session.get(f"{V1}/evidence/{eid}", timeout=15)
        assert g.status_code == 404

    def test_audit_has_evidence_and_package_events(self, admin_session):
        r = admin_session.get(f"{API}/nextgen/audit/events", timeout=15)
        assert r.status_code == 200
        types = {e["event_type"] for e in r.json()["items"]}
        assert "evidence.uploaded" in types
        assert "evidence.deleted_pending" in types
        assert "evidence.package_finalized" in types
        assert "mission.stage_advanced" in types


# ── AWE requirement ‘WEATHER_RECORD’ enforced ──────────────────
class TestAWEWeatherRequirement:
    def test_awe_validate_missing_weather_fails(self, admin_session, admin_awe_mission_id):
        v = admin_session.post(
            f"{V1}/missions/{admin_awe_mission_id}/package/validate", timeout=15,
        ).json()
        assert v["overall"] == "FAIL"
        keys = {r["key"]: r for r in v["results"]}
        # awe_environmental_present result is present
        assert "awe_environmental_present" in keys
        assert keys["awe_environmental_present"]["result"] == "FAIL"
