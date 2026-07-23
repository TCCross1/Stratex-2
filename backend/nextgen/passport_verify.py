"""Hash-chain verification for NextGen Passport ledgers (C-P-002).

Verification never mutates the ledger. Historical unsigned entries are
classified as LEGACY_UNSEALED rather than automatically INVALID.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from .db import nx_collections, strip_mongo_id
from .passport_seal import verify_entry_seal


def _canonical_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _recompute_content_hash(entry: Dict[str, Any]) -> str:
    body = {
        "passport_id": entry.get("passport_id"),
        "seq": entry.get("seq"),
        "entry_type": entry.get("entry_type"),
        "payload": entry.get("payload"),
        "prior_hash": entry.get("prior_hash"),
        "at": entry.get("at"),
        "authored_by": entry.get("authored_by"),
    }
    return hashlib.sha256(_canonical_bytes(body)).hexdigest()


async def verify_passport_chain(
    *,
    tenant_id: str,
    passport_id: str,
) -> Dict[str, Any]:
    """Evaluate chain integrity. Never mutates data."""
    passport = await nx_collections.passports.find_one({
        "tenant_id": tenant_id,
        "canonical_id": passport_id,
    })
    if not passport:
        return {
            "result": "UNAVAILABLE",
            "passport_id": passport_id,
            "tenant_id": tenant_id,
            "issues": [{"code": "PASSPORT_NOT_FOUND"}],
            "entry_count": 0,
        }

    entries = [
        strip_mongo_id(e)
        async for e in nx_collections.passport_entries.find({
            "tenant_id": tenant_id,
            "passport_id": passport_id,
        }).sort("seq", 1)
    ]

    issues: List[Dict[str, Any]] = []
    has_legacy_unsealed = False
    seen_seq: Dict[int, int] = {}
    expected_seq = 1
    prior: Optional[str] = None

    for e in entries:
        seq = e.get("seq")
        if seq is None:
            issues.append({"code": "MISSING_ENTRY", "detail": "entry missing seq",
                           "entry_id": e.get("canonical_id")})
            continue
        seen_seq[seq] = seen_seq.get(seq, 0) + 1
        if seen_seq[seq] > 1:
            issues.append({"code": "DUPLICATE_SEQUENCE", "seq": seq,
                           "entry_id": e.get("canonical_id")})

        schema = e.get("schema_version")
        if schema is not None and str(schema) not in {"1", "2", "2.0"}:
            issues.append({"code": "UNSUPPORTED_SCHEMA", "schema_version": schema,
                           "entry_id": e.get("canonical_id")})

        if seq != expected_seq:
            # Gap or out-of-order relative to dense 1..N expectation.
            if seq > expected_seq:
                issues.append({
                    "code": "MISSING_ENTRY",
                    "expected_seq": expected_seq,
                    "found_seq": seq,
                })
            else:
                issues.append({
                    "code": "INVALID_SEQUENCE",
                    "expected_seq": expected_seq,
                    "found_seq": seq,
                    "entry_id": e.get("canonical_id"),
                })
        expected_seq = max(expected_seq, int(seq) + 1)

        if e.get("prior_hash") != prior:
            issues.append({
                "code": "INVALID_PREVIOUS_HASH",
                "seq": seq,
                "entry_id": e.get("canonical_id"),
                "expected_prior": prior,
                "stored_prior": e.get("prior_hash"),
            })

        recomputed = _recompute_content_hash(e)
        if recomputed != e.get("content_hash"):
            issues.append({
                "code": "INVALID_ENTRY_HASH",
                "seq": seq,
                "entry_id": e.get("canonical_id"),
            })

        seal_status, seal_detail = verify_entry_seal(e)
        if seal_status == "LEGACY_UNSEALED":
            has_legacy_unsealed = True
        elif seal_status == "SEAL_INVALID":
            issues.append({
                "code": "INVALID_SIGNATURE",
                "seq": seq,
                "entry_id": e.get("canonical_id"),
                "detail": seal_detail,
            })
        elif seal_status == "SEAL_KEY_MISSING":
            issues.append({
                "code": "INCOMPLETE",
                "seq": seq,
                "entry_id": e.get("canonical_id"),
                "detail": "seal_key_missing",
            })
        elif seal_status == "SEAL_UNSUPPORTED":
            issues.append({
                "code": "UNSUPPORTED_SCHEMA",
                "seq": seq,
                "entry_id": e.get("canonical_id"),
                "detail": seal_detail,
            })

        prior = e.get("content_hash")

    head_hash = passport.get("head_hash")
    head_revision = passport.get("revision")
    if entries:
        last = entries[-1]
        if head_hash and head_hash != last.get("content_hash"):
            issues.append({
                "code": "HEAD_MISMATCH",
                "passport_head_hash": head_hash,
                "last_entry_hash": last.get("content_hash"),
            })
        if head_revision is not None and last.get("revision") is not None:
            if int(head_revision) != int(last["revision"]):
                issues.append({
                    "code": "HEAD_MISMATCH",
                    "detail": "revision",
                    "passport_revision": head_revision,
                    "last_entry_revision": last.get("revision"),
                })

    # Receipt consistency (best-effort, non-mutating).
    for e in entries:
        receipt = await nx_collections.passport_receipts.find_one({
            "tenant_id": tenant_id,
            "passport_entry_id": e.get("canonical_id"),
        })
        if receipt and receipt.get("receipt_hash") not in {
            None, e.get("content_hash"),
        }:
            issues.append({
                "code": "INVALID_ENTRY_HASH",
                "detail": "receipt_mismatch",
                "entry_id": e.get("canonical_id"),
            })

    if any(i["code"] == "DUPLICATE_SEQUENCE" for i in issues):
        result = "DUPLICATE_SEQUENCE"
    elif any(i["code"] == "MISSING_ENTRY" for i in issues):
        result = "MISSING_ENTRY"
    elif any(i["code"] == "INVALID_PREVIOUS_HASH" for i in issues):
        result = "INVALID_PREVIOUS_HASH"
    elif any(i["code"] == "INVALID_ENTRY_HASH" for i in issues):
        result = "INVALID_ENTRY_HASH"
    elif any(i["code"] == "INVALID_SIGNATURE" for i in issues):
        result = "INVALID_SIGNATURE"
    elif any(i["code"] == "HEAD_MISMATCH" for i in issues):
        result = "HEAD_MISMATCH"
    elif any(i["code"] == "UNSUPPORTED_SCHEMA" for i in issues):
        result = "UNSUPPORTED_SCHEMA"
    elif any(i["code"] == "INVALID_SEQUENCE" for i in issues):
        result = "INVALID_SEQUENCE"
    elif any(i["code"] == "INCOMPLETE" for i in issues):
        result = "INCOMPLETE"
    elif has_legacy_unsealed and not issues:
        result = "VALID_WITH_LEGACY_UNSEALED_ENTRIES"
    elif not issues:
        result = "VALID"
    else:
        result = "INVALID_SEQUENCE"

    return {
        "result": result,
        "passport_id": passport_id,
        "tenant_id": tenant_id,
        "property_id": passport.get("property_id"),
        "entry_count": len(entries),
        "passport_revision": passport.get("revision"),
        "passport_head_hash": passport.get("head_hash"),
        "has_legacy_unsealed_entries": has_legacy_unsealed,
        "issues": issues,
        # Never expose signing keys or raw confidential payloads.
        "safe": True,
    }
