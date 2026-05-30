"""STRATEX Materials Configurator (v2) — stored alongside encrypted cost matrix."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends
from pydantic import BaseModel

from core import api, contractor_only, db, now_iso


class MaterialsConfigBody(BaseModel):
    system: str
    picks: Dict[str, Any] = {}
    custom_text: Optional[str] = ""


@api.get("/contractor/materials-config")
async def get_materials_config(user=Depends(contractor_only)):
    doc = await db.materials_config.find_one({"user_id": user["id"]}, {"_id": 0})
    return doc or {"system": "asphalt_shingle_system", "picks": {}, "custom_text": ""}


@api.put("/contractor/materials-config")
async def put_materials_config(body: MaterialsConfigBody, user=Depends(contractor_only)):
    payload = {
        "user_id": user["id"],
        "system": body.system,
        "picks": body.picks or {},
        "custom_text": body.custom_text or "",
        "updated_at": now_iso(),
    }
    await db.materials_config.update_one(
        {"user_id": user["id"]}, {"$set": payload}, upsert=True,
    )
    return {"ok": True, "system": payload["system"], "pick_count": len(payload["picks"])}
