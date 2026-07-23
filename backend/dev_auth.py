"""Development-only authentication containment (C-P-001C).

Enabled only when ALL of the following hold:
  * DEV_NO_AUTH is explicitly truthy, AND
  * APP_ENV is an explicit local/dev/preview/sandbox/test value, AND
  * no production environment or production-hostname signal is present.

Production rejects this bypass unconditionally (APP_ENV + hostname checks),
even if DEV_NO_AUTH=true is misconfigured.

This module mints real JWTs via the existing create_access_token helper for
clearly-synthetic development identities. It does not weaken password login,
MFA, tenant, role, or property authorization. Synthetic identities carry
unusable random password hashes and cannot authenticate through /api/auth/login.

Rate limiting is process-local and in-memory: suitable for local/preview and
single-process containment only. It is NOT distributed-production-safe.
"""
from __future__ import annotations

import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core import db, _public_user
from stratex_auth import create_access_token, create_refresh_token, hash_password

dev_router = APIRouter(prefix="/api/auth/dev", tags=["dev-auth"])

DEV_ROLES = ("admin", "ceo", "contractor", "operator")
DEFAULT_ROLE = "admin"

_RATE_MAX = 10
_RATE_WINDOW_SEC = 60.0
_RATE_BUCKET_CAP = 4096
_rate_buckets: Dict[str, Deque[float]] = {}

_PROD_ENVS = {"production", "prod", "live"}
_ALLOWED_ENVS = {"local", "development", "dev", "preview", "sandbox", "test"}
_PROD_DOMAINS = ("stratexdrone.com",)
_TRUTHY = {"true", "1", "yes", "on"}

_SYNTHETIC: Dict[str, Dict[str, str]] = {
    "admin": {
        "email": "dev-admin@stratex.dev",
        "legal": "DEV Admin (BYPASS)",
        "company": "STRATEX DEV SANDBOX",
    },
    "ceo": {
        "email": "dev-ceo@stratex.dev",
        "legal": "DEV CEO (BYPASS)",
        "company": "STRATEX DEV SANDBOX",
    },
    "contractor": {
        "email": "dev-contractor@stratex.dev",
        "legal": "DEV Contractor (BYPASS)",
        "company": "STRATEX DEV SANDBOX",
    },
    "operator": {
        "email": "dev-operator@stratex.dev",
        "legal": "DEV Operator (BYPASS)",
        "company": "STRATEX FLEET DEV",
    },
}


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def is_production() -> bool:
    """True when any production signal is present.

    CEO_EMAIL is intentionally ignored: it may contain the company domain in
    every environment and must not be treated as a production host signal.
    """
    if _env("APP_ENV").lower() in _PROD_ENVS:
        return True
    haystack = " ".join(
        [
            _env("CORS_ORIGINS"),
            _env("PUBLIC_FRONTEND_URL"),
            _env("FRONTEND_URL"),
            _env("PROD_HOSTS"),
        ]
    ).lower()
    return any(dom in haystack for dom in _PROD_DOMAINS)


def dev_auth_enabled() -> bool:
    """Single source of truth for whether the bypass may operate."""
    if _env("DEV_NO_AUTH").lower() not in _TRUTHY:
        return False
    if is_production():
        return False
    return _env("APP_ENV").lower() in _ALLOWED_ENVS


def environment_label() -> str:
    return _env("APP_ENV").lower() or "unknown"


def _rate_limit_key(request: Request) -> str:
    # Do not trust X-Forwarded-For without an explicit trusted-proxy policy.
    return request.client.host if request.client else "unknown"


def _prune_rate_buckets(now: float) -> None:
    """Drop stale/empty buckets and enforce a hard key cap."""
    stale = [
        key
        for key, dq in _rate_buckets.items()
        if not dq or (now - dq[-1]) > _RATE_WINDOW_SEC
    ]
    for key in stale:
        _rate_buckets.pop(key, None)
    if len(_rate_buckets) <= _RATE_BUCKET_CAP:
        return
    # Evict least-recently-active buckets when over cap.
    ranked = sorted(
        _rate_buckets.items(),
        key=lambda item: item[1][-1] if item[1] else 0.0,
    )
    overflow = len(_rate_buckets) - _RATE_BUCKET_CAP
    for key, _ in ranked[:overflow]:
        _rate_buckets.pop(key, None)


