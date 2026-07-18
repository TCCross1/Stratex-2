"""Habitat magic-link + AWE + HTML report endpoints.

Directive 008 · Field-pilot delivery surface.

- POST /v1/properties/{id}/habitat-link  — contractor issues expiring signed
   link for the homeowner. Kill-list revocable per SD-022.
- GET  /v1/habitat/{token}               — PUBLIC token-gated read. No auth.
   Rate-limit-lite via in-memory counter. Returns only homeowner-safe fields.
- GET  /v1/properties/{id}/awe           — deterministic AWE composite
   (Directive 008 AWE Composite Intelligence).
- GET  /v1/properties/{id}/report/{template}/html — polished HTML projection
   suitable for direct print or later PDF rendering.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..auth import NxSession, nx_session
from ..awe import compute_composite
from ..db import now_iso_utc, nx_collections, nx_id, strip_mongo_id
from ._router import nextgen_r


V1 = "/v1"

# Very small in-memory rate-limit for the public Habitat surface. Preview
# only — a real limiter goes into a Redis or fronting proxy in prod.
_RL_BUCKET: Dict[str, List[float]] = defaultdict(list)
_RL_WINDOW_S = 60
_RL_MAX = 30


def _rate_limit(key: str):
    now = time.time()
    bucket = [t for t in _RL_BUCKET[key] if now - t < _RL_WINDOW_S]
    bucket.append(now)
    _RL_BUCKET[key] = bucket
    if len(bucket) > _RL_MAX:
        raise HTTPException(429, "Too many requests")


class HabitatLinkBody(BaseModel):
    ttl_hours: int = 168  # 7 days default
    audience: str = "homeowner"


@nextgen_r.post(V1 + "/properties/{property_id}/habitat-link")
async def issue_habitat_link(
    property_id: str,
    body: HabitatLinkBody,
    session: NxSession = Depends(nx_session),
):
    if body.audience not in {"homeowner", "adjuster", "insurer", "public"}:
        raise HTTPException(400, "audience must be one of homeowner|adjuster|insurer|public")
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id, "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found")
    ttl_hours = max(1, min(body.ttl_hours, 30 * 24))
    token = secrets.token_urlsafe(24)
    now = now_iso_utc()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
    grant = {
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "grantor_user_id": session.user_id,
        "property_id": property_id,
        "audience": body.audience,
        "token": token,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "issued_at": now,
        "expires_at": expires_at,
        "revoked_at": None,
        "access_count": 0,
    }
    await nx_collections.habitat_grants.insert_one(dict(grant))
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": "habitat.link_issued",
        "actor_id": session.user_id,
        "resource_kind": "property",
        "resource_id": property_id,
        "at": now,
        "payload": {"audience": body.audience, "ttl_hours": ttl_hours},
    })
    return {
        "grant_id": grant["canonical_id"],
        "token": token,
        "expires_at": expires_at,
        "audience": body.audience,
        "public_url": f"/habitat/{token}",
    }


@nextgen_r.post(V1 + "/habitat-grants/{grant_id}/revoke")
async def revoke_grant(grant_id: str, session: NxSession = Depends(nx_session)):
    g = await nx_collections.habitat_grants.find_one({
        "canonical_id": grant_id, "tenant_id": session.tenant_id,
    })
    if not g:
        raise HTTPException(404, "Grant not found")
    await nx_collections.habitat_grants.update_one(
        {"canonical_id": grant_id},
        {"$set": {"revoked_at": now_iso_utc()}},
    )
    return {"ok": True}


@nextgen_r.get(V1 + "/properties/{property_id}/habitat-grants")
async def list_grants(property_id: str, session: NxSession = Depends(nx_session)):
    cursor = nx_collections.habitat_grants.find({
        "tenant_id": session.tenant_id, "property_id": property_id,
    }).sort("issued_at", -1)
    items = []
    async for g in cursor:
        d = strip_mongo_id(g)
        d.pop("token", None)  # do not re-expose the token
        items.append(d)
    return {"items": items, "count": len(items)}


async def _resolve_token(token: str) -> Dict:
    _rate_limit(f"tok:{token[:12]}")
    grant = await nx_collections.habitat_grants.find_one({"token": token})
    if not grant:
        raise HTTPException(404, "Invalid or expired link")
    if grant.get("revoked_at"):
        raise HTTPException(410, "Link revoked")
    try:
        exp = datetime.fromisoformat(grant["expires_at"])
    except Exception:
        exp = None
    if exp and datetime.now(timezone.utc) > exp:
        raise HTTPException(410, "Link expired")
    await nx_collections.habitat_grants.update_one(
        {"canonical_id": grant["canonical_id"]},
        {"$inc": {"access_count": 1}, "$set": {"last_accessed_at": now_iso_utc()}},
    )
    return grant


# ── Public Habitat read (no auth) ────────────────────────────────────────
@nextgen_r.get(V1 + "/habitat/{token}")
async def habitat_public_read(token: str):
    grant = await _resolve_token(token)
    tenant_id = grant["tenant_id"]
    property_id = grant["property_id"]

    prop = await nx_collections.properties.find_one({"canonical_id": property_id})
    if not prop:
        raise HTTPException(404, "Property not found")

    # Approved PIOs (homeowner-safe filter).
    pios = [strip_mongo_id(p) async for p in nx_collections.intelligence_objects.find({
        "tenant_id": tenant_id, "property_id": property_id,
        "state": {"$in": ["approved", "passport_committed"]},
    })]
    homeowner_pios = [p for p in pios if (p.get("visibility") or {}).get("homeowner")]

    # Finalized evidence set (for AWE completeness).
    finalized_evidence: set = set()
    async for pkg in nx_collections.mission_packages.find({
        "tenant_id": tenant_id, "property_id": property_id, "status": "finalized",
    }):
        for e in pkg.get("evidence_ids", []):
            finalized_evidence.add(e)

    awe = compute_composite(homeowner_pios, finalized_evidence)

    # Homeowner-safe intelligence list.
    def strip_pio(p):
        return {
            "building_system": p["building_system"],
            "building_component": p["building_component"],
            "severity": p["severity"],
            "priority": p["priority"],
            "risk_level": p["risk_level"],
            "awe_impact": p["awe_impact"],
            "observation": p["observation"],
            "recommended_action": p.get("recommended_action"),
            "maintenance_recommendation": p.get("maintenance_recommendation"),
            "estimated_remaining_life_years": p.get("estimated_remaining_life_years"),
        }

    key_findings = sorted(
        homeowner_pios,
        key=lambda p: -{"CRITICAL": 5, "MAJOR": 4, "MODERATE": 3,
                          "MINOR": 2, "INFORMATIONAL": 1}.get(p["severity"], 0),
    )[:8]

    # Timeline (public safe).
    timeline = []
    async for t in nx_collections.property_timeline.find({
        "tenant_id": tenant_id, "property_id": property_id,
    }).sort("at", -1):
        timeline.append({
            "at": t["at"], "kind": t["kind"], "summary": t.get("summary"),
        })

    # Last inspection = latest mission with a finalized package.
    last_mission = await nx_collections.missions.find_one(
        {"tenant_id": tenant_id, "property_id": property_id},
        sort=[("created_at", -1)],
    )

    return {
        "property_summary": {
            "address": prop["address"],
            "unit_label": prop.get("unit_label"),
        },
        "inspection_date": last_mission.get("created_at") if last_mission else None,
        "awe": awe,
        "key_findings": [strip_pio(p) for p in key_findings],
        "priority_items": [strip_pio(p) for p in homeowner_pios
                            if p.get("priority") in {"URGENT", "IMMEDIATE", "IMPORTANT"}][:12],
        "maintenance": [strip_pio(p) for p in homeowner_pios
                          if p.get("maintenance_recommendation")][:12],
        "timeline": timeline,
        "audience": grant["audience"],
        "expires_at": grant["expires_at"],
    }


# ── Deterministic AWE composite (authenticated tenant view) ──────────────
@nextgen_r.get(V1 + "/properties/{property_id}/awe")
async def property_awe(property_id: str, session: NxSession = Depends(nx_session)):
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id, "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found")
    pios = [strip_mongo_id(p) async for p in nx_collections.intelligence_objects.find({
        "tenant_id": session.tenant_id, "property_id": property_id,
        "state": {"$in": ["approved", "passport_committed"]},
    })]
    finalized_evidence: set = set()
    async for pkg in nx_collections.mission_packages.find({
        "tenant_id": session.tenant_id, "property_id": property_id, "status": "finalized",
    }):
        for e in pkg.get("evidence_ids", []):
            finalized_evidence.add(e)
    return {"property_id": property_id, "awe": compute_composite(pios, finalized_evidence)}


# ── Polished HTML report projection ──────────────────────────────────────
def _render_html_report(property_doc: Dict, awe: Dict, pios: List[Dict], template: str) -> str:
    def dial(score: int, label: str) -> str:
        color = ("#00FF9C" if score >= 80 else "#FFB020" if score >= 60 else "#FF5A5F")
        return f"""
        <div style="text-align:center;padding:14px;background:#0B111A;border:1px solid #1D2836;border-radius:6px">
          <div style="font:9px/1.4 'JetBrains Mono',monospace;letter-spacing:.28em;color:#8A9BAE;text-transform:uppercase">{label}</div>
          <div style="font:700 44px/1 Helvetica;color:{color};margin:8px 0">{score}</div>
          <div style="font:9px/1.4 'JetBrains Mono',monospace;letter-spacing:.24em;color:#8A9BAE">/ 100</div>
        </div>"""

    addr = property_doc["address"]
    sev_pill = {"CRITICAL": "#FF5A5F", "MAJOR": "#FFB020",
                 "MODERATE": "#FFB020", "MINOR": "#00FF9C",
                 "INFORMATIONAL": "#8A9BAE"}
    rows = "".join(
        f"""<tr>
          <td style="padding:10px 12px;border-bottom:1px solid #1D2836;font-size:12px">{p['building_system']} / {p['building_component']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #1D2836">
            <span style="padding:3px 8px;border:1px solid {sev_pill.get(p['severity'],'#8A9BAE')};color:{sev_pill.get(p['severity'],'#8A9BAE')};font:9px/1 'JetBrains Mono',monospace;letter-spacing:.2em;border-radius:999px">{p['severity']}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #1D2836;font-size:12px">{p['observation']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #1D2836;font-size:12px">{p.get('recommended_action') or '—'}</td>
        </tr>"""
        for p in pios
    )
    return f"""<!doctype html><html><head><meta charset=utf-8><title>Stratex Property Report</title>
<style>
  body {{ background:#05080D;color:#E6EEF6;font-family:'Helvetica Neue',Arial,sans-serif;margin:0;padding:32px }}
  .kicker {{ font:10px/1 'JetBrains Mono',monospace;letter-spacing:.32em;color:#4DF6FF;text-transform:uppercase }}
  h1 {{ font-size:34px;color:#fff;margin:6px 0 12px }}
  h2 {{ font:600 13px/1.4 Helvetica;color:#4DF6FF;letter-spacing:.16em;text-transform:uppercase;margin:32px 0 12px;border-bottom:1px solid #1D2836;padding-bottom:8px }}
  h2 span {{ color:#FFB020;font-family:'JetBrains Mono',monospace;margin-right:10px }}
  .grid4 {{ display:grid;grid-template-columns:repeat(4,1fr);gap:14px }}
  table {{ width:100%;border-collapse:collapse;margin-top:8px;background:#0B111A;border:1px solid #1D2836;border-radius:4px;overflow:hidden }}
  th {{ padding:9px 12px;background:rgba(77,246,255,.05);color:#4DF6FF;font:10px/1 'JetBrains Mono',monospace;letter-spacing:.22em;text-align:left;text-transform:uppercase;border-bottom:1px solid #2A3A4E }}
  .subtitle {{ color:#8A9BAE;font-size:13px;max-width:720px;line-height:1.6 }}
  .band {{ margin-top:22px;padding:12px 16px;background:#0B111A;border:1px solid #1D2836;border-radius:4px;font-size:12px;color:#8A9BAE }}
</style></head><body>
  <div class=kicker>// STRATEX™ CORE · PROPERTY INTELLIGENCE REPORT · {template.upper()}</div>
  <h1>{addr['line1']}, {addr['city']} {addr['region']} {addr['postal_code']}</h1>
  <div class=subtitle>Read-only projection of approved Property Intelligence. Reports are computed at read time from the canonical intelligence engine — never authored inside the report.</div>

  <h2><span>§01</span>AWE Composite Intelligence</h2>
  <div class=grid4>
    {dial(awe['air']['score'], 'Air')}
    {dial(awe['water']['score'], 'Water')}
    {dial(awe['energy']['score'], 'Energy')}
    {dial(awe['composite_index'], 'Composite')}
  </div>
  <div class=band>
    Release state · <b style=color:#FFB020>{awe['release_state']}</b> · Blueprint §17.1 field-pilot gate.
    Confidence <b>{awe['confidence_pct']}%</b> · Evidence completeness <b>{awe['evidence_completeness_pct']}%</b> ·
    Contributing PIOs — Air {awe['air']['contributing_pios']} · Water {awe['water']['contributing_pios']} · Energy {awe['energy']['contributing_pios']}
  </div>

  <h2><span>§02</span>Property Intelligence</h2>
  <table>
    <thead><tr><th>System / Component</th><th>Severity</th><th>Observation</th><th>Recommended Action</th></tr></thead>
    <tbody>{rows or '<tr><td colspan=4 style="padding:24px;text-align:center;color:#8A9BAE">No approved intelligence visible to this template.</td></tr>'}</tbody>
  </table>
</body></html>"""


@nextgen_r.get(V1 + "/properties/{property_id}/report/{template}/html",
                response_class=HTMLResponse)
async def property_report_html(
    property_id: str,
    template: str,
    session: NxSession = Depends(nx_session),
):
    prop = await nx_collections.properties.find_one({
        "canonical_id": property_id, "tenant_id": session.tenant_id,
    })
    if not prop:
        raise HTTPException(404, "Property not found")
    pios = [strip_mongo_id(p) async for p in nx_collections.intelligence_objects.find({
        "tenant_id": session.tenant_id, "property_id": property_id,
        "state": {"$in": ["approved", "passport_committed"]},
    })]

    # Same visibility rules as JSON projection.
    from .intelligence import _project_intelligence_for_report
    projection = _project_intelligence_for_report(pios, template)
    finalized_evidence: set = set()
    async for pkg in nx_collections.mission_packages.find({
        "tenant_id": session.tenant_id, "property_id": property_id, "status": "finalized",
    }):
        for e in pkg.get("evidence_ids", []):
            finalized_evidence.add(e)
    awe = compute_composite(
        [p for p in pios if (p.get("visibility") or {}).get(
            {"homeowner_summary": "homeowner", "executive_summary": "internal"}.get(template, "internal"),
            template == "executive_summary",
        )],
        finalized_evidence,
    )
    # Merge full-record for rows (projection.items are field-limited).
    full_records = [p for p in pios if (p.get("visibility") or {}).get(
        {"contractor_full": "contractor", "homeowner_summary": "homeowner",
         "insurance_claim": "adjuster", "hoa_summary": "public",
         "energy_focused": "homeowner", "executive_summary": "internal",
         "property_health": "homeowner"}.get(template, "internal"),
        template == "executive_summary",
    )]
    return HTMLResponse(_render_html_report(prop, awe, full_records, template))
