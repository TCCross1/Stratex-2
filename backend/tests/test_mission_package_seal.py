"""
Focused unit tests for Mission Package Sealing — Field Test v1
"""

import pytest
from backend.nextgen.mission_package_seal import (
    seal_package,
    verify_seal,
    create_empty_package,
    SealingError,
    content_hash,
)


def test_create_empty_package():
    pkg = create_empty_package(
        mission_id="mission-001",
        tenant_id="tenant-001",
        property_id="prop-001",
    )
    assert pkg["package_id"]
    assert pkg["mission_id"] == "mission-001"
    assert "mission_metadata" in pkg
    assert "evidence_manifest" in pkg
    assert "geometry_candidate" in pkg
    assert "awe_candidate" in pkg


def test_seal_and_verify_roundtrip():
    pkg = create_empty_package(
        mission_id="mission-002",
        tenant_id="tenant-001",
        property_id="prop-001",
        capture_type="DAYTIME_PRECISION_MAPPING",
    )
    # Add a low-confidence plane that should be withheld
    pkg["geometry_candidate"]["planes"] = [
        {"id": "plane-1", "confidence": 0.92, "area": 120.5},
        {"id": "plane-2", "confidence": 0.41, "area": 18.0},  # should be WITHHELD
    ]

    sealed = seal_package(pkg, seal_key=b"test-key-for-unit-tests")
    assert sealed["seal_record"]["signature"]
    assert sealed["content_hash"]
    assert verify_seal(sealed, seal_key=b"test-key-for-unit-tests") is True

    # Low confidence plane must be marked WITHHELD
    planes = sealed["geometry_candidate"]["planes"]
    withheld = [p for p in planes if p.get("truth_classification") == "WITHHELD"]
    assert len(withheld) == 1
    assert withheld[0]["id"] == "plane-2"


def test_missing_required_field_raises():
    pkg = create_empty_package("m1", "t1", "p1")
    del pkg["tenant_id"]
    with pytest.raises(SealingError) as exc:
        seal_package(pkg, seal_key=b"test-key")
    assert exc.value.code == "MISSING_IDENTITY"


def test_tampered_package_fails_verify():
    pkg = create_empty_package("m3", "t1", "p1")
    sealed = seal_package(pkg, seal_key=b"test-key")
    # Tamper
    sealed["geometry_candidate"]["planes"].append({"id": "evil", "confidence": 0.99})
    assert verify_seal(sealed, seal_key=b"test-key") is False
