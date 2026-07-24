"""Writer-authority inventory assertions for C-P-001C / C-P-002 (static)."""
from __future__ import annotations

from pathlib import Path

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
        if "passport_entries.insert_one" in text:
            offenders.append(path.name)
        if "nextgen_passport_entries" in text and "insert_one" in text:
            offenders.append(path.name)
    assert offenders == []

    # Supporting modules may assist but must not be alternate writers.
    for rel in (
        "nextgen/governed_publish_service.py",
        "nextgen/approval_policy.py",
        "nextgen/passport_conflicts.py",
        "nextgen/passport_verify.py",
        "nextgen/passport_indexes.py",
        "nextgen/passport_seal.py",
    ):
        text = _source(rel)
        assert "passport_entries.insert_one" not in text, rel


def test_intelligence_and_findings_delegate_through_governed_publish():
    intel = _source("nextgen/routes/intelligence.py")
    findings = _source("nextgen/routes/findings.py")
    assert "from ..governed_publish_service import governed_publish" in intel
    assert "await governed_publish(" in intel
    assert "from ..governed_publish_service import governed_publish" in findings
    assert "await governed_publish(" in findings
    assert "passport_entries.insert_one" not in intel
    assert "passport_entries.insert_one" not in findings
    # Direct ledger inserts must not remain in approval doors.
    assert "await append_entry(" not in intel
    assert "await append_entry(" not in findings


def test_governed_publish_delegates_to_append_entry():
    pub = _source("nextgen/governed_publish_service.py")
    assert "from .passport_service import append_entry" in pub
    assert "await append_entry(" in pub
    assert "MODULE_IDENTITY = \"nextgen.governed_publish_service\"" in pub
    assert "workflow.governed_publish_service" not in pub
    # Runtime proof: importable identity matches the real module path.
    from nextgen.governed_publish_service import MODULE_IDENTITY, governed_publish
    assert MODULE_IDENTITY == "nextgen.governed_publish_service"
    assert callable(governed_publish)


def test_both_doors_use_unified_approval_policy():
    intel = _source("nextgen/routes/intelligence.py")
    findings = _source("nextgen/routes/findings.py")
    assert "evaluate_approval_policy" in intel
    assert "evaluate_approval_policy" in findings
    policy = _source("nextgen/approval_policy.py")
    assert "SEPARATION_OF_DUTIES" in policy
    assert "superadmin" in policy


def test_habitat_has_no_canonical_passport_write():
    habitat = _source("nextgen/routes/habitat.py")
    assert "append_entry" not in habitat
    assert "governed_publish" not in habitat
    assert "passport_entries.insert_one" not in habitat
    assert "property_passports" not in habitat
    # Import / module coupling must also stay absent (projection-only surface).
    assert "from ..passport_service" not in habitat
    assert "from ..governed_publish_service" not in habitat
    assert "from ..approval_policy" not in habitat
    assert "passport_entries" not in habitat
    assert "nextgen_passport_entries" not in habitat
    for i, line in enumerate(habitat.splitlines(), 1):
        if "insert_one" not in line:
            continue
        assert "passport" not in line.lower(), (
            f"habitat.py:{i} must not insert into passport collections: {line}"
        )


def test_habitat_projection_schemas_have_no_passport_write_authority():
    schemas_dir = BACKEND / "nextgen" / "schemas" / "habitat"
    assert schemas_dir.is_dir()
    import_needles = (
        "from ..passport_service",
        "from ..governed_publish_service",
        "from ..approval_policy",
        "from nextgen.passport_service",
        "from nextgen.governed_publish_service",
        "from nextgen.approval_policy",
        "passport_entries.insert_one",
        "await append_entry",
        "await governed_publish",
    )
    for path in schemas_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in import_needles:
            assert needle not in text, f"{path.name} must not contain {needle!r}"


def test_legacy_internal_writers_remain_disclosed():
    # Compatibility writers that remain (not eliminated by C-P-001C / C-P-002).
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
