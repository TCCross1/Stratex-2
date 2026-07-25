"""PX-006A-R1 immutable ODM reconstruction governance tests."""

from __future__ import annotations

import pytest

from nextgen.dataset_lab.odm_image import (
    ODMImageError,
    load_odm_registry,
    pinned_odm_reference,
    validate_odm_image_record,
)
from nextgen.dataset_lab.reconstruction import (
    ReconstructionError,
    compare_reconstruction_runs,
    run_odm_reconstruction,
)


def test_odm_registry_immutable_and_verified():
    reg = load_odm_registry()
    image = reg["image"]
    assert image["verified"] is True
    assert image["repository"] == "opendronemap/odm"
    assert image["tag"] != "latest"
    assert image["digest"].startswith("sha256:")
    assert len(image["digest"]) == len("sha256:") + 64
    assert image["pinned_reference"] == f"opendronemap/odm@{image['digest']}"
    assert reg.get("intended_use") == "DEVELOPMENT_RECONSTRUCTION_ONLY"


def test_reject_latest_and_mutable_and_wrong_digest():
    with pytest.raises(ODMImageError):
        pinned_odm_reference("opendronemap/odm:latest")
    with pytest.raises(ODMImageError):
        pinned_odm_reference("opendronemap/odm:3.5.6")
    with pytest.raises(ODMImageError):
        pinned_odm_reference("opendronemap/odm@sha256:" + ("a" * 64))
    with pytest.raises(ODMImageError):
        pinned_odm_reference("other/repo@sha256:" + ("b" * 64))


def test_reject_malformed_and_missing_digest_in_record():
    base = dict(load_odm_registry()["image"])
    bad = dict(base)
    bad["digest"] = "notadigest"
    with pytest.raises(ODMImageError):
        validate_odm_image_record(bad)
    bad2 = dict(base)
    bad2["tag"] = "latest"
    with pytest.raises(ODMImageError):
        validate_odm_image_record(bad2)
    bad3 = dict(base)
    bad3["repository"] = "evil/odm"
    with pytest.raises(ODMImageError):
        validate_odm_image_record(bad3)


def test_path_escape_and_low_disk_and_timeout(monkeypatch):
    import os
    from pathlib import Path

    root = os.environ.get("STRATEX_DATASET_ROOT", "/tmp/stratex-external-datasets")
    monkeypatch.setenv("STRATEX_DATASET_ROOT", root)
    r = run_odm_reconstruction("MYGLA", force_input_escape=True, output_dirname="t_in")
    assert r["failure_classification"] == "PATH_ESCAPE"
    assert r.get("promoted") is False

    r = run_odm_reconstruction(
        "MYGLA", force_output_escape="/tmp/evil", output_dirname="t_out"
    )
    assert r["failure_classification"] == "PATH_ESCAPE"
    assert r.get("promoted") is False

    if not (Path(root) / "MYGLA" / "latest_acquisition.json").is_file():
        pytest.skip("MYGLA local corpus unavailable for low-disk gate")
    r = run_odm_reconstruction("MYGLA", simulate_low_disk=True, output_dirname="t_disk")
    assert r["failure_classification"] == "LOW_DISK"
    assert r.get("promoted") is False


def test_license_blocked_dji(monkeypatch, tmp_path):
    # Use real dataset root if present; otherwise skip soft
    import os
    root = os.environ.get("STRATEX_DATASET_ROOT", "/tmp/stratex-external-datasets")
    monkeypatch.setenv("STRATEX_DATASET_ROOT", root)
    from pathlib import Path

    if not (Path(root) / "DJI_TERRA_SAMPLE" / "license_status.json").is_file():
        pytest.skip("DJI local corpus unavailable")
    r = run_odm_reconstruction("DJI_TERRA_SAMPLE", output_dirname="t_dji")
    assert r.get("promoted") is False
    assert r.get("status") in {"LICENSE_BLOCKED", "FAILED"}
    assert "LICENSE" in str(r.get("failure_classification") or r.get("classification"))


def test_compare_runs_classification():
    a = {
        "profile": "smoke",
        "source": {"repository_commit": "abc"},
        "environment": {"container_digest": "sha256:" + "1" * 64},
        "outputs_discovered": {"orthophoto": {"present": True}, "mesh": {"present": False}},
        "output_checksums": {"orthophoto": "aaa"},
        "duration_seconds": 10,
    }
    b = {
        "profile": "smoke",
        "source": {"repository_commit": "abc"},
        "environment": {"container_digest": "sha256:" + "1" * 64},
        "outputs_discovered": {"orthophoto": {"present": True}, "mesh": {"present": False}},
        "output_checksums": {"orthophoto": "bbb"},
        "duration_seconds": 12,
    }
    cmp = compare_reconstruction_runs(a, b)
    assert cmp["same_source_revision"] is True
    assert cmp["same_odm_digest"] is True
    assert cmp["repeatability_by_output"]["orthophoto"] == "STRUCTURALLY_REPEATABLE"


def test_no_latest_in_reconstruction_module():
    from pathlib import Path

    text = Path(__file__).resolve().parents[1].joinpath(
        "nextgen/dataset_lab/reconstruction.py"
    ).read_text(encoding="utf-8")
    assert "odm:latest" not in text
    assert "pinned_odm_reference" in text


def test_dataset_lab_still_has_no_passport_writer():
    from pathlib import Path

    lab = Path(__file__).resolve().parents[1] / "nextgen" / "dataset_lab"
    for path in lab.glob("*.py"):
        t = path.read_text(encoding="utf-8")
        assert "passport_entries.insert_one" not in t
        assert "governed_publish(" not in t


def test_gcp_wgs84_utm_header_accepted():
    from nextgen.dataset_lab.reconstruction import _validate_gcp_structure
    from pathlib import Path
    import os

    root = os.environ.get("STRATEX_DATASET_ROOT", "/tmp/stratex-external-datasets")
    gcp = Path(root) / "BELLUS" / "content" / "gcp_list.txt"
    if not gcp.is_file():
        pytest.skip("BELLUS GCP unavailable")
    v = _validate_gcp_structure(gcp)
    assert v["valid_structure"] is True
    assert v["header_seen"] is True
    assert v["gcp_point_rows"] >= 1
