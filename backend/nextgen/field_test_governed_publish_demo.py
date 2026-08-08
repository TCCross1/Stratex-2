"""
Field-test governed publish demo — pipeline seal (with ATC) + Passport publish.

Usage (repo root):
  python3 -m backend.nextgen.field_test_governed_publish_demo --dry-run
  python3 -m backend.nextgen.field_test_governed_publish_demo

Live mode requires MONGO_URL (+ DB_NAME), motor, and pymongo installed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

DEMO_SEAL_KEY = b"field-test-demo-key"
DEMO_ACTOR_ID = "field-test-governed-publish-demo"

PUBLICATION_REQUEST_REQUIRED = (
    "tenant_id",
    "property_id",
    "source_type",
    "source_id",
    "entry_type",
    "payload",
    "idempotency_key",
)

PUBLICATION_PAYLOAD_REQUIRED = (
    "package_id",
    "mission_id",
    "content_hash",
    "seal",
)


def validate_publication_request(publication_request: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate publication_request shape for governed publish."""
    errors: List[str] = []
    for key in PUBLICATION_REQUEST_REQUIRED:
        if not publication_request.get(key):
            errors.append(f"missing publication_request.{key}")

    payload = publication_request.get("payload") or {}
    if not isinstance(payload, dict):
        errors.append("publication_request.payload must be an object")
    else:
        for key in PUBLICATION_PAYLOAD_REQUIRED:
            if not payload.get(key):
                errors.append(f"missing publication_request.payload.{key}")

    if publication_request.get("source_type") != "mission_package":
        errors.append("publication_request.source_type must be mission_package")
    if publication_request.get("entry_type") != "MISSION_EVIDENCE":
        errors.append("publication_request.entry_type must be MISSION_EVIDENCE")

    return len(errors) == 0, errors


def run_pipeline_seal() -> Dict[str, Any]:
    """Run sample mission through field_test_pipeline (preflight + pre-seal ATC + seal)."""
    from backend.nextgen.field_test_pipeline import run_single_path_pipeline
    from backend.nextgen.sample_field_test_package import sample_pipeline_kwargs

    result = run_single_path_pipeline(**sample_pipeline_kwargs(seal_key=DEMO_SEAL_KEY))
    return {
        "pipeline_success": result.success,
        "mission_id": result.mission_id,
        "state": result.state,
        "readiness": result.readiness,
        "seal_readiness": result.seal_readiness,
        "errors": result.errors,
        "publication_request": result.publication_request,
        "package_id": (result.sealed_package or {}).get("package_id"),
        "content_hash_prefix": ((result.sealed_package or {}).get("content_hash") or "")[:16],
    }


def _ensure_live_env() -> None:
    if not os.environ.get("MONGO_URL"):
        raise RuntimeError("MONGO_URL is not set")
    os.environ.setdefault("DB_NAME", "stratex_field_test")
    os.environ.setdefault("PASSPORT_TRANSACTIONS_AVAILABLE", "0")


async def _mongo_ping() -> Tuple[bool, str]:
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        return False, "motor is not installed (pip install motor pymongo)"

    url = os.environ["MONGO_URL"]
    client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=4000)
    try:
        await client.admin.command("ping")
        return True, "ok"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    finally:
        client.close()


async def run_live_publish(publication_request: Dict[str, Any]) -> Dict[str, Any]:
    """Attach expected passport head tokens and call publish_sealed_package."""
    from backend.nextgen.governed_publish_service import load_expected_state
    from backend.nextgen.publish_bridge import publish_sealed_package

    tenant_id = publication_request["tenant_id"]
    property_id = publication_request["property_id"]

    head = await load_expected_state(tenant_id=tenant_id, property_id=property_id)
    pr = dict(publication_request)
    pr["expected_revision"] = head["revision"]
    pr["expected_head_hash"] = head["head_hash"]

    publish_result = await publish_sealed_package(
        pr,
        actor_id=DEMO_ACTOR_ID,
        actor_role="field_test_demo",
        correlation_id=f"field-test-demo:{pr.get('source_id')}",
    )

    return {
        "expected_state": {
            "revision": head["revision"],
            "head_hash": head["head_hash"],
            "passport_id": head.get("passport_id"),
        },
        "publication_request_with_expected_state": {
            "expected_revision": pr["expected_revision"],
            "expected_head_hash": pr["expected_head_hash"],
            "idempotency_key": pr.get("idempotency_key"),
            "source_id": pr.get("source_id"),
        },
        "publish_result": publish_result,
    }


