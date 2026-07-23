"""C-P-002 focused tests — concurrency, idempotency, indexes, conflicts,
chain verification, sealing, approval policy, publication boundaries.

Uses an in-memory FakeCollections double (Mongo unavailable in this agent
environment). Simulated concurrency is disclosed as non-production proof.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
from typing import Any, Dict, List

import pytest

# Ensure NextGen imports can resolve MONGO_URL/DB_NAME asserts in db.py
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_cp002_unit")
os.environ["PASSPORT_TRANSACTIONS_AVAILABLE"] = "0"
os.environ.pop("PASSPORT_SEAL_REQUIRED", None)
os.environ.pop("APP_ENV", None)

from nextgen import (  # noqa: E402
    approval_policy,
    governed_publish_service,
    passport_conflicts,
    passport_indexes,
    passport_seal,
    passport_service,
    passport_verify,
)
from nextgen.passport_errors import (  # noqa: E402
    IdempotencyConflictError,
    MissingExpectedStateError,
    StaleExpectedStateError,
    TransactionUnavailableError,
)
from fake_mongo import DuplicateKeyError, FakeCollections, install_fake_collections  # noqa: E402


@pytest.fixture
def fake(monkeypatch):
    modules = [
        passport_service,
        passport_conflicts,
        passport_indexes,
        passport_verify,
        governed_publish_service,
    ]
    fc = install_fake_collections(monkeypatch, *modules)
    # Ephemeral seal keys for sealing tests (never committed secrets).
    ver = "vtest"
    key = secrets.token_hex(32)
    monkeypatch.setenv("PASSPORT_SEAL_KEY_VERSION", ver)
    monkeypatch.setenv(f"PASSPORT_SEAL_KEY_{ver}", key)
    monkeypatch.delenv("PASSPORT_SEAL_REQUIRED", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("PASSPORT_TRANSACTIONS_AVAILABLE", "0")
    return fc


async def _append(fake, **kwargs):
    return await passport_service.append_entry(**kwargs)


# ── Concurrency / OCC ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_append_at_current_revision_succeeds(fake):
    r = await _append(
        fake,
        tenant_id="t1", property_id="p1", entry_type="INTELLIGENCE_APPROVED",
        payload={"x": 1}, authored_by="u1",
        expected_revision=0, expected_head_hash=None,
        idempotency_key="k1", require_expected_state=True,
    )
    assert r["status"] == "COMMITTED"
    assert r["entry"]["seq"] == 1
    assert r["entry"]["revision"] == 1


@pytest.mark.asyncio
async def test_append_at_current_head_hash_succeeds(fake):
    r1 = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    head = r1["entry"]["content_hash"]
    r2 = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 2}, authored_by="u1",
        expected_revision=1, expected_head_hash=head,
        idempotency_key="b", require_expected_state=True,
    )
    assert r2["status"] == "COMMITTED"
    assert r2["entry"]["seq"] == 2


@pytest.mark.asyncio
async def test_stale_revision_returns_conflict(fake):
    await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    with pytest.raises(StaleExpectedStateError) as ei:
        await _append(
            fake, tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 2}, authored_by="u2",
            expected_revision=0, idempotency_key="b",
            require_expected_state=True,
        )
    assert ei.value.conflict["status"] == "OPEN"
    assert ei.value.conflict["attempted_expected_revision"] == 0
    assert ei.value.conflict["actual_revision"] == 1
    n = await fake.passport_entries.count_documents({"tenant_id": "t1"})
    assert n == 1


@pytest.mark.asyncio
async def test_stale_head_hash_returns_conflict(fake):
    r1 = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 2}, authored_by="u1",
        expected_revision=1, expected_head_hash=r1["entry"]["content_hash"],
        idempotency_key="b", require_expected_state=True,
    )
    with pytest.raises(StaleExpectedStateError):
        await _append(
            fake, tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 3}, authored_by="u2",
            expected_revision=2, expected_head_hash=r1["entry"]["content_hash"],
            idempotency_key="c", require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_missing_expected_state_rejected_for_governed(fake):
    with pytest.raises(MissingExpectedStateError):
        await _append(
            fake, tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u1",
            idempotency_key="a", require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_simultaneous_same_base_one_winner(fake):
    """Simulated concurrency (asyncio gather) — not production proof."""
    async def attempt(key):
        try:
            return await _append(
                fake, tenant_id="t1", property_id="p1", entry_type="X",
                payload={"k": key}, authored_by="u1",
                expected_revision=0, idempotency_key=key,
                require_expected_state=True,
            )
        except StaleExpectedStateError as e:
            return e

    results = await asyncio.gather(*[attempt(f"k{i}") for i in range(10)])
    committed = [r for r in results if isinstance(r, dict) and r.get("status") == "COMMITTED"]
    conflicts = [r for r in results if isinstance(r, StaleExpectedStateError)]
    assert len(committed) == 1
    assert len(conflicts) == 9
    n = await fake.passport_entries.count_documents({"tenant_id": "t1"})
    assert n == 1
    ccount = await fake.passport_conflicts.count_documents({"tenant_id": "t1"})
    assert ccount == 9


@pytest.mark.asyncio
async def test_tenant_and_property_isolation(fake):
    await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    r2 = await _append(
        fake, tenant_id="t2", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    assert r2["entry"]["tenant_id"] == "t2"
    assert r2["entry"]["seq"] == 1
    r3 = await _append(
        fake, tenant_id="t1", property_id="p2", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    assert r3["entry"]["property_id"] == "p2"


# ── Idempotency ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_same_request_returns_original(fake):
    r1 = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-1",
        require_expected_state=True,
    )
    r2 = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-1",
        require_expected_state=True,
    )
    assert r2["status"] == "DUPLICATE_SAME_REQUEST"
    assert r2["entry"]["canonical_id"] == r1["entry"]["canonical_id"]
    n = await fake.passport_entries.count_documents({"tenant_id": "t1"})
    assert n == 1


@pytest.mark.asyncio
async def test_reused_key_changed_content_rejected(fake):
    await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-1",
        require_expected_state=True,
    )
    with pytest.raises(IdempotencyConflictError):
        await _append(
            fake, tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 2}, authored_by="u1",
            expected_revision=1, idempotency_key="idem-1",
            require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_receipt_retains_original_result(fake):
    r = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-1",
        require_expected_state=True,
    )
    assert r["receipt"]["receipt_hash"] == r["entry"]["content_hash"]
    assert r["receipt"]["commit_status"] == "COMMITTED"
    assert r["receipt"]["idempotency_key"] == "idem-1"


# ── Indexes ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_index_definitions_include_required(fake):
    defs = passport_indexes.index_definitions()
    names = {d["name"] for d in defs}
    assert "uniq_tenant_passport_seq" in names
    assert "uniq_tenant_passport_idempotency_key" in names
    assert "idx_conflict_queue_lookup" in names


@pytest.mark.asyncio
async def test_index_creation_idempotent(fake):
    r1 = await passport_indexes.ensure_passport_indexes()
    r2 = await passport_indexes.ensure_passport_indexes()
    assert r1["ready"] is True
    assert r2["ready"] is True
    assert r2["created"] == []
    assert "uniq_tenant_passport_seq" in r2["existed"]


@pytest.mark.asyncio
async def test_conflicting_data_fails_unique_index_safely(fake):
    # Seed duplicate sequences without unique index first.
    await fake.passport_entries.insert_one({
        "tenant_id": "t1", "passport_id": "pp", "seq": 1, "canonical_id": "e1",
    })
    await fake.passport_entries.insert_one({
        "tenant_id": "t1", "passport_id": "pp", "seq": 1, "canonical_id": "e2",
    })
    report = await passport_indexes.ensure_passport_indexes()
    assert report["ready"] is False
    assert any(f["index"] == "uniq_tenant_passport_seq" for f in report["failed"])
    assert report["production_readiness"] == "NOT READY"
    # Historical duplicates untouched.
    n = await fake.passport_entries.count_documents({"passport_id": "pp"})
    assert n == 2


# ── Conflict / rebase ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_conflict_review_and_rebase(fake):
    await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    with pytest.raises(StaleExpectedStateError) as ei:
        await _append(
            fake, tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 2}, authored_by="u2",
            expected_revision=0, idempotency_key="stale-key",
            require_expected_state=True, source_type="finding", source_id="f1",
        )
    conflict = ei.value.conflict
    original_fp = conflict["attempted_request_fingerprint"]
    assert conflict["status"] == "OPEN"

    updated = await passport_conflicts.mark_conflict_status(
        tenant_id="t1", conflict_id=conflict["conflict_id"],
        status="UNDER_REVIEW", reviewer="admin1",
        resolution_reason="investigating",
    )
    assert updated["status"] == "UNDER_REVIEW"
    assert updated["attempted_request_fingerprint"] == original_fp

    head = await passport_service.get_passport_head(tenant_id="t1", property_id="p1")
    pub = await governed_publish_service.governed_publish(
        tenant_id="t1", property_id="p1",
        source_type="finding", source_id="f1",
        entry_type="INTELLIGENCE_APPROVED",
        payload={"a": 2, "rebased": True},
        actor_id="admin1", actor_role="admin",
        idempotency_key="rebase-new-key",
        expected_revision=head["revision"],
        expected_head_hash=head["head_hash"],
        publication_context={"rebase_of_conflict_id": conflict["conflict_id"]},
    )
    assert pub["status"] == "COMMITTED"
    final = await passport_conflicts.mark_conflict_status(
        tenant_id="t1", conflict_id=conflict["conflict_id"],
        status="REBASED", reviewer="admin1",
        resolution_reason="rebased against head",
        replacement_append_id=pub["entry"]["canonical_id"],
        rebased_idempotency_key="rebase-new-key",
    )
    # Original attempt provenance immutable.
    assert final["attempted_request_fingerprint"] == original_fp
    assert final["attempted_idempotency_key"] == "stale-key"
    assert final["replacement_append_id"] == pub["entry"]["canonical_id"]


def test_unauthorized_conflict_reviewer_role():
    assert passport_conflicts.role_may_review_conflicts("contractor") is False
    assert passport_conflicts.role_may_review_conflicts("admin") is True
    assert passport_conflicts.role_may_review_conflicts("ceo") is True
    assert passport_conflicts.role_may_review_conflicts("passport_reviewer") is True


# ── Chain verification + sealing ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_chain_and_legacy_unsealed(fake, monkeypatch):
    monkeypatch.delenv("PASSPORT_SEAL_KEY_VERSION", raising=False)
    r = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    report = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=r["passport"]["canonical_id"],
    )
    assert report["result"] in {
        "VALID", "VALID_WITH_LEGACY_UNSEALED_ENTRIES",
    }


@pytest.mark.asyncio
async def test_sealed_entry_verifies_and_wrong_key_fails(fake, monkeypatch):
    r = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    assert r["entry"]["seal_status"] == "SEALED"
    assert r["entry"]["signature_algorithm"] == "HMAC-SHA256"
    report = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=r["passport"]["canonical_id"],
    )
    assert report["result"] == "VALID"

    # Wrong key version material.
    monkeypatch.setenv("PASSPORT_SEAL_KEY_vtest", secrets.token_hex(32))
    report2 = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=r["passport"]["canonical_id"],
    )
    assert report2["result"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_altered_payload_detected(fake):
    r = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    # Mutate stored payload (simulating tampering) without rewriting via API.
    await fake.passport_entries.update_one(
        {"canonical_id": r["entry"]["canonical_id"]},
        {"$set": {"payload": {"a": 999}}},
    )
    report = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=r["passport"]["canonical_id"],
    )
    assert report["result"] == "INVALID_ENTRY_HASH"


@pytest.mark.asyncio
async def test_verification_does_not_mutate(fake):
    r = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    before = await fake.passport_entries.find_one(
        {"canonical_id": r["entry"]["canonical_id"]}
    )
    await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=r["passport"]["canonical_id"],
    )
    after = await fake.passport_entries.find_one(
        {"canonical_id": r["entry"]["canonical_id"]}
    )
    assert before == after


@pytest.mark.asyncio
async def test_duplicate_sequence_detected(fake):
    r = await _append(
        fake, tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="a",
        require_expected_state=True,
    )
    # Inject a duplicate seq row directly (bypass writer) to simulate corruption.
    bad = dict(r["entry"])
    bad["canonical_id"] = "injected"
    bad["content_hash"] = "deadbeef"
    # Temporarily no unique index
    fake._store.setdefault("passport_entries", []).append(bad)
    report = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=r["passport"]["canonical_id"],
    )
    assert report["result"] == "DUPLICATE_SEQUENCE"


@pytest.mark.asyncio
async def test_production_seal_required_fails_closed(fake, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PASSPORT_SEAL_KEY_VERSION", raising=False)
    monkeypatch.delenv("PASSPORT_SEAL_KEY_vtest", raising=False)
    with pytest.raises(Exception):
        await _append(
            fake, tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u1",
            expected_revision=0, idempotency_key="a",
            require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_transaction_unavailable_fails_closed_in_strict(fake, monkeypatch):
    monkeypatch.setenv("PASSPORT_REQUIRE_TRANSACTIONS", "1")
    monkeypatch.setenv("PASSPORT_TRANSACTIONS_AVAILABLE", "0")
    with pytest.raises(TransactionUnavailableError):
        await _append(
            fake, tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u1",
            expected_revision=0, idempotency_key="a",
            require_expected_state=True,
        )
    n = await fake.passport_entries.count_documents({})
    assert n == 0


# ── Approval policy ──────────────────────────────────────────────────────

def test_sod_blocks_author_across_privileged_roles():
    source = {
        "tenant_id": "t1", "property_id": "p1",
        "status": "PENDING_REVIEW", "author_id": "author1",
    }
    for role in ("admin", "ceo", "superadmin", "gm"):
        d = approval_policy.evaluate_approval_policy(
            source_kind="finding", source=source,
            actor_id="author1", actor_role=role,
            tenant_id="t1", property_id="p1",
            expected_revision=0, expected_head_hash=None,
        )
        assert d.allowed is False
        assert d.code == "SEPARATION_OF_DUTIES"


def test_intelligence_author_cannot_self_approve():
    source = {
        "tenant_id": "t1", "property_id": "p1",
        "state": "candidate", "created_by": "insp1",
        "inspector_user_id": "insp1",
        "risk_tier": "tier_2_contractor_review",
        "evidence_ids": ["e1"],
    }
    d = approval_policy.evaluate_approval_policy(
        source_kind="intelligence", source=source,
        actor_id="insp1", actor_role="admin",
        tenant_id="t1", property_id="p1",
        require_evidence=True,
        expected_revision=0, expected_head_hash=None,
    )
    assert d.allowed is False
    assert d.code == "SEPARATION_OF_DUTIES"


def test_eligible_separate_reviewer_can_approve():
    finding = {
        "tenant_id": "t1", "property_id": "p1",
        "status": "PENDING_REVIEW", "author_id": "author1",
    }
    d = approval_policy.evaluate_approval_policy(
        source_kind="finding", source=finding,
        actor_id="reviewer2", actor_role="admin",
        tenant_id="t1", property_id="p1",
        expected_revision=0, expected_head_hash=None,
    )
    assert d.allowed is True


def test_ineligible_role_rejected():
    finding = {
        "tenant_id": "t1", "property_id": "p1",
        "status": "PENDING_REVIEW", "author_id": "author1",
    }
    d = approval_policy.evaluate_approval_policy(
        source_kind="finding", source=finding,
        actor_id="c1", actor_role="contractor",
        tenant_id="t1", property_id="p1",
        expected_revision=0, expected_head_hash=None,
    )
    assert d.allowed is False
    assert d.code == "ROLE_INELIGIBLE"


def test_tenant_and_property_mismatch_rejected():
    finding = {
        "tenant_id": "t1", "property_id": "p1",
        "status": "PENDING_REVIEW", "author_id": "a",
    }
    d = approval_policy.evaluate_approval_policy(
        source_kind="finding", source=finding,
        actor_id="r", actor_role="admin",
        tenant_id="t2", property_id="p1",
        expected_revision=0,
    )
    assert d.code == "TENANT_MISMATCH"
    d2 = approval_policy.evaluate_approval_policy(
        source_kind="finding", source=finding,
        actor_id="r", actor_role="admin",
        tenant_id="t1", property_id="p9",
        expected_revision=0,
    )
    assert d2.code == "PROPERTY_MISMATCH"


def test_evidence_required_for_intelligence():
    source = {
        "tenant_id": "t1", "property_id": "p1",
        "state": "candidate", "created_by": "a",
        "risk_tier": "tier_2_contractor_review",
        "evidence_ids": [],
    }
    d = approval_policy.evaluate_approval_policy(
        source_kind="intelligence", source=source,
        actor_id="r", actor_role="admin",
        tenant_id="t1", property_id="p1",
        require_evidence=True, expected_revision=0,
    )
    assert d.code == "EVIDENCE_REQUIRED"


def test_policy_identity_stable():
    assert approval_policy.policy_identity() == (
        "nextgen.approval_policy.evaluate_approval_policy"
    )


# ── Publication via governed_publish ─────────────────────────────────────

@pytest.mark.asyncio
async def test_governed_publish_success_and_idempotent(fake):
    r1 = await governed_publish_service.governed_publish(
        tenant_id="t1", property_id="p1",
        source_type="finding", source_id="f1",
        entry_type="INTELLIGENCE_APPROVED",
        payload={"finding_id": "f1"},
        actor_id="admin1", actor_role="admin",
        idempotency_key="finding.publish:f1",
        expected_revision=0, expected_head_hash=None,
    )
    assert r1["status"] == "COMMITTED"
    r2 = await governed_publish_service.governed_publish(
        tenant_id="t1", property_id="p1",
        source_type="finding", source_id="f1",
        entry_type="INTELLIGENCE_APPROVED",
        payload={"finding_id": "f1"},
        actor_id="admin1", actor_role="admin",
        idempotency_key="finding.publish:f1",
        expected_revision=0, expected_head_hash=None,
    )
    assert r2["status"] == "DUPLICATE_SAME_REQUEST"
    n = await fake.passport_entries.count_documents({"tenant_id": "t1"})
    assert n == 1


@pytest.mark.asyncio
async def test_governed_publish_missing_expected_state(fake):
    with pytest.raises(MissingExpectedStateError):
        await governed_publish_service.governed_publish(
            tenant_id="t1", property_id="p1",
            source_type="finding", source_id="f1",
            entry_type="INTELLIGENCE_APPROVED",
            payload={"finding_id": "f1"},
            actor_id="admin1",
        )


@pytest.mark.asyncio
async def test_stale_governed_publish_creates_conflict(fake):
    await governed_publish_service.governed_publish(
        tenant_id="t1", property_id="p1",
        source_type="finding", source_id="f0",
        entry_type="INTELLIGENCE_APPROVED",
        payload={"finding_id": "f0"},
        actor_id="admin1",
        idempotency_key="finding.publish:f0",
        expected_revision=0, expected_head_hash=None,
    )
    with pytest.raises(StaleExpectedStateError) as ei:
        await governed_publish_service.governed_publish(
            tenant_id="t1", property_id="p1",
            source_type="finding", source_id="f1",
            entry_type="INTELLIGENCE_APPROVED",
            payload={"finding_id": "f1"},
            actor_id="admin1",
            idempotency_key="finding.publish:f1",
            expected_revision=0, expected_head_hash=None,
        )
    assert ei.value.conflict["status"] == "OPEN"


def test_no_default_seal_secret_in_source():
    text = open(
        os.path.join(os.path.dirname(__file__), "..", "nextgen", "passport_seal.py"),
        encoding="utf-8",
    ).read()
    assert "DEFAULT" not in text or "default production" not in text.lower()
    assert "sk_live" not in text
    assert "hmac_secret =" not in text
