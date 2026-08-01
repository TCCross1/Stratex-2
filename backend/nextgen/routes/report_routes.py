"""
Property Intelligence Report routes — Field Test v1

POST /api/nextgen/reports/compose
POST /api/nextgen/reports/compose/html
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..auth import NxSession, nx_session
from ..report_composer import compose_full_report
from ..report_html import render_report_html
from ..mission_package_seal import verify_seal
from ._router import nextgen_r


class ComposeReportRequest(BaseModel):
    sealed_package: Dict[str, Any]
    passport_projection: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    require_valid_seal: bool = True
    homeowner_safe: bool = False


@nextgen_r.post("/reports/compose")
async def compose_report(
    req: ComposeReportRequest,
    session: NxSession = Depends(nx_session),
):
    pkg = req.sealed_package
    if pkg.get("tenant_id") and pkg["tenant_id"] != session.tenant_id:
        raise HTTPException(403, "Package tenant mismatch")

    if req.require_valid_seal and pkg.get("seal_record"):
        if not verify_seal(pkg):
            report = compose_full_report(pkg, req.passport_projection, req.extra)
            report["seal_warning"] = "Seal verification failed against current key; report is non-authoritative"
            return report

    return compose_full_report(pkg, req.passport_projection, req.extra)


@nextgen_r.post("/reports/compose/html", response_class=HTMLResponse)
async def compose_report_html(
    req: ComposeReportRequest,
    session: NxSession = Depends(nx_session),
):
    pkg = req.sealed_package
    if pkg.get("tenant_id") and pkg["tenant_id"] != session.tenant_id:
        raise HTTPException(403, "Package tenant mismatch")
    report = compose_full_report(pkg, req.passport_projection, req.extra)
    html = render_report_html(report, homeowner_safe=req.homeowner_safe)
    return HTMLResponse(content=html)
