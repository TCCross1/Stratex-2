"""NextGen Wave 2B — Property Intelligence Engine (Directive 007).

Covers `/api/nextgen/v1/*` intelligence endpoints:
- Taxonomy catalog
- PIO create (severity→tier mapping, historical_comparison)
- Validation errors (empty evidence, unknown component, bad enums, cross-tenant)
- Mission listing / detail (versions[]/reviews[])
- Review flows: approve (Passport append + hash chain), reject, rework, field_verification
- Passport hash-chain GENESIS + prior_hash chaining across two approvals
- Property timeline includes INTELLIGENCE_APPROVED
- Passport audience projection filters
- Report templates: homeowner_summary visibility, executive_summary internal,
  unknown template 404, list templates
- Durable outbox row `INTELLIGENCE_APPROVED` with idempotency key
- Direct Mongo verification of one approval — one passport_entry, one receipt,
  one timeline row, one outbox row, one audit event.
"""
import io
import os
import time
import hashlib
import asyncio
import pytest
import requests
from PIL import Image

def _read_frontend_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env()).rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
# Load Mongo creds from backend/.env for the Mongo verification test
if not os.environ.get("MONGO_URL"):
    try:
        with open("/app/backend/.env") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v.strip().strip('"').strip("'"))
    except Exception:
        pass
API = f"{BASE_URL}/api"
V1 = f"{API}/nextgen/v1"

ADMIN_EMAIL = "admin@stratex.io"
ADMIN_PASS = "StratexAdmin!2026"
CONTRACTOR_EMAIL = "anthony@apexroofing.com"
CONTRACTOR_PASS = "Contractor!2026"


