"""Versioned HMAC-SHA256 entry sealing for NextGen Passport ledger entries.

Prospective sealing only — historical hash-only entries are never rewritten.
Signing secrets come from the environment; nothing is committed or logged.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Dict, Optional, Tuple

from .db import now_iso_utc

ALGORITHM = "HMAC-SHA256"
_ENV_ACTIVE = "PASSPORT_SEAL_KEY_VERSION"
_ENV_KEY_PREFIX = "PASSPORT_SEAL_KEY_"  # e.g. PASSPORT_SEAL_KEY_v1


class SealConfigurationError(RuntimeError):
    """Raised when sealing is required but key material is absent/invalid."""


def _strict_mode() -> bool:
    env = (os.environ.get("APP_ENV") or "").strip().lower()
    if env in {"production", "prod", "live"}:
        return True
    return (os.environ.get("PASSPORT_SEAL_REQUIRED") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def active_key_version() -> Optional[str]:
    return (os.environ.get(_ENV_ACTIVE) or "").strip() or None


def _key_for_version(version: str) -> Optional[bytes]:
    raw = os.environ.get(f"{_ENV_KEY_PREFIX}{version}") or ""
    raw = raw.strip()
    if not raw:
        return None
    return raw.encode("utf-8")


def sealing_available() -> bool:
    ver = active_key_version()
    return bool(ver and _key_for_version(ver))


def canonicalize_for_seal(entry_body: Dict[str, Any]) -> bytes:
    import json
    return json.dumps(entry_body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal_entry(entry_body: Dict[str, Any]) -> Dict[str, Any]:
    """Return sealing metadata for a newly committed entry.

    In strict/production mode, missing key material fails closed.
    In non-strict environments without keys, returns empty sealing metadata
    so local tests can still exercise concurrency/idempotency without secrets.
    """
    ver = active_key_version()
    key = _key_for_version(ver) if ver else None
    if not ver or not key:
        if _strict_mode():
            raise SealConfigurationError(
                "Passport entry sealing is required but PASSPORT_SEAL_KEY_VERSION "
                "/ PASSPORT_SEAL_KEY_<version> are not configured."
            )
        return {
            "signature_algorithm": None,
            "signature_key_version": None,
            "entry_signature": None,
            "sealed_at": None,
            "seal_status": "UNSEALED_DEV",
        }
    digest = hmac.new(key, canonicalize_for_seal(entry_body), hashlib.sha256).hexdigest()
    return {
        "signature_algorithm": ALGORITHM,
        "signature_key_version": ver,
        "entry_signature": digest,
        "sealed_at": now_iso_utc(),
        "seal_status": "SEALED",
    }


def verify_entry_seal(entry: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Return (status, detail).

    status ∈ {SEAL_VALID, LEGACY_UNSEALED, SEAL_INVALID, SEAL_KEY_MISSING,
              SEAL_UNSUPPORTED}
    """
    algo = entry.get("signature_algorithm")
    sig = entry.get("entry_signature")
    ver = entry.get("signature_key_version")
    if not algo and not sig:
        # Historical hash-only / Phase-2B tenant-salt signature rows.
        if entry.get("signature") and not entry.get("entry_signature"):
            return "LEGACY_UNSEALED", "hash_or_tenant_salt_signature"
        return "LEGACY_UNSEALED", "no_seal_metadata"
    if algo != ALGORITHM:
        return "SEAL_UNSUPPORTED", f"algorithm={algo!r}"
    if not ver or not sig:
        return "SEAL_INVALID", "incomplete_seal_metadata"
    key = _key_for_version(ver)
    if not key:
        return "SEAL_KEY_MISSING", f"version={ver}"
    body = {
        "passport_id": entry.get("passport_id"),
        "seq": entry.get("seq"),
        "entry_type": entry.get("entry_type"),
        "payload": entry.get("payload"),
        "prior_hash": entry.get("prior_hash"),
        "at": entry.get("at"),
        "authored_by": entry.get("authored_by"),
        "content_hash": entry.get("content_hash"),
        "revision": entry.get("revision"),
    }
    expected = hmac.new(key, canonicalize_for_seal(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return "SEAL_INVALID", "digest_mismatch"
    return "SEAL_VALID", ver
