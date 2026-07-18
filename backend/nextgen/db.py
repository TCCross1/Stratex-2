"""NextGen DB helpers.

- `nx_collections` gives access to nextgen_-prefixed collections.
- `nx_id()` returns a lexicographically monotonic ULID-like string for canonical
  identifiers (as required by Canonical Data Model v1.0 §1.1).
- `now_iso_utc()` returns a stable ISO-8601 UTC timestamp used across all
  audit and ledger writes.
"""
from __future__ import annotations

import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core import db as _shared_db

# Environment guard — always use MONGO_URL/DB_NAME from .env.
assert os.environ.get("MONGO_URL"), "MONGO_URL missing"
assert os.environ.get("DB_NAME"), "DB_NAME missing"


class _Collections:
    """Namespaced accessor for NextGen collections.

    Access as `nx_collections.organizations`, `.properties`, `.missions`, etc.
    All collections are prefixed with `nextgen_` inside the shared MongoDB.
    """

    def __getattr__(self, name: str):
        return _shared_db[f"nextgen_{name}"]


nx_collections = _Collections()


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# Base32 (Crockford) alphabet for ULID-like ids.
_ULID_ALPHA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def nx_id() -> str:
    """Return a 26-char lexicographically ordered id (ULID pattern).

    We generate a monotonic id ourselves rather than pulling in a dep, since
    we only need lexical ordering + uniqueness at typical request rates.
    """
    ts_ms = int(time.time() * 1000)
    ts_part = ""
    n = ts_ms
    for _ in range(10):
        ts_part = _ULID_ALPHA[n & 0x1F] + ts_part
        n >>= 5
    rnd_bytes = secrets.token_bytes(10)
    rnd_int = int.from_bytes(rnd_bytes, "big")
    rnd_part = ""
    for _ in range(16):
        rnd_part = _ULID_ALPHA[rnd_int & 0x1F] + rnd_part
        rnd_int >>= 5
    return ts_part + rnd_part


def strip_mongo_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Drop `_id` (ObjectId) so responses stay JSON-safe.

    Canonical NextGen id lives on the `canonical_id` field per Data Model v1.0.
    """
    if not doc:
        return doc
    d = dict(doc)
    d.pop("_id", None)
    return d
