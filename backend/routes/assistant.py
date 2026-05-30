"""STRATEX Investor / Tour AI Assistant routes.

Claude Haiku 4.5 via EMERGENT_LLM_KEY. Greets the investor on first login,
follows them across routes with tailored briefings, persists each session's
history in db.assistant_conversations.
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import Depends, HTTPException
from pydantic import BaseModel

from core import api, current_user, db, logger, now_iso


class AssistantTurn(BaseModel):
    role: str  # 'user' | 'assistant'
    content: str


class AssistantChatBody(BaseModel):
    session_id: Optional[str] = None
    user_message: str
    route: Optional[str] = "/"
    route_briefing: Optional[str] = ""
    user_first_name: Optional[str] = "there"


ASSISTANT_SYSTEM_TMPL = (
    "You are the STRATEX™ in-app guide for {first_name}, an investor walking through the "
    "STRATEX SaaS platform for drone-based roof inspections. Be warm, concise, and concrete — "
    "two to four short sentences per reply unless asked for depth. Speak in first person ('I'). "
    "Never invent features. When the current screen has a route briefing, anchor your answer to it. "
    "If asked about something not on the current screen, briefly explain and suggest the route that "
    "shows it. Avoid jargon dumps. Always end with an inviting follow-up question when natural."
)


@api.post("/assistant/chat")
async def assistant_chat(body: AssistantChatBody, user=Depends(current_user)):
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(500, "EMERGENT_LLM_KEY not configured")

    session_id = body.session_id or f"{user['id']}::{uuid.uuid4()}"
    first_name = (body.user_first_name or user.get("first_name") or "there").strip() or "there"

    system_msg = ASSISTANT_SYSTEM_TMPL.format(first_name=first_name)
    if body.route_briefing:
        system_msg += f"\n\nCURRENT_SCREEN ({body.route}):\n{body.route_briefing.strip()}"

    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system_msg,
    ).with_model("anthropic", "claude-haiku-4-5-20251001")

    try:
        reply = await chat.send_message(UserMessage(text=body.user_message))
    except Exception as e:
        logger.warning(f"assistant_chat LLM error: {e!r}")
        raise HTTPException(502, f"assistant unavailable: {type(e).__name__}")

    now = now_iso()
    await db.assistant_conversations.update_one(
        {"session_id": session_id, "user_id": user["id"]},
        {
            "$setOnInsert": {
                "session_id": session_id,
                "user_id": user["id"],
                "user_email": user["email"],
                "started_at": now,
            },
            "$set": {"last_route": body.route, "last_active_at": now},
            "$push": {
                "messages": {
                    "$each": [
                        {"role": "user", "content": body.user_message, "route": body.route, "ts": now},
                        {"role": "assistant", "content": reply, "route": body.route, "ts": now},
                    ]
                }
            },
        },
        upsert=True,
    )

    return {"session_id": session_id, "reply": reply}
