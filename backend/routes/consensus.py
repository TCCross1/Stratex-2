"""STRATEX™ Consensus AI Validation Core — REST surface.

Pure addition layer (per global preservation lock). Exposes the
`ConsensusAuditPanel` over the existing /api router. Persists every
verdict in `db.consensus_audits` for the admin audit trail.

Endpoints (all under shared /api router):
  POST /api/ceo/consensus/verify              — accepts raw measurement dataset
  POST /api/ceo/consensus/verify-job/{job_id} — pulls from db.jobs, runs panel
  GET  /api/ceo/consensus/recent              — last N committed verdicts
  GET  /api/ceo/consensus/by-job/{job_id}     — latest verdict for one job
  GET  /api/admin/consensus                   — admin audit feed (paged)

Auto-trigger: a background asyncio sweep watches for jobs that have been
audit-approved but lack a consensus verdict, and runs the panel automatically.
The sweep is idempotent and starts on app startup via `start_auto_sweep()`.

Seeding: `seed_consensus_demo()` writes one AUTHENTICATED verdict against
`crown-demo` on cold-boot so the new CEO tile lights up immediately.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core import api, ceo_only, db, current_user, now_iso
from consensus_validation_engine import (
    ConsensusAuditPanel,
    StructuralMeasurementDataset,
)

PANEL = ConsensusAuditPanel()
AUDIT_COLLECTION = "consensus_audits"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _admin_or_ceo(user=Depends(current_user)):
    role = (user.get("role") or "").lower()
    if role not in {"ceo", "admin"}:
        raise HTTPException(403, "Admin or CEO clearance required")
    return user


def _build_dataset_from_job(job: Dict[str, Any]) -> StructuralMeasurementDataset:
    """Project a job document into the dataclass the engine expects.

    Tolerates schema drift — falls back to deliverable / measurements / proposal
    sub-blocks, then to top-level keys.
    """
    deliv = job.get("deliverable") or {}
    meas = job.get("measurements") or deliv.get("measurements") or {}
    proposal = job.get("proposal") or deliv.get("proposal") or {}

    pitch = meas.get("pitch_angles_degrees") or meas.get("pitch_angles") or [
        meas.get("primary_pitch_deg", 22.0)
    ]
    if not isinstance(pitch, list) or not pitch:
        pitch = [22.0]

    return StructuralMeasurementDataset(
        job_id=job.get("id") or job.get("_id") or "unknown",
        surface_area_sqft=float(
            meas.get("roof_area_sqft")
            or meas.get("surface_area_sqft")
            or job.get("roof_area_sqft")
            or 0.0
        ),
        pitch_angles_degrees=[float(p) for p in pitch],
        moisture_retention_zones_sqft=float(
            meas.get("moisture_retention_zones_sqft")
            or meas.get("moisture_sqft")
            or job.get("moisture_sqft")
            or 0.0
        ),
        valley_linear_footage=float(
            meas.get("valley_linear_footage")
            or meas.get("valley_lf")
            or job.get("valley_lf")
            or 0.0
        ),
        calculated_bom_cost=float(
            proposal.get("bom_cost_usd")
            or proposal.get("subtotal_usd")
            or job.get("bom_cost_usd")
            or 0.0
        ),
    )


async def _persist_verdict(job_id: str, verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Write the verdict to db.consensus_audits + return the stored doc."""
    doc = {
        "id": str(uuid.uuid4()),
        "job_id": job_id,
        "verification_status": verdict.get("verification_status"),
        "consensus_score": verdict.get("consensus_score"),
        "committed_payload": verdict.get("committed_payload"),
        "audit_records": verdict.get("audit_records", []),
        "error_logs": verdict.get("error_logs", []),
        "action": verdict.get("action"),
        "injected_for_demo": verdict.get("injected_for_demo", False),
        "created_at": now_iso(),
    }
    await db[AUDIT_COLLECTION].insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class VerifyDatasetBody(BaseModel):
    job_id: str
    surface_area_sqft: float
    pitch_angles_degrees: List[float] = Field(default_factory=lambda: [22.0])
    moisture_retention_zones_sqft: float = 0.0
    valley_linear_footage: float = 0.0
    calculated_bom_cost: float = 0.0


class InjectVarianceBody(BaseModel):
    """All fields optional — endpoint falls back to crown-demo defaults."""
    job_id: Optional[str] = None
    surface_area_sqft: Optional[float] = None
    pitch_angles_degrees: Optional[List[float]] = None
    moisture_retention_zones_sqft: Optional[float] = None
    valley_linear_footage: Optional[float] = None
    calculated_bom_cost: Optional[float] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api.post("/ceo/consensus/verify")
