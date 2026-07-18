"""NextGen shared APIRouter — `/api/nextgen/*`."""
from __future__ import annotations

from fastapi import APIRouter

nextgen_r = APIRouter(prefix="/nextgen", tags=["nextgen"])
