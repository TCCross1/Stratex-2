"""RT-003 security / failure guards — static detection helpers.

Classifies honesty findings. Does not claim production READY.
Does not modify Lane 1 business modules (outbox_worker is prohibited for Lane 5).
Production readiness: NOT READY.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parents[2]
DIGESTS = ROOT / "engineering" / "rt002" / "IMAGE_DIGESTS.yaml"
WORKFLOW = ROOT / ".github" / "workflows" / "stratex-live-integration.yml"
OUTBOX_WORKER = ROOT / "backend" / "nextgen" / "outbox_worker.py"
NEXTGEN = ROOT / "backend" / "nextgen"


@dataclass
class GuardFinding:
    guard_id: str
    status: str  # PASS | FAIL | FINDING | UNAVAILABLE
    summary: str
    details: List[str] = field(default_factory=list)
    remediation_owner: Optional[str] = None

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "guard_id": self.guard_id,
            "status": self.status,
            "summary": self.summary,
            "details": list(self.details),
            "remediation_owner": self.remediation_owner,
            "production_readiness": "NOT_READY",
        }


def guard_floating_python_image() -> GuardFinding:
    """Fail if live workflow still runs a floating python:3.12-slim tag."""
    if not WORKFLOW.is_file():
        return GuardFinding(
            guard_id="floating_python_image",
            status="UNAVAILABLE",
            summary="Live integration workflow missing",
            details=[str(WORKFLOW)],
        )
    text = WORKFLOW.read_text(encoding="utf-8")
    digests = yaml.safe_load(DIGESTS.read_text(encoding="utf-8")) if DIGESTS.is_file() else {}
    py = (digests.get("images") or {}).get("python_harness") or {}
    ref = py.get("reference") or ""
    details: List[str] = []

    if not ref or "@sha256:" not in ref or not str(py.get("digest", "")).startswith("sha256:"):
        return GuardFinding(
            guard_id="floating_python_image",
            status="FAIL",
            summary="python_harness digest missing or not pinned in IMAGE_DIGESTS.yaml",
            details=[f"reference={ref!r}"],
        )

    # Floating bare tag as docker image argument is forbidden.
    floating_hits = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.search(r"(^|[\s\"'])python:3\.12-slim([\s\"']|$)", line) and "@sha256:" not in line:
            floating_hits.append(f"L{i}:{stripped}")
    if floating_hits:
        return GuardFinding(
            guard_id="floating_python_image",
            status="FAIL",
            summary="Floating python:3.12-slim still present in workflow",
            details=floating_hits,
        )

    if "PYTHON_HARNESS_REF" not in text and ref not in text:
        details.append("workflow does not reference PYTHON_HARNESS_REF or pinned digest ref")
        return GuardFinding(
            guard_id="floating_python_image",
            status="FAIL",
            summary="Workflow does not use digest-pinned python harness",
            details=details,
        )

    if "contents: read" not in text:
        return GuardFinding(
            guard_id="floating_python_image",
            status="FAIL",
            summary="Workflow must retain contents: read least privilege",
            details=["permissions contents:read missing"],
        )

    details.append(f"pinned_reference={ref}")
    return GuardFinding(
        guard_id="floating_python_image",
        status="PASS",
        summary="python harness is digest-pinned; no floating 3.12-slim tag",
        details=details,
    )


def guard_dlq_scrub_detection() -> GuardFinding:
    """Detect whether dead-letter path scrubs secret keys from payload.

    Lane 5 must not rewrite outbox_worker. Honest FINDING if scrub is absent.
    """
    if not OUTBOX_WORKER.is_file():
        return GuardFinding(
            guard_id="dlq_scrub_detection",
            status="UNAVAILABLE",
            summary="outbox_worker.py not present in tree",
            details=[str(OUTBOX_WORKER)],
            remediation_owner="LANE_1_CORE_PASSPORT",
        )
    text = OUTBOX_WORKER.read_text(encoding="utf-8")
    if "async def _move_to_dead_letter" not in text:
        return GuardFinding(
            guard_id="dlq_scrub_detection",
            status="UNAVAILABLE",
            summary="_move_to_dead_letter not found",
            remediation_owner="LANE_1_CORE_PASSPORT",
        )

    # Extract the dead-letter function body (until next top-level async def).
    start = text.index("async def _move_to_dead_letter")
    rest = text[start:]
    m = re.search(r"\nasync def |\ndef ", rest[1:])
    body = rest[: m.start() + 1] if m else rest

    copies_raw = (
        '"payload": event.get("payload")' in body
        or "\"payload\": event.get('payload')" in body
        or "payload\": event.get(\"payload\") or {}" in body
    )
    uses_scrub = "_scrub(" in body and "payload" in body

    if copies_raw and not uses_scrub:
        return GuardFinding(
            guard_id="dlq_scrub_detection",
            status="FINDING",
            summary="DLQ copies raw event payload without _scrub — residual secret-mirror risk",
            details=[
                "Detected payload assignment from event.get('payload') without _scrub in _move_to_dead_letter",
                "Audit path uses _scrub; DLQ path does not",
            ],
            remediation_owner="LANE_1_CORE_PASSPORT",
        )
    if uses_scrub:
        return GuardFinding(
            guard_id="dlq_scrub_detection",
            status="PASS",
            summary="DLQ path appears to scrub payload before persistence",
            details=["_scrub referenced in _move_to_dead_letter"],
            remediation_owner="LANE_1_CORE_PASSPORT",
        )
    return GuardFinding(
        guard_id="dlq_scrub_detection",
        status="FINDING",
        summary="Unable to confirm DLQ payload scrubbing",
        details=["No clear _scrub usage on DLQ payload path"],
        remediation_owner="LANE_1_CORE_PASSPORT",
    )


def guard_duplicate_writer() -> GuardFinding:
    """Fail if a secondary passport_entries.insert_one exists outside passport_service."""
    passport = NEXTGEN / "passport_service.py"
    if not passport.is_file():
        return GuardFinding(
            guard_id="duplicate_writer",
            status="UNAVAILABLE",
            summary="passport_service.py missing",
        )
    offenders: List[str] = []
    for path in NEXTGEN.rglob("*.py"):
        if path.name == "passport_service.py":
            continue
        if "tests" in path.parts:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "passport_entries.insert_one" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{i}")
            elif "nextgen_passport_entries" in line and "insert_one" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{i}")
    if offenders:
        return GuardFinding(
            guard_id="duplicate_writer",
            status="FAIL",
            summary="Secondary Passport ledger writer detected",
            details=offenders[:20],
            remediation_owner="LANE_1_CORE_PASSPORT",
        )
    return GuardFinding(
        guard_id="duplicate_writer",
        status="PASS",
        summary="No secondary passport_entries.insert_one outside passport_service",
    )


def guard_false_ready() -> GuardFinding:
    """Fail if RT-002 readiness can report READY without required components,
    or if digests claim production READY.
    """
    details: List[str] = []
    digests = yaml.safe_load(DIGESTS.read_text(encoding="utf-8"))
    if digests.get("production_readiness") not in {"NOT_READY", "NOT READY"}:
        return GuardFinding(
            guard_id="false_ready",
            status="FAIL",
            summary="IMAGE_DIGESTS.yaml must remain production_readiness NOT_READY",
            details=[f"got={digests.get('production_readiness')!r}"],
        )

    # Import readiness without installing package — path inject.
    import sys

    eng = str(ROOT / "engineering")
    if eng not in sys.path:
        sys.path.insert(0, eng)
    from rt002.readiness import OverallState, ReadinessReport  # type: ignore

    empty = ReadinessReport()
    if empty.compute_overall() == OverallState.READY:
        return GuardFinding(
            guard_id="false_ready",
            status="FAIL",
            summary="Empty readiness report incorrectly reports READY",
        )
    details.append(f"empty_overall={empty.overall.value}")

    partial = ReadinessReport()
    partial.set("mongo_reachable", True, "ok")
    if partial.compute_overall() == OverallState.READY:
        return GuardFinding(
            guard_id="false_ready",
            status="FAIL",
            summary="Partial readiness incorrectly reports READY",
            details=["only mongo_reachable set"],
        )
    details.append(f"partial_overall={partial.overall.value}")

    unavailable = ReadinessReport()
    unavailable.set("mongo_reachable", False, "INTEGRATION_ENVIRONMENT_UNAVAILABLE: docker")
    if unavailable.compute_overall() == OverallState.READY:
        return GuardFinding(
            guard_id="false_ready",
            status="FAIL",
            summary="Unavailable path incorrectly reports READY",
        )
    details.append(f"unavailable_overall={unavailable.overall.value}")

    public = unavailable.as_public_dict()
    if public.get("production_readiness") not in {"NOT_READY", "NOT READY"}:
        return GuardFinding(
            guard_id="false_ready",
            status="FAIL",
            summary="Public readiness dict must keep production_readiness NOT_READY",
            details=[repr(public.get("production_readiness"))],
        )

    return GuardFinding(
        guard_id="false_ready",
        status="PASS",
        summary="Readiness model rejects false READY; digests remain NOT_READY",
        details=details,
    )


def run_security_failure_guards() -> List[GuardFinding]:
    return [
        guard_floating_python_image(),
        guard_dlq_scrub_detection(),
        guard_duplicate_writer(),
        guard_false_ready(),
    ]
