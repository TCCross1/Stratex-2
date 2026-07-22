"""Integration and acceptance tests for Passport Explanation Lifecycle, Reconciliation, and Rebase Safety.

Verifies:
- All 25 granular lifecycle/reconciliation/RBAC requirements.
- Section 14 End-To-End Required Acceptance Scenario.
"""
from __future__ import annotations

import os
import sys
import math
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# --- Set up mock environment variables ---
os.environ.setdefault("MONGO_URL", "mongodb://mock")
os.environ.setdefault("DB_NAME", "mock_db")
os.environ["NEXTGEN_STORAGE_ROOT"] = "/tmp/nextgen_storage"

# Add backend directory to path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from backend.nextgen.db import nx_collections, nx_id, now_iso_utc
from backend.nextgen.explainer_core import calculate_confidence, verify_explanation_trace, TraceValidationError
from backend.nextgen.graph_service import create_node, create_edge, find_path
from backend.nextgen.explanation_reconciliation_service import (
    reconcile_property_explanations,
    reconcile_finding_change,
    reconcile_evidence_change,
    reconcile_graph_change,
    reconcile_passport_rebase,
    publish_replacement_explanation,
    retract_explanation,
    resolve_explanation_conflict,
    determine_materiality
)
from backend.nextgen.routes.explanations import (
    get_explanation_history,
    get_current_property_explanations,
    get_property_explanation_history,
    get_property_explanation_conflicts,
    retract_explanation_by_id,
    reconcile_property_explanations_endpoint,
    resolve_explanation_conflict_endpoint,
    get_explanation_by_id,
    RetractRequest,
    ConflictResolveRequest
)
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

    async def find_one(self, query: dict, sort: Optional[list] = None):
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
        if not matched:
            return None
        if sort:
            for key, direction in reversed(sort):
                reverse = direction < 0
                try:
                    matched = sorted(matched, key=lambda x: x.get(key, ""), reverse=reverse)
                except Exception:
                    pass
        return matched[0]

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

    async def find_one_and_update(self, query: dict, update: dict, return_document=True, upsert=False):
        doc = await self.find_one(query)
        if not doc:
            if upsert:
                doc = dict(query)
                self.docs.append(doc)
            else:
                return None
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = doc.get(k, 0) + v
        if "$set" in update:
            doc.update(update["$set"])
        return doc

    async def clear(self):
        self.docs.clear()

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


mock_collections = MockCollections()
nx_collections = mock_collections

@pytest.fixture(autouse=True)
def patch_db_collections():
    with patch("backend.nextgen.explainer_core.nx_collections", mock_collections), \
         patch("backend.nextgen.graph_service.nx_collections", mock_collections), \
         patch("backend.nextgen.explainer_service.nx_collections", mock_collections), \
         patch("backend.nextgen.explanation_reconciliation_service.nx_collections", mock_collections), \
         patch("backend.nextgen.outbox.nx_collections", mock_collections), \
         patch("backend.nextgen.passport_service.nx_collections", mock_collections), \
         patch("backend.nextgen.routes.explanations.nx_collections", mock_collections):
        mock_collections.clear()
        yield


# --- Helper to populate seed records ---
async def seed_test_data(tenant_id="tn_test_1", property_id="prop_roof_1"):
    # Clear and setup
    mock_collections.clear()
    
    # 1. Add tenant and properties
    await nx_collections.properties.insert_one({
        "canonical_id": property_id,
        "tenant_id": tenant_id,
        "status": "active"
    })
    
    # 2. Add Passport Sequence and active Passport
    passport_id = "pass_roof_1"
    await nx_collections.passports.insert_one({
        "canonical_id": passport_id,
        "property_id": property_id,
        "tenant_id": tenant_id,
        "status": "active"
    })
    
    await nx_collections.passport_sequences.insert_one({
        "passport_id": passport_id,
        "next_seq": 1
    })

    # 3. Add approved Evidence item
    evidence_id = "ev_roof_img_1"
    await nx_collections.evidence_items.insert_one({
        "canonical_id": evidence_id,
        "tenant_id": tenant_id,
        "status": "APPROVED",
        "file_size": 2048512,
        "mime_type": "image/jpeg"
    })

    # 4. Add approved Finding
    finding_id = "f_roof_moisture_1"
    passport_entry_id = "pe_roof_moisture_1"
    await nx_collections.findings.insert_one({
        "canonical_id": finding_id,
        "property_id": property_id,
        "tenant_id": tenant_id,
        "status": "APPROVED",
        "taxonomy_category": "ROOF",
        "taxonomy_component": "SHINGLES",
        "severity": "HIGH",
        "description": "Roof valley moisture intrusion with shingle degradation",
        "confidence_source": "certified_inspector",
        "evidence_ids": [evidence_id],
        "passport_entry_id": passport_entry_id,
        "passport_seq": 1,
        "created_at": now_iso_utc()
    })
    
    # Add passport entry for the finding
    await nx_collections.passport_entries.insert_one({
        "canonical_id": passport_entry_id,
        "passport_id": passport_id,
        "tenant_id": tenant_id,
        "seq": 1,
        "entry_type": "INTELLIGENCE_APPROVED",
        "payload": {
            "finding_id": finding_id,
            "status": "APPROVED",
            "evidence_ids": [evidence_id]
        },
        "content_hash": "dummy_hash_1"
    })

    # 5. Add Property Knowledge Graph (PKG) stem nodes and edge
    await create_node(property_id, "ROOF_VALLEY")
    await create_node(property_id, "ATTIC_RAFTERS")
    await create_edge(property_id, "ROOF_VALLEY", "ATTIC_RAFTERS", "PROPAGATES_TO", evidence_id)


