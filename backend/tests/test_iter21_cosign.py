"""Iteration 21 — Claim Snapshot Carrier Co-Sign flow regression.

Covers the new endpoints in routes/claim_cosign.py:
  • POST /api/claim-snapshot/{pid}/cosign/request   (mint + idempotent reuse)
  • GET  /api/claim-snapshot/cosign/verify/{token}  (pre + post sign)
  • POST /api/claim-snapshot/cosign/submit/{token}  (signs + receipt SHA-256)
  • POST /api/claim-snapshot/cosign/submit/{token}  (409 on re-use)
  • GET  /api/claim-snapshot/{pid}/cosign/status    (SIGNED state)
  • GET  /api/passport/{pid}                        (COSIGN ledger entry)
  • GET  /api/passport/{pid}/verify                 (chain intact)

Also re-asserts iter-20 regression endpoints still work.
"""
from __future__ import annotations

import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stratex-quant.preview.emergentagent.com").rstrip("/")
PID = "877D9E3C8FC3"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module", autouse=True)
def ensure_seed(api):
    r = api.post(f"{BASE_URL}/api/passport/seed/demo", timeout=30)
    assert r.status_code in (200, 201), r.text[:300]
    r = api.post(f"{BASE_URL}/api/claim-snapshot/seed/{PID}", timeout=60)
    assert r.status_code == 200, r.text[:300]


# ---- helpers ----------------------------------------------------------
def _purge_unsigned_token(api):
    """The request endpoint reuses any UNSIGNED token. To deterministically
    test reuse we just call it twice; the same token must come back."""


