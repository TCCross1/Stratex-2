"""
Field Test claim-code demo — seal sample mission, register Passport property,
print normalized address + claim_code when no Habitat owner exists.

Run:
  python3 -m backend.nextgen.field_test_claim_code_demo
"""

from __future__ import annotations

import json

from backend.nextgen.sample_field_test_package import (
    SAMPLE_ADDRESS_LINE,
    SAMPLE_CITY_STATE_ZIP,
    build_sample_package,
)
from backend.nextgen.mission_package_seal import seal_package
from backend.nextgen.mission_to_passport import prepare_for_governed_publish
from backend.nextgen.passport_property_registry import register_sealed_mission

DEMO_SEAL_KEY = b"field-test-demo-key"


def run_claim_code_demo() -> dict:
    raw = build_sample_package()
    sealed = seal_package(raw, seal_key=DEMO_SEAL_KEY)
    handoff = prepare_for_governed_publish(sealed, seal_key=DEMO_SEAL_KEY)
    registration = register_sealed_mission(
        sealed,
        address_line=SAMPLE_ADDRESS_LINE,
        city_state_zip=SAMPLE_CITY_STATE_ZIP,
    )

    normalized = registration["normalized_address"]
    summary = {
        "seal_valid": True,
        "status": handoff["status"],
        "normalized_address": normalized["normalized_display"],
        "normalized_address_hash": normalized["normalized_address_hash"],
        "property_id": sealed["property_id"],
        "mission_id": sealed["mission_id"],
        "habitat_owner_exists": registration["habitat_owner_exists"],
        "claim_code_created": registration["claim_code_created"],
        "claim_code": registration["claim_code"],
        "claim_code_status": (
            registration["property_record"].get("claim_code_status")
            if registration["claim_code"]
            else None
        ),
    }
    return summary


def main() -> None:
    print(json.dumps(run_claim_code_demo(), indent=2))


if __name__ == "__main__":
    main()