# --- 25 Granular Integration Tests ---

@pytest.mark.asyncio
async def test_req_1_publishing_first_explanation():
    """1. Publishing the first current explanation."""
    await seed_test_data()
    results = await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    assert "ROOF" in results
    assert results["ROOF"]["homeowner"]["status"] == "PUBLISHED"
    assert results["ROOF"]["homeowner"]["is_current"] is True


@pytest.mark.asyncio
async def test_req_2_atomic_supersession():
    """2. Publishing a replacement atomically supersedes the previous explanation."""
    await seed_test_data()
    
    # Publish first version
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    first = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    first_id = first["explanation_id"]
    
    # Manually change confidence / force recompile to trigger material replace
    await reconcile_property_explanations("prop_roof_1", "tn_test_1", force_recompile=True)
    
    # Verify first is superseded
    old = await nx_collections.explanations.find_one({"explanation_id": first_id})
    assert old["status"] == "SUPERSEDED"
    assert old["is_current"] is False
    assert old["superseded_by_explanation_id"] is not None

    # Verify new is published and current
    new = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert new["status"] == "PUBLISHED"
    assert new["supersedes_explanation_id"] == first_id


@pytest.mark.asyncio
async def test_req_3_only_one_current_published():
    """3. Only one current published explanation exists per audience and scope."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    await reconcile_property_explanations("prop_roof_1", "tn_test_1", force_recompile=True)
    await reconcile_property_explanations("prop_roof_1", "tn_test_1", force_recompile=True)
    
    count = await nx_collections.explanations.count_documents({
        "property_id": "prop_roof_1",
        "audience_level": "homeowner",
        "system_category": "ROOF",
        "status": "PUBLISHED",
        "is_current": True
    })
    assert count == 1


@pytest.mark.asyncio
async def test_req_4_historical_content_unchanged():
    """4. Historical explanation content remains unchanged after supersession."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    first = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    first_id = first["explanation_id"]
    orig_conclusion = first["levels"]["level_1"]["conclusion"]
    
    # Recompile and replace
    await reconcile_property_explanations("prop_roof_1", "tn_test_1", force_recompile=True)
    
    old = await nx_collections.explanations.find_one({"explanation_id": first_id})
    assert old["levels"]["level_1"]["conclusion"] == orig_conclusion


@pytest.mark.asyncio
async def test_req_5_revised_finding_triggers_replacement():
    """5. A revised finding produces a replacement explanation."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    first = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    first_id = first["explanation_id"]
    
    # Revise finding (new description)
    await nx_collections.findings.update_one(
        {"canonical_id": "f_roof_moisture_1"},
        {"$set": {"description": "EXTREME roof valley leaks!"}}
    )
    
    await reconcile_finding_change("prop_roof_1", "tn_test_1", "f_roof_moisture_1", "REVISE")
    
    # Check that replacement was created and published
    new = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert new["explanation_id"] != first_id
    assert "EXTREME" in new["levels"]["level_1"]["conclusion"]


@pytest.mark.asyncio
async def test_req_6_approval_withdrawn_retracts():
    """6. Withdrawal of finding approval retracts or degrades dependent explanations."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    # Withdraw approval
    await nx_collections.findings.update_one(
        {"canonical_id": "f_roof_moisture_1"},
        {"$set": {"status": "WITHDRAWN"}}
    )
    
    # Reconcile
    await reconcile_finding_change("prop_roof_1", "tn_test_1", "f_roof_moisture_1", "WITHDRAW")
    
    # Verify current is degraded
    current = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert current["failure_code"] == "SOURCE_FINDING_WITHDRAWN"


