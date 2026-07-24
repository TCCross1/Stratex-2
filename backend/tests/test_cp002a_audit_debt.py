"""C-P-002A audit-debt closure tests.

FakeMongo evidence / simulated concurrency — not production transaction proof.
Covers: active Passport uniqueness, index readiness, idempotency fingerprint
completeness, conflict deduplication, property authorization helpers,
Intelligence publication consistency, module identity, bounded verification.
"""
from __future__ import annotations

import asyncio
import os
import secrets

import pytest
from fastapi import HTTPException

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_cp002a_unit")
os.environ["PASSPORT_TRANSACTIONS_AVAILABLE"] = "0"
os.environ.pop("PASSPORT_SEAL_REQUIRED", None)
os.environ.pop("APP_ENV", None)
os.environ.pop("PASSPORT_REQUIRE_INDEXES", None)

from nextgen import (  # noqa: E402
    approval_policy,
    auth as nx_auth,
    governed_publish_service,
    passport_conflicts,
    passport_indexes,
    passport_service,
    passport_verify,
)
from nextgen.passport_errors import (  # noqa: E402
    IdempotencyConflictError,
    IndexReadinessError,
    StaleExpectedStateError,
)
from nextgen.routes import passports as passport_routes  # noqa: E402
from fake_mongo import DuplicateKeyError, install_fake_collections  # noqa: E402


