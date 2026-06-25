"""STRATEX™ — TC the AI Project Manager.

TC ("Tactical Commander") is the in-app guide that walks every user
through every portal in plain language. The backend wires a streaming
chat endpoint that:

  • carries page context (route + active app + contractor brand) into
    the system prompt so TC always knows where the user is standing
  • streams Claude-Sonnet tokens over SSE for the live-typing feel
  • keeps the prompt tight and brand-locked — TC never goes off the
    "Future Noire" rails
"""
from __future__ import annotations

import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

load_dotenv()

router = APIRouter(prefix="/api/tc", tags=["tc-assistant"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# ── PAGE CONTEXT LIBRARY ──────────────────────────────────────────────
# Maps route prefix → human-readable explainer that TC opens with.
PAGE_GUIDES = {
    "/":                  "Home — the App Launcher. Click any icon on the left rail to open that app in the display screen. The big STRATEX logo is the default 'idle' state.",
    "/deck":              "Contractor Command Deck — the gold-framed cockpit. Shows current projects, billing balance, vendor network, final reports box, pre-flight gateway. Daily situational awareness lives here.",
    "/reports/binder":    "Reports Binder — the 17-page forensic deliverable. Left rail lists every page (Cover · Twin · Thermal · Moisture · Energy · BOM · Catalog · Labor · Profitability · Final). Click a page to open it; the gold-bezel ones are final/master pages.",
    "/passport/":         "Property Passport portal — public read-only view of a homeowner's certified record. Big seal at the top, immutable hash-chained ledger, live Open-Meteo weather shield. This is the carrier link an insurance adjuster opens with no login.",
    "/contractor/verify": "3-Contact Verification Wall — new contractors must submit three verifiable references (supplier · past client · GC) before the dashboard unlocks. Status bar shows green when all three are verified.",
    "/gm/roster":         "GM Roster & Pricing Inventory — the General Manager tier. Left panel = preferred vendor brands (GAF, Owens Corning, James Hardie...). Right panel = SKU-level cost + markup + auto-computed sell price.",
    "/demo/scan":         "New Drone Scan wizard — runs uploaded drone imagery through the 5-Agent expert system (Geometry, Material, Thermal, BIM, Supply Chain) and outputs a forensic report in under 90 seconds.",
    "/demo/twin":         "Diagnostic Twin — rotatable 3D parametric model of the property with substrate layers, framing skeleton, and a live moisture pulse overlay.",
    "/demo/quant":        "Quant™ Estimator — multi-agent estimating engine that auto-maps every line-item to Xactimate codes under the locked 20/25 O&P envelope.",
    "/switchboard":       "Master Switchboard — every operational dashboard in STRATEX™ on one screen, grouped by audience (Demo · Executive · Operations · Field · Reports).",
    "/contractor/brand":  "Contractor Branding page — upload your logo + business info. Everything cascades through the deck and every PDF deliverable.",
}

DEFAULT_GUIDE = "STRATEX™ — Strategic Thermal Reconnaissance platform. Drone-driven roof forensics, dual-version PDF reports, and a tamper-evident Property Passport for the homeowner."

SYSTEM_PROMPT_BASE = """You are TC — short for 'Tactical Commander' — the in-app
AI Project Manager for STRATEX™, a drone-based roof forensics + B2B SaaS platform.

Your job: walk the user through every feature, every portal, every button, in
plain, friendly, *short* sentences. Never lecture. Always close with one
suggested next click ("Try clicking X next…").

VOICE
  • Confident, calm, mission-control. Future-noire aesthetic.
  • One paragraph max, ~80 words. Use line breaks. Never wall-of-text.
  • Avoid emojis. Use → for next-step arrows.
  • Refer to the user as 'Commander'.

RULES
  • You ONLY help with STRATEX features. If asked off-topic, redirect:
    "I only run the STRATEX cockpit, Commander — let's keep our eyes on the rig."
  • You can summarise any page they're on, explain what a button does,
    or walk them through a 3-step demo flow.
  • If you don't know exactly, say "Let me defer that to Tony" — never invent.

PLATFORM CHEAT-SHEET
  • Tenants: CEO → GM → Contractor (3-tier).
  • Reports: 17-page Adjuster PDF · 6-page Homeowner PDF · 1-page Property Passport certificate.
  • Property Passport = immutable, hash-chained, public carrier link for insurers.
  • Weather Shield = live Open-Meteo 30-day storm correlation.
  • Brand: official red+white "American Roofing Company" logo (the live demo tenant).
"""


class TcChatBody(BaseModel):
    message: str
    route: str = "/"
    active_app: Optional[str] = None
    history: List[dict] = Field(default_factory=list)
    session_id: Optional[str] = "tc-default"


def _build_system_prompt(route: str, active_app: Optional[str]) -> str:
    # Match longest prefix in PAGE_GUIDES
    guide = DEFAULT_GUIDE
    best_match_len = 0
    for prefix, txt in PAGE_GUIDES.items():
        if route.startswith(prefix) and len(prefix) > best_match_len:
            guide = txt
            best_match_len = len(prefix)
    app_hint = f"\nUser just opened the '{active_app}' app window." if active_app else ""
    return (
        SYSTEM_PROMPT_BASE
        + f"\n\nCURRENT CONTEXT\n  Route: {route}\n  Page: {guide}{app_hint}\n"
    )


@router.post("/chat")
async def tc_chat_stream(body: TcChatBody):
    """Stream TC's response (or fall back to single-shot if SDK lacks streaming)."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    system_prompt = _build_system_prompt(body.route, body.active_app)

    async def event_generator():
        try:
            chat = (
                LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=body.session_id or "tc-default",
                    system_message=system_prompt,
                )
                .with_model("anthropic", "claude-sonnet-4-6")
            )
            user_msg = UserMessage(text=body.message)

            # Prefer real streaming if SDK exposes it; otherwise chunk the final
            # text into bite-sized SSE frames so the UI still feels live.
            if hasattr(chat, "stream_message"):
                from emergentintegrations.llm.chat import TextDelta, StreamDone  # type: ignore
                async for ev in chat.stream_message(user_msg):
                    if isinstance(ev, TextDelta):
                        yield f"data: {ev.content}\n\n"
                    elif isinstance(ev, StreamDone):
                        break
            else:
                full = await chat.send_message(user_msg)
                # Slice into ~12-char chunks so the typewriter effect still feels live.
                for i in range(0, len(full), 12):
                    yield f"data: {full[i:i+12]}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)[:200]}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/page-guide")
async def page_guide(route: str = "/"):
    """Quick non-LLM helper — returns the static guide blurb for a route.
    Used by the chat panel header to show TC's 'briefing' on entry."""
    guide = DEFAULT_GUIDE
    best = 0
    for prefix, txt in PAGE_GUIDES.items():
        if route.startswith(prefix) and len(prefix) > best:
            guide = txt
            best = len(prefix)
    return {"route": route, "briefing": guide}
