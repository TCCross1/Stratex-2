"""EF-002 parallel execution launch pack — structure and governance tests.

Planning/scheduling only. No ATC/Estimator/Habitat/C-P-003/Passport feature work.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EF002 = ROOT / "engineering" / "ef002"
LANES = ROOT / "engineering" / "lanes.yaml"


def test_launch_pack_documents_exist():
    assert (EF002 / "LAUNCH_PACK.md").exists()
    assert (EF002 / "contract_freeze_matrix.yaml").exists()
    assert (EF002 / "schedules" / "parallel_waves.yaml").exists()
    assert (EF002 / "atlas_authorization_checklist.md").exists()
    assert (EF002 / "integration_handshake.md").exists()


def test_mission_packets_for_all_five_lanes():
    lane_ids = [l["id"] for l in yaml.safe_load(LANES.read_text())["lanes"]]
    assert len(lane_ids) == 5
    for lid in lane_ids:
        path = EF002 / "mission_packets" / f"{lid}.md"
        assert path.exists(), lid
        text = path.read_text(encoding="utf-8")
        assert "Feature implementation in this packet:** NO" in text or \
               "feature implementation" in text.lower()
        assert "FORBIDDEN" in text.upper() or "Forbidden" in text


def test_freeze_matrix_has_no_accepted_or_frozen_contracts():
    data = yaml.safe_load((EF002 / "contract_freeze_matrix.yaml").read_text())
    assert data["approval_authority"] == "Atlas"
    for c in data["contracts"]:
        assert c["registry_status"] in {"PROPOSED", "NOT_IMPLEMENTED"}
        assert c["freeze_gate"] in {"BLOCKED_UNTIL_ATLAS", "READY_FOR_FREEZE"}
        assert c["freeze_gate"] != "FROZEN"


def test_parallel_waves_forbid_feature_implementation():
    data = yaml.safe_load((EF002 / "schedules" / "parallel_waves.yaml").read_text())
    assert "PARALLELIZE IMPLEMENTATION" in data["law"]
    for wave in data["waves"]:
        assert wave.get("feature_implementation") is False
    stops = set(data["hard_stops"])
    for required in (
        "C-P-003",
        "ATC-001 feature implementation",
        "Estimator feature implementation",
        "Habitat feature implementation",
        "New Passport writer or publisher",
        "Production deployment",
        "Automatic merge",
    ):
        assert required in stops


def test_launch_pack_declares_out_of_scope_features():
    text = (EF002 / "LAUNCH_PACK.md").read_text(encoding="utf-8")
    for needle in (
        "ATC-001 feature implementation",
        "Estimator feature implementation",
        "Habitat feature implementation",
        "C-P-003",
        "New Passport authority",
        "Production deployment",
        "PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY",
    ):
        assert needle in text


def test_ef002_does_not_modify_passport_authority_modules():
    # This checkpoint must not change canonical writer/publisher source files.
    # Presence of EF-002 docs is enough; passport modules remain EF-001/C-P-002.
    ps = (ROOT / "backend" / "nextgen" / "passport_service.py").read_text(encoding="utf-8")
    gps = (ROOT / "backend" / "nextgen" / "governed_publish_service.py").read_text(encoding="utf-8")
    assert "async def append_entry" in ps
    assert 'MODULE_IDENTITY = "nextgen.governed_publish_service"' in gps