# ───────────────────────────────────────────────────────────────────────
# Co-sign — request (mint + idempotent)
# ───────────────────────────────────────────────────────────────────────
class TestCosignRequest:
    def test_request_mints_token(self, api, request):
        r = api.post(
            f"{BASE_URL}/api/claim-snapshot/{PID}/cosign/request",
            json={"requester_name": "TEST_Contractor", "carrier_company": "TEST_Carrier"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert "token" in j and len(j["token"]) >= 16
        assert j["sign_path"] == f"/cosign/{j['token']}"
        assert "requested_at" in j
        # Stash for next test
        request.config._cosign_token = j["token"]

    def test_request_reuses_pending(self, api, request):
        prev = getattr(request.config, "_cosign_token", None)
        assert prev, "previous test must have set token"
        r = api.post(
            f"{BASE_URL}/api/claim-snapshot/{PID}/cosign/request",
            json={"requester_name": "TEST_Contractor", "carrier_company": "TEST_Carrier"},
            timeout=30,
        )
        assert r.status_code == 200
        j = r.json()
        assert j["token"] == prev, f"expected reuse of {prev}, got {j['token']}"
        assert j["reused"] is True


# ───────────────────────────────────────────────────────────────────────
# Co-sign — verify (before sign)
# ───────────────────────────────────────────────────────────────────────
class TestCosignVerifyUnsigned:
    def test_verify_returns_diff_unsigned(self, api, request):
        token = request.config._cosign_token
        r = api.get(f"{BASE_URL}/api/claim-snapshot/cosign/verify/{token}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j["token"] == token
        assert j["passport_id"] == PID
        assert j["signed_at"] is None
        assert isinstance(j["diff"], dict)
        assert "deltas" in j["diff"]
        assert "verdict" in j["diff"]


# ───────────────────────────────────────────────────────────────────────
# Co-sign — submit + receipt
# ───────────────────────────────────────────────────────────────────────
class TestCosignSubmit:
    def test_submit_creates_receipt(self, api, request):
        token = request.config._cosign_token
        r = api.post(
            f"{BASE_URL}/api/claim-snapshot/cosign/submit/{token}",
            json={
                "adjuster_name": "TEST_Jane Reyes",
                "adjuster_company": "TEST_State Farm",
                "adjuster_license": "KY-CL-999999",
                "decision": "APPROVED",
                "notes": "TEST regression run iter-21",
            },
            timeout=30,
        )
        assert r.status_code == 200, r.text[:400]
        j = r.json()
        assert j["passport_id"] == PID
        assert j["decision"] == "APPROVED"
        assert "signed_at" in j
        assert HEX64.match(j["receipt_hash"]), f"bad receipt hash: {j['receipt_hash']}"
        request.config._receipt_hash = j["receipt_hash"]

    def test_submit_again_conflict(self, api, request):
        token = request.config._cosign_token
        r = api.post(
            f"{BASE_URL}/api/claim-snapshot/cosign/submit/{token}",
            json={
                "adjuster_name": "TEST_Replay",
                "adjuster_company": "TEST_Replay",
                "decision": "DENIED",
            },
            timeout=30,
        )
        assert r.status_code == 409, f"expected 409, got {r.status_code}: {r.text[:200]}"

    def test_verify_after_sign(self, api, request):
        token = request.config._cosign_token
        r = api.get(f"{BASE_URL}/api/claim-snapshot/cosign/verify/{token}", timeout=30)
        assert r.status_code == 200
        j = r.json()
        assert j["signed_at"] is not None
        assert j["decision"] == "APPROVED"
        assert j["receipt_hash"] == request.config._receipt_hash


# ───────────────────────────────────────────────────────────────────────
# Co-sign — status
# ───────────────────────────────────────────────────────────────────────
class TestCosignStatus:
    def test_status_signed(self, api, request):
        r = api.get(f"{BASE_URL}/api/claim-snapshot/{PID}/cosign/status", timeout=30)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        assert j["state"] == "SIGNED"
        assert "signed_at" in j
        assert "signer" in j and j["signer"]["adjuster_name"].startswith("TEST_")
        assert HEX64.match(j["receipt_hash"])
        assert "token_tail" in j and len(j["token_tail"]) == 8


# ───────────────────────────────────────────────────────────────────────
# Passport ledger — COSIGN entry + chain still verifies
# ───────────────────────────────────────────────────────────────────────
class TestPassportLedgerCosignEntry:
    def test_cosign_entry_in_ledger(self, api, request):
        r = api.get(f"{BASE_URL}/api/passport/{PID}", timeout=30)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        ledger = j.get("ledger") or (j.get("passport") or {}).get("ledger") or []
        assert isinstance(ledger, list) and len(ledger) >= 1
        cosign_entries = [e for e in ledger if e.get("event") == "COSIGN"]
        assert cosign_entries, "no COSIGN entries in ledger"
        # The last COSIGN entry must carry the signed payload
        last = cosign_entries[-1]
        payload = last.get("payload") or {}
        assert payload.get("adjuster_name", "").startswith("TEST_") or last.get("status") == "APPROVED"
        assert payload.get("decision") == "APPROVED"
        assert payload.get("receipt_hash") == request.config._receipt_hash

    def test_ledger_chain_verifies(self, api):
        r = api.get(f"{BASE_URL}/api/passport/{PID}/verify", timeout=30)
        assert r.status_code == 200, r.text[:300]
        j = r.json()
        # endpoint returns {tamper_evident: true, broken_seqs: []} when intact
        ok = j.get("ok") is True or (j.get("tamper_evident") is True and not j.get("broken_seqs"))
        assert ok, f"chain broken: {j}"


# ───────────────────────────────────────────────────────────────────────
# Regression — iter-20 endpoints still healthy
# ───────────────────────────────────────────────────────────────────────
class TestIter20Regression:
    def test_seed(self, api):
        r = api.post(f"{BASE_URL}/api/claim-snapshot/seed/{PID}", timeout=60)
        assert r.status_code == 200

    def test_latest(self, api):
        r = api.get(f"{BASE_URL}/api/claim-snapshot/{PID}/latest", timeout=90)
        assert r.status_code == 200
        assert r.json().get("verdict") in ("CLAIM_SUPPORTABLE", "MONITOR", "NO_CHANGE")

    def test_diff(self, api):
        r = api.post(f"{BASE_URL}/api/claim-snapshot/{PID}/diff",
                     json={"seq_a": 1, "seq_b": 2}, timeout=90)
        assert r.status_code == 200

    def test_pdf(self, api):
        r = api.get(f"{BASE_URL}/api/claim-snapshot/{PID}/pdf", timeout=180)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_storms_active(self, api):
        r = api.get(f"{BASE_URL}/api/storms/active",
                    params={"lat": 38.0406, "lon": -84.5037, "radius_miles": 100},
                    timeout=60)
        assert r.status_code == 200
