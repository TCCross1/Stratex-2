"""Deterministic offline tests for C-P-001C development-auth containment.

No live network, no hard-coded credentials, no owner identities.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import dev_auth
from dev_auth import DevLoginBody, dev_auth_enabled, dev_login, is_production


def _reset_env(monkeypatch, **kv):
    for name in (
        "DEV_NO_AUTH",
        "APP_ENV",
        "CORS_ORIGINS",
        "PUBLIC_FRONTEND_URL",
        "FRONTEND_URL",
        "PROD_HOSTS",
    ):
        monkeypatch.delenv(name, raising=False)
    for k, v in kv.items():
        monkeypatch.setenv(k, v)


@pytest.fixture(autouse=True)
def _clear_rate_buckets():
    dev_auth._reset_rate_limits()
    yield
    dev_auth._reset_rate_limits()


def _req(host="127.0.0.1"):
    return SimpleNamespace(
        client=SimpleNamespace(host=host),
        url=SimpleNamespace(path="/api/auth/dev/login"),
        method="POST",
    )


# ── Environment fail-closed ──────────────────────────────────────────────

def test_missing_app_env_fails_closed(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true")
    assert is_production() is False
    assert dev_auth_enabled() is False


def test_blank_app_env_fails_closed(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV="   ")
    assert dev_auth_enabled() is False


def test_unknown_app_env_fails_closed(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV="staging")
    assert dev_auth_enabled() is False


@pytest.mark.parametrize("env", ["production", "prod", "live"])
def test_production_envs_fail_closed(monkeypatch, env):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV=env)
    assert is_production() is True
    assert dev_auth_enabled() is False


def test_production_hostname_fails_closed(monkeypatch):
    _reset_env(
        monkeypatch,
        DEV_NO_AUTH="true",
        APP_ENV="preview",
        PUBLIC_FRONTEND_URL="https://app.stratexdrone.com",
    )
    assert is_production() is True
    assert dev_auth_enabled() is False


def test_dev_no_auth_alone_fails_closed(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true")
    assert dev_auth_enabled() is False


def test_flag_absent_fails_closed(monkeypatch):
    _reset_env(monkeypatch, APP_ENV="preview")
    assert dev_auth_enabled() is False


def test_flag_false_fails_closed(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="false", APP_ENV="preview")
    assert dev_auth_enabled() is False


def test_approved_preview_enabled(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV="preview")
    assert is_production() is False
    assert dev_auth_enabled() is True


def test_ceo_email_domain_does_not_mark_production(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV="preview")
    monkeypatch.setenv("CEO_EMAIL", "ops@stratexdrone.com")
    assert is_production() is False
    assert dev_auth_enabled() is True


# ── Request guards ───────────────────────────────────────────────────────

def test_dev_login_disabled_returns_403(monkeypatch):
    _reset_env(monkeypatch, APP_ENV="preview")
    with pytest.raises(HTTPException) as ei:
        asyncio.run(dev_login(DevLoginBody(role="admin"), _req()))
    assert ei.value.status_code == 403


def test_dev_login_production_returns_403(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV="production")
    with pytest.raises(HTTPException) as ei:
        asyncio.run(dev_login(DevLoginBody(role="admin"), _req()))
    assert ei.value.status_code == 403


def test_dev_login_rejects_unknown_role(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV="preview")

    async def _fake_user(role):
        return {"id": "u1", "email": "dev-admin@stratex.dev", "role": role}

    monkeypatch.setattr(dev_auth, "_ensure_synthetic_user", _fake_user)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(dev_login(DevLoginBody(role="superuser"), _req()))
    assert ei.value.status_code == 400


# ── Rate limit ───────────────────────────────────────────────────────────

def test_rate_limiter_allows_ten_then_429():
    req = _req("10.0.0.5")
    for _ in range(dev_auth._RATE_MAX):
        dev_auth._check_rate_limit(req)
    with pytest.raises(HTTPException) as ei:
        dev_auth._check_rate_limit(req)
    assert ei.value.status_code == 429
    assert "Retry-After" in ei.value.headers
    assert int(ei.value.headers["Retry-After"]) >= 1


def test_rate_limiter_isolates_ips():
    a, b = _req("10.0.0.1"), _req("10.0.0.2")
    for _ in range(dev_auth._RATE_MAX):
        dev_auth._check_rate_limit(a)
    with pytest.raises(HTTPException):
        dev_auth._check_rate_limit(a)
    dev_auth._check_rate_limit(b)  # independent bucket


def test_rate_limiter_window_reset():
    req = _req("10.0.0.9")
    for _ in range(dev_auth._RATE_MAX):
        dev_auth._check_rate_limit(req)
    key = dev_auth._rate_limit_key(req)
    old = time.monotonic() - (dev_auth._RATE_WINDOW_SEC + 5)
    dev_auth._rate_buckets[key] = deque([old] * dev_auth._RATE_MAX)
    dev_auth._check_rate_limit(req)  # must not raise


def test_production_takes_precedence_over_rate_limit(monkeypatch):
    _reset_env(monkeypatch, DEV_NO_AUTH="true", APP_ENV="production")
    req = _req("172.16.0.10")
    for _ in range(dev_auth._RATE_MAX + 3):
        with pytest.raises(HTTPException) as ei:
            asyncio.run(dev_login(DevLoginBody(role="admin"), req))
        assert ei.value.status_code == 403


def test_disabled_login_eventually_rate_limits(monkeypatch):
    _reset_env(monkeypatch, APP_ENV="preview")  # flag off
    req = _req("172.16.0.11")
    audited = {"n": 0}

    async def _audit(_request):
        audited["n"] += 1

    monkeypatch.setattr(dev_auth, "_audit_rate_limit_block", _audit)
    for _ in range(dev_auth._RATE_MAX):
        with pytest.raises(HTTPException) as ei:
            asyncio.run(dev_login(DevLoginBody(role="admin"), req))
        assert ei.value.status_code == 403
    with pytest.raises(HTTPException) as ei2:
        asyncio.run(dev_login(DevLoginBody(role="admin"), req))
    assert ei2.value.status_code == 429
    assert "Retry-After" in ei2.value.headers
    assert audited["n"] == 1


def test_rate_limit_audit_payload_has_no_secrets(monkeypatch):
    captured = {}

    class _Coll:
        async def insert_one(self, doc):
            captured.update(doc)

    monkeypatch.setattr(dev_auth, "db", SimpleNamespace(dev_auth_events=_Coll()))
    asyncio.run(dev_auth._audit_rate_limit_block(_req("9.9.9.9")))
    assert captured["event"] == "dev_auth.rate_limited"
    assert captured["reason"] == "rate_limit_exceeded"
    blob = str(captured).lower()
    for forbidden in ("password", "bearer", "token", "totp", "mfa", "authorization"):
        assert forbidden not in blob
