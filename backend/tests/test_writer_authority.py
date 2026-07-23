"""Writer-authority inventory assertions for C-P-001C (static + import)."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def _source(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8")


def test_append_entry_is_sole_nextgen_ledger_writer():
    svc = _source("nextgen/passport_service.py")
    assert "async def append_entry" in svc
    assert "passport_entries.insert_one" in svc

    # No other NextGen route module should insert into passport_entries.
    routes_dir = BACKEND / "nextgen" / "routes"
    offenders = []
    for path in routes_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "passport_entries.insert_one" in text or "nextgen_passport_entries" in text and "insert_one" in text:
            offenders.append(path.name)
    assert offenders == []


def test_intelligence_and_findings_delegate_to_append_entry():
    intel = _source("nextgen/routes/intelligence.py")
    findings = _source("nextgen/routes/findings.py")
    assert "from ..passport_service import append_entry" in intel
    assert "await append_entry(" in intel
    assert "from ..passport_service import append_entry" in findings
    assert "await append_entry(" in findings
    assert "passport_entries.insert_one" not in intel
    assert "passport_entries.insert_one" not in findings


def test_habitat_has_no_canonical_passport_write():
    habitat = _source("nextgen/routes/habitat.py")
    assert "append_entry" not in habitat
    assert "passport_entries.insert_one" not in habitat
    assert "property_passports" not in habitat


def test_legacy_internal_writers_remain_disclosed():
    # Compatibility writers that remain (not eliminated by C-P-001C).
    storm = _source("routes/storm_watcher.py")
    assert "property_passports" in storm
    assert "_append_ledger" in storm

    snap = _source("routes/claim_snapshot.py")
    assert "require_legacy_passport_writer" in snap

    cosign = _source("routes/claim_cosign.py")
    assert "require_legacy_passport_writer" in cosign
    assert "purpose-bound" in cosign.lower() or "purpose-bound" in _source(
        "routes/claim_cosign.py"
    ).lower()


def test_dev_auth_module_documents_non_distributed_limiter():
    text = _source("dev_auth.py")
    assert "NOT distributed-production-safe" in text or "NOT distributed" in text
    assert "X-Forwarded-For" in text
