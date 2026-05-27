"""
HYDRA Core™ — Orchestration State Router
========================================

GET /api/orchestration/state
    Returns the live status of the three specialized HYDRA agent processes:
      * Parent Node       — supervisor, owns dispatch
      * Sandbox Child     — sandboxed execution worker
      * Architect Child   — long-horizon planning / topology worker

Authentication: every request MUST carry an ``X-HYDRA-Token`` header whose
value matches the server-side ``HYDRA_API_TOKEN`` env var. A missing or
mismatched token returns 401 Unauthorized. When the env var is not set the
endpoint is hard-locked (returns 503 Service Unavailable) to fail-closed
rather than fail-open.

NOTE — the agent payload is mocked per Phase 3 spec; the live runtime will
swap this out for a Redis/Mongo-backed orchestrator query in Phase 4.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException, status

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

# --------------------------------------------------------------------------- #
# Auth guard                                                                  #
# --------------------------------------------------------------------------- #
_HEADER_NAME = "X-HYDRA-Token"
_ENV_VAR = "HYDRA_API_TOKEN"


def _verify_hydra_token(x_hydra_token: str | None) -> None:
    """Constant-time token check against ``HYDRA_API_TOKEN``.

    Fails CLOSED: if no server-side token is configured, the endpoint is
    rejected with 503 so we never accidentally expose orchestration state
    on a misconfigured host.
    """
    server_token = os.environ.get(_ENV_VAR, "").strip()
    if not server_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Orchestration API disabled ({_ENV_VAR} not configured).",
        )
    if not x_hydra_token or not _constant_time_eq(x_hydra_token, server_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or missing {_HEADER_NAME} header.",
            headers={"WWW-Authenticate": _HEADER_NAME},
        )


def _constant_time_eq(a: str, b: str) -> bool:
    """Length-independent constant-time string comparison."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a.encode("utf-8"), b.encode("utf-8")):
        result |= x ^ y
    return result == 0


# --------------------------------------------------------------------------- #
# Mock orchestrator payload (Phase 3 blueprint — replaced in Phase 4)         #
# --------------------------------------------------------------------------- #
def _build_agent_matrix() -> List[Dict[str, Any]]:
    return [
        {
            "id": "parent-node",
            "label": "Parent Node",
            "role": "supervisor",
            "status": "active",
            "color": "yellow",
            "load": 100,
        },
        {
            "id": "sandbox-child",
            "label": "Sandbox Child",
            "role": "execution",
            "status": "idle",
            "color": "green",
            "load": 0,
        },
        {
            "id": "architect-child",
            "label": "Architect Child",
            "role": "planner",
            "status": "processing",
            "color": "blue",
            "load": 45,
        },
    ]


# --------------------------------------------------------------------------- #
# Route                                                                       #
# --------------------------------------------------------------------------- #
@router.get(
    "/state",
    summary="HYDRA agent orchestration matrix",
    response_description="Live status of Parent / Sandbox / Architect agents",
)
async def orchestration_state(
    x_hydra_token: str | None = Header(default=None, alias=_HEADER_NAME),
) -> Dict[str, Any]:
    """Return the orchestration matrix for the frontend dashboard."""
    _verify_hydra_token(x_hydra_token)

    agents = _build_agent_matrix()
    total_load = sum(a["load"] for a in agents)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "matrix_version": "phase-3-mock",
        "agents": agents,
        "aggregate": {
            "agent_count": len(agents),
            "total_load_pct": total_load,
            "average_load_pct": round(total_load / max(len(agents), 1), 1),
        },
    }


__all__ = ["router"]