@pytest.fixture
def fake(monkeypatch):
    modules = [
        passport_service,
        passport_conflicts,
        passport_indexes,
        passport_verify,
        governed_publish_service,
        nx_auth,
        passport_routes,
    ]
    fc = install_fake_collections(monkeypatch, *modules)
    ver = "vtest"
    key = secrets.token_hex(32)
    monkeypatch.setenv("PASSPORT_SEAL_KEY_VERSION", ver)
    monkeypatch.setenv(f"PASSPORT_SEAL_KEY_{ver}", key)
    monkeypatch.delenv("PASSPORT_SEAL_REQUIRED", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("PASSPORT_REQUIRE_INDEXES", raising=False)
    monkeypatch.setenv("PASSPORT_TRANSACTIONS_AVAILABLE", "0")
    passport_indexes.set_index_readiness_for_tests(
        state=passport_indexes.STATE_NOT_INITIALIZED,
        checked_at=None,
        failed_index=None,
        error_classification=None,
        critical_failed=False,
    )
    return fc


async def _append(**kwargs):
    return await passport_service.append_entry(**kwargs)


# ── Phase 2: active Passport unique index ────────────────────────────────

@pytest.mark.asyncio
async def test_one_active_passport_succeeds(fake):
    report = await passport_indexes.ensure_passport_indexes()
    assert report["state"] == "READY"
    await fake.passports.insert_one({
        "canonical_id": "pp1", "tenant_id": "t1", "property_id": "p1",
        "status": "active",
    })
    await fake.passports.insert_one({
        "canonical_id": "pp2", "tenant_id": "t1", "property_id": "p2",
        "status": "active",
    })
    n = await fake.passports.count_documents({"status": "active"})
    assert n == 2


@pytest.mark.asyncio
async def test_second_active_passport_same_tenant_property_fails(fake):
    await passport_indexes.ensure_passport_indexes()
    await fake.passports.insert_one({
        "canonical_id": "pp1", "tenant_id": "t1", "property_id": "p1",
        "status": "active",
    })
    with pytest.raises(DuplicateKeyError):
        await fake.passports.insert_one({
            "canonical_id": "pp2", "tenant_id": "t1", "property_id": "p1",
            "status": "active",
        })


@pytest.mark.asyncio
async def test_archived_history_permitted_alongside_active(fake):
    await passport_indexes.ensure_passport_indexes()
    await fake.passports.insert_one({
        "canonical_id": "pp_old", "tenant_id": "t1", "property_id": "p1",
        "status": "archived",
    })
    await fake.passports.insert_one({
        "canonical_id": "pp_old2", "tenant_id": "t1", "property_id": "p1",
        "status": "superseded",
    })
    await fake.passports.insert_one({
        "canonical_id": "pp_active", "tenant_id": "t1", "property_id": "p1",
        "status": "active",
    })
    n = await fake.passports.count_documents({"property_id": "p1"})
    assert n == 3


@pytest.mark.asyncio
async def test_active_passport_tenant_and_property_isolation(fake):
    await passport_indexes.ensure_passport_indexes()
    await fake.passports.insert_one({
        "canonical_id": "a", "tenant_id": "t1", "property_id": "p1", "status": "active",
    })
    await fake.passports.insert_one({
        "canonical_id": "b", "tenant_id": "t2", "property_id": "p1", "status": "active",
    })
    await fake.passports.insert_one({
        "canonical_id": "c", "tenant_id": "t1", "property_id": "p2", "status": "active",
    })
    assert await fake.passports.count_documents({"status": "active"}) == 3


@pytest.mark.asyncio
async def test_active_index_creation_idempotent(fake):
    r1 = await passport_indexes.ensure_passport_indexes()
    r2 = await passport_indexes.ensure_passport_indexes()
    assert r1["ready"] and r2["ready"]
    assert "uniq_active_passport_per_tenant_property" in (
        r1["created"] + r1["existed"]
    )
    assert r2["created"] == []


@pytest.mark.asyncio
async def test_existing_duplicate_active_fails_index_safely(fake):
    await fake.passports.insert_one({
        "canonical_id": "d1", "tenant_id": "t1", "property_id": "p1", "status": "active",
    })
    await fake.passports.insert_one({
        "canonical_id": "d2", "tenant_id": "t1", "property_id": "p1", "status": "active",
    })
    report = await passport_indexes.ensure_passport_indexes()
    assert report["ready"] is False
    assert report["state"] == "FAILED"
    assert any(
        f["index"] == "uniq_active_passport_per_tenant_property" for f in report["failed"]
    )
    assert await fake.passports.count_documents({"status": "active"}) == 2
    dupes = await passport_indexes.probe_duplicate_active_passports()
    assert any(d["tenant_id_prefix"] == "t1"[:8] for d in dupes)


# ── Phase 3: critical index readiness ────────────────────────────────────

@pytest.mark.asyncio
async def test_successful_init_sets_ready(fake):
    report = await passport_indexes.ensure_passport_indexes()
    assert report["state"] == "READY"
    assert passport_indexes.indexes_are_ready()
    ready = passport_indexes.get_index_readiness()
    assert ready["state"] == "READY"
    assert "password" not in str(ready).lower()
    assert "mongodb://" not in str(ready).lower()


@pytest.mark.asyncio
async def test_critical_failure_sets_failed(fake):
    await fake.passport_entries.insert_one({
        "tenant_id": "t1", "passport_id": "pp", "seq": 1, "canonical_id": "e1",
    })
    await fake.passport_entries.insert_one({
        "tenant_id": "t1", "passport_id": "pp", "seq": 1, "canonical_id": "e2",
    })
    report = await passport_indexes.ensure_passport_indexes()
    assert report["state"] == "FAILED"
    assert report["critical_failed"] is True
    assert passport_indexes.get_index_readiness()["state"] == "FAILED"


@pytest.mark.asyncio
async def test_strict_publication_blocked_when_indexes_not_ready(fake, monkeypatch):
    passport_indexes.set_index_readiness_for_tests(
        state=passport_indexes.STATE_FAILED,
        failed_index="uniq_active_passport_per_tenant_property",
        error_classification="DUPLICATE_DATA_BLOCKS_UNIQUE_INDEX",
        critical_failed=True,
    )
    monkeypatch.setenv("PASSPORT_REQUIRE_INDEXES", "1")
    with pytest.raises(IndexReadinessError):
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u1",
            expected_revision=0, idempotency_key="k",
            require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_noncritical_index_failure_classified(fake):
    await fake.outbox_events.insert_one({"idempotency_key": "same", "canonical_id": "o1"})
    await fake.outbox_events.insert_one({"idempotency_key": "same", "canonical_id": "o2"})
    report = await passport_indexes.ensure_passport_indexes()
    assert report["ready"] is False
    assert report["state"] == "FAILED"
    outbox_fail = [f for f in report["failed"] if f["index"] == "uniq_outbox_idempotency_key"]
    assert outbox_fail
    assert outbox_fail[0]["critical"] is False


# ── Phase 4: complete idempotency fingerprint ────────────────────────────

@pytest.mark.asyncio
async def test_idempotency_same_request_duplicate(fake):
    r1 = await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-1",
        publication_context={"door": "intel"},
        require_expected_state=True,
    )
    r2 = await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-1",
        publication_context={"door": "intel"},
        require_expected_state=True,
    )
    assert r1["status"] == "COMMITTED"
    assert r2["status"] == "DUPLICATE_SAME_REQUEST"
    assert r2["entry"]["canonical_id"] == r1["entry"]["canonical_id"]


