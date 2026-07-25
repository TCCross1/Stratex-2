"""Integration tests for Intelligence Explainer Engine™ vertical slice.

Verifies:
- Core Mathematics and Confidence calculations (RS, Dt, FC, WC weights, temporal decay)
- Trace Verification (Ledger hash chaining integrity, raising TraceValidationError on tamper)
- Property Knowledge Graph (PKG) adjacency, traversal, and Supreme Engineering Law Guardrail
- Multi-Level Explainer compile pipeline, action-binds on low confidence, and degraded fallback
- FastAPI Router integration, RBAC rules (preventing homeowners from querying level 3/4)
"""
from __future__ import annotations

import os
import sys
import math
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# --- Set up mock environment variables before importing backend modules ---
os.environ.setdefault("MONGO_URL", "mongodb://mock")
os.environ.setdefault("DB_NAME", "mock_db")
os.environ["NEXTGEN_STORAGE_ROOT"] = "/tmp/nextgen_storage"

# Add backend directory to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

# Import core nextgen dependencies
from backend.nextgen.db import nx_collections, nx_id, now_iso_utc
from backend.nextgen.explainer_core import calculate_confidence, verify_explanation_trace, TraceValidationError
from backend.nextgen.graph_service import create_node, create_edge, find_path, is_evidence_approved_in_passport
from backend.nextgen.explainer_service import compile_explanation
from backend.nextgen.routes.explanations import get_explanation_by_id, query_explanations, get_property_explanations, ExplainerQueryRequest, QueryFilters, ConfidenceRange
from backend.nextgen.auth import NxSession
from fastapi import HTTPException


# --- Mock MongoDB Collections Class ---

class MockCursor:
    def __init__(self, data):
        self.data = data
        self._index = 0

    def skip(self, n: int):
        self.data = self.data[n:]
        return self

    def limit(self, n: int):
        self.data = self.data[:n]
        return self

    def sort(self, key: str, direction: int = 1):
        # Mock sorting simply by key (descending if direction < 0)
        reverse = direction < 0
        try:
            self.data = sorted(self.data, key=lambda x: x.get(key, ""), reverse=reverse)
        except Exception:
            pass
        return self

    async def to_list(self, length=None):
        if length is not None:
            return self.data[:length]
        return self.data

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.data):
            raise StopAsyncIteration
        val = self.data[self._index]
        self._index += 1
        return val


class MockCollection:
    def __init__(self, name: str):
        self.name = name
        self.docs = []

    async def find_one(self, query: dict):
        for d in self.docs:
            match = True
            for k, v in query.items():
                if isinstance(v, dict):
                    # handle subquery like $gte, $lte, $in
                    for sk, sv in v.items():
                        if sk == "$gte" and d.get(k, 0) < sv:
                            match = False
                        elif sk == "$lte" and d.get(k, 0) > sv:
                            match = False
                        elif sk == "$in" and d.get(k) not in sv:
                            match = False
                elif d.get(k) != v:
                    match = False
            if match:
                return d
        return None

    def find(self, query: dict):
        matched = []
        for d in self.docs:
            match = True
            for k, v in query.items():
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        if sk == "$gte" and d.get(k, 0) < sv:
                            match = False
                        elif sk == "$lte" and d.get(k, 0) > sv:
                            match = False
                        elif sk == "$in" and d.get(k) not in sv:
                            match = False
                elif d.get(k) != v:
                    match = False
            if match:
                matched.append(d)
        return MockCursor(matched)

    async def insert_one(self, doc: dict):
        self.docs.append(doc)
        return doc

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        doc = await self.find_one(query)
        if not doc:
            if upsert:
                doc = dict(query)
                self.docs.append(doc)
            else:
                return
        if "$set" in update:
            doc.update(update["$set"])

    async def count_documents(self, query: dict):
        matched = []
        for d in self.docs:
            match = True
            for k, v in query.items():
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        if sk == "$gte" and d.get(k, 0) < sv:
                            match = False
                        elif sk == "$lte" and d.get(k, 0) > sv:
                            match = False
                        elif sk == "$in" and d.get(k) not in sv:
                            match = False
                elif d.get(k) != v:
                    match = False
            if match:
                matched.append(d)
        return len(matched)


class MockCollections:
    def __init__(self):
        self._cols = {}

    def __getattr__(self, name: str):
        if name not in self._cols:
            self._cols[name] = MockCollection(name)
        return self._cols[name]

    def clear(self):
        for col in self._cols.values():
            col.docs.clear()


# Instantiate and patch mock collections globally
mock_collections = MockCollections()

