"""FastAPI router endpoints for Intelligence Explainer Engine™ (Directive 013).

Provides:
- GET /explanations (filtered and paginated snapshots)
- GET /explanations/{id} (detailed snapshot with role-based level filtering)
- GET /property/{id}/explain (compile / retrieve property-wide high-density feed)
- POST /explain/query (DSL query engine for contractors/engineers)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import NxSession, nx_session
from ..db import now_iso_utc, nx_collections, strip_mongo_id
from ..explainer_service import compile_explanation
from ._router import nextgen_r

V1 = "/v1"


# --- Schemas ---

class ConfidenceRange(BaseModel):
    min: float = 0.0
    max: float = 100.0


class QueryFilters(BaseModel):
    confidence_range: Optional[ConfidenceRange] = None
    severity_level: Optional[str] = None
    search_keyword: Optional[str] = None


class ExplainerQueryRequest(BaseModel):
    property_ids: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    filters: Optional[QueryFilters] = None


# --- Endpoints ---

@nextgen_r.get(f"{V1}/explanations")
async def get_explanations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    system_category: Optional[str] = None,
    min_confidence: Optional[float] = None,
    property_id: Optional[str] = None,
    session: NxSession = Depends(nx_session),
):
    """Retrieve historical paginated and filtered explanation snapshots."""
    query: Dict[str, Any] = {"tenant_id": session.tenant_id}

    if system_category:
        query["system_category"] = system_category.strip().upper()
    if min_confidence is not None:
        query["overall_confidence_score"] = {"$gte": min_confidence}
    if property_id:
        query["property_id"] = property_id

    cursor = nx_collections.explanations.find(query).skip(offset).limit(limit)
    results = await cursor.to_list(None)
    total = await nx_collections.explanations.count_documents(query)

    # Format the summary view for results list
    formatted_results = []
    for r in results:
        formatted_results.append({
            "explanation_id": r["explanation_id"],
            "property_id": r["property_id"],
            "system_category": r["system_category"],
            "overall_confidence_score": r["overall_confidence_score"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        })

    return {
        "total_records": total,
        "limit": limit,
        "offset": offset,
        "results": formatted_results
    }


@nextgen_r.get(f"{V1}/explanations/{{id}}")
async def get_explanation_by_id(
    id: str,
    level: Optional[int] = Query(None, ge=1, le=4),
    session: NxSession = Depends(nx_session),
):
    """Retrieve detailed explanation snapshot by unique ID with level RBAC filtering."""
    explanation = await nx_collections.explanations.find_one({
        "explanation_id": id,
        "tenant_id": session.tenant_id
    })
    if not explanation:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Explanation snapshot with ID {id} not found."
            }
        )

    # RBAC Guard: Homeowners cannot access level 3 or level 4
    is_homeowner = session.role == "homeowner"
    if is_homeowner and level in {3, 4}:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "INSUFFICIENT_ACCESS_ROLE",
                "message": f"Role '{session.role}' is not authorized to query Level {level} traces."
            }
        )

    # Clean mongo ID
    result = strip_mongo_id(explanation)

    # Apply level filtering
    levels = result.get("levels", {})
    filtered_levels = {}

    if level is not None:
        lvl_key = f"level_{level}"
        if lvl_key in levels:
            filtered_levels[lvl_key] = levels[lvl_key]
    else:
        # If no specific level is requested, filter by role access
        if is_homeowner:
            # Homeowner only gets level 1
            if "level_1" in levels:
                filtered_levels["level_1"] = levels["level_1"]
        else:
            # Other roles get all levels
            filtered_levels = levels

    result["levels"] = filtered_levels

    # Homeowner doesn't see evidence trace details or level 4
    if is_homeowner:
        result.pop("evidence_trace", None)

    return result


@nextgen_r.get(f"{V1}/property/{{id}}/explain")
async def get_property_explanations(
    id: str,
    bypass_cache: bool = Query(False),
    session: NxSession = Depends(nx_session),
):
    """Retrieve or compile the latest high-density explanation feed for all property systems."""
    # Ensure property exists
    prop = await nx_collections.properties.find_one({
        "canonical_id": id,
        "tenant_id": session.tenant_id
    })
    if not prop:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Property with ID {id} not found."
            }
        )

    # Ingest / Compile for WATER_INTRUSION, ROOF, and FOUNDATION systems
    categories = ["ROOF", "WATER_INTRUSION", "FOUNDATION"]
    compiled = {}
    dna_version = 1

    for cat in categories:
        try:
            exp = await compile_explanation(
                property_id=id,
                tenant_id=session.tenant_id,
                system_category=cat,
                user_id=session.user_id,
                bypass_cache=bypass_cache
            )
            dna_version = exp.get("dna_version_referenced", 1)

            # Format feed entry (conclusion & why_this_matters from Level 1)
            lvl1 = exp.get("levels", {}).get("level_1", {})
            compiled[cat] = {
                "explanation_id": exp["explanation_id"],
                "overall_confidence_score": exp["overall_confidence_score"],
                "conclusion": lvl1.get("conclusion", "No active observation."),
                "why_this_matters": lvl1.get("why_this_matters", "N/A"),
            }
        except Exception as e:
            # Handle failure gracefully by continuing
            pass

    return {
        "property_id": id,
        "dna_version_referenced": dna_version,
        "compiled_at": now_iso_utc(),
        "explanations": compiled
    }


@nextgen_r.post(f"{V1}/explain/query")
async def query_explanations(
    body: ExplainerQueryRequest,
    session: NxSession = Depends(nx_session),
):
    """Execute DSL pattern query on historical snapshots. Only for contractor/engineer."""
    if session.role == "homeowner":
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "INSUFFICIENT_ACCESS_ROLE",
                "message": "Role 'homeowner' is not authorized to execute explanation queries."
            }
        )

    query: Dict[str, Any] = {"tenant_id": session.tenant_id}

    if body.property_ids:
        query["property_id"] = {"$in": body.property_ids}
    if body.categories:
        query["system_category"] = {"$in": [c.upper() for c in body.categories]}

    # Handle confidence range filter
    if body.filters and body.filters.confidence_range:
        query["overall_confidence_score"] = {
            "$gte": body.filters.confidence_range.min,
            "$lte": body.filters.confidence_range.max,
        }

    results = await nx_collections.explanations.find(query).to_list(None)

    # Apply search keyword in-memory
    filtered_results = []
    keyword = (body.filters.search_keyword or "").strip().lower() if body.filters else None

    for r in results:
        # Check keyword in conclusion or description
        match = True
        if keyword:
            lvl1 = r.get("levels", {}).get("level_1", {})
            conclusion = lvl1.get("conclusion", "").lower()
            desc = " ".join(lvl1.get("supporting_evidence", [])).lower()
            if keyword not in conclusion and keyword not in desc:
                match = False

        if match:
            lvl1 = r.get("levels", {}).get("level_1", {})
            filtered_results.append({
                "property_id": r["property_id"],
                "explanation_id": r["explanation_id"],
                "system_category": r["system_category"],
                "overall_confidence_score": r["overall_confidence_score"],
                "preview": {
                    "conclusion": lvl1.get("conclusion", ""),
                    "severity": r.get("certainty_level", "UNKNOWN"),
                    "why_this_matters": lvl1.get("why_this_matters", "")
                }
            })

    return {
        "query_timestamp": now_iso_utc(),
        "match_count": len(filtered_results),
        "results": filtered_results
    }


# ── Lifecycle, Reconciliation & Conflict Endpoints ───────────────────────

class RetractRequest(BaseModel):
    reason: str


class ConflictResolveRequest(BaseModel):
    resolution: str
    resolution_reason: str


@nextgen_r.get(f"{V1}/explanations/{{id}}/history")
async def get_explanation_history(
    id: str,
    session: NxSession = Depends(nx_session),
):
    """Retrieve the full historical supersession chain of an explanation."""
    from ..explanation_reconciliation_service import nx_collections

    # Fetch targeted explanation first
    exp = await nx_collections.explanations.find_one({
        "explanation_id": id,
        "tenant_id": session.tenant_id
    })
    if not exp:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "RESOURCE_NOT_FOUND",
                "message": f"Explanation with ID {id} not found."
            }
        )

    # RBAC Guard: Homeowners cannot view non-homeowner history
    if session.role == "homeowner" and exp.get("audience_level") != "homeowner":
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "INSUFFICIENT_ACCESS_ROLE",
                "message": "Homeowners are only authorized to view homeowner-safe explanations."
            }
        )

    # Fetch all historical versions of the same projection scope
    query = {
        "tenant_id": session.tenant_id,
        "property_id": exp["property_id"],
        "system_category": exp["system_category"],
        "audience_level": exp.get("audience_level", "homeowner")
    }
    
    cursor = nx_collections.explanations.find(query).sort("created_at", -1)
    results = [strip_mongo_id(d) async for d in cursor]
    return {"history": results, "count": len(results)}


@nextgen_r.get(f"{V1}/property/{{property_id}}/explanations/current")
async def get_current_property_explanations(
    property_id: str,
    scope: Optional[str] = Query(None),
    audience: Optional[str] = Query(None),
    session: NxSession = Depends(nx_session),
):
    """Retrieve the active current published explanations for a property."""
    from ..explanation_reconciliation_service import nx_collections

    if scope and not isinstance(scope, str):
        scope = None
    if audience and not isinstance(audience, str):
        audience = None

    query = {
        "tenant_id": session.tenant_id,
        "property_id": property_id,
        "status": "PUBLISHED",
        "is_current": True
    }

    if scope:
        query["system_category"] = scope.strip().upper()

    # RBAC Guard / audience filter forcing
    if session.role == "homeowner":
        query["audience_level"] = "homeowner"
    elif audience:
        query["audience_level"] = audience
    else:
        # Default for engineer/contractor is all or engineer
        pass

    cursor = nx_collections.explanations.find(query)
    results = [strip_mongo_id(d) async for d in cursor]
    
    # Hide evidence trace for homeowners
    if session.role == "homeowner":
        for r in results:
            r.pop("evidence_trace", None)
            if "levels" in r and "level_4" in r["levels"]:
                r["levels"].pop("level_4")
            if "levels" in r and "level_3" in r["levels"]:
                r["levels"].pop("level_3")
            if "levels" in r and "level_2" in r["levels"]:
                r["levels"].pop("level_2")

    return {"results": results, "count": len(results)}


@nextgen_r.get(f"{V1}/property/{{property_id}}/explanations/history")
async def get_property_explanation_history(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    """Retrieve all historical explanations (all versions/statuses) for a property."""
    from ..explanation_reconciliation_service import nx_collections

    query = {
        "tenant_id": session.tenant_id,
        "property_id": property_id
    }

    if session.role == "homeowner":
        query["audience_level"] = "homeowner"

    cursor = nx_collections.explanations.find(query).sort("created_at", -1)
    results = [strip_mongo_id(d) async for d in cursor]

    # Clean outputs for homeowners
    if session.role == "homeowner":
        for r in results:
            r.pop("evidence_trace", None)
            if "levels" in r:
                r["levels"] = {"level_1": r["levels"].get("level_1")}

    return {"results": results, "count": len(results)}


@nextgen_r.get(f"{V1}/property/{{property_id}}/explanation-conflicts")
async def get_property_explanation_conflicts(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    """Retrieve all explanation/rebase conflicts for a property."""
    from ..explanation_reconciliation_service import nx_collections

    if session.role == "homeowner":
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "INSUFFICIENT_ACCESS_ROLE",
                "message": "Homeowners are not authorized to view explanation conflicts."
            }
        )

    query = {
        "tenant_id": session.tenant_id,
        "property_id": property_id
    }

    cursor = nx_collections.explanation_conflicts.find(query).sort("detected_at", -1)
    results = [strip_mongo_id(d) async for d in cursor]
    return {"results": results, "count": len(results)}


@nextgen_r.post(f"{V1}/explanations/{{id}}/retract")
async def retract_explanation_by_id(
    id: str,
    body: RetractRequest,
    session: NxSession = Depends(nx_session),
):
    """Retract an explanation by ID."""
    from ..explanation_reconciliation_service import retract_explanation

    APPROVER_ROLES = {"ceo", "admin", "gm"}
    if session.role not in APPROVER_ROLES:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "INSUFFICIENT_ACCESS_ROLE",
                "message": f"Role '{session.role}' is not authorized to retract explanations."
            }
        )

    try:
        retracted = await retract_explanation(id, body.reason, session.user_id)
        return {"status": "SUCCESS", "explanation": retracted}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "RETRACTION_FAILED",
                "message": str(e)
            }
        )


@nextgen_r.post(f"{V1}/property/{{property_id}}/explanations/reconcile")
async def reconcile_property_explanations_endpoint(
    property_id: str,
    session: NxSession = Depends(nx_session),
):
    """Manually triggers explanation reconciliation for a property."""
    from ..explanation_reconciliation_service import reconcile_property_explanations

    ALLOWED_RECONCILERS = {"ceo", "admin", "gm", "contractor", "inspector", "engineer"}
    if session.role not in ALLOWED_RECONCILERS:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "INSUFFICIENT_ACCESS_ROLE",
                "message": f"Role '{session.role}' is not authorized to trigger manual reconciliation."
            }
        )

    try:
        results = await reconcile_property_explanations(property_id, session.tenant_id, session.user_id, force_recompile=True)
        return {"status": "SUCCESS", "reconciliation_results": results}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "RECONCILIATION_FAILED",
                "message": str(e)
            }
        )


@nextgen_r.post(f"{V1}/explanation-conflicts/{{conflict_id}}/resolve")
async def resolve_explanation_conflict_endpoint(
    conflict_id: str,
    body: ConflictResolveRequest,
    session: NxSession = Depends(nx_session),
):
    """Resolves an open explanation/passport conflict."""
    from ..explanation_reconciliation_service import resolve_explanation_conflict

    APPROVER_ROLES = {"ceo", "admin", "gm"}
    if session.role not in APPROVER_ROLES:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "INSUFFICIENT_ACCESS_ROLE",
                "message": f"Role '{session.role}' is not authorized to resolve explanation conflicts."
            }
        )

    try:
        resolved = await resolve_explanation_conflict(
            conflict_id=conflict_id,
            resolution=body.resolution,
            resolution_reason=body.resolution_reason,
            resolved_by=session.user_id,
            tenant_id=session.tenant_id
        )
        return {"status": "SUCCESS", "conflict": resolved}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "CONFLICT_RESOLUTION_FAILED",
                "message": str(e)
            }
        )