async def consensus_verify(body: VerifyDatasetBody, user=Depends(ceo_only)):
    dataset = StructuralMeasurementDataset(
        job_id=body.job_id,
        surface_area_sqft=body.surface_area_sqft,
        pitch_angles_degrees=body.pitch_angles_degrees or [22.0],
        moisture_retention_zones_sqft=body.moisture_retention_zones_sqft,
        valley_linear_footage=body.valley_linear_footage,
        calculated_bom_cost=body.calculated_bom_cost,
    )
    verdict = PANEL.verify_and_commit_scan_data(dataset)
    return await _persist_verdict(body.job_id, verdict)


@api.post("/ceo/consensus/verify-job/{job_id}")
async def consensus_verify_job(job_id: str, user=Depends(ceo_only)):
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    dataset = _build_dataset_from_job(job)
    verdict = PANEL.verify_and_commit_scan_data(dataset)
    return await _persist_verdict(job_id, verdict)


@api.post("/ceo/consensus/inject-variance")
async def consensus_inject_variance(
    body: InjectVarianceBody = InjectVarianceBody(),
    user=Depends(ceo_only),
):
    """DEMO-MODE only: fabricate a REJECTED_VARIANCE_CRITICAL verdict so the CEO
    can showcase the safety net catching a bad scan in front of investors.

    Two of the four AI agents intentionally disagree with the base measurement
    (V2 sees +12.4 ft² extra moisture; V3 sees +98.6 ft² extra area + $312.50
    extra BOM cost). Variance logs read identically to a real failure path so
    the audit trail at /admin/consensus is visually indistinguishable.

    A follow-up call to /api/ceo/consensus/verify or /verify-job/{id} resolves
    the rejection (re-scan path complete).
    """
    job_id = body.job_id or "crown-demo"
    surface = body.surface_area_sqft if body.surface_area_sqft is not None else 3420.50
    pitches = body.pitch_angles_degrees or [22.5, 22.5, 22.4, 22.6]
    moisture = body.moisture_retention_zones_sqft if body.moisture_retention_zones_sqft is not None else 148.20
    bom = body.calculated_bom_cost if body.calculated_bom_cost is not None else 8742.18

    base = {
        "agent": "AI_VALIDATOR_1_GEOMETRY",
        "calculated_area": round(surface, 2),
        "primary_angle_mean": round(sum(pitches) / len(pitches), 2),
        "moisture_footprint": round(moisture, 2),
        "bom_cost_evaluation": round(bom, 2),
        "status": "COMPLETED",
    }
    # Other validators intentionally diverge so consensus fails.
    v2 = dict(base, agent="AI_VALIDATOR_2_THERMAL_MOISTURE",
              moisture_footprint=round(moisture + 12.40, 2))
    v3 = dict(base, agent="AI_VALIDATOR_3_QUANTITY_ESTIMATOR",
              calculated_area=round(surface + 98.60, 2),
              bom_cost_evaluation=round(bom + 312.50, 2))
    v4 = dict(base, agent="AI_VALIDATOR_4_AUDITOR_GENERAL")

    error_logs = [
        "Variance detected on AI_VALIDATOR_2_THERMAL_MOISTURE: "
        "moisture footprint delta +12.40 ft² beyond tolerance (0.01)",
        "Variance detected on AI_VALIDATOR_3_QUANTITY_ESTIMATOR: "
        "area delta +98.60 ft², BOM cost delta +$312.50 beyond tolerance (0.01)",
    ]
    verdict = {
        "verification_status": "REJECTED_VARIANCE_CRITICAL",
        "consensus_score": 0.0,
        "committed_payload": base,
        "audit_records": [base, v2, v3, v4],
        "error_logs": error_logs,
        "action": "TRIGGER_VECTOR_RE_SCAN_LOOP_MAINTAIN_FLIGHT",
        "injected_for_demo": True,
    }
    return await _persist_verdict(job_id, verdict)


@api.get("/ceo/consensus/recent")
async def consensus_recent(
    limit: int = Query(10, ge=1, le=100),
    user=Depends(_admin_or_ceo),
):
    cursor = db[AUDIT_COLLECTION].find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    return {"items": items, "count": len(items)}