def _check_rate_limit(request: Request) -> None:
    key = _rate_limit_key(request)
    now = time.monotonic()
    _prune_rate_buckets(now)
    dq = _rate_buckets.setdefault(key, deque())
    while dq and (now - dq[0]) > _RATE_WINDOW_SEC:
        dq.popleft()
    if len(dq) >= _RATE_MAX:
        retry_after = max(1, int(_RATE_WINDOW_SEC - (now - dq[0])) + 1)
        raise HTTPException(
            429,
            "Too many development-login attempts. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
    dq.append(now)


def _reset_rate_limits() -> None:
    """Test helper — clears all rate-limit buckets."""
    _rate_buckets.clear()


async def _audit_rate_limit_block(request: Request) -> None:
    """Record a throttled attempt with no secrets."""
    try:
        await db.dev_auth_events.insert_one(
            {
                "id": str(uuid.uuid4()),
                "at": datetime.now(timezone.utc).isoformat(),
                "event": "dev_auth.rate_limited",
                "route": request.url.path,
                "method": request.method,
                "ip": request.client.host if request.client else None,
                "reason": "rate_limit_exceeded",
            }
        )
    except Exception:
        # Best-effort audit must never grant access.
        pass


async def _ensure_synthetic_user(role: str) -> Dict[str, Any]:
    """Return the clearly-synthetic sandbox identity for `role`."""
    spec = _SYNTHETIC[role]
    existing = await db.users.find_one({"email": spec["email"]})
    if existing:
        return existing
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": str(uuid.uuid4()),
        "email": spec["email"],
        "legal_name": spec["legal"],
        "company_name": spec["company"],
        "role": role,
        # Unusable random hash — cannot authenticate via password login.
        "password_hash": hash_password(uuid.uuid4().hex + uuid.uuid4().hex),
        "totp_secret": None,
        "totp_enrolled": False,
        "nda_accepted": True,
        "nda_signed_at": now,
        "dev_synthetic": True,
        "tour_mode": False,
        "created_at": now,
    }
    await db.users.insert_one(dict(user))
    return user


async def _audit_role_entry(user: Dict[str, Any], request: Request) -> None:
    try:
        await db.dev_auth_events.insert_one(
            {
                "id": str(uuid.uuid4()),
                "at": datetime.now(timezone.utc).isoformat(),
                "event": "dev_auth.role_entered",
                "user_id": user["id"],
                "email": user["email"],
                "role": user["role"],
                "environment": environment_label(),
                "ip": request.client.host if request.client else None,
                "synthetic": True,
            }
        )
    except Exception:
        pass


class DevLoginBody(BaseModel):
    role: str = DEFAULT_ROLE


@dev_router.get("/status")
async def dev_status():
    """Safe in every environment — reports enabled=false in production."""
    return {
        "enabled": dev_auth_enabled(),
        "environment": environment_label(),
        "production_locked": is_production(),
        "roles": list(DEV_ROLES),
        "default_role": DEFAULT_ROLE,
        "banner": "DEVELOPMENT AUTH BYPASS ACTIVE",
    }


@dev_router.post("/login")
async def dev_login(body: DevLoginBody, request: Request):
    # Production check always wins over rate-limit and feature flags.
    if is_production():
        raise HTTPException(
            403,
            "Development auth bypass is permanently disabled in production.",
        )
    try:
        _check_rate_limit(request)
    except HTTPException as exc:
        if exc.status_code == 429:
            await _audit_rate_limit_block(request)
        raise
    if not dev_auth_enabled():
        raise HTTPException(
            403,
            "Development auth bypass is disabled. Set DEV_NO_AUTH=true and a "
            "non-production APP_ENV (local/dev/preview) to enable it.",
        )

    role = (body.role or DEFAULT_ROLE).strip().lower()
    if role not in DEV_ROLES:
        raise HTTPException(400, f"role must be one of {list(DEV_ROLES)}")

    user = await _ensure_synthetic_user(role)
    access = create_access_token(user["id"], user["role"], user["email"])
    refresh = create_refresh_token(user["id"])
    await _audit_role_entry(user, request)

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "user": _public_user(user),
        "dev_bypass": True,
        "environment": environment_label(),
    }
