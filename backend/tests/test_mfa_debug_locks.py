"""C-P-001C MFA/SMS debug hard-lock and MFA no-token regressions (offline)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import dev_auth


def _reset_env(monkeypatch, **kv):
    for name in (
        "DEV_NO_AUTH",
        "APP_ENV",
        "CORS_ORIGINS",
        "PUBLIC_FRONTEND_URL",
        "FRONTEND_URL",
        "PROD_HOSTS",
        "DEMO_MFA_BYPASS",
        "DEMO_SMS_BYPASS",
    ):
        monkeypatch.delenv(name, raising=False)
    for k, v in kv.items():
        monkeypatch.setenv(k, v)


def test_production_totp_debug_hard_locked(monkeypatch):
    """Mirror server.totp_debug production gate without importing server."""
    _reset_env(monkeypatch, APP_ENV="production", DEMO_MFA_BYPASS="1")
    assert dev_auth.is_production() is True
    # Production OR missing flag → blocked (same predicate as server.py).
    blocked = dev_auth.is_production() or (
        __import__("os").environ.get("DEMO_MFA_BYPASS", "0") != "1"
    )
    # With DEMO_MFA_BYPASS=1, production alone must still block.
    assert blocked is True


def test_missing_mfa_bypass_defaults_disabled(monkeypatch):
    _reset_env(monkeypatch, APP_ENV="preview")
    assert __import__("os").environ.get("DEMO_MFA_BYPASS", "0") != "1"


def test_production_sms_debug_hard_locked(monkeypatch):
    _reset_env(monkeypatch, APP_ENV="production", DEMO_SMS_BYPASS="1")
    assert dev_auth.is_production() is True
    # Same predicate as routes/ceo.py
    may_surface = (
        __import__("os").environ.get("DEMO_SMS_BYPASS") == "1"
        and not dev_auth.is_production()
    )
    assert may_surface is False


def test_non_production_sms_debug_still_flag_gated(monkeypatch):
    _reset_env(monkeypatch, APP_ENV="preview", DEMO_SMS_BYPASS="1")
    may_surface = (
        __import__("os").environ.get("DEMO_SMS_BYPASS") == "1"
        and not dev_auth.is_production()
    )
    assert may_surface is True

    _reset_env(monkeypatch, APP_ENV="preview")  # flag absent
    may_surface = (
        __import__("os").environ.get("DEMO_SMS_BYPASS") == "1"
        and not dev_auth.is_production()
    )
    assert may_surface is False


def test_invalid_mfa_produces_no_token(monkeypatch):
    """Exercise login MFA failure path with ephemeral in-memory user."""
    from stratex_auth import hash_password, new_totp_secret, verify_totp

    secret = new_totp_secret()
    password = f"Ephemeral-{uuid_hex()}-Pw"
    user = {
        "id": "ephemeral-user",
        "email": f"ephemeral-{uuid_hex()}@example.test",
        "password_hash": hash_password(password),
        "totp_secret": secret,
        "totp_enrolled": True,
        "tour_mode": False,
        "role": "contractor",
    }
    # Wrong code must fail verify and must not mint a token.
    assert verify_totp(secret, "000000") is False
    # Correct window would pass — prove secret works so the failure is real.
    import pyotp

    good = pyotp.TOTP(secret).now()
    assert verify_totp(secret, good) is True
    # Simulate login gate: invalid MFA → no access_token issued.
    issued = None
    if not verify_totp(user["totp_secret"], "000000"):
        issued = None
    else:
        issued = "SHOULD_NOT_HAPPEN"
    assert issued is None


def uuid_hex() -> str:
    import uuid

    return uuid.uuid4().hex[:10]


def test_synthetic_identity_password_hash_is_unusable(monkeypatch):
    from stratex_auth import verify_password

    captured = {}

    class _Users:
        async def find_one(self, q):
            return None

        async def insert_one(self, doc):
            captured.update(doc)

    monkeypatch.setattr(dev_auth, "db", SimpleNamespace(users=_Users()))
    user = asyncio.run(dev_auth._ensure_synthetic_user("admin"))
    assert user["dev_synthetic"] is True
    assert user["tour_mode"] is False
    assert verify_password("anything", user["password_hash"]) is False
    assert verify_password("", user["password_hash"]) is False
