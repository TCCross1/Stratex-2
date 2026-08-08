"""
Passport property records keyed by normalized address — Field Test v1.

Core seals missions; this registry stores the official Passport-side property
record and mints a claim_code when no Habitat owner is linked yet.

Does NOT replace governed_publish or append_entry. Field-test minimum uses an
in-process store (optionally persisted as JSON for demos).
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .address_normalize import normalize_address

logger = logging.getLogger("stratex.passport_property_registry")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# tenant_id + normalized_address_hash -> property record
_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _registry_key(tenant_id: str, normalized_address_hash: str) -> str:
    return f"{tenant_id}:{normalized_address_hash}"


def _registry_path() -> Optional[Path]:
    raw = (os.environ.get("STRATEX_PASSPORT_PROPERTY_REGISTRY_PATH") or "").strip()
    if not raw:
        return None
    return Path(raw)


def _persist_registry() -> None:
    path = _registry_path()
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_REGISTRY, indent=2, sort_keys=True), encoding="utf-8")
    except OSError as exc:
        logger.warning("passport_property_registry persist failed: %s", exc)


def _load_registry() -> None:
    path = _registry_path()
    if not path or not path.is_file():
        return
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            _REGISTRY.clear()
            _REGISTRY.update(loaded)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("passport_property_registry load failed: %s", exc)


_load_registry()


def reset_registry() -> None:
    """Test helper — clear in-memory registry."""
    _REGISTRY.clear()


def generate_claim_code() -> str:
    """Human-readable claim code for Habitat owner onboarding."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    part = lambda: "".join(secrets.choice(alphabet) for _ in range(4))
    return f"STRX-{part()}-{part()}"


def habitat_owner_exists(record: Optional[Dict[str, Any]]) -> bool:
    if not record:
        return False
    return bool(record.get("habitat_owner_user_id"))


def get_property_by_address(tenant_id: str, address_line: str, city_state_zip: str) -> Optional[Dict[str, Any]]:
    normalized = normalize_address(address_line, city_state_zip)
    return _REGISTRY.get(_registry_key(tenant_id, normalized["normalized_address_hash"]))


def get_property_by_claim_code(claim_code: str) -> Optional[Dict[str, Any]]:
    code = (claim_code or "").strip().upper()
    for record in _REGISTRY.values():
        if (record.get("claim_code") or "").upper() == code:
            return dict(record)
    return None


def register_sealed_mission(
    sealed_package: Dict[str, Any],
    *,
    address_line: str,
    city_state_zip: str,
) -> Dict[str, Any]:
    """
    Upsert Passport property record for normalized address after a successful seal.

    When no Habitat owner is linked, mint claim_code once (idempotent per address).
    """
    tenant_id = sealed_package["tenant_id"]
    property_id = sealed_package["property_id"]
    normalized = normalize_address(address_line, city_state_zip)
    key = _registry_key(tenant_id, normalized["normalized_address_hash"])
    now = _now_iso()

    mission_entry = {
        "mission_id": sealed_package.get("mission_id"),
        "package_id": sealed_package.get("package_id"),
        "content_hash_prefix": (sealed_package.get("content_hash") or "")[:16],
        "sealed_at": (sealed_package.get("seal_record") or {}).get("sealed_at") or now,
    }

    existing = _REGISTRY.get(key)
    if existing:
        missions: List[Dict[str, Any]] = list(existing.get("missions") or [])
        if not any(m.get("package_id") == mission_entry["package_id"] for m in missions):
            missions.append(mission_entry)
        record = dict(existing)
        record["missions"] = missions
        record["updated_at"] = now
        record["latest_package_id"] = mission_entry["package_id"]
        record["property_id"] = property_id
    else:
        record = {
            "record_id": secrets.token_hex(8),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "normalized_address": normalized,
            "habitat_owner_user_id": None,
            "claim_code": None,
            "claim_code_status": None,
            "claim_code_created_at": None,
            "missions": [mission_entry],
            "latest_package_id": mission_entry["package_id"],
            "created_at": now,
            "updated_at": now,
        }

    claim_created = False
    if not habitat_owner_exists(record) and not record.get("claim_code"):
        record["claim_code"] = generate_claim_code()
        record["claim_code_status"] = "pending_redemption"
        record["claim_code_created_at"] = now
        claim_created = True

    _REGISTRY[key] = record
    _persist_registry()

    return {
        "property_record": dict(record),
        "normalized_address": normalized,
        "habitat_owner_exists": habitat_owner_exists(record),
        "claim_code_created": claim_created,
        "claim_code": record.get("claim_code"),
    }


def link_habitat_owner(
    *,
    tenant_id: str,
    address_line: str,
    city_state_zip: str,
    habitat_owner_user_id: str,
) -> Dict[str, Any]:
    """
    Mark a property as owned in Habitat (used by future redemption flow / tests).
    """
    normalized = normalize_address(address_line, city_state_zip)
    key = _registry_key(tenant_id, normalized["normalized_address_hash"])
    record = _REGISTRY.get(key)
    if not record:
        raise KeyError("property record not found for normalized address")

    updated = dict(record)
    updated["habitat_owner_user_id"] = habitat_owner_user_id
    updated["claim_code_status"] = "redeemed"
    updated["updated_at"] = _now_iso()
    _REGISTRY[key] = updated
    _persist_registry()
    return dict(updated)
