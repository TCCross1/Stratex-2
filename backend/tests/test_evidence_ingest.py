"""Unit tests for Evidence Ingest — Field Test v1"""

from backend.nextgen.evidence_ingest import (
    ingest_media_item,
    assemble_package_from_capture,
    build_demo_capture_package,
)
from backend.nextgen.mission_package_seal import seal_package
from backend.nextgen.mission_to_passport import prepare_for_governed_publish


def test_ingest_media_item_has_hash():
    item = ingest_media_item("RGB", "2026-08-01T12:00:00Z", "Matrice 4E Wide", 5_000_000)
    assert item["content_hash"]
    assert item["media_type"] == "RGB"
    assert item["size_bytes"] == 5_000_000


def test_assemble_package_structure():
    items = [
        ingest_media_item("RGB", "2026-08-01T12:00:00Z", "Matrice 4E Wide", 5_000_000),
        ingest_media_item("THERMAL", "2026-08-01T12:05:00Z", "Matrice 4T", 2_000_000),
    ]
    pkg = assemble_package_from_capture(
        mission_id="m-test",
        tenant_id="t1",
        property_id="p1",
        capture_type="DAYTIME_PRECISION_MAPPING",
        media_items=items,
        aircraft="DJI Matrice 4E",
    )
    assert pkg["mission_id"] == "m-test"
    assert len(pkg["evidence_manifest"]["items"]) == 2
    assert pkg["mission_metadata"]["media_count"] == 2


def test_demo_package_seals_and_withholds():
    raw = build_demo_capture_package()
    sealed = seal_package(raw, seal_key=b"test-key")
    assert sealed["seal_record"]["signature"]
    handoff = prepare_for_governed_publish(sealed, seal_key=b"test-key")
    assert handoff["status"] == "READY_FOR_GOVERNED_PUBLISH"
    # low-conf plane should be withheld
    assert handoff["publication_request"]["payload"]["geometry_summary"]["withheld_count"] >= 1
