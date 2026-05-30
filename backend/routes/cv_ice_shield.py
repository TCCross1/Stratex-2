"""STRATEX CV pipeline routes — Sub-Surface Ice & Water Shield Detection.

Strict-typed analysis pipeline lives in /app/backend/roof_cv_ice_shield.py.
If composite confidence < 0.90, the frame is auto-halted and routed into
the existing telemetry_halts queue surfaced by /admin/overseer.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import Depends, HTTPException

from core import api, current_user, db, now_iso
from roof_cv_ice_shield import (
    IceShieldAnalysis,
    ValleyFrame,
    analyze_valley_frame,
)


@api.post("/cv/ice-shield/analyze", response_model=IceShieldAnalysis)
async def cv_ice_shield_analyze(frame: ValleyFrame, user=Depends(current_user)):
    if user.get("role") not in ("operator", "admin", "contractor"):
        raise HTTPException(403, "role not permitted")

    result = analyze_valley_frame(frame)

    await db.cv_ice_shield_analyses.insert_one({
        "id": str(uuid.uuid4()),
        "submitted_by": user["id"],
        "submitted_role": user["role"],
        "frame_id": frame.frame_id,
        "contractor_id": frame.contractor_id,
        "job_id": frame.job_id,
        "valley_track_id": frame.valley_track_id,
        "analysis": result.model_dump(),
        "created_at": now_iso(),
    })

    if result.halted and result.halt_payload:
        await db.telemetry_halts.insert_one({
            "id": str(uuid.uuid4()),
            "status": "open",
            "created_at": now_iso(),
            **result.halt_payload,
        })

    if result.flag_for_estimation_pipeline:
        await db.jobs.update_one(
            {"id": frame.job_id},
            {"$set": {
                "moisture_anomaly_flagged": True,
                "moisture_anomaly_last_frame_id": frame.frame_id,
                "moisture_anomaly_flagged_at": now_iso(),
            }},
        )

    if result.has_ice_and_water_shield:
        await db.jobs.update_one(
            {"id": frame.job_id},
            {"$set": {
                "has_ice_and_water_shield": True,
                "code_compliant_underlayment": True,
                "ice_shield_confirmed_frame_id": frame.frame_id,
                "ice_shield_confirmed_at": now_iso(),
            }},
        )

    return result


@api.get("/cv/ice-shield/recent")
async def cv_ice_shield_recent(limit: int = 50, user=Depends(current_user)):
    """List recent CV analyses with cross-referenced halt status for /admin/cv-ice-shield."""
    q: Dict[str, Any] = {}
    if user.get("role") == "operator":
        q["submitted_by"] = user["id"]
    elif user.get("role") != "admin":
        my_job_ids = [j["id"] async for j in db.jobs.find({"contractor_id": user["id"]}, {"_id": 0, "id": 1})]
        q["job_id"] = {"$in": my_job_ids}

    docs = (
        await db.cv_ice_shield_analyses.find(q, {"_id": 0})
        .sort("created_at", -1)
        .to_list(length=max(1, min(limit, 200)))
    )

    halt_frame_ids = [d["frame_id"] for d in docs if d["analysis"].get("halted")]
    halts_by_frame: Dict[str, Dict[str, Any]] = {}
    if halt_frame_ids:
        async for h in db.telemetry_halts.find(
            {"source": "ice_shield_cv", "frame_id": {"$in": halt_frame_ids}},
            {"_id": 0},
        ):
            halts_by_frame[h["frame_id"]] = h

    for d in docs:
        d["halt_record"] = halts_by_frame.get(d["frame_id"])

    counts = {
        "ice_water_shield_present": sum(1 for d in docs if d["analysis"]["classification"] == "Ice_Water_Shield_Present"),
        "moisture_anomaly":         sum(1 for d in docs if d["analysis"]["classification"] == "Moisture_Anomaly"),
        "unverified_halt":          sum(1 for d in docs if d["analysis"]["classification"] == "Unverified_Halt"),
    }
    return {"count": len(docs), "counts": counts, "items": docs}


@api.post("/cv/ice-shield/replay/{frame_id}")
async def cv_ice_shield_replay(frame_id: str, user=Depends(current_user)):
    """Compliance dry-run: rebuild the synthetic AUTHORIZE_FLEET_LAUNCH manifest
    that this CV frame would have produced. NO DB writes, NO real launch — pure
    read-side audit replay for insurer / regulator walkthroughs.
    """
    doc = await db.cv_ice_shield_analyses.find_one({"frame_id": frame_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"frame {frame_id} not found")

    if user.get("role") == "operator" and doc["submitted_by"] != user["id"]:
        raise HTTPException(403, "not your frame")
    if user.get("role") == "contractor":
        job = await db.jobs.find_one({"id": doc["job_id"]}, {"_id": 0, "contractor_id": 1})
        if not job or job.get("contractor_id") != user["id"]:
            raise HTTPException(403, "not your job")

    a = doc["analysis"]
    halt = await db.telemetry_halts.find_one({"source": "ice_shield_cv", "frame_id": frame_id}, {"_id": 0})

    would_authorize = (
        a["classification"] == "Ice_Water_Shield_Present"
        and not a["halted"]
        and a["confidence"] >= 0.90
    )

    return {
        "replay_id": str(uuid.uuid4()),
        "dry_run": True,
        "frame_id": frame_id,
        "job_id": doc["job_id"],
        "valley_track_id": doc["valley_track_id"],
        "recorded_at": doc["created_at"],
        "verdict": {
            "would_authorize": would_authorize,
            "classification": a["classification"],
            "composite_confidence": a["confidence"],
            "confidence_threshold": 0.90,
            "reasoning": a.get("reasoning", ""),
        },
        "checks": [
            {"name": p["name"], "passed": p["passed"], "detail": p["detail"]}
            for p in a.get("preconditions", [])
        ],
        "flags": {
            "has_ice_and_water_shield": a["has_ice_and_water_shield"],
            "code_compliant_underlayment": a["code_compliant_underlayment"],
            "flag_for_estimation_pipeline": a["flag_for_estimation_pipeline"],
        },
        "halt_record": halt,
        "synthetic_command": {
            "command": "AUTHORIZE_FLEET_LAUNCH",
            "dry_run": True,
            "would_emit": would_authorize,
            "payload": {
                "project_id": doc["job_id"],
                "frame_id": frame_id,
                "valley_track_id": doc["valley_track_id"],
                "cv_classification": a["classification"],
                "cv_confidence": a["confidence"],
            },
        },
        "audit": {
            "replayed_by_user_id": user["id"],
            "replayed_by_role": user["role"],
            "replayed_at": now_iso(),
        },
    }
