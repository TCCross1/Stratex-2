"""STRATEX Telemetry Anomaly Halt + Overseer review queue + Admin Financial Blocker.

The frontend BEES rendering loop posts structured halt payloads here when it
detects sub-pipeline anomalies on the Electric Teal diagnostic layer.
Admin reads via /admin/overseer-queue.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from core import admin_only, api, current_user, db, now_iso


class TelemetryHaltPayload(BaseModel):
    project_id: Optional[str] = None
    layer: str
    severity: str
    reason_code: str
    reason_label: str
    telemetry_snapshot: Dict[str, Any] = {}
    causal_logs: List[str] = []
    fps_observed: Optional[float] = None
    fps_threshold: Optional[float] = None
    client_timestamp: Optional[str] = None
    user_agent: Optional[str] = None


@api.post("/telemetry/anomaly-halt")
async def post_telemetry_halt(body: TelemetryHaltPayload, request: Request, user=Depends(current_user)):
    """Frontend BEES pipeline → Overseer queue."""
    valid_sev = {"advisory", "warning", "critical"}
    if body.severity not in valid_sev:
        raise HTTPException(400, f"severity must be one of {sorted(valid_sev)}")
    record = {
        "id": str(uuid.uuid4()),
        "project_id": body.project_id,
        "layer": body.layer or "electric_teal_diagnostic",
        "severity": body.severity,
        "reason_code": body.reason_code,
        "reason_label": body.reason_label,
        "telemetry_snapshot": body.telemetry_snapshot or {},
        "causal_logs": body.causal_logs[:30],
        "fps_observed": body.fps_observed,
        "fps_threshold": body.fps_threshold,
        "client_timestamp": body.client_timestamp,
        "user_agent": (body.user_agent or "")[:240],
        "server_timestamp": now_iso(),
        "reported_by_user_id": user["id"],
        "reported_by_role": user["role"],
        "reported_by_email": user["email"],
        "review_status": "open",
        "reviewed_at": None,
        "reviewed_by": None,
    }
    await db.overseer_queue.insert_one(record)
    record.pop("_id", None)
    return {"ok": True, "halt_id": record["id"], "review_status": "open"}


@api.get("/admin/overseer-queue")
async def get_overseer_queue(status: str = "open", user=Depends(admin_only)):
    valid = {"open", "reviewed", "dismissed", "all"}
    if status not in valid:
        raise HTTPException(400, f"status must be one of {sorted(valid)}")
    q = {} if status == "all" else {"review_status": status}
    docs = await db.overseer_queue.find(q, {"_id": 0}).sort("server_timestamp", -1).to_list(length=300)
    open_count = await db.overseer_queue.count_documents({"review_status": "open"})
    return {"count": len(docs), "open_count": open_count, "items": docs}


@api.put("/admin/overseer-queue/{halt_id}")
async def update_overseer_item(halt_id: str, payload: Dict[str, Any], user=Depends(admin_only)):
    new_status = (payload or {}).get("review_status")
    if new_status not in ("reviewed", "dismissed"):
        raise HTTPException(400, "review_status must be 'reviewed' or 'dismissed'.")
    upd = {"review_status": new_status, "reviewed_at": now_iso(), "reviewed_by": user["email"]}
    if payload.get("review_note"):
        upd["review_note"] = str(payload["review_note"])[:500]
    res = await db.overseer_queue.update_one({"id": halt_id}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(404, "Halt id not found.")
    return {"ok": True, "halt_id": halt_id, "review_status": new_status}


# ---------------------------------------------------------------------------
# ADMIN FINANCIAL BLOCKER — Section 2.2 of Executive Spec
# ---------------------------------------------------------------------------
FINANCIAL_FIELDS_TO_STRIP = (
    "contractor_cost_matrix",
    "labor_per_hour",
    "profit_overhead_multipliers",
    "onboarding_metrics",
    "_encrypted",
)


@api.get("/admin/contractor/{contractor_id}/financial-config")
async def admin_view_contractor_financial(contractor_id: str, user=Depends(admin_only)):
    """Hard-empty `{}` — financial isolation by policy."""
    target = await db.users.find_one({"id": contractor_id}, {"_id": 0})
    if not target:
        raise HTTPException(404, "Contractor not found.")
    return {}