@pytest.mark.asyncio
async def test_idempotency_changed_publication_context_conflict(fake):
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-ctx",
        publication_context={"door": "intel"},
        require_expected_state=True,
    )
    with pytest.raises(IdempotencyConflictError):
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u1",
            expected_revision=0, idempotency_key="idem-ctx",
            publication_context={"door": "findings"},
            require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_idempotency_changed_expected_revision_conflict(fake):
    r = await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-rev",
        require_expected_state=True,
    )
    head = r["entry"]["content_hash"]
    with pytest.raises(IdempotencyConflictError):
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u1",
            expected_revision=1, expected_head_hash=head,
            idempotency_key="idem-rev",
            require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_idempotency_changed_expected_head_conflict(fake):
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, expected_head_hash=None,
        idempotency_key="idem-head",
        require_expected_state=True,
    )
    with pytest.raises(IdempotencyConflictError):
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u1",
            expected_revision=0, expected_head_hash="deadbeef",
            idempotency_key="idem-head",
            require_expected_state=True,
        )


@pytest.mark.asyncio
async def test_idempotency_changed_payload_conflict(fake):
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="idem-pay",
        require_expected_state=True,
    )
    with pytest.raises(IdempotencyConflictError):
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 2}, authored_by="u1",
            expected_revision=0, idempotency_key="idem-pay",
            require_expected_state=True,
        )


# ── Phase 5: conflict deduplication ──────────────────────────────────────

@pytest.mark.asyncio
async def test_three_identical_stale_retries_one_open_conflict(fake):
    await passport_indexes.ensure_passport_indexes()
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="ok",
        require_expected_state=True,
    )
    ids = []
    for i in range(3):
        with pytest.raises(StaleExpectedStateError) as ei:
            await _append(
                tenant_id="t1", property_id="p1", entry_type="X",
                payload={"stale": True}, authored_by="u1",
                expected_revision=0, idempotency_key=f"stale-{i}",
                require_expected_state=True,
            )
        ids.append(ei.value.conflict["conflict_id"])
    assert len(set(ids)) == 1
    n = await fake.passport_conflicts.count_documents({
        "tenant_id": "t1", "status": "OPEN",
    })
    assert n == 1
    conflict = await passport_conflicts.get_conflict(
        tenant_id="t1", conflict_id=ids[0],
    )
    assert conflict["duplicate_delivery_count"] >= 3


@pytest.mark.asyncio
async def test_concurrent_identical_stale_retries_one_conflict(fake):
    """Simulated concurrency (asyncio gather) — FakeMongo evidence."""
    await passport_indexes.ensure_passport_indexes()
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="base",
        require_expected_state=True,
    )

    async def stale(i):
        try:
            await _append(
                tenant_id="t1", property_id="p1", entry_type="X",
                payload={"stale": True}, authored_by="u1",
                expected_revision=0, idempotency_key=f"c-{i}",
                require_expected_state=True,
            )
            return None
        except StaleExpectedStateError as e:
            return e.conflict["conflict_id"]

    results = await asyncio.gather(*[stale(i) for i in range(10)])
    ids = [r for r in results if r]
    assert len(ids) == 10
    assert len(set(ids)) == 1
    n = await fake.passport_conflicts.count_documents({"status": "OPEN"})
    assert n == 1


@pytest.mark.asyncio
async def test_different_payload_fingerprint_new_conflict(fake):
    await passport_indexes.ensure_passport_indexes()
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="base",
        require_expected_state=True,
    )
    with pytest.raises(StaleExpectedStateError) as e1:
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"stale": 1}, authored_by="u1",
            expected_revision=0, idempotency_key="s1",
            require_expected_state=True,
        )
    with pytest.raises(StaleExpectedStateError) as e2:
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"stale": 2}, authored_by="u1",
            expected_revision=0, idempotency_key="s2",
            require_expected_state=True,
        )
    assert e1.value.conflict["conflict_id"] != e2.value.conflict["conflict_id"]
    assert await fake.passport_conflicts.count_documents({"status": "OPEN"}) == 2


