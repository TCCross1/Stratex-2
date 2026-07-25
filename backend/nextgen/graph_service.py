"""Property Knowledge Graph (PKG) Service.

Handles virtual adjacency, system/component node and edge creation, 
and path traversal. Enforces the Supreme Engineering Law edge-creation guardrail.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from .db import nx_collections, nx_id, now_iso_utc, strip_mongo_id


async def is_evidence_approved_in_passport(property_id: str, evidence_id: str) -> bool:
    """Verifies that the evidence ID exists within an APPROVED finding / Passport entry."""
    # 1. Fetch the passport for the property
    passport = await nx_collections.passports.find_one({
        "property_id": property_id,
        "status": "active"
    })
    if not passport:
        return False

    # 2. Fetch all passport entries for this passport
    passport_entries = await nx_collections.passport_entries.find({
        "passport_id": passport["canonical_id"]
    }).to_list(None)

    # Collect all APPROVED findings' IDs from passport entries or findings
    approved_finding_ids = set()
    for entry in passport_entries:
        finding_id = entry.get("payload", {}).get("finding_id")
        if finding_id:
            approved_finding_ids.add(finding_id)
        # Direct check on payload if evidence_ids are stored there
        if evidence_id in entry.get("payload", {}).get("evidence_ids", []):
            return True

    # 3. Fetch corresponding APPROVED findings
    if approved_finding_ids:
        findings = await nx_collections.findings.find({
            "canonical_id": {"$in": list(approved_finding_ids)},
            "property_id": property_id,
            "status": "APPROVED"
        }).to_list(None)
        
        for f in findings:
            if evidence_id in f.get("evidence_ids", []):
                return True

    # Check findings collection directly for approved findings with the evidence_id
    direct_findings = await nx_collections.findings.find({
        "property_id": property_id,
        "status": "APPROVED",
        "evidence_ids": evidence_id
    }).to_list(None)
    if direct_findings:
        return True

    return False


async def create_node(property_id: str, system_name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create or retrieve a node in the Property Knowledge Graph."""
    now = now_iso_utc()
    node_name = system_name.strip().upper()
    existing = await nx_collections.graph_nodes.find_one({
        "property_id": property_id,
        "name": node_name
    })
    if existing:
        return strip_mongo_id(existing)

    node = {
        "canonical_id": nx_id(),
        "property_id": property_id,
        "name": node_name,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    await nx_collections.graph_nodes.insert_one(dict(node))
    return strip_mongo_id(node)


async def create_edge(
    property_id: str,
    from_node: str,
    to_node: str,
    relationship: str,
    evidence_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an edge in the Property Knowledge Graph.
    
    Supreme Engineering Law Guardrail:
    Blocks edge creation if the edge fails to cite a valid, verified, and APPROVED evidence_id.
    """
    # Normalize node names
    u_from = from_node.strip().upper()
    u_to = to_node.strip().upper()
    u_rel = relationship.strip().upper()

    # Enforce Supreme Engineering Law Guardrail
    is_approved = await is_evidence_approved_in_passport(property_id, evidence_id)
    if not is_approved:
        raise ValueError(
            f"Supreme Engineering Law: Edge creation failed. "
            f"Evidence ID '{evidence_id}' is not approved in the Passport ledger for property '{property_id}'."
        )

    # Ensure nodes exist
    await create_node(property_id, u_from)
    await create_node(property_id, u_to)

    now = now_iso_utc()
    existing = await nx_collections.graph_edges.find_one({
        "property_id": property_id,
        "from_node": u_from,
        "to_node": u_to,
        "relationship": u_rel,
    })
    if existing:
        return strip_mongo_id(existing)

    edge = {
        "canonical_id": nx_id(),
        "property_id": property_id,
        "from_node": u_from,
        "to_node": u_to,
        "relationship": u_rel,
        "evidence_id": evidence_id,
        "status": (metadata or {}).get("status", "active"),
        "valid_from_passport_version": (metadata or {}).get("valid_from_passport_version", 1),
        "valid_to_passport_version": (metadata or {}).get("valid_to_passport_version"),
        "source_finding_version_id": (metadata or {}).get("source_finding_version_id"),
        "source_evidence_ids": (metadata or {}).get("source_evidence_ids", [evidence_id]),
        "invalidated_at": (metadata or {}).get("invalidated_at"),
        "invalidation_reason": (metadata or {}).get("invalidation_reason"),
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    await nx_collections.graph_edges.insert_one(dict(edge))
    return strip_mongo_id(edge)


async def find_path(
    property_id: str,
    start_node: str,
    end_node: str,
    max_depth: int = 5,
    passport_version: Optional[int] = None,
) -> List[str]:
    """Acyclical pathfinder traversal utility to resolve connections up to max_depth hops.
    
    Returns a list of formatted edge strings, e.g. ["NODE_A --[REL]--> NODE_B"]
    """
    u_start = start_node.strip().upper()
    u_end = end_node.strip().upper()

    # Load all edges for the property to perform in-memory traversal
    edges = await nx_collections.graph_edges.find({"property_id": property_id}).to_list(None)

    # Filter out invalidated, retracted or out-of-version boundaries
    valid_edges = []
    for edge in edges:
        if edge.get("status") in {"invalidated", "retracted"}:
            continue
        if edge.get("invalidated_at") is not None:
            continue
        if passport_version is not None:
            from_v = edge.get("valid_from_passport_version")
            to_v = edge.get("valid_to_passport_version")
            if from_v is not None and passport_version < from_v:
                continue
            if to_v is not None and passport_version > to_v:
                continue
        valid_edges.append(edge)

    # Build adjacency list: { from_node: [(to_node, relationship)] }
    adj: Dict[str, List[tuple[str, str]]] = {}
    for edge in valid_edges:
        f = edge["from_node"]
        t = edge["to_node"]
        r = edge["relationship"]
        adj.setdefault(f, []).append((t, r))

    # Perform DFS to find any path within max_depth hops
    def dfs(current: str, target: str, depth: int, visited: set, path_edges: List[str]) -> Optional[List[str]]:
        if current == target:
            return path_edges
        if depth >= max_depth:
            return None

        visited.add(current)
        for neighbor, relationship in adj.get(current, []):
            if neighbor not in visited:
                edge_str = f"{current} --[{relationship}]--> {neighbor}"
                res = dfs(neighbor, target, depth + 1, visited, path_edges + [edge_str])
                if res is not None:
                    return res
        visited.remove(current)
        return None

    visited_set = set()
    path = dfs(u_start, u_end, 0, visited_set, [])
    return path or []
