"""Stratex Core NextGen — backend module.

This package implements the NextGen architecture (Blueprint v1.2 · Sequence
Diagrams v1.0 · Canonical Data Model v1.0). It is *namespace-isolated* from
legacy code:

- HTTP routes mount under `/api/nextgen/*`
- MongoDB collections carry the `nextgen_` prefix
- Frontend surface mounts under `/nextgen/*`

Legacy `stratexdrone.com` production surfaces are unaffected.

Importing `nextgen.routes` (done from `server.py` at startup) registers the
decorators on the shared `api` router built in `core.py`. Importing this
package alone does not pull FastAPI route modules so field-test CLIs and unit
tests can import seal/export helpers without Mongo or auth dependencies.
"""
from __future__ import annotations
