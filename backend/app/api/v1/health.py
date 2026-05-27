"""
HYDRA Core™ — Health & Hardware Telemetry Endpoint
==================================================

GET /api/health
    200 OK — payload includes the HYDRA HardwareProfile so the frontend
    Orchestration Matrix can render host CPU count + visible GPU architectures.

Used by:
  * Docker HEALTHCHECK (returns 200 with minimal body)
  * Kubernetes liveness/readiness probes
  * Frontend dashboard hardware tile
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, status

from app.core.hardware import detect_hardware

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Liveness + hardware telemetry",
    response_description="Service health envelope with serialized HardwareProfile",
)
async def health() -> Dict[str, Any]:
    """Return 200 OK with the current host's compute-fabric snapshot.

    The hardware probe is `@lru_cache`-d so this endpoint is O(1) after the
    first call — safe to hammer from health checks every 30s.
    """
    profile = detect_hardware()
    return {
        "status": "ok",
        "service": "stratex-hydra-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hardware": profile.as_dict(),
        "multi_gpu": profile.supports_multi_gpu,
    }


__all__ = ["router"]