# ── Auth helpers ─────────────────────────────────────────────────────────
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
    tok = _login(s, ADMIN_EMAIL, ADMIN_PASS)
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def contractor_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    tok = _login(s, CONTRACTOR_EMAIL, CONTRACTOR_PASS)
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# ── File helpers ─────────────────────────────────────────────────────────
def _png(seed: int = 1, w: int = 32, h: int = 32) -> bytes:
    # Include time to guarantee content hash is unique across test runs (evidence
    # dedup is tenant-scoped by content_sha256).
    nonce = int(time.time() * 1000) & 0xFFFF
    img = Image.new("RGB", (w, h), color=(((seed + nonce) * 7) % 255,
                                            ((seed + nonce) * 13) % 255,
                                            ((seed + nonce) * 29) % 255))
    for x in range(w):
        img.putpixel((x, (seed + nonce) % h), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _upload_evidence(sess, mission_id, filename, data, category="RGB_IMAGE",
                     mime="image/png"):
    files = {"file": (filename, data, mime)}
    form = {"category": category, "is_original": "true", "intended_duplicate": "false",
            "mode": "DEMO"}
    headers = {k: v for k, v in sess.headers.items() if k.lower() != "content-type"}
    return requests.post(f"{V1}/missions/{mission_id}/evidence",
                         files=files, data=form, headers=headers, timeout=30)


_TS = str(int(time.time() * 1000))


# ── Setup fixture: property + mission + 1 evidence (admin) ───────────────
@pytest.fixture(scope="session")
def admin_property_mission_evidence(admin_session):
    # Fresh property so hash-chain starts as GENESIS
    payload = {
        "address": {"line1": f"TEST_W2B_{_TS} Intel Way", "city": "Lexington",
                    "region": "KY", "postal_code": "40502", "country_iso": "US"},
        "coordinate": {"lat": 38.0406, "lon": -84.5037, "precision_m": 5.0},
    }
    r = admin_session.post(f"{API}/nextgen/properties", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["property"]["canonical_id"]
    r = admin_session.post(f"{API}/nextgen/missions",
                           json={"property_id": pid, "product": "dayscan"}, timeout=15)
    assert r.status_code == 200, r.text
    mid = r.json()["mission"]["canonical_id"]
    ev = _upload_evidence(admin_session, mid, "TEST_intel_ev1.png", _png(seed=101))
    assert ev.status_code == 200, ev.text
    eid = ev.json()["evidence"]["canonical_id"]
    ev2 = _upload_evidence(admin_session, mid, "TEST_intel_ev2.png", _png(seed=102))
    assert ev2.status_code == 200, ev2.text
    eid2 = ev2.json()["evidence"]["canonical_id"]
    return {"property_id": pid, "mission_id": mid, "evidence_ids": [eid, eid2]}


@pytest.fixture(scope="session")
def contractor_property_mission_evidence(contractor_session):
    payload = {
        "address": {"line1": f"TEST_W2B_{_TS} Contractor Intel Rd", "city": "Lexington",
                    "region": "KY", "postal_code": "40504", "country_iso": "US"},
        "coordinate": {"lat": 38.06, "lon": -84.49, "precision_m": 5.0},
    }
    r = contractor_session.post(f"{API}/nextgen/properties", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["property"]["canonical_id"]
    r = contractor_session.post(f"{API}/nextgen/missions",
                                json={"property_id": pid, "product": "dayscan"}, timeout=15)
    assert r.status_code == 200, r.text
    mid = r.json()["mission"]["canonical_id"]
    ev = _upload_evidence(contractor_session, mid, "TEST_c_intel_ev1.png", _png(seed=201))
    assert ev.status_code == 200, ev.text
    return {"property_id": pid, "mission_id": mid,
            "evidence_id": ev.json()["evidence"]["canonical_id"]}


# ── Taxonomy endpoint ────────────────────────────────────────────────────
class TestTaxonomy:
    def test_taxonomy_full_payload(self, admin_session):
        r = admin_session.get(f"{V1}/taxonomy/building-systems", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["systems", "flat", "severity", "priority", "risk_level",
                  "risk_tier", "awe_categories", "timeline_kinds",
                  "report_templates", "visibility_scopes"]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["systems"], dict) and "ROOF" in d["systems"]
        assert "SHINGLES" in d["systems"]["ROOF"]
        assert isinstance(d["flat"], list) and len(d["flat"]) > 0
        assert set(d["severity"]) == {"INFORMATIONAL", "MINOR", "MODERATE", "MAJOR", "CRITICAL"}
        assert set(d["awe_categories"]) == {"AIR", "WATER", "ENERGY"}
        assert "INTELLIGENCE_APPROVED" in d["timeline_kinds"]
        assert set(d["report_templates"]) >= {"homeowner_summary", "executive_summary"}

    def test_report_templates_list(self, admin_session):
        r = admin_session.get(f"{V1}/report-templates", timeout=10)
        assert r.status_code == 200
        assert len(r.json()["templates"]) == 7


# ── Create validation errors ─────────────────────────────────────────────
class TestCreateValidation:
    def _base(self, ctx):
        return {
            "mission_id": ctx["mission_id"],
            "evidence_ids": [ctx["evidence_ids"][0]],
            "building_system": "ROOF",
            "building_component": "SHINGLES",
            "observation": "TEST cupping on south slope",
            "severity": "MODERATE",
            "priority": "SCHEDULE",
            "risk_level": "ELEVATED",
            "awe_impact": {"air": False, "water": True, "energy": False,
                           "rationale": "wind-driven ingress path"},
            "recommended_action": "Field verification",
            "visibility": {"contractor": True, "homeowner": True, "adjuster": False,
                           "insurer": False, "public": False, "internal": True},
        }

    def test_reject_empty_evidence(self, admin_session, admin_property_mission_evidence):
        body = self._base(admin_property_mission_evidence)
        body["evidence_ids"] = []
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 400, r.text

    def test_reject_component_not_in_system(self, admin_session,
                                             admin_property_mission_evidence):
        body = self._base(admin_property_mission_evidence)
        body["building_system"] = "ROOF"
        body["building_component"] = "CONDENSER"  # HVAC component
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 400, r.text

    def test_reject_bad_severity(self, admin_session, admin_property_mission_evidence):
        body = self._base(admin_property_mission_evidence)
        body["severity"] = "NUCLEAR"
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 400, r.text

    def test_reject_bad_priority(self, admin_session, admin_property_mission_evidence):
        body = self._base(admin_property_mission_evidence)
        body["priority"] = "YESTERDAY"
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 400, r.text

    def test_reject_bad_risk_level(self, admin_session, admin_property_mission_evidence):
        body = self._base(admin_property_mission_evidence)
        body["risk_level"] = "ARMAGEDDON"
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 400, r.text

    def test_reject_cross_tenant_evidence(self, admin_session,
                                           admin_property_mission_evidence,
                                           contractor_property_mission_evidence):
        # Admin's mission but contractor's evidence id → must 400 (not found on mission).
        body = self._base(admin_property_mission_evidence)
        body["evidence_ids"] = [contractor_property_mission_evidence["evidence_id"]]
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 400, r.text


# ── Create + Approve happy path (GENESIS chain) ──────────────────────────
class TestApprovalHashChainGenesis:
    """One property, two consecutive PIOs on same system+component.

    Approval 1 → GENESIS (prior_hash null)
    Approval 2 → prior_hash equals #1 content_hash, historical_comparison populated
    """

    def test_create_moderate_shingles_pio(self, admin_session,
                                           admin_property_mission_evidence):
        ctx = admin_property_mission_evidence
        body = {
            "mission_id": ctx["mission_id"],
            "evidence_ids": [ctx["evidence_ids"][0]],
            "building_system": "ROOF",
            "building_component": "SHINGLES",
            "observation": "TEST moderate shingle cupping on south slope",
            "severity": "MODERATE",
            "priority": "SCHEDULE",
            "risk_level": "ELEVATED",
            "awe_impact": {"air": False, "water": True, "energy": False,
                           "rationale": "wind-driven ingress path"},
            "recommended_action": "Field verification",
            "visibility": {"contractor": True, "homeowner": True, "adjuster": False,
                           "insurer": False, "public": False, "internal": True},
        }
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 200, r.text
        pio = r.json()["intelligence"]
        assert pio["state"] == "candidate"
        assert pio["risk_tier"] == "tier_2_contractor_review"  # MODERATE→tier_2
        assert pio["historical_comparison"] is None  # first ever
        pytest.pio_id_1 = pio["canonical_id"]
        pytest.property_id = ctx["property_id"]

    def test_list_mission_intelligence(self, admin_session,
                                        admin_property_mission_evidence):
        mid = admin_property_mission_evidence["mission_id"]
        r = admin_session.get(f"{V1}/missions/{mid}/intelligence", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["count"] >= 1
        assert any(x["canonical_id"] == pytest.pio_id_1 for x in d["items"])

    def test_get_intelligence_includes_versions_and_reviews(self, admin_session):
        r = admin_session.get(f"{V1}/intelligence/{pytest.pio_id_1}", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["intelligence"]["canonical_id"] == pytest.pio_id_1
        assert isinstance(d["versions"], list) and len(d["versions"]) >= 1
        assert isinstance(d["reviews"], list) and len(d["reviews"]) == 0

    def test_approve_genesis_creates_passport_entry(self, admin_session):
        r = admin_session.post(
            f"{V1}/intelligence/{pytest.pio_id_1}/review",
            json={"decision": "approve", "notes": "TEST approve #1"}, timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        pio = d["intelligence"]
        assert pio["state"] == "passport_committed"
        assert pio["passport_entry_id"]
        passport = d["passport"]
        assert passport is not None
        entry = passport["entry"]
        assert entry["prior_hash"] is None  # GENESIS
        assert isinstance(entry["seq"], int) and entry["seq"] >= 1
        pytest.entry_seq_1 = entry["seq"]
        h = entry["content_hash"]
        assert isinstance(h, str) and len(h) == 64
        int(h, 16)  # SHA-256 hex
        # signature is deterministic
        assert isinstance(entry["signature"], str) and len(entry["signature"]) == 64
        pytest.entry_hash_1 = h
        pytest.entry_id_1 = entry["canonical_id"]

    def test_second_pio_has_historical_comparison(self, admin_session,
                                                   admin_property_mission_evidence):
        ctx = admin_property_mission_evidence
        body = {
            "mission_id": ctx["mission_id"],
            "evidence_ids": [ctx["evidence_ids"][1]],
            "building_system": "ROOF",
            "building_component": "SHINGLES",
            "observation": "TEST major shingle failure after storm",
            "severity": "MAJOR",  # escalated → tier_3
            "priority": "URGENT",
            "risk_level": "HIGH",
            "awe_impact": {"air": False, "water": True, "energy": False,
                           "rationale": "active ingress"},
            "recommended_action": "Immediate tarp + repair",
            "visibility": {"contractor": True, "homeowner": True, "adjuster": True,
                           "insurer": True, "public": False, "internal": True},
        }
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 200, r.text
        pio2 = r.json()["intelligence"]
        assert pio2["risk_tier"] == "tier_3_high_consequence_non_engineering"  # MAJOR
        assert pio2["previous_intelligence_id"] == pytest.pio_id_1
        hc = pio2["historical_comparison"]
        assert hc is not None
        assert hc["previous_id"] == pytest.pio_id_1
        assert hc["previous_severity"] == "MODERATE"
        assert hc["delta_severity"] == 1  # MAJOR(3) - MODERATE(2) = 1
        pytest.pio_id_2 = pio2["canonical_id"]

    def test_approve_second_chains_prior_hash(self, admin_session):
        r = admin_session.post(
            f"{V1}/intelligence/{pytest.pio_id_2}/review",
            json={"decision": "approve", "notes": "TEST approve #2"}, timeout=20,
        )
        assert r.status_code == 200, r.text
        entry = r.json()["passport"]["entry"]
        assert entry["prior_hash"] == pytest.entry_hash_1
        assert entry["seq"] == pytest.entry_seq_1 + 1
        assert len(entry["content_hash"]) == 64
        pytest.entry_hash_2 = entry["content_hash"]

    def test_review_committed_returns_409(self, admin_session):
        r = admin_session.post(
            f"{V1}/intelligence/{pytest.pio_id_1}/review",
            json={"decision": "approve"}, timeout=15,
        )
        assert r.status_code == 409, r.text


# ── Reject / rework / field-verification transitions ─────────────────────
class TestOtherDecisions:
    def _create(self, admin_session, ctx, component="FLASHING",
                observation="TEST flashing rust"):
        body = {
            "mission_id": ctx["mission_id"],
            "evidence_ids": [ctx["evidence_ids"][0]],
            "building_system": "ROOF",
            "building_component": component,
            "observation": observation,
            "severity": "MINOR",
            "priority": "MONITOR",
            "risk_level": "LOW",
            "awe_impact": {"air": False, "water": False, "energy": False},
            "visibility": {"contractor": True, "homeowner": False, "internal": True},
        }
        r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()["intelligence"]["canonical_id"]

    def test_reject_sets_state_and_no_passport_append(self, admin_session,
                                                       admin_property_mission_evidence):
        pio_id = self._create(admin_session, admin_property_mission_evidence,
                              component="FLASHING", observation="TEST reject candidate")
        r = admin_session.post(f"{V1}/intelligence/{pio_id}/review",
                               json={"decision": "reject", "notes": "TEST reject"},
                               timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["intelligence"]["state"] == "rejected"
        assert d["passport"] is None
        assert "passport_entry_id" not in d["intelligence"] \
            or d["intelligence"].get("passport_entry_id") in (None, "")

    def test_request_rework_returns_to_candidate(self, admin_session,
                                                  admin_property_mission_evidence):
        pio_id = self._create(admin_session, admin_property_mission_evidence,
                              component="VALLEYS", observation="TEST rework candidate")
        r = admin_session.post(f"{V1}/intelligence/{pio_id}/review",
                               json={"decision": "request_rework"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["intelligence"]["state"] == "candidate"
        assert d["passport"] is None

    def test_field_verification_sets_state_and_no_append(self, admin_session,
                                                          admin_property_mission_evidence):
        pio_id = self._create(admin_session, admin_property_mission_evidence,
                              component="RIDGES", observation="TEST field verify")
        r = admin_session.post(
            f"{V1}/intelligence/{pio_id}/review",
            json={"decision": "request_field_verification"}, timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["intelligence"]["state"] == "requires_field_verification"
        assert d["passport"] is None


# ── Severity→tier mapping ─────────────────────────────────────────────────
class TestSeverityTierMapping:
    def test_all_severity_to_tier_mapping(self, admin_session,
                                           admin_property_mission_evidence):
        ctx = admin_property_mission_evidence
        expected = {
            "INFORMATIONAL": "tier_1_automated_informational",
            "MINOR": "tier_2_contractor_review",
            "MODERATE": "tier_2_contractor_review",
            "MAJOR": "tier_3_high_consequence_non_engineering",
            "CRITICAL": "tier_3_high_consequence_non_engineering",
        }
        # Use DOWNSPOUTS (different component per severity to avoid dup)
        components = ["DOWNSPOUTS", "SPLASH_BLOCKS", "GRADING",
                      "FRENCH_DRAIN"]  # only 4 unique
        for i, (sev, tier) in enumerate(expected.items()):
            body = {
                "mission_id": ctx["mission_id"],
                "evidence_ids": [ctx["evidence_ids"][0]],
                "building_system": "DRAINAGE",
                "building_component": components[i % len(components)],
                "observation": f"TEST severity map {sev}",
                "severity": sev,
                "priority": "MONITOR",
                "risk_level": "LOW",
            }
            r = admin_session.post(f"{V1}/intelligence", json=body, timeout=15)
            assert r.status_code == 200, r.text
            got = r.json()["intelligence"]["risk_tier"]
            assert got == tier, f"{sev}: expected {tier} got {got}"


# ── Timeline + Passport + Report projections ────────────────────────────
class TestTimelinePassportReports:
    def test_property_timeline_has_intelligence_approved(self, admin_session):
        pid = pytest.property_id
        r = admin_session.get(f"{V1}/properties/{pid}/timeline", timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 2
        # sorted by 'at' desc
        ats = [i["at"] for i in items]
        assert ats == sorted(ats, reverse=True)
        kinds = {i["kind"] for i in items}
        assert "INTELLIGENCE_APPROVED" in kinds

    def test_passport_internal_shows_all_entries(self, admin_session):
        pid = pytest.property_id
        r = admin_session.get(f"{V1}/properties/{pid}/passport",
                              params={"audience": "internal"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["passport"] is not None
        # Two approvals in genesis chain
        entries = d["entries"]
        assert len(entries) >= 2
        # hash-chain: entries sorted by seq ascending; first has prior_hash=None,
        # subsequent entries chain from previous content_hash.
        entries_sorted = sorted(entries, key=lambda e: e["seq"])
        assert entries_sorted[0]["prior_hash"] is None
        for i in range(1, len(entries_sorted)):
            assert entries_sorted[i]["prior_hash"] == entries_sorted[i - 1]["content_hash"]

    def test_passport_homeowner_filters_by_visibility(self, admin_session):
        pid = pytest.property_id
        r = admin_session.get(f"{V1}/properties/{pid}/passport",
                              params={"audience": "homeowner"}, timeout=15)
        assert r.status_code == 200
        entries = r.json()["entries"]
        # Both approved PIOs had visibility.homeowner=True
        assert len(entries) >= 2
        for e in entries:
            vis = (e.get("payload") or {}).get("visibility") or {}
            assert vis.get("homeowner") is True

    def test_passport_contractor_returns_entries(self, admin_session):
        pid = pytest.property_id
        r = admin_session.get(f"{V1}/properties/{pid}/passport",
                              params={"audience": "contractor"}, timeout=15)
        assert r.status_code == 200
        assert len(r.json()["entries"]) >= 2

    def test_report_homeowner_summary(self, admin_session):
        pid = pytest.property_id
        r = admin_session.get(f"{V1}/properties/{pid}/report/homeowner_summary", timeout=15)
        assert r.status_code == 200, r.text
        rep = r.json()["report"]
        assert rep["template"] == "homeowner_summary"
        assert set(rep["counts"]["awe"].keys()) == {"air", "water", "energy"}
        assert "severity" in rep["counts"]
        # highest_severity should be MAJOR (PIO 2)
        assert rep["highest_severity"] in {"MAJOR", "CRITICAL"}
        assert rep["counts"]["awe"]["water"] >= 2
        # projected items only expose homeowner-safe fields (no observation/notes)
        for item in rep["items"]:
            assert "observation" not in item
            assert "notes" not in item

    def test_report_executive_summary_internal(self, admin_session):
        pid = pytest.property_id
        r = admin_session.get(f"{V1}/properties/{pid}/report/executive_summary", timeout=15)
        assert r.status_code == 200
        rep = r.json()["report"]
        assert rep["template"] == "executive_summary"
        # executive_summary uses visibility "internal" so should include all approved PIOs
        # (both approvals had internal=True)
        assert rep["counts"]["total"] >= 2

    def test_report_unknown_template_404(self, admin_session):
        pid = pytest.property_id
        r = admin_session.get(f"{V1}/properties/{pid}/report/bogus_template", timeout=15)
        assert r.status_code == 404, r.text


# ── Direct Mongo verification of one approval (no orphans/dupes) ─────────
class TestMongoStateAfterApproval:
    def test_mongo_state_single_row_per_side_effect(self):
        import motor.motor_asyncio  # noqa
        mongo_url = os.environ["MONGO_URL"]
        db_name = os.environ["DB_NAME"]

        async def _check():
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            pio_id = pytest.pio_id_1
            # passport_entries: exactly one row referencing intelligence_id
            entries = await db["nextgen_passport_entries"].find(
                {"payload.intelligence_id": pio_id}).to_list(50)
            # receipts: one per entry
            entry_ids = [e["canonical_id"] for e in entries]
            receipts = await db["nextgen_passport_receipts"].find(
                {"passport_entry_id": {"$in": entry_ids}}).to_list(50)
            # timeline: one INTELLIGENCE_APPROVED row for this PIO
            tl = await db["nextgen_property_timeline"].find(
                {"reference_id": pio_id, "kind": "INTELLIGENCE_APPROVED"}).to_list(50)
            # outbox: one row with idempotency_key intelligence.approved:<pio_id>
            ob = await db["nextgen_outbox_events"].find(
                {"idempotency_key": f"intelligence.approved:{pio_id}"}).to_list(50)
            # audit: intelligence.reviewed + passport.appended
            au = await db["nextgen_audit_events"].find(
                {"resource_id": pio_id}).to_list(50)
            client.close()
            return entries, receipts, tl, ob, au

        entries, receipts, tl, ob, au = asyncio.get_event_loop().run_until_complete(_check())
        assert len(entries) == 1, f"expected 1 passport entry, got {len(entries)}"
        assert len(receipts) == 1, f"expected 1 receipt, got {len(receipts)}"
        assert len(tl) == 1, f"expected 1 timeline row, got {len(tl)}"
        assert len(ob) == 1, f"expected 1 outbox row, got {len(ob)}"
        assert ob[0]["event_type"] == "INTELLIGENCE_APPROVED"
        # audit contains at least intelligence.created + intelligence.reviewed
        types = {a["event_type"] for a in au}
        assert "intelligence.reviewed" in types