def run_dry_run() -> Dict[str, Any]:
    pipeline = run_pipeline_seal()
    summary: Dict[str, Any] = {
        "mode": "dry-run",
        "mongo_required": False,
        "pipeline_success": pipeline["pipeline_success"],
        "pipeline_errors": pipeline["errors"],
        "package_id": pipeline.get("package_id"),
        "content_hash_prefix": pipeline.get("content_hash_prefix"),
        "seal_readiness_ready": (pipeline.get("seal_readiness") or {}).get("ready"),
    }

    if not pipeline["pipeline_success"]:
        summary["status"] = "PIPELINE_FAILED"
        summary["message"] = "Pipeline did not reach publication_request (ATC or seal blocked)"
        return summary

    pr = pipeline["publication_request"] or {}
    ok, errors = validate_publication_request(pr)
    summary["publication_request_valid"] = ok
    summary["validation_errors"] = errors
    if ok:
        summary["status"] = "DRY_RUN_OK"
        summary["message"] = (
            "Pipeline + publication_request shape valid. "
            "Live publish needs MONGO_URL, motor, pymongo, and expected_revision/head_hash from passport head."
        )
        summary["publication_request_preview"] = {
            "tenant_id": pr.get("tenant_id"),
            "property_id": pr.get("property_id"),
            "source_type": pr.get("source_type"),
            "source_id": pr.get("source_id"),
            "entry_type": pr.get("entry_type"),
            "idempotency_key": pr.get("idempotency_key"),
            "payload_keys": sorted((pr.get("payload") or {}).keys()),
        }
    else:
        summary["status"] = "VALIDATION_FAILED"
        summary["message"] = "publication_request failed shape validation"

    return summary


async def run_live() -> Dict[str, Any]:
    _ensure_live_env()
    mongo_ok, mongo_detail = await _mongo_ping()
    if not mongo_ok:
        return {
            "mode": "live",
            "status": "MONGO_UNAVAILABLE",
            "message": mongo_detail,
            "hint": (
                "Start MongoDB, export MONGO_URL and DB_NAME, then run: "
                "pip install motor pymongo && "
                "python3 -m backend.nextgen.field_test_governed_publish_demo"
            ),
        }

    pipeline = run_pipeline_seal()
    summary: Dict[str, Any] = {
        "mode": "live",
        "mongo_ping": mongo_detail,
        "db_name": os.environ.get("DB_NAME"),
        "pipeline_success": pipeline["pipeline_success"],
        "pipeline_errors": pipeline["errors"],
    }

    if not pipeline["pipeline_success"]:
        summary["status"] = "PIPELINE_FAILED"
        summary["message"] = "Pipeline did not reach publication_request"
        return summary

    pr = pipeline["publication_request"] or {}
    ok, errors = validate_publication_request(pr)
    if not ok:
        summary["status"] = "VALIDATION_FAILED"
        summary["validation_errors"] = errors
        summary["message"] = "publication_request invalid before publish"
        return summary

    try:
        publish = await run_live_publish(pr)
    except Exception as exc:
        summary["status"] = "PUBLISH_FAILED"
        summary["message"] = f"{type(exc).__name__}: {exc}"
        return summary

    summary["expected_state"] = publish["expected_state"]
    summary["publish_result_status"] = publish["publish_result"].get("status")
    summary["publish_result"] = publish["publish_result"]

    pub_status = publish["publish_result"].get("status")
    if pub_status == "PUBLISHED":
        inner = publish["publish_result"].get("result") or {}
        summary["status"] = "SUCCESS"
        summary["message"] = inner.get("status") or "PUBLISHED"
        summary["entry_id"] = (inner.get("entry") or {}).get("canonical_id")
        summary["revision"] = (inner.get("entry") or {}).get("revision")
    else:
        summary["status"] = pub_status or "PUBLISH_FAILED"
        summary["message"] = (
            publish["publish_result"].get("message")
            or publish["publish_result"].get("reason")
            or "Governed publish did not succeed"
        )

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Field-test pipeline seal + governed Passport publish demo",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline + validate publication_request only (no Mongo)",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        summary = run_dry_run()
    else:
        try:
            summary = asyncio.run(run_live())
        except RuntimeError as exc:
            summary = {
                "mode": "live",
                "status": "MONGO_UNAVAILABLE",
                "message": str(exc),
                "hint": (
                    "Export MONGO_URL and DB_NAME, install motor pymongo, then re-run. "
                    "Use --dry-run to validate publication_request without Mongo."
                ),
            }

    print(json.dumps(summary, indent=2))
    status = summary.get("status", "")
    if status in {"SUCCESS", "DRY_RUN_OK"}:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