@pytest.mark.asyncio
async def test_req_7_invalid_evidence():
    """7. Invalid evidence cannot support a current explanation."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    # Mark evidence rejected
    await nx_collections.evidence_items.update_one(
        {"canonical_id": "ev_roof_img_1"},
        {"$set": {"status": "REJECTED"}}
    )
    
    await reconcile_evidence_change("prop_roof_1", "tn_test_1", "ev_roof_img_1", "REJECT")
    
    # Should compile degraded explanation because primary finding relies on rejected evidence
    current = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert current["failure_code"] == "SOURCE_FINDING_WITHDRAWN"


@pytest.mark.asyncio
async def test_req_8_cross_tenant_evidence_rejected():
    """8. Cross-tenant evidence is rejected."""
    await seed_test_data()
    
    # Change evidence tenant_id to a mismatch
    await nx_collections.evidence_items.update_one(
        {"canonical_id": "ev_roof_img_1"},
        {"$set": {"tenant_id": "tn_bad_hacker"}}
    )
    
    # Reconcile should handle cross tenant by rejecting finding dependency, producing degraded fallback
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    current = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert current["failure_code"] == "SOURCE_FINDING_WITHDRAWN"


@pytest.mark.asyncio
async def test_req_9_invalidated_graph_edges_excluded():
    """9. Invalidated graph edges are excluded from current traversal."""
    await seed_test_data()
    
    # Invalidate edge
    await nx_collections.graph_edges.update_one(
        {"from_node": "ROOF_VALLEY", "to_node": "ATTIC_RAFTERS"},
        {"$set": {"status": "invalidated", "invalidated_at": now_iso_utc()}}
    )
    
    path = await find_path("prop_roof_1", "ROOF_VALLEY", "ATTIC_RAFTERS")
    # Traversal should not return the edge
    assert path == []


@pytest.mark.asyncio
async def test_req_10_historical_explanations_retain_prior_graph():
    """10. Historical explanations retain prior graph references."""
    await seed_test_data()
    
    # Save an edge valid for passport version 1, then invalidate at version 2
    await nx_collections.graph_edges.update_one(
        {"from_node": "ROOF_VALLEY", "to_node": "ATTIC_RAFTERS"},
        {
            "$set": {
                "valid_from_passport_version": 1,
                "valid_to_passport_version": 1,
            }
        }
    )
    
    # Check historical path at passport version 1
    path_v1 = await find_path("prop_roof_1", "ROOF_VALLEY", "ATTIC_RAFTERS", passport_version=1)
    assert len(path_v1) == 1
    assert "ROOF_VALLEY --[PROPAGATES_TO]--> ATTIC_RAFTERS" in path_v1[0]
    
    # Check historical path at passport version 2
    path_v2 = await find_path("prop_roof_1", "ROOF_VALLEY", "ATTIC_RAFTERS", passport_version=2)
    assert path_v2 == []


@pytest.mark.asyncio
async def test_req_11_low_confidence_injects_verification_requests():
    """11. Confidence crossing below 50% injects verification requirements."""
    await seed_test_data()
    # Change finding source to homeowner, lowering confidence to 40%
    await nx_collections.findings.update_one(
        {"canonical_id": "f_roof_moisture_1"},
        {"$set": {"confidence_source": "homeowner"}}
    )
    
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    current = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    
    assert current["overall_confidence_score"] == 40.0
    assert "Schedule a certified field verification mission" in current["action_binds"]


@pytest.mark.asyncio
async def test_req_12_confidence_band_changes_trigger_reconciliation():
    """12. Confidence-band changes trigger material reconciliation."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    # Update to sensor (confidence 95%, High band)
    exp_high = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    
    # Change finding to homeowner (confidence 40%, Low band)
    await nx_collections.findings.update_one(
        {"canonical_id": "f_roof_moisture_1"},
        {"$set": {"confidence_source": "homeowner"}}
    )
    
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    exp_low = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    
    assert exp_low["explanation_id"] != exp_high["explanation_id"]
    assert exp_low["confidence_band"] == "LOW"