@pytest.mark.asyncio
async def test_different_actual_head_creates_new_conflict(fake):
    await passport_indexes.ensure_passport_indexes()
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="base",
        require_expected_state=True,
    )
    with pytest.raises(StaleExpectedStateError) as e1:
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"stale": True}, authored_by="u1",
            expected_revision=0, idempotency_key="s1",
            require_expected_state=True,
        )
    # Advance head with a different successful append.
    prev = await fake.passports.find_one({"property_id": "p1", "tenant_id": "t1"})
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 2}, authored_by="u1",
        expected_revision=prev["revision"],
        expected_head_hash=prev["head_hash"],
        idempotency_key="advance",
        require_expected_state=True,
    )
    with pytest.raises(StaleExpectedStateError) as e2:
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"stale": True}, authored_by="u1",
            expected_revision=0, idempotency_key="s2",
            require_expected_state=True,
        )
    assert e1.value.conflict["conflict_id"] != e2.value.conflict["conflict_id"]
    assert e1.value.conflict["actual_revision"] != e2.value.conflict["actual_revision"]


@pytest.mark.asyncio
async def test_resolve_preserves_history_and_new_conflict_possible(fake):
    await passport_indexes.ensure_passport_indexes()
    await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="base",
        require_expected_state=True,
    )
    with pytest.raises(StaleExpectedStateError) as e1:
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"stale": True}, authored_by="u1",
            expected_revision=0, idempotency_key="s1",
            require_expected_state=True,
        )
    cid = e1.value.conflict["conflict_id"]
    await passport_conflicts.mark_conflict_status(
        tenant_id="t1", conflict_id=cid, status="REJECTED",
        reviewer="admin", resolution_reason="not applicable",
    )
    hist = await passport_conflicts.get_conflict(tenant_id="t1", conflict_id=cid)
    assert hist["status"] == "REJECTED"
    assert hist.get("attempted_request_fingerprint")
    with pytest.raises(StaleExpectedStateError) as e2:
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"stale": True}, authored_by="u1",
            expected_revision=0, idempotency_key="s2",
            require_expected_state=True,
        )
    assert e2.value.conflict["conflict_id"] != cid
    assert e2.value.conflict["status"] == "OPEN"
    assert await fake.passport_conflicts.count_documents({}) == 2


# ── Phase 6: property-level conflict authorization ───────────────────────

@pytest.mark.asyncio
async def test_authorize_property_same_tenant_ok(fake):
    await fake.properties.insert_one({
        "canonical_id": "p1", "tenant_id": "t1", "name": "Home",
    })
    session = nx_auth.NxSession(
        {"id": "u1", "role": "admin"},
        {"canonical_id": "t1"},
    )
    prop = await nx_auth.authorize_property(session, "p1")
    assert prop["canonical_id"] == "p1"


@pytest.mark.asyncio
async def test_authorize_property_cross_tenant_404(fake):
    await fake.properties.insert_one({
        "canonical_id": "p1", "tenant_id": "t1", "name": "Home",
    })
    session = nx_auth.NxSession(
        {"id": "u2", "role": "admin"},
        {"canonical_id": "t2"},
    )
    with pytest.raises(HTTPException) as ei:
        await nx_auth.authorize_property(session, "p1")
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_conflict_load_requires_property_auth(fake):
    await fake.properties.insert_one({
        "canonical_id": "p1", "tenant_id": "t1", "name": "Home",
    })
    await fake.passports.insert_one({
        "canonical_id": "pp1", "tenant_id": "t1", "property_id": "p1",
        "status": "active",
    })
    conflict = await passport_conflicts.create_conflict_record(
        tenant_id="t1", passport_id="pp1", property_id="p1",
        source_type="intel", source_id="i1",
        attempted_idempotency_key="k",
        attempted_expected_revision=0,
        attempted_expected_head_hash=None,
        actual_revision=1, actual_head_hash="abc",
        attempted_request_fingerprint="fp",
        actor="u1", actor_role="admin", correlation_id=None,
        conflict_reason="STALE_EXPECTED_STATE",
    )
    ok_session = nx_auth.NxSession(
        {"id": "u1", "role": "admin"}, {"canonical_id": "t1"},
    )
    loaded = await passport_routes._load_authorized_conflict(
        ok_session, conflict["conflict_id"],
    )
    assert loaded["conflict_id"] == conflict["conflict_id"]

    other = nx_auth.NxSession(
        {"id": "u9", "role": "admin"}, {"canonical_id": "t2"},
    )
    with pytest.raises(HTTPException) as ei:
        await passport_routes._load_authorized_conflict(other, conflict["conflict_id"])
    assert ei.value.status_code == 404

    contractor = nx_auth.NxSession(
        {"id": "c1", "role": "contractor"}, {"canonical_id": "t1"},
    )
    with pytest.raises(HTTPException) as ei2:
        await passport_routes._load_authorized_conflict(
            contractor, conflict["conflict_id"],
        )
    assert ei2.value.status_code == 404


