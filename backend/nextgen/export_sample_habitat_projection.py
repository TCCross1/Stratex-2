"""CLI/helper: build sample mission package and print Habitat projection JSON."""

from __future__ import annotations

import json
from backend.nextgen.sample_field_test_package import build_sample_package
from backend.nextgen.habitat_projection_export import export_habitat_projection


def main() -> dict:
    pkg = build_sample_package()
    # Sample packages are sealed in full path; export remains non-authoritative until Passport write
    projection = export_habitat_projection(
        pkg,
        address_line="1234 Appalachian Way",
        city_state_zip="London, KY 40741",
        authoritative=False,
    )
    return projection


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