@api.get("/ceo/consensus/by-job/{job_id}")
async def consensus_by_job(job_id: str, user=Depends(_admin_or_ceo)):
    doc = await db[AUDIT_COLLECTION].find_one(
        {"job_id": job_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )
    if not doc:
        return {"job_id": job_id, "verification_status": None, "audit_records": []}
    return doc


# Public read-only summary for the contractor deliverable badge — returns ONLY
# the verdict status, score, and timestamp (no inner agent payload, no costs).
@api.get("/consensus/public/by-job/{job_id}")
async def consensus_public_by_job(job_id: str):
    doc = await db[AUDIT_COLLECTION].find_one(
        {"job_id": job_id},
        {"_id": 0, "verification_status": 1, "consensus_score": 1, "created_at": 1},
        sort=[("created_at", -1)],
    )
    if not doc:
        return {"job_id": job_id, "verification_status": None, "consensus_score": None}
    return {"job_id": job_id, **doc}


@api.get("/admin/consensus")
async def admin_consensus_feed(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    user=Depends(_admin_or_ceo),
):
    q: Dict[str, Any] = {}
    if status:
        q["verification_status"] = status
    cursor = db[AUDIT_COLLECTION].find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    items = await cursor.to_list(length=limit)
    # quick aggregate counts
    auth_count = await db[AUDIT_COLLECTION].count_documents({"verification_status": "AUTHENTICATED"})
    rej_count = await db[AUDIT_COLLECTION].count_documents(
        {"verification_status": "REJECTED_VARIANCE_CRITICAL"}
    )
    return {
        "items": items,
        "count": len(items),
        "totals": {"authenticated": auth_count, "rejected": rej_count},
    }


# ---------------------------------------------------------------------------
# Background auto-trigger sweep
# ---------------------------------------------------------------------------

_auto_task: Optional[asyncio.Task] = None
_SWEEP_INTERVAL_SEC = 45


async def _auto_sweep_loop() -> None:
    """Watch for audit-approved jobs lacking a consensus verdict; run the panel."""
    while True:
        try:
            # Pull recently approved jobs that don't yet have a verdict committed
            cursor = db.jobs.find(
                {
                    "$or": [
                        {"audit_approved_at": {"$exists": True, "$ne": None}},
                        {"status": {"$in": ["AUDIT_APPROVED", "SENT", "audit_approved", "sent"]}},
                    ],
                },
                {"id": 1, "deliverable": 1, "measurements": 1, "proposal": 1,
                 "roof_area_sqft": 1, "moisture_sqft": 1, "valley_lf": 1, "bom_cost_usd": 1},
            ).limit(200)
            jobs = await cursor.to_list(length=200)
            for j in jobs:
                jid = j.get("id")
                if not jid:
                    continue
                already = await db[AUDIT_COLLECTION].find_one({"job_id": jid})
                if already:
                    continue
                try:
                    dataset = _build_dataset_from_job(j)
                    verdict = PANEL.verify_and_commit_scan_data(dataset)
                    await _persist_verdict(jid, verdict)
                except Exception as e:
                    # Best-effort sweep; surface in log but never crash the loop
                    print(f"[consensus-sweep] failed job {jid}: {e}")
        except Exception as e:
            print(f"[consensus-sweep] loop error: {e}")
        await asyncio.sleep(_SWEEP_INTERVAL_SEC)


def start_auto_sweep() -> None:
    global _auto_task
    if _auto_task and not _auto_task.done():
        return
    _auto_task = asyncio.create_task(_auto_sweep_loop())


# ---------------------------------------------------------------------------
# Cold-boot demo seed — writes one AUTHENTICATED verdict for crown-demo
# ---------------------------------------------------------------------------

async def seed_consensus_demo() -> Dict[str, Any]:
    """Idempotently seed a demo verdict so the new CEO tile + admin feed light up."""
    JOB_ID = "crown-demo"
    existing = await db[AUDIT_COLLECTION].find_one({"job_id": JOB_ID})
    if existing:
        return {"seeded": False, "reason": "already exists"}
    dataset = StructuralMeasurementDataset(
        job_id=JOB_ID,
        surface_area_sqft=3420.50,
        pitch_angles_degrees=[22.5, 22.5, 22.4, 22.6],
        moisture_retention_zones_sqft=148.20,
        valley_linear_footage=86.0,
        calculated_bom_cost=8742.18,
    )
    verdict = PANEL.verify_and_commit_scan_data(dataset)
    doc = await _persist_verdict(JOB_ID, verdict)
    return {"seeded": True, "doc": doc}