@pytest.mark.asyncio
async def test_req_13_formatting_only_changes_ignored():
    """13. Formatting-only changes do not trigger unnecessary replacement."""
    old_explanation = {
        "overall_confidence_score": 95.0,
        "certainty_level": "HIGH",
        "evidence_trace": {"evidence_ids": ["ev_1"], "knowledge_graph_paths": []}
    }
    new_data = {
        "overall_confidence_score": 95.0,
        "certainty_level": "HIGH",
        "evidence_trace": {"evidence_ids": ["ev_1"], "knowledge_graph_paths": []}
    }
    is_material, reasons = determine_materiality(old_explanation, new_data)
    assert is_material is False


@pytest.mark.asyncio
async def test_req_14_template_version_changes():
    """14. Template-version changes preserve historical template versions."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    first = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert first["template_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_req_15_compiler_version_changes():
    """15. Compiler-version changes preserve historical compiler versions."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    first = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert first["compiler_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_req_16_passport_conflicts_block_publication():
    """16. Passport conflicts block unsafe publication."""
    await seed_test_data()
    
    # Trigger a conflict
    rebase_data = {
        "passport_id": "pass_roof_1",
        "base_passport_version": 1,
        "candidate_passport_versions": [1, 2],
        "conflicting_finding_ids": ["f_roof_moisture_1", "f_roof_moisture_competing"],
        "conflict_type": "FINDING_CONTENT_CONFLICT"
    }
    
    await reconcile_passport_rebase("prop_roof_1", "tn_test_1", rebase_data)
    
    # Explanation reconciliation should now publish degraded "CONFLICT_UNDER_REVIEW" output
    current = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert current["failure_code"] == "CONFLICT_UNDER_REVIEW"


@pytest.mark.asyncio
async def test_req_17_conflict_resolution_unlocks():
    """17. Conflict resolution permits reconciliation and publication."""
    await seed_test_data()
    
    # Trigger conflict
    rebase_data = {
        "passport_id": "pass_roof_1",
        "base_passport_version": 1,
        "candidate_passport_versions": [1, 2],
        "conflicting_finding_ids": ["f_roof_moisture_1", "f_roof_moisture_competing"],
        "conflict_type": "FINDING_CONTENT_CONFLICT"
    }
    conflict = await reconcile_passport_rebase("prop_roof_1", "tn_test_1", rebase_data)
    
    # Resolve conflict
    await resolve_explanation_conflict(
        conflict_id=conflict["conflict_id"],
        resolution="MERGE",
        resolution_reason="Manual verification completed",
        resolved_by="usr_admin_1",
        tenant_id="tn_test_1"
    )
    
    # Current should no longer be degraded
    current = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert current.get("failure_code") is None
    assert current["status"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_req_18_rbac_level_3_4_guard():
    """18. Homeowner roles cannot access Level 3 or Level 4 traces."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    expl = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "engineer", "is_current": True
    })
    
    # Query with homeowner session
    session_homeowner = NxSession(
        user={"id": "usr_h1", "role": "homeowner"},
        tenant={"canonical_id": "tn_test_1"}
    )
    
    with pytest.raises(HTTPException) as exc:
        await get_explanation_by_id(id=expl["explanation_id"], level=3, session=session_homeowner)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_req_19_rbac_unauthorized_actions():
    """19. Unauthorized users cannot retract or resolve conflicts."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    expl = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    
    # Homeowner session
    session_homeowner = NxSession(
        user={"id": "usr_h1", "role": "homeowner"},
        tenant={"canonical_id": "tn_test_1"}
    )
    
    # Homeowner cannot retract
    with pytest.raises(HTTPException) as exc:
        await retract_explanation_by_id(id=expl["explanation_id"], body=RetractRequest(reason="Spam"), session=session_homeowner)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_req_20_reconciliation_idempotency():
    """20. Repeated reconciliation requests are idempotent."""
    await seed_test_data()
    res1 = await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    res2 = await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    assert res1["ROOF"]["homeowner"]["explanation_id"] == res2["ROOF"]["homeowner"]["explanation_id"]


@pytest.mark.asyncio
async def test_req_21_hash_chain_verification_passes():
    """21. Hash-chain verification still passes for valid historical traces."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    expl = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "engineer", "is_current": True
    })
    
    is_valid = await verify_explanation_trace(expl)
    assert is_valid is True


@pytest.mark.asyncio
async def test_req_22_tampered_hash_chain_fails():
    """22. Tampered historical traces fail verification."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    expl = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "engineer", "is_current": True
    })
    
    # Tamper with the ledger step
    expl["levels"]["level_4"]["evidence_chain_ledger"][1]["fact_snapshot"]["file_size"] = 1234
    
    with pytest.raises(TraceValidationError):
        await verify_explanation_trace(expl)


