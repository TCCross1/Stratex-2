"""C-P-001C Legacy Passport / claim mutation authorization tests (offline).

Uses deterministic fake request objects and monkeypatched auth — no live
credentials, no owner identities, no hard-coded reusable passwords.
"""
from __future__ import annotations

import asyncio
import inspect
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routes import passport as passport_mod
from routes import claim_cosign as cosign_mod


def _req(path="/api/passport/issue", method="POST", host="127.0.0.1"):
    return SimpleNamespace(
        client=SimpleNamespace(host=host),
        url=SimpleNamespace(path=path),
        method=method,
        headers={},
    )


@pytest.fixture
def blocked_audit(monkeypatch):
    rows = []

    class _Coll:
        async def insert_one(self, doc):
            rows.append(doc)

    monkeypatch.setattr(
        passport_mod,
        "db",
        SimpleNamespace(__getitem__=lambda self, name: _Coll()),
    )
    # db["legacy_passport_blocked_writes"] path uses db[...] — replace with mapping
    store = {"legacy_passport_blocked_writes": _Coll()}

    class _DB:
        def __getitem__(self, name):
            return store[name]

    monkeypatch.setattr(passport_mod, "db", _DB())
    return rows


def test_unauthenticated_writer_rejected(blocked_audit, monkeypatch):
    async def _boom(request, db):
        raise HTTPException(401, "Not authenticated")

    monkeypatch.setattr(passport_mod, "_extract_user", _boom)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(passport_mod.require_legacy_passport_writer(_req()))
    assert ei.value.status_code == 403
    assert blocked_audit and blocked_audit[0]["reason"] == "unauthenticated"
    assert blocked_audit[0]["actor"] == "anonymous"
    blob = str(blocked_audit[0]).lower()
    for forbidden in ("password", "bearer", "authorization", "totp"):
        assert forbidden not in blob


@pytest.mark.parametrize(
    "role",
    ["contractor", "operator", "homeowner"],
)
def test_non_privileged_roles_rejected(blocked_audit, monkeypatch, role):
    async def _user(request, db):
        return {
            "id": str(uuid.uuid4()),
            "email": f"{role}@example.test",
            "role": role,
            "is_superadmin": False,
        }

    monkeypatch.setattr(passport_mod, "_extract_user", _user)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(passport_mod.require_legacy_passport_writer(_req()))
    assert ei.value.status_code == 403
    assert blocked_audit[-1]["reason"] == "insufficient_privilege"
    assert blocked_audit[-1]["actor"] == "authenticated"


@pytest.mark.parametrize("role", ["admin", "ceo"])
def test_admin_and_ceo_accepted(monkeypatch, role):
    async def _user(request, db):
        return {"id": "u1", "email": f"{role}@example.test", "role": role}

    monkeypatch.setattr(passport_mod, "_extract_user", _user)
    user = asyncio.run(passport_mod.require_legacy_passport_writer(_req()))
    assert user["role"] == role


def test_existing_is_superadmin_claim_accepted(monkeypatch):
    """Accept only an already-present claim — no global privilege expansion."""
    async def _user(request, db):
        return {
            "id": "u2",
            "email": "ops@example.test",
            "role": "contractor",
            "is_superadmin": True,
        }

    monkeypatch.setattr(passport_mod, "_extract_user", _user)
    user = asyncio.run(passport_mod.require_legacy_passport_writer(_req()))
    assert user["is_superadmin"] is True


def test_passport_mutation_routes_declare_writer_dependency():
    for fn in (
        passport_mod.issue_passport,
        passport_mod.append_event,
        passport_mod.seed_demo_passport,
    ):
        params = inspect.signature(fn).parameters
        assert "_writer" in params


def test_claim_snapshot_seed_declares_writer_dependency():
    from routes import claim_snapshot as snap

    assert "_writer" in inspect.signature(snap.seed_demo_scans).parameters


def test_cosign_request_declares_writer_dependency():
    assert "_writer" in inspect.signature(cosign_mod.request_cosign).parameters


def test_cosign_submit_rejects_empty_token(monkeypatch):
    audited = []

    async def _audit(request, reason, user=None):
        audited.append({"reason": reason, "user": user})

    monkeypatch.setattr(cosign_mod, "_log_blocked_write", _audit)

    with pytest.raises(HTTPException) as ei:
        asyncio.run(
            cosign_mod.submit_cosign(
                "   ",
                cosign_mod.CosignSubmitIn(
                    adjuster_name="A Tester",
                    adjuster_company="Carrier Co",
                    decision="APPROVED",
                ),
                _req(path="/api/claim-snapshot/cosign/submit/"),
            )
        )
    assert ei.value.status_code == 403
    assert audited and audited[0]["reason"] == "cosign_token_missing"


def test_cosign_submit_rejects_unknown_token(monkeypatch):
    audited = []

    async def _audit(request, reason, user=None):
        audited.append(reason)

    async def _missing(token):
        return None

    monkeypatch.setattr(cosign_mod, "_log_blocked_write", _audit)
    monkeypatch.setattr(cosign_mod, "_get_cosign", _missing)

    with pytest.raises(HTTPException) as ei:
        asyncio.run(
            cosign_mod.submit_cosign(
                "not-a-real-token",
                cosign_mod.CosignSubmitIn(
                    adjuster_name="A Tester",
                    adjuster_company="Carrier Co",
                    decision="APPROVED",
                ),
                _req(path="/api/claim-snapshot/cosign/submit/x"),
            )
        )
    assert ei.value.status_code == 404
    assert "cosign_token_invalid" in audited


def test_blocked_audit_excludes_sensitive_fields(blocked_audit, monkeypatch):
    async def _boom(request, db):
        raise HTTPException(401, "Not authenticated")

    monkeypatch.setattr(passport_mod, "_extract_user", _boom)
    with pytest.raises(HTTPException):
        asyncio.run(passport_mod.require_legacy_passport_writer(_req()))
    doc = blocked_audit[0]
    assert set(doc.keys()) >= {
        "id", "at", "reason", "path", "method", "ip", "actor",
    }
    assert "password" not in doc
    assert "token" not in doc
    assert "authorization" not in doc