@pytest.fixture(autouse=True)
def patch_db_collections():
    with patch("backend.nextgen.explainer_core.nx_collections", mock_collections), \
         patch("backend.nextgen.graph_service.nx_collections", mock_collections), \
         patch("backend.nextgen.explainer_service.nx_collections", mock_collections), \
         patch("backend.nextgen.routes.explanations.nx_collections", mock_collections):
        mock_collections.clear()
        yield


# --- Step 1: Core Mathematics, Confidence, and Trace Verification Tests ---

def test_confidence_math_rs_reliability():
    """Verify that different source types produce correct base reliability (Rs)."""
    # 1. Inspector / Engineer -> Rs = 1.00 (under 0 age/decay, consensus, complete)
    score, certainty = calculate_confidence("inspector", 0, "WATER_INTRUSION")
    assert score == 100.0
    assert certainty == "HIGH"

    # 2. Sensor -> Rs = 0.95
    score, certainty = calculate_confidence("sensor", 0, "WATER_INTRUSION")
    assert score == 95.0
    assert certainty == "HIGH"

    # 3. UAV -> Rs = 0.85
    score, certainty = calculate_confidence("uav", 0, "WATER_INTRUSION")
    assert score == 85.0
    assert certainty == "HIGH"

    # 4. Homeowner -> Rs = 0.40
    score, certainty = calculate_confidence("homeowner", 0, "WATER_INTRUSION")
    assert score == 40.0
    assert certainty == "LOW"

    # 5. Missing -> Rs = 0.00
    score, certainty = calculate_confidence("missing", 0, "WATER_INTRUSION")
    assert score == 0.0
    assert certainty == "UNKNOWN"


def test_confidence_math_temporal_decay():
    """Verify exponential temporal decay math for fast, medium, slow systems."""
    # Fast-changing system (WATER_INTRUSION), lambda = 0.0038
    # age = 180 days -> D_t = e^(-0.0038 * 180) ~= 0.504
    # Rs = 1.00, consensus, complete
    score, certainty = calculate_confidence("inspector", 180, "WATER_INTRUSION")
    expected = 1.00 * math.exp(-0.0038 * 180) * 1.00 * 1.00 * 100.0
    assert abs(score - expected) < 1.0
    assert certainty == "MEDIUM"

    # Medium-changing system (ROOF), lambda = 0.00095
    # age = 730 days -> D_t = e^(-0.00095 * 730) ~= 0.50
    score, certainty = calculate_confidence("inspector", 730, "ROOF")
    expected = 1.00 * math.exp(-0.00095 * 730) * 1.00 * 1.00 * 100.0
    assert abs(score - expected) < 1.0


def test_confidence_math_conflict_and_coverage():
    """Verify multipliers for conflicts and coverage weight."""
    # Minor conflict (0.85) and complete coverage
    score, certainty = calculate_confidence("sensor", 0, "WATER_INTRUSION", conflict_level="minor_conflict")
    # Rs = 0.95, Fc = 0.85, Wc = 1.00 -> 0.95 * 0.85 * 100 = 80.75 -> 80.8%
    assert score == 80.8
    assert certainty == "HIGH"

    # Major conflict (0.50) and partial scan (0.50)
    score, certainty = calculate_confidence("inspector", 0, "WATER_INTRUSION", conflict_level="major_conflict", coverage="partial")
    # Rs = 1.00, Fc = 0.50, Wc = 0.50 -> 1.00 * 0.50 * 0.50 * 100 = 25.0%
    assert score == 25.0
    assert certainty == "LOW"


@pytest.mark.asyncio
async def test_trace_verification_ledger_chain():
    """Verify the trace verification algorithm rejects tampered ledger steps."""
    # Seed passport and entries
    passport_id = "pass_123"
    entry_id = "entry_123"
    await mock_collections.passport_entries.insert_one({
        "canonical_id": entry_id,
        "entry_type": "INTELLIGENCE_APPROVED",
        "status": "APPROVED",
        "payload": {"finding_id": "find_1"}
    })

    # Prepare complete trace
    explanation = {
        "evidence_trace": {
            "origin_mission_ids": ["msn_1"],
            "evidence_ids": ["ev_1"],
            "passport_entry_ids": [entry_id],
            "dna_nodes_referenced": ["roof.shingles"],
            "knowledge_graph_paths": ["A --[DRAINS]--> B"],
            "applicable_standards": ["IRC 2021"]
        },
        "levels": {
            "level_4": {
                "evidence_chain_ledger": [
                    {
                        "step_index": 0,
                        "source_type": "MISSION",
                        "reference_id": "msn_1",
                        "fact_snapshot": {"status": "completed"},
                        "payload_hash": "sha256:2fa3b8ce8fdbfbfe30d9cb52b3112a97cf1e95ec8fc4b96796245037d6ec8f67" # calculated correctly in compile
                    }
                ]
            }
        }
    }

    # Correct running hash calculation for single step
    import json
    import hashlib
    snapshot = json.dumps({"status": "completed"}, sort_keys=True)
    step_payload = f"0:MISSION:msn_1:{snapshot}:"
    correct_hash = hashlib.sha256(step_payload.encode()).hexdigest()
    explanation["levels"]["level_4"]["evidence_chain_ledger"][0]["payload_hash"] = f"sha256:{correct_hash}"

    # Verify original is valid
    assert await verify_explanation_trace(explanation) is True

    # Tamper with the fact snapshot -> must raise TraceValidationError
    explanation["levels"]["level_4"]["evidence_chain_ledger"][0]["fact_snapshot"]["status"] = "tampered!"
    with pytest.raises(TraceValidationError) as excinfo:
        await verify_explanation_trace(explanation)
    assert "compromised" in str(excinfo.value)