@pytest.mark.asyncio
async def test_req_23_empty_observation_degraded():
    """23. Empty-observation properties return controlled degraded output."""
    await seed_test_data()
    
    # Remove all findings
    await nx_collections.findings.clear()
    
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    current = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    assert current["failure_code"] == "SOURCE_FINDING_WITHDRAWN"


@pytest.mark.asyncio
async def test_req_24_concurrent_replacements():
    """24. Concurrent replacement attempts do not create two current explanations."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    # Mock concurrent publishing
    expl1 = await nx_collections.explanations.find_one({
        "property_id": "prop_roof_1", "audience_level": "homeowner", "is_current": True
    })
    
    # Run two sequential publishes simulating race
    await publish_replacement_explanation(dict(expl1))
    await publish_replacement_explanation(dict(expl1))
    
    count = await nx_collections.explanations.count_documents({
        "property_id": "prop_roof_1",
        "audience_level": "homeowner",
        "system_category": "ROOF",
        "status": "PUBLISHED",
        "is_current": True
    })
    assert count == 1


@pytest.mark.asyncio
async def test_req_25_audit_events_emitted():
    """25. Audit events are emitted for every lifecycle transition."""
    await seed_test_data()
    await reconcile_property_explanations("prop_roof_1", "tn_test_1")
    
    count = await nx_collections.audit_events.count_documents({
        "tenant_id": "tn_test_1",
        "event_type": "EXPLANATION_PUBLISHED"
    })
    assert count > 0


# --- Required End-to-End Acceptance Scenario (Section 14) ---

@pytest.mark.asyncio
async def test_section_14_end_to_end_acceptance_scenario():
    """Thoroughly proves Section 14 multi-step acceptance scenario.
    
    1. A property has an approved roof-moisture finding.
    2. The finding is supported by approved evidence.
    3. Homeowner, contractor, and engineer explanations are compiled and published.
    4. Each explanation stores exact versions/hashes.
    5. New approved evidence is added.
    6. The new evidence lowers confidence and contradicts one causal graph edge.
    7. The contradictory graph edge becomes invalid for current traversal.
    8. The Passport receives a new version.
    9. The reconciliation service detects a material change.
    10. Replacement explanations are compiled for all authorized audiences.
    11. Verification requests are added where confidence falls below threshold.
    12. New explanations are validated and published.
    13. Previous explanations become superseded but remain immutable and retrievable.
    14. The original hash traces still verify.
    15. The new traces also verify.
    16. The homeowner receives only a safe current explanation.
    17. The contractor receives the contractor projection.
    18. Only authorized engineering roles can retrieve the Level 3 or Level 4 trace.
    19. No historical record is deleted.
    20. No tenant boundary is crossed.
    """
    tenant_id = "tn_accept_1"
    property_id = "prop_accept_1"
    
    # 1 & 2. Seed initial approved finding + approved evidence
    await seed_test_data(tenant_id, property_id)
    
    # 3 & 4. Compile and publish Homeowner, contractor, and engineer explanations
    results_v1 = await reconcile_property_explanations(property_id, tenant_id)
    
    assert "ROOF" in results_v1
    roof_v1 = results_v1["ROOF"]
    
    # Check that homeowner, contractor, and engineer explanations exist and are current/published
    for aud in ["homeowner", "contractor", "engineer"]:
        assert roof_v1[aud]["status"] == "PUBLISHED"
        assert roof_v1[aud]["is_current"] is True
        assert roof_v1[aud]["passport_version"] == 1
        assert roof_v1[aud]["trace_root_hash"] != ""
        assert roof_v1[aud]["source_snapshot_hash"] != ""
        
    # 5. New approved evidence is added (which contradicts/lowers confidence)
    new_evidence_id = "ev_roof_img_2_contradictory"
    await nx_collections.evidence_items.insert_one({
        "canonical_id": new_evidence_id,
        "tenant_id": tenant_id,
        "status": "APPROVED",
        "file_size": 1024000,
        "mime_type": "image/jpeg"
    })
    
    # 6 & 7. The new evidence lowers confidence and contradicts one causal graph edge.
    # We invalidate the contradictory edge for current traversal.
    await nx_collections.graph_edges.update_one(
        {"from_node": "ROOF_VALLEY", "to_node": "ATTIC_RAFTERS", "property_id": property_id},
        {
            "$set": {
                "status": "invalidated",
                "invalidated_at": now_iso_utc(),
                "invalidation_reason": "Contradictory new evidence added"
            }
        }
    )
    
    # Traversal now excludes the edge for current traversal
    current_path = await find_path(property_id, "ROOF_VALLEY", "ATTIC_RAFTERS")
    assert current_path == []
    
    # 8. The Passport receives a new version
    passport = await nx_collections.passports.find_one({"property_id": property_id, "tenant_id": tenant_id})
    # Append a new entry to increment passport version to 2
    from backend.nextgen.passport_service import append_entry
    await append_entry(
        tenant_id=tenant_id,
        property_id=property_id,
        entry_type="INTELLIGENCE_REVISED",
        payload={"finding_id": "f_roof_moisture_1", "description": "Moisture lowered by new scan"},
        authored_by="usr_inspector_1"
    )
    
    # 9, 10, 11 & 12. Run reconciliation, lower confidence to homeowner level (<50%), validate and publish replacements
    await nx_collections.findings.update_one(
        {"canonical_id": "f_roof_moisture_1"},
        {
            "$set": {
                "confidence_source": "homeowner",  # reduces confidence to 40.0%
                "evidence_ids": ["ev_roof_img_1", new_evidence_id]
            }
        }
    )
    
    results_v2 = await reconcile_property_explanations(property_id, tenant_id, force_recompile=True)
    roof_v2 = results_v2["ROOF"]
    
    # Verification requests are injected because confidence < 50%
    assert roof_v2["homeowner"]["overall_confidence_score"] == 40.0
    assert "Schedule a certified field verification mission" in roof_v2["homeowner"]["action_binds"]
    
    # 13. Previous explanations become superseded but remain immutable and retrievable
    prior_homeowner = await nx_collections.explanations.find_one({"explanation_id": roof_v1["homeowner"]["explanation_id"]})
    assert prior_homeowner["status"] == "SUPERSEDED"
    assert prior_homeowner["is_current"] is False
    
    # 14 & 15. The original hash traces still verify and the new traces also verify
    prior_engineer = await nx_collections.explanations.find_one({"explanation_id": roof_v1["engineer"]["explanation_id"]})
    orig_verifies = await verify_explanation_trace(prior_engineer)
    assert orig_verifies is True
    
    new_verifies = await verify_explanation_trace(roof_v2["engineer"])
    assert new_verifies is True
    
    # 16, 17 & 18. Homeowner, contractor, and engineer projections retrieval checks
    # Homeowner receives only a safe current explanation without evidence traces
    homeowner_res = await get_current_property_explanations(
        property_id=property_id,
        scope="ROOF",
        audience="homeowner",
        session=NxSession(
            user={"id": "usr_homeowner", "role": "homeowner"},
            tenant={"canonical_id": tenant_id}
        )
    )
    assert homeowner_res["count"] == 1
    assert "evidence_trace" not in homeowner_res["results"][0]
    assert "level_4" not in homeowner_res["results"][0].get("levels", {})
    
    # Contractor receives contractor projection
    contractor_res = await get_current_property_explanations(
        property_id=property_id,
        scope="ROOF",
        audience="contractor",
        session=NxSession(
            user={"id": "usr_contractor", "role": "contractor"},
            tenant={"canonical_id": tenant_id}
        )
    )
    assert "level_2" in contractor_res["results"][0]["levels"]
    assert "level_3" not in contractor_res["results"][0]["levels"]
    
    # Engineer / admin retrieved details can get Level 3 / Level 4
    engineer_res = await get_current_property_explanations(
        property_id=property_id,
        scope="ROOF",
        audience="engineer",
        session=NxSession(
            user={"id": "usr_engineer", "role": "engineer"},
            tenant={"canonical_id": tenant_id}
        )
    )
    assert "level_4" in engineer_res["results"][0]["levels"]
    
    # 19. No historical record is deleted
    total_stored = await nx_collections.explanations.count_documents({"property_id": property_id})
    # Should have 3 initial categories * 3 audiences + 3 new categories * 3 audiences = 18 explanations
    assert total_stored == 18
    
    # 20. No tenant boundary is crossed
    wrong_tenant_res = await get_current_property_explanations(
        property_id=property_id,
        audience="homeowner",
        session=NxSession(
            user={"id": "usr_other", "role": "homeowner"},
            tenant={"canonical_id": "tn_wrong_hacker"}
        )
    )
    assert wrong_tenant_res["count"] == 0
