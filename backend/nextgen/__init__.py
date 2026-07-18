"""Stratex Core NextGen — backend module.

This package implements the NextGen architecture (Blueprint v1.2 · Sequence
Diagrams v1.0 · Canonical Data Model v1.0). It is *namespace-isolated* from
legacy code:

- HTTP routes mount under `/api/nextgen/*`
- MongoDB collections carry the `nextgen_` prefix
- Frontend surface mounts under `/nextgen/*`

Legacy `stratexdrone.com` production surfaces are unaffected.

Importing this package is what registers the decorators on the shared
`api` router built in `core.py`.
"""
from __future__ import annotations

# Route modules must be imported so their `@nextgen_r.get/post` decorators
# execute BEFORE `app.include_router(api)` runs in `server.py`.
from . import routes  # noqa: F401
