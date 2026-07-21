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
