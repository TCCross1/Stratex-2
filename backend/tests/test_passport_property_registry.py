"""Unit tests for Passport property registry + claim codes (field test v1)."""

import pytest

from backend.nextgen.address_normalize import normalize_address
from backend.nextgen.mission_package_seal import create_empty_package, seal_package
from backend.nextgen.passport_property_registry import (
    generate_claim_code,
    get_property_by_claim_code,
    habitat_owner_exists,
    link_habitat_owner,
    register_sealed_mission,
    reset_registry,
)


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


def test_normalize_address_stable_hash():
    a = normalize_address("1234 Appalachian Way", "London, KY 40741")
    b = normalize_address("  1234   appalachian way ", " london, ky 40741 ")
    assert a["normalized_display"] == b["normalized_display"]
    assert a["normalized_address_hash"] == b["normalized_address_hash"]


def test_register_sealed_mission_mints_claim_code():
    pkg = create_empty_package("m1", "tenant-a", "prop-1")
    sealed = seal_package(pkg, seal_key=b"test-key")
    result = register_sealed_mission(
        sealed,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
    )
    assert result["claim_code_created"] is True
    assert result["claim_code"].startswith("STRX-")
    assert result["habitat_owner_exists"] is False
    assert habitat_owner_exists(result["property_record"]) is False


def test_register_same_address_is_idempotent_for_claim_code():
    pkg1 = create_empty_package("m1", "tenant-a", "prop-1")
    sealed1 = seal_package(pkg1, seal_key=b"test-key")
    first = register_sealed_mission(
        sealed1,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
    )

    pkg2 = create_empty_package("m2", "tenant-a", "prop-1")
    sealed2 = seal_package(pkg2, seal_key=b"test-key")
    second = register_sealed_mission(
        sealed2,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
    )

    assert second["claim_code_created"] is False
    assert second["claim_code"] == first["claim_code"]
    assert len(second["property_record"]["missions"]) == 2


def test_no_claim_code_when_habitat_owner_exists():
    pkg = create_empty_package("m1", "tenant-a", "prop-1")
    sealed = seal_package(pkg, seal_key=b"test-key")
    register_sealed_mission(
        sealed,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
    )
    link_habitat_owner(
        tenant_id="tenant-a",
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
        habitat_owner_user_id="owner-user-99",
    )

    pkg2 = create_empty_package("m2", "tenant-a", "prop-1")
    sealed2 = seal_package(pkg2, seal_key=b"test-key")
    result = register_sealed_mission(
        sealed2,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
    )
    assert result["habitat_owner_exists"] is True
    # Existing claim_code remains on record but no new code is minted
    assert result["claim_code_created"] is False


def test_get_property_by_claim_code():
    assert generate_claim_code().count("-") == 2
    pkg = create_empty_package("m1", "tenant-a", "prop-1")
    sealed = seal_package(pkg, seal_key=b"test-key")
    reg = register_sealed_mission(
        sealed,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
    )
    found = get_property_by_claim_code(reg["claim_code"])
    assert found is not None
    assert found["property_id"] == "prop-1"
