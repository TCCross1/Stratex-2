"""NextGen route registration.

Each submodule below binds `@nextgen_r.get/post` decorators. We import them
all first, THEN include the router into the shared `api` so all handlers are
attached before FastAPI finalizes the route table.
"""
from __future__ import annotations

# Bind handlers first.
from . import (  # noqa: F401
    catalog,
    organizations,
    properties,
    missions,
    passports,
    workflow,
    audit,
    evidence,
    intelligence,
    findings,
    habitat,
    mission_package_routes,  # Field Test v1 — Canonical Mission Package sealing
)

# Then mount onto the shared /api router.
from core import api  # noqa: E402

from ._router import nextgen_r  # noqa: E402

api.include_router(nextgen_r)