# --- Step 2: Property Knowledge Graph (PKG) Service Tests ---

@pytest.mark.asyncio
async def test_pkg_supreme_engineering_law_guardrail():
    """Verify that edges can only cite APPROVED evidence from the Passport."""
    property_id = "prop_green"
    evidence_id = "ev_approved"

    # Seed Passport for prop_green
    await mock_collections.passports.insert_one({
        "canonical_id": "pass_green",
        "property_id": property_id,
        "status": "active"
    })

    # Try creating edge when evidence is NOT approved -> raises ValueError
    with pytest.raises(ValueError) as excinfo:
        await create_edge(property_id, "ROOF_VALLEY", "ATTIC_RAFTERS", "DRAINS_TO", evidence_id)
    assert "Supreme Engineering Law" in str(excinfo.value)

    # Approve finding with this evidence
    await mock_collections.passport_entries.insert_one({
        "canonical_id": "entry_green_1",
        "passport_id": "pass_green",
        "entry_type": "INTELLIGENCE_APPROVED",
        "payload": {"finding_id": "find_green_1"}
    })
    await mock_collections.findings.insert_one({
        "canonical_id": "find_green_1",
        "property_id": property_id,
        "status": "APPROVED",
        "evidence_ids": [evidence_id]
    })

    # Create edge now -> must succeed
    edge = await create_edge(property_id, "ROOF_VALLEY", "ATTIC_RAFTERS", "DRAINS_TO", evidence_id)
    assert edge["from_node"] == "ROOF_VALLEY"
    assert edge["to_node"] == "ATTIC_RAFTERS"
    assert edge["relationship"] == "DRAINS_TO"


@pytest.mark.asyncio
async def test_pkg_acyclic_pathfinding_traversal():
    """Verify finding connections up to 5 hops depth."""
    property_id = "prop_castle"
    evidence_id = "ev_good"

    # Approve evidence
    await mock_collections.passports.insert_one({"canonical_id": "pass_castle", "property_id": property_id, "status": "active"})
    await mock_collections.passport_entries.insert_one({
        "canonical_id": "entry_castle",
        "passport_id": "pass_castle",
        "entry_type": "INTELLIGENCE_APPROVED",
        "payload": {"finding_id": "find_castle"}
    })
    await mock_collections.findings.insert_one({
        "canonical_id": "find_castle",
        "property_id": property_id,
        "status": "APPROVED",
        "evidence_ids": [evidence_id]
    })

    # Create connected systems: A -> B -> C -> D -> E
    await create_edge(property_id, "A", "B", "DRAINS_TO", evidence_id)
    await create_edge(property_id, "B", "C", "TOUCHES", evidence_id)
    await create_edge(property_id, "C", "D", "LEAKS_INTO", evidence_id)
    await create_edge(property_id, "D", "E", "SPOILS", evidence_id)

    # Resolve path from A to E (4 hops)
    path = await find_path(property_id, "A", "E")
    assert len(path) == 4
    assert path[0] == "A --[DRAINS_TO]--> B"
    assert path[1] == "B --[TOUCHES]--> C"
    assert path[2] == "C --[LEAKS_INTO]--> D"
    assert path[3] == "D --[SPOILS]--> E"


# --- Step 3: Explainer Pipeline & Template Engine Tests ---