@pytest.mark.asyncio
async def test_mismatched_passport_property_rejected(fake):
    await fake.properties.insert_one({
        "canonical_id": "p1", "tenant_id": "t1", "name": "A",
    })
    await fake.properties.insert_one({
        "canonical_id": "p2", "tenant_id": "t1", "name": "B",
    })
    await fake.passports.insert_one({
        "canonical_id": "pp1", "tenant_id": "t1", "property_id": "p1",
        "status": "active",
    })
    conflict = await passport_conflicts.create_conflict_record(
        tenant_id="t1", passport_id="pp1", property_id="p2",
        source_type="intel", source_id="i1",
        attempted_idempotency_key="k",
        attempted_expected_revision=0,
        attempted_expected_head_hash=None,
        actual_revision=1, actual_head_hash="abc",
        attempted_request_fingerprint="fp2",
        actor="u1", actor_role="admin", correlation_id=None,
        conflict_reason="STALE_EXPECTED_STATE",
    )
    session = nx_auth.NxSession(
        {"id": "u1", "role": "admin"}, {"canonical_id": "t1"},
    )
    with pytest.raises(HTTPException) as ei:
        await passport_routes._load_authorized_conflict(session, conflict["conflict_id"])
    assert ei.value.status_code == 404


# ── Phase 7: Intelligence publication consistency ────────────────────────

def test_publication_failed_is_retryable_not_terminal():
    decision = approval_policy.evaluate_approval_policy(
        source_kind="intelligence",
        source={
            "state": "publication_failed",
            "tenant_id": "t1",
            "property_id": "p1",
            "risk_tier": "tier_2_contractor_review",
            "authored_by": "author1",
            "evidence_ids": ["e1"],
        },
        actor_id="reviewer1",
        actor_role="admin",
        tenant_id="t1",
        property_id="p1",
        require_evidence=True,
        expected_revision=1,
        expected_head_hash="abc",
        require_expected_state=True,
    )
    assert decision.allowed is True


def test_passport_committed_not_reapprovable():
    decision = approval_policy.evaluate_approval_policy(
        source_kind="intelligence",
        source={
            "state": "passport_committed",
            "tenant_id": "t1",
            "property_id": "p1",
            "risk_tier": "tier_2_contractor_review",
            "authored_by": "author1",
            "evidence_ids": ["e1"],
        },
        actor_id="reviewer1",
        actor_role="admin",
        tenant_id="t1",
        property_id="p1",
        require_evidence=True,
        expected_revision=1,
        expected_head_hash="abc",
        require_expected_state=True,
    )
    assert decision.allowed is False
    assert decision.code == "SOURCE_STATE_INVALID"


def test_self_approval_still_rejected():
    decision = approval_policy.evaluate_approval_policy(
        source_kind="intelligence",
        source={
            "state": "pending_review",
            "tenant_id": "t1",
            "property_id": "p1",
            "risk_tier": "tier_2_contractor_review",
            "created_by": "same_user",
            "author_id": "same_user",
            "evidence_ids": ["e1"],
        },
        actor_id="same_user",
        actor_role="admin",
        tenant_id="t1",
        property_id="p1",
        require_evidence=True,
        expected_revision=0,
        expected_head_hash=None,
        require_expected_state=True,
    )
    assert decision.allowed is False
    assert decision.code == "SEPARATION_OF_DUTIES"


def test_intelligence_route_no_plain_approved_before_publish():
    text = open(
        os.path.join(
            os.path.dirname(__file__), "..", "nextgen", "routes", "intelligence.py",
        ),
        encoding="utf-8",
    ).read()
    assert "passport_committed" in text
    assert "publication_failed" in text
    assert "Do NOT persist plain" in text


@pytest.mark.asyncio
async def test_committed_append_retry_no_duplicate(fake):
    """Crash/retry recovery via same idempotency key — FakeMongo evidence."""
    r1 = await governed_publish_service.governed_publish(
        tenant_id="t1", property_id="p1",
        source_type="intelligence", source_id="intel-1",
        entry_type="INTELLIGENCE_APPROVED",
        payload={"intelligence_id": "intel-1", "x": 1},
        actor_id="reviewer1", actor_role="admin",
        idempotency_key="intelligence.publish:intel-1",
        expected_revision=0, expected_head_hash=None,
    )
    r2 = await governed_publish_service.governed_publish(
        tenant_id="t1", property_id="p1",
        source_type="intelligence", source_id="intel-1",
        entry_type="INTELLIGENCE_APPROVED",
        payload={"intelligence_id": "intel-1", "x": 1},
        actor_id="reviewer1", actor_role="admin",
        idempotency_key="intelligence.publish:intel-1",
        expected_revision=0, expected_head_hash=None,
    )
    assert r2["status"] == "DUPLICATE_SAME_REQUEST" or (
        r2["entry"]["canonical_id"] == r1["entry"]["canonical_id"]
    )
    n = await fake.passport_entries.count_documents({"tenant_id": "t1"})
    assert n == 1


