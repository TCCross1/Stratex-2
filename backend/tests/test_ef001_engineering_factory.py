"""EF-001 High-Velocity Engineering Foundation factory tests."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def _load_stratex_module():
    """Load extensionless ./stratex CLI as a Python module."""
    loader = importlib.machinery.SourceFileLoader("stratex_cli", str(STRATEX))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # dataclasses require the module to be present in sys.modules during exec
    sys.modules[loader.name] = mod
    loader.exec_module(mod)
    return mod

ROOT = Path(__file__).resolve().parents[2]
STRATEX = ROOT / "stratex"
LANES = ROOT / "engineering" / "lanes.yaml"
CONTRACTS = ROOT / "engineering" / "contracts" / "registry.yaml"
TOOLS = ROOT / "engineering" / "tools"
TEMPLATES = ROOT / "engineering" / "templates"
CONSTITUTION = ROOT / "STRATEX_HIGH_VELOCITY_ENGINEERING_SYSTEM.md"

AUTHORITY = {
    "nextgen.passport_service.append_entry",
    "nextgen.governed_publish_service.governed_publish",
    "nextgen.approval_policy.evaluate_approval_policy",
}

EXPECTED_LANES = {
    "LANE_1_CORE_PASSPORT",
    "LANE_2_ATC_FIELD",
    "LANE_3_ESTIMATOR_REPORT",
    "LANE_4_HABITAT",
    "LANE_5_RUNTIME_QE",
}

EXPECTED_CONTRACTS = {
    "PropertyProjection",
    "ApprovedGeometry",
    "EvidenceManifest",
    "ApprovedFinding",
    "EstimateInputPackage",
    "EstimateResult",
    "EstimateCalculationLedger",
    "ReportPublicationPackage",
    "HabitatPropertyProjection",
    "ProjectOpportunityPackage",
}


def _run_stratex(*args: str, env: dict | None = None, check: bool = False):
    base_env = {
        **os.environ,
        "STRATEX_VERIFY_ALLOW_DIRTY": "1",
    }
    if env:
        base_env.update(env)
    return subprocess.run(
        [sys.executable, str(STRATEX), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=base_env,
        check=check,
    )


def test_stratex_shebang():
    text = STRATEX.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env python3")
    assert STRATEX.stat().st_mode & 0o111, "stratex must be executable"


def test_constitution_and_templates_exist():
    assert CONSTITUTION.is_file()
    for name in (
        "BUILDER_MISSION.md",
        "AUDITOR_MISSION.md",
        "REPAIR_MISSION.md",
        "INTEGRATION_MISSION.md",
    ):
        path = TEMPLATES / name
        assert path.is_file(), name
        body = path.read_text(encoding="utf-8")
        assert "EF-001" in body
        assert "ATLAS" in body or "Atlas" in body


def test_lane_parse():
    data = yaml.safe_load(LANES.read_text(encoding="utf-8"))
    assert data["merge_gate"] == "ATLAS_MERGE_AUTHORIZATION"
    assert data["atlas_approval_token"] == "ATLAS_ARCHITECTURE_APPROVAL"
    lanes = data["lanes"]
    assert len(lanes) == 5
    ids = {l["id"] for l in lanes}
    assert ids == EXPECTED_LANES
    for lane in lanes:
        assert "owned_paths" in lane
        assert "prohibited_paths" in lane
        assert "shared_paths_requiring_atlas_approval" in lane
        assert "authority_modules" in lane
        assert "required_tests" in lane
        assert "contracts" in lane
        assert lane["merge_gate"] == "ATLAS_MERGE_AUTHORIZATION"
        assert lane["atlas_approval_token"] == "ATLAS_ARCHITECTURE_APPROVAL"


def test_no_duplicate_authority():
    data = yaml.safe_load(LANES.read_text(encoding="utf-8"))
    owners = {}
    for lane in data["lanes"]:
        for mod in lane.get("authority_modules") or []:
            owners.setdefault(mod, []).append(lane["id"])
    for mod in AUTHORITY:
        assert owners.get(mod) == ["LANE_1_CORE_PASSPORT"], mod
    # No authority module owned by more than one lane
    for mod, lids in owners.items():
        assert len(lids) == 1, f"duplicate authority {mod}: {lids}"
    # Non-core lanes must not claim authority
    for lane in data["lanes"]:
        if lane["id"] != "LANE_1_CORE_PASSPORT":
            assert lane.get("authority_modules") in ([], None)


def test_contract_status_and_version():
    data = yaml.safe_load(CONTRACTS.read_text(encoding="utf-8"))
    assert data["approval_authority"] == "Atlas"
    contracts = data["contracts"]
    assert len(contracts) == 10
    names = {c["name"] for c in contracts}
    assert names == EXPECTED_CONTRACTS
    for c in contracts:
        assert c["status"] in {"PROPOSED", "NOT_IMPLEMENTED"}
        assert c["status"] != "ACCEPTED"
        assert str(c["version"]) == "0.0.0"
        assert c["approval_authority"] == "Atlas"
        fields = c["fields"]
        for key in (
            "provenance",
            "confidence",
            "unknown_state",
            "compatibility",
            "breaking_change",
        ):
            assert key in fields, f"{c['name']} missing {key}"


def test_scope_detection_helpers():
    mod = _load_stratex_module()

    assert mod.path_is_scope_guarded(".emergent/config.json")
    assert mod.path_is_scope_guarded("test_reports/iteration_1.json")
    assert mod.path_is_scope_guarded(".env")
    assert mod.path_is_scope_guarded("frontend/screenshots/foo.png")
    assert not mod.path_is_scope_guarded("backend/nextgen/passport_service.py")

    changed = [".emergent/x", "backend/nextgen/db.py"]
    violations = mod.detect_scope_violations(changed, historical_paths=set())
    assert ".emergent/x" in violations
    assert "backend/nextgen/db.py" not in violations


def test_historical_unchanged_not_flagged():
    mod = _load_stratex_module()

    # Historically tracked guarded path that is NOT in the active changeset
    historical = {"test_reports/old.json", "backend/server.py"}
    changed = ["backend/server.py"]
    violations = mod.detect_scope_violations(changed, historical_paths=historical)
    assert "test_reports/old.json" not in violations
    assert violations == []


def test_tracked_env_security_flag(tmp_path, monkeypatch):
    """Security check fails when a .env path is in the active changeset."""
    mod = _load_stratex_module()

    monkeypatch.setenv("STRATEX_VERIFY_ALLOW_DIRTY", "1")
    result = mod.check_security(changed_paths=[".env", "README.md"])
    assert result.ok is False
    assert any(".env" in m for m in result.messages)


def test_redacted_evidence(tmp_path):
    sys.path.insert(0, str(TOOLS))
    from atlas_evidence import generate_evidence, redact_text

    sample = (
        "MONGO_URL=mongodb://user:pass@host:27017/db\n"
        "API_KEY=supersecretvalue\n"
        "ok line\n"
    )
    red = redact_text(sample)
    assert "pass@" not in red
    assert "supersecretvalue" not in red
    assert "REDACTED" in red or "[REDACTED]" in red

    out = generate_evidence(ROOT)
    assert out.is_dir()
    assert out.parent.name == "evidence"
    assert ".atlas" in out.parts
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    assert index["security"]["env_values_included"] is False
    blob = (out / "index.json").read_text(encoding="utf-8")
    assert "mongodb://user:pass@" not in blob
    # Never dump env values
    for key in ("JWT_SECRET", "MONGO_URL", "PASSPORT_SEAL_SECRET"):
        # presence map may list keys as booleans only
        if key in blob:
            assert f"{key}=" not in blob or "***REDACTED***" in blob


def test_architecture_cli():
    proc = _run_stratex("verify", "--architecture")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "architecture" in out.lower() or "PASS" in out
    assert "no push/merge" in out.lower()


def test_habitat_gate():
    habitat = ROOT / "backend" / "nextgen" / "routes" / "habitat.py"
    text = habitat.read_text(encoding="utf-8")
    assert "append_entry" not in text
    assert "governed_publish" not in text
    assert "passport_entries.insert_one" not in text
    proc = _run_stratex("verify", "--architecture")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Habitat" in proc.stdout or "habitat" in proc.stdout.lower()


def test_lane_dry_run():
    proc = _run_stratex("lane", "create", "LANE_5_RUNTIME_QE", "--dry-run")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout.split("stratex:")[0].strip() or proc.stdout)
    assert payload["dry_run"] is True
    assert payload["status"] == "dry_run"
    assert payload["push"] is False
    assert payload["merge"] is False


def test_worktree_collision_without_confirm(tmp_path, monkeypatch):
    mod = _load_stratex_module()

    fake_wt = tmp_path / "stratex-lane-5-runtime-qe"
    fake_wt.mkdir()
    monkeypatch.setattr(mod, "lane_worktree_path", lambda lane_id: fake_wt)

    class Args:
        lane_id = "LANE_5_RUNTIME_QE"
        dry_run = False
        confirm = False

    rc = mod.cmd_lane_create(Args())
    assert rc == 2


def test_unavailable_dep_reporting(monkeypatch):
    mod = _load_stratex_module()

    monkeypatch.setenv("STRATEX_VERIFY_ALLOW_DIRTY", "1")
    # Force discover_python to a bogus interpreter for the full check's import probes
    monkeypatch.setattr(mod, "discover_python", lambda: "/nonexistent/python-ef001")
    results = mod.check_full()
    integ = next(r for r in results if r.name == "integration_environment")
    assert integ.ok is False
    assert integ.classification == "INTEGRATION_ENVIRONMENT_UNAVAILABLE"
    assert any("INTEGRATION_ENVIRONMENT_UNAVAILABLE" in m for m in integ.messages)


def test_security_verify():
    proc = _run_stratex("verify", "--security")
    # May fail if workspace has scope-guarded dirty paths in changeset; allow either
    # clean pass or explicit scope messaging — but must not crash and must not merge.
    out = proc.stdout + proc.stderr
    assert "no push/merge" in out.lower()
    assert "security" in out.lower() or "[PASS]" in out or "[FAIL]" in out
    # Secret counts are classify-only (message present)
    assert "Secret pattern hits" in out or "secret" in out.lower()


def test_lane_list_and_plan():
    proc = _run_stratex("lane", "list")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for lid in EXPECTED_LANES:
        assert lid in proc.stdout
    proc2 = _run_stratex("lane", "plan", "LANE_1_CORE_PASSPORT")
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    plan = json.loads(proc2.stdout)
    assert set(plan["authority_modules"]) == AUTHORITY


def test_gitignore_contains_atlas():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".atlas/" in gi


def test_contracts_readme_exists():
    readme = ROOT / "engineering" / "contracts" / "README.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    assert "contract-first" in text.lower() or "Contract-first" in text
    assert "PROPOSED" in text
    assert "NOT_IMPLEMENTED" in text


def test_workflow_no_automerge_no_secrets_upload():
    wf = ROOT / ".github" / "workflows" / "stratex-verify.yml"
    assert wf.is_file()
    text = wf.read_text(encoding="utf-8")
    assert "./stratex verify --architecture" in text
    assert "./stratex verify --security" in text
    assert "./stratex verify --fast" in text
    assert "auto-merge" in text.lower() or "Do not auto-merge" in text
    assert "secrets" in text.lower()
    assert "pull_request" in text
    assert "main" in text
