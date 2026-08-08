"""CLI/helper: build sample mission package, seal it, and print Habitat projection JSON."""

from __future__ import annotations

import json

from backend.nextgen.sample_field_test_package import build_sample_package
from backend.nextgen.mission_package_seal import seal_package
from backend.nextgen.habitat_projection_export import export_habitat_projection

DEMO_SEAL_KEY = b"field-test-demo-key"


def main() -> dict:
    raw = build_sample_package()
    sealed = seal_package(raw, seal_key=DEMO_SEAL_KEY)
    projection = export_habitat_projection(
        sealed,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
        authoritative=False,
    )
    return projection


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
