"""STRATEX Admin Sales Hub + Competitive Intel + CRM stubs.

Pre-cached Central Kentucky sales targets, dynamic competitive intel hooks
for the onboarding funnel, and append-only CRM collections (outreach notes,
call logs, communication templates).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from core import _public_user, admin_only, api, db, now_iso  # noqa: F401

# ---------------------------------------------------------------------------
# Seed: Central-KY sales targets
# ---------------------------------------------------------------------------
KY_SALES_TARGETS_SEED = [
    {"id": "ale-roofing",     "name": "ALE Roofing LLC", "aka": "Formerly Atlas Contracting / Elleman Contracting",
     "base": "Lexington, KY", "phone": "859-402-5211",
     "focus": "Historic Preservation, Slate, Copper, Custom Internal Box Gutters, Residential/Commercial Replacements",
     "lat": 38.0406, "lng": -84.5037, "status": "uncontacted",
     "est_annual_revenue_usd": 4_800_000, "est_overhead_leak_pct": 0.18, "hook_archetype": "specialty_slate_copper"},
    {"id": "burnett-roofing", "name": "Burnett Roofing",
     "base": "656 Bizzell Drive, Lexington, KY 40510", "phone": "859-253-0116",
     "focus": "Tier 1 Commercial Manufacturing, Single-Ply Membranes (EPDM/TPO/PVC), Modified Bitumen, Architectural Sheet Metal",
     "lat": 38.0739, "lng": -84.5494, "status": "uncontacted",
     "est_annual_revenue_usd": 14_500_000, "est_overhead_leak_pct": 0.22, "hook_archetype": "commercial_membrane"},
    {"id": "centimark",       "name": "CentiMark Corporation",
     "base": "260 Crossfield Dr, Unit 4, Versailles, KY 40383", "phone": "502-716-5777",
     "focus": "Large-Scale Industrial, Thermal Shock Inspections, Commercial Property Maintenance Assets",
     "lat": 38.0530, "lng": -84.7286, "status": "uncontacted",
     "est_annual_revenue_usd": 22_000_000, "est_overhead_leak_pct": 0.24, "hook_archetype": "industrial_pm_assets"},
    {"id": "big-league",      "name": "Big League Roofers",
     "base": "3022 Lexington Road, Nicholasville, KY 40356 · 2901 Richmond Road, Lexington, KY 40509", "phone": "859-693-7663",
     "focus": "High-Volume GAF Master Elite Residential, Hail/Storm Insurance Adjuster Coordination",
     "lat": 37.8806, "lng": -84.5728, "status": "uncontacted",
     "est_annual_revenue_usd": 9_200_000, "est_overhead_leak_pct": 0.27, "hook_archetype": "high_volume_storm"},
    {"id": "godsend",         "name": "A Godsend Roofing LLC",
     "base": "380 E Main St, Lexington, KY 40507", "phone": "859-432-7663",
     "focus": "Commercial/Residential Master Applicators, Complex Custom Step Flashing, Storm Repair Logistics",
     "lat": 38.0457, "lng": -84.4906, "status": "uncontacted",
     "est_annual_revenue_usd": 6_400_000, "est_overhead_leak_pct": 0.21, "hook_archetype": "mixed_master_applicator"},
    {"id": "odessa",          "name": "Odessa Roofing, Inc.",
     "base": "232 Gold Rush Road, Suite 110, Lexington, KY 40503", "phone": "859-271-0524",
     "focus": "KRCA/NRCA Members, Custom Copper Flashing, Synthetic Slate, High-End Residential Architecture",
     "lat": 38.0019, "lng": -84.5310, "status": "uncontacted",
     "est_annual_revenue_usd": 5_600_000, "est_overhead_leak_pct": 0.19, "hook_archetype": "high_end_residential"},
    {"id": "barrier",         "name": "Barrier Roofs",
     "base": "Lexington, KY", "phone": "859-251-5119",
     "focus": "High-Volume Owens Corning Platinum Dealer, Insurance Claims Supplementing",
     "lat": 38.0406, "lng": -84.5037, "status": "uncontacted",
     "est_annual_revenue_usd": 7_800_000, "est_overhead_leak_pct": 0.26, "hook_archetype": "high_volume_storm"},
]


# ---------------------------------------------------------------------------
# Competitive Intel (onboarding hook generator)
# ---------------------------------------------------------------------------
BLENDED_LEAK_PCT = 0.22
STRATEX_RECLAIM_FRACTION = 0.65

HOOK_TEMPLATES: Dict[str, Dict[str, str]] = {
    "specialty_slate_copper": {
        "headline": "Out-reclaim {name} on every slate/copper callback",
        "body": "{name}'s specialty book bleeds about ${target_leak} per year to callback measurements and custom-fab waste. STRATEX'd hand you back ${user_reclaim}/yr from the same overhead category — {delta_text}.",
    },
    "commercial_membrane": {
        "headline": "Beat {name}'s membrane-callback overhead",
        "body": "{name} loses an estimated ${target_leak}/yr to membrane recall trips, photo-rework, and adjuster delay. STRATEX puts ${user_reclaim}/yr back on your line — {delta_text}.",
    },
    "industrial_pm_assets": {
        "headline": "Reclaim more than {name}'s entire PM-asset bleed",
        "body": "Industrial PM portfolios like {name}'s leak around ${target_leak}/yr to inspection scheduling friction and thermal-survey rework. STRATEX recovers ${user_reclaim}/yr in your operation — {delta_text}.",
    },
    "high_volume_storm": {
        "headline": "Out-pace {name} on storm-cycle margin",
        "body": "{name}'s storm-cycle business absorbs ~${target_leak}/yr in adjuster supplementing, return-trip mileage, and ladder-safety overhead. STRATEX clawback for you: ${user_reclaim}/yr — {delta_text}.",
    },
    "mixed_master_applicator": {
        "headline": "Out-margin {name} on every mixed-scope job",
        "body": "{name}'s step-flash and storm-logistics overhead runs about ${target_leak}/yr. STRATEX hands you ${user_reclaim}/yr back from the same leak pattern — {delta_text}.",
    },
    "high_end_residential": {
        "headline": "Match {name}'s margin without the artisan overhead",
        "body": "{name}'s NRCA-grade residential book loses ~${target_leak}/yr to custom-flash callbacks and synthetic-slate cut-waste. STRATEX recovers ${user_reclaim}/yr from your overhead band — {delta_text}.",
    },
}

DEFAULT_HOOK = {
    "headline": "Out-reclaim {name}'s overhead bleed",
    "body": "{name} loses approximately ${target_leak}/yr to the 5-overhead leak pattern (callbacks, mileage, ladder safety, adjuster delay, blended labor). STRATEX'd hand you back ${user_reclaim}/yr — {delta_text}.",
}


def _money(n: float) -> str:
    n = max(0.0, float(n))
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return f"{n:.0f}"


class CompetitiveIntelBody(BaseModel):
    historical_sales_2_years: float
    leads_per_month: Optional[int] = 0


@api.post("/onboarding/competitive-intel")
async def onboarding_competitive_intel(body: CompetitiveIntelBody):
    """Return ranked outreach hooks comparing the prospect to the 7 KY targets.

    PUBLIC by design — the /onboard funnel runs anonymously.
    """
    user_2yr = max(0.0, float(body.historical_sales_2_years))
    user_annual = user_2yr / 2.0
    user_leak = user_annual * BLENDED_LEAK_PCT
    user_reclaim = user_leak * STRATEX_RECLAIM_FRACTION

    targets = await db.sales_targets.find({}, {"_id": 0}).to_list(length=50)
    if not targets:
        targets = KY_SALES_TARGETS_SEED

    rows = []
    for t in targets:
        rev = float(t.get("est_annual_revenue_usd", 0) or 0)
        leak_pct = float(t.get("est_overhead_leak_pct", 0) or 0)
        if rev <= 0 or leak_pct <= 0:
            continue
        target_leak = rev * leak_pct
        delta = user_reclaim - target_leak
        beat = delta >= 0
        if beat:
            delta_text = f"you'd reclaim ${_money(abs(delta))}/yr MORE than {t['name']} loses to that pattern"
        else:
            shortfall_pct = (user_reclaim / target_leak) if target_leak > 0 else 0
            delta_text = f"that's {shortfall_pct * 100:.0f}% of their estimated bleed — you'd close the gap fast"

        archetype = t.get("hook_archetype", "")
        tmpl = HOOK_TEMPLATES.get(archetype, DEFAULT_HOOK)
        fmt = {
            "name": t["name"],
            "target_leak": _money(target_leak),
            "user_reclaim": _money(user_reclaim),
            "delta_text": delta_text,
        }
        rows.append({
            "id": t["id"],
            "name": t["name"],
            "focus": t.get("focus", ""),
            "phone": t.get("phone", ""),
            "archetype": archetype,
            "target_annual_revenue_usd": rev,
            "target_overhead_leak_pct": leak_pct,
            "target_annual_leak_usd": round(target_leak, 2),
            "user_reclaim_usd": round(user_reclaim, 2),
            "delta_usd": round(delta, 2),
            "user_beats_target": beat,
            "headline": tmpl["headline"].format(**fmt),
            "body": tmpl["body"].format(**fmt),
        })

    rows.sort(key=lambda r: (not r["user_beats_target"], -r["delta_usd"]))

    return {
        "user": {
            "annual_sales_usd": round(user_annual, 2),
            "estimated_overhead_leak_usd": round(user_leak, 2),
            "stratex_annual_reclaim_usd": round(user_reclaim, 2),
            "blended_leak_pct": BLENDED_LEAK_PCT,
            "stratex_reclaim_fraction": STRATEX_RECLAIM_FRACTION,
        },
        "targets_count": len(rows),
        "targets_user_beats": sum(1 for r in rows if r["user_beats_target"]),
        "rows": rows,
    }


@api.get("/admin/sales-targets")
async def admin_sales_targets(user=Depends(admin_only)):
    """Admin-only: returns the pre-cached Lexington-radius contractor list."""
    docs = await db.sales_targets.find({}, {"_id": 0}).to_list(length=200)
    if not docs:
        return {"targets": KY_SALES_TARGETS_SEED, "source": "seed_constant"}
    return {"targets": docs, "source": "mongo"}


# ---------------------------------------------------------------------------
# ADMIN CRM — outreach notes, call logs, communication templates
# ---------------------------------------------------------------------------
def _known_target_ids() -> set:
    return {t["id"] for t in KY_SALES_TARGETS_SEED}


class OutreachNoteIn(BaseModel):
    body: str
    author: Optional[str] = ""
    channel: Optional[str] = "manual"


@api.get("/admin/sales-targets/{target_id}/outreach-notes")
async def list_outreach_notes(target_id: str, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    notes = await db.sales_outreach_notes.find(
        {"target_id": target_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=500)
    return {"target_id": target_id, "count": len(notes), "notes": notes}


@api.post("/admin/sales-targets/{target_id}/outreach-notes")
async def add_outreach_note(target_id: str, body: OutreachNoteIn, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    if not (body.body or "").strip():
        raise HTTPException(400, "Note body is required.")
    note = {
        "id": str(uuid.uuid4()),
        "target_id": target_id,
        "body": body.body.strip(),
        "author": body.author or user.get("email"),
        "channel": body.channel or "manual",
        "created_at": now_iso(),
        "created_by_user_id": user["id"],
    }
    await db.sales_outreach_notes.insert_one(note)
    note.pop("_id", None)
    return {"ok": True, "note": note}


class CallLogIn(BaseModel):
    outcome: str
    duration_seconds: int = 0
    notes: Optional[str] = ""
    callback_at: Optional[str] = None


@api.get("/admin/sales-targets/{target_id}/call-logs")
async def list_call_logs(target_id: str, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    logs = await db.sales_call_logs.find(
        {"target_id": target_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=500)
    return {"target_id": target_id, "count": len(logs), "logs": logs}


@api.post("/admin/sales-targets/{target_id}/call-logs")
async def add_call_log(target_id: str, body: CallLogIn, user=Depends(admin_only)):
    if target_id not in _known_target_ids():
        raise HTTPException(404, "Unknown sales target.")
    valid_outcomes = {"connected", "voicemail", "no_answer", "callback_scheduled", "wrong_number"}
    if body.outcome not in valid_outcomes:
        raise HTTPException(400, f"outcome must be one of {sorted(valid_outcomes)}")
    log = {
        "id": str(uuid.uuid4()),
        "target_id": target_id,
        "outcome": body.outcome,
        "duration_seconds": max(0, int(body.duration_seconds or 0)),
        "notes": (body.notes or "").strip(),
        "callback_at": body.callback_at,
        "created_at": now_iso(),
        "created_by_user_id": user["id"],
        "created_by_email": user["email"],
    }
    await db.sales_call_logs.insert_one(log)
    log.pop("_id", None)
    return {"ok": True, "log": log}


_DEFAULT_TEMPLATES = [
    {
        "id": "intro-sms",
        "channel": "sms",
        "name": "Cold Intro · Drone Demo",
        "subject": None,
        "body": "Hi {contact_name} — {sender_name} with STRATEX™. We deploy autonomous drone roof inspections (no ladders, no climbing) and lock estimates to insurance grade. Worth a 15-min walkthrough? — {sender_name}",
    },
    {
        "id": "intro-email",
        "channel": "email",
        "name": "Cold Intro · Email",
        "subject": "STRATEX™ Strategic Thermal Reconnaissance — 15-min walkthrough for {company}",
        "body": "Hi {contact_name},\n\nI'm {sender_name} with STRATEX™ — we deliver autonomous drone roof inspections fused with sub-surface thermal capacitance modeling, so estimates land insurance-grade without a ladder ever touching the roof.\n\nFor a shop like {company} ({focus}), a 15-min walkthrough usually pencils out within the first project. Open this week?\n\n— {sender_name}",
    },
    {
        "id": "demo-followup-email",
        "channel": "email",
        "name": "Post-Demo Follow-Up",
        "subject": "STRATEX™ — your {company} ROI breakdown",
        "body": "Hi {contact_name},\n\nGreat speaking with you. Per the live ROI matrix we ran together, {company} reclaims approximately ${annual_savings} in the first 12 months by retiring manual ladder estimates. Attached: full Cost-Basis Matrix + sample Quant™ report.\n\nReady to schedule your pilot scan?\n\n— {sender_name}",
    },
    {
        "id": "callback-sms",
        "channel": "sms",
        "name": "Callback Reminder",
        "subject": None,
        "body": "Hi {contact_name}, {sender_name} from STRATEX™ following up on our chat. Ladder-free roof recon, 60-second deployment. Got 10 min?",
    },
]


class CommTemplateIn(BaseModel):
    id: str
    channel: str
    name: str
    subject: Optional[str] = None
    body: str


@api.get("/admin/communication-templates")
async def list_communication_templates(user=Depends(admin_only)):
    docs = await db.communication_templates.find({}, {"_id": 0}).to_list(length=200)
    if not docs:
        await db.communication_templates.insert_many(
            [{**t, "created_at": now_iso(), "system_seed": True} for t in _DEFAULT_TEMPLATES]
        )
        docs = await db.communication_templates.find({}, {"_id": 0}).to_list(length=200)
    return {"count": len(docs), "templates": docs}


@api.put("/admin/communication-templates/{template_id}")
async def upsert_communication_template(template_id: str, body: CommTemplateIn, user=Depends(admin_only)):
    if body.channel not in ("sms", "email"):
        raise HTTPException(400, "channel must be 'sms' or 'email'.")
    if body.channel == "email" and not (body.subject or "").strip():
        raise HTTPException(400, "Email templates require a subject.")
    if template_id != body.id:
        raise HTTPException(400, "Path id and body id must match.")
    doc = {
        "id": body.id,
        "channel": body.channel,
        "name": body.name,
        "subject": body.subject,
        "body": body.body,
        "updated_at": now_iso(),
        "updated_by": user["email"],
    }
    await db.communication_templates.update_one(
        {"id": body.id}, {"$set": doc}, upsert=True,
    )
    return {"ok": True, "template": doc}