# ── Phase 8: publication module identity ─────────────────────────────────

def test_module_identity_is_real_runtime_module():
    assert governed_publish_service.MODULE_IDENTITY == "nextgen.governed_publish_service"
    assert "workflow." not in governed_publish_service.MODULE_IDENTITY
    import nextgen.governed_publish_service as mod
    assert mod.__name__ == "nextgen.governed_publish_service"
    assert callable(mod.governed_publish)


def test_no_second_publisher_module():
    import importlib.util
    try:
        spec = importlib.util.find_spec("workflow.governed_publish_service")
    except ModuleNotFoundError:
        spec = None
    assert spec is None
    # No compatibility duplicate under backend/workflow either.
    import os as _os
    assert not _os.path.isdir(
        _os.path.join(_os.path.dirname(__file__), "..", "workflow")
    )


# ── Phase 9: bounded chain verification ──────────────────────────────────

@pytest.mark.asyncio
async def test_chain_below_and_at_limit_valid(fake):
    r = await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"n": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="v1",
        require_expected_state=True,
    )
    pid = r["entry"]["passport_id"]
    for i in range(2, 6):
        prev = await fake.passports.find_one({"canonical_id": pid})
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"n": i}, authored_by="u1",
            expected_revision=prev["revision"],
            expected_head_hash=prev["head_hash"],
            idempotency_key=f"v{i}",
            require_expected_state=True,
        )
    report = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=pid, max_entries=5,
    )
    assert report["result"] in {"VALID", "VALID_WITH_LEGACY_UNSEALED_ENTRIES"}
    assert report["truncated"] is False
    assert report["inspected_count"] == 5


@pytest.mark.asyncio
async def test_chain_above_limit_incomplete(fake, monkeypatch):
    monkeypatch.setenv("PASSPORT_VERIFY_MAX_ENTRIES", "2")
    r = await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"n": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="b1",
        require_expected_state=True,
    )
    pid = r["entry"]["passport_id"]
    for i in range(2, 4):
        prev = await fake.passports.find_one({"canonical_id": pid})
        await _append(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"n": i}, authored_by="u1",
            expected_revision=prev["revision"],
            expected_head_hash=prev["head_hash"],
            idempotency_key=f"b{i}",
            require_expected_state=True,
        )
    report = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=pid,
    )
    assert report["result"] == "INCOMPLETE"
    assert report["truncated"] is True
    assert report["result"] != "VALID"
    assert report["reason"] == "PASSPORT_VERIFY_MAX_ENTRIES_EXCEEDED"


@pytest.mark.asyncio
async def test_malformed_zero_negative_limits_use_default(fake, monkeypatch):
    for bad in ("0", "-5", "nope"):
        monkeypatch.setenv("PASSPORT_VERIFY_MAX_ENTRIES", bad)
        assert passport_verify.verify_max_entries() == passport_verify.DEFAULT_VERIFY_MAX_ENTRIES
    monkeypatch.delenv("PASSPORT_VERIFY_MAX_ENTRIES", raising=False)
    assert passport_verify.verify_max_entries() == passport_verify.DEFAULT_VERIFY_MAX_ENTRIES


@pytest.mark.asyncio
async def test_verification_still_detects_alteration_and_readonly(fake):
    r = await _append(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"n": 1}, authored_by="u1",
        expected_revision=0, idempotency_key="alt",
        require_expected_state=True,
    )
    pid = r["entry"]["passport_id"]
    before = await fake.passport_entries.find_one({"passport_id": pid})
    await fake.passport_entries.update_one(
        {"canonical_id": before["canonical_id"]},
        {"$set": {"payload": {"n": 999}}},
    )
    report = await passport_verify.verify_passport_chain(
        tenant_id="t1", passport_id=pid,
    )
    assert report["result"] == "INVALID_ENTRY_HASH"
    after = await fake.passport_entries.find_one({"canonical_id": before["canonical_id"]})
    assert after["payload"]["n"] == 999
