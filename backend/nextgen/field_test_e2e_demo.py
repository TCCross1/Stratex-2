"""
Field Test End-to-End Demo
ATC Readiness → Evidence Ingest → Seal → Handoff → Report

Run (once backend env is available):
  python -m backend.nextgen.field_test_e2e_demo
"""

from __future__ import annotations

import json

from .atc.readiness import evaluate_readiness
from .evidence_ingest import build_demo_capture_package
from .mission_package_seal import seal_package
from .mission_to_passport import prepare_for_governed_publish
from .report_composer import compose_full_report


def run():
    mission_id = "MISSION-FT-E2E-001"

    # 1. ATC readiness
    readiness = evaluate_readiness(
        mission_id,
        weather_ok=True,
        battery_pct=87.0,
        rtk_ready=True,
        pilot_authorized=True,
    )
    if not readiness.ready:
        print("ATC NOT READY:", readiness.blocking_failures)
        return

    # 2. Evidence ingest (simulates post-flight media + geometry + AWE)
    raw_package = build_demo_capture_package(mission_id=mission_id)

    # 3. Seal
    sealed = seal_package(raw_package, seal_key=b"field-test-e2e-key")

    # 4. Prepare for governed publish
    handoff = prepare_for_governed_publish(sealed, seal_key=b"field-test-e2e-key")

    # 5. Compose report
    report = compose_full_report(sealed)

    summary = {
        "atc_ready": readiness.ready,
        "package_id": sealed["package_id"],
        "content_hash_prefix": sealed["content_hash"][:16],
        "planes_published": handoff["publication_request"]["payload"]["geometry_summary"]["plane_count"],
        "planes_withheld": handoff["publication_request"]["payload"]["geometry_summary"]["withheld_count"],
        "findings": len(sealed["awe_candidate"]["findings"]),
        "report_id": report["report_id"],
        "handoff_status": handoff["status"],
        "sections": list(report["sections"].keys()),
    }
    print(json.dumps(summary, indent=2))
    return readiness, sealed, handoff, report


if __name__ == "__main__":
    run()
