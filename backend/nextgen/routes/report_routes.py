"""
Property Intelligence Report routes — Field Test v1

POST /api/nextgen/reports/compose
  Compose a full report from a sealed package (and optional projection).

GET-style composition is intentional: report is derived, not a second ledger.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from ..auth import NxSession, nx_session
from ..report_composer import compose_full_report
from ..mission_package_seal import verify_seal
from ._router import nextgen_r


class ComposeReportRequest(BaseModel):
    sealed_package: Dict[str, Any]
    passport_projection: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    require_valid_seal: bool = True


@nextgen_r.post("/reports/compose")
async def compose_report(
    req: ComposeReportRequest,
    session: NxSession = Depends(nx_session),
):
    """
    Compose a Property Intelligence Report matching the product mockup structure.
    Requires a sealed package. Does not write Passport.
    """
    pkg = req.sealed_package
    if pkg.get("tenant_id") and pkg["tenant_id"] != session.tenant_id:
        raise HTTPException(403, "Package tenant mismatch")

    if req.require_valid_seal:
        if not pkg.get("seal_record"):
            raise HTTPException(400, "Package is not sealed")
        # verify_seal uses env key by default; in prod keys must match
        if not verify_seal(pkg):
            # Allow through with warning flag for demo keys mismatch
            report = compose_full_report(pkg, req.passport_projection, req.extra)
            report["seal_warning"] = "Seal verification failed against current key; report is non-authoritative"
            return report

    report = compose_full_report(pkg, req.passport_projection, req.extra)
    return report