@pytest.mark.asyncio
async def test_compilation_pipeline_success():
    """Verify compilation produces valid snapshots and respects low confidence actions."""
    property_id = "prop_palace"
    tenant_id = "tenant_hq"
    user_id = "usr_pilot"

    # Seed DNA
    await mock_collections.property_dna.insert_one({
        "property_id": property_id,
        "tenant_id": tenant_id,
        "version": 14
    })

    # Seed approved finding with low confidence source (homeowner)
    finding_id = "find_wet"
    passport_entry_id = "pass_entry_wet"
    await mock_collections.passport_entries.insert_one({
        "canonical_id": passport_entry_id,
        "passport_id": "pass_prop_palace",
        "entry_type": "INTELLIGENCE_APPROVED",
        "status": "APPROVED",
        "payload": {"status": "APPROVED"}
    })
    await mock_collections.findings.insert_one({
        "canonical_id": finding_id,
        "property_id": property_id,
        "tenant_id": tenant_id,
        "status": "APPROVED",
        "taxonomy_category": "WATER_INTRUSION",
        "manual_observation": True, # triggers homeowner source weight
        "severity": "MODERATE",
        "description": "Continuous leak in attic corner rafters",
        "evidence_ids": ["ev_damp_sensor_99"],
        "passport_entry_id": passport_entry_id,
        "passport_seq": 5
    })

    # Compile explanation snapshot
    exp = await compile_explanation(property_id, tenant_id, "WATER_INTRUSION", user_id, bypass_cache=True)
    
    assert exp["property_id"] == property_id
    assert exp["system_category"] == "WATER_INTRUSION"
    # Homeowner source Rs = 0.40 -> Confidence is Low (40%)
    assert exp["overall_confidence_score"] == 40.0
    assert exp["certainty_level"] == "LOW"

    # Low confidence must trigger automatic action-bind: "Schedule a certified field verification mission" as very first next step
    l1 = exp["levels"]["level_1"]
    assert l1["recommended_next_steps"][0] == "Schedule a certified field verification mission"


@pytest.mark.asyncio
async def test_compilation_pipeline_degraded_fallback():
    """Verify fallback degraded snap when zero findings are approved."""
    property_id = "prop_empty"
    tenant_id = "tenant_hq"
    user_id = "usr_pilot"

    exp = await compile_explanation(property_id, tenant_id, "WATER_INTRUSION", user_id, bypass_cache=True)
    
    assert exp["overall_confidence_score"] == 0.0
    assert exp["certainty_level"] == "UNKNOWN"
    assert "No active observations" in exp["levels"]["level_1"]["conclusion"]
    assert exp["levels"]["level_1"]["recommended_next_steps"] == ["Schedule a certified field verification mission"]


# --- Step 4: FastAPI Router Integration & RBAC Tests ---

@pytest.mark.asyncio
async def test_fastapi_endpoints_rbac_restrictions():
    """Verify that homeowners are prevented from accessing Level 3 or 4 technical details."""
    tenant_id = "tenant_abc"
    explanation_id = "expl_992"

    # Seed compiled explanation
    await mock_collections.explanations.insert_one({
        "explanation_id": explanation_id,
        "property_id": "prop_99",
        "tenant_id": tenant_id,
        "system_category": "WATER_INTRUSION",
        "overall_confidence_score": 92.5,
        "levels": {
            "level_1": {"conclusion": "Leak found"},
            "level_2": {"conclusion": "Contractor finding"},
            "level_3": {"conclusion": "Engineering finding"},
            "level_4": {"evidence_chain_ledger": []}
        }
    })

    # Mock NxSession for Homeowner
    homeowner_session = NxSession(
        user={"id": "u_home", "role": "homeowner"},
        tenant={"canonical_id": tenant_id}
    )

    # 1. Homeowner fetches without specific level -> must filter out levels 2, 3, 4
    res = await get_explanation_by_id(explanation_id, level=None, session=homeowner_session)
    assert "level_1" in res["levels"]
    assert "level_2" not in res["levels"]
    assert "level_3" not in res["levels"]
    assert "level_4" not in res["levels"]
    assert "evidence_trace" not in res  # Stripped for homeowner

    # 2. Homeowner requests Level 3 -> must raise 403 Forbidden
    with pytest.raises(HTTPException) as excinfo:
        await get_explanation_by_id(explanation_id, level=3, session=homeowner_session)
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail["error_code"] == "INSUFFICIENT_ACCESS_ROLE"

    # 3. Homeowner queries list of explanations via POST -> must raise 403 Forbidden
    query_req = ExplainerQueryRequest(
        property_ids=["prop_99"],
        categories=["WATER_INTRUSION"]
    )
    with pytest.raises(HTTPException) as excinfo:
        await query_explanations(query_req, session=homeowner_session)
    assert excinfo.value.status_code == 403
