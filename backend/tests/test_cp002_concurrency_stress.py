"""C-P-002 concurrency stress — deterministic simulated concurrency.

DISCLOSURE: These tests use asyncio gather against an in-memory FakeCollections
double. They prove logical invariants of the append/idempotency/conflict
machinery under interleaved coroutines. They are NOT production proof of
MongoDB replica-set transaction behavior under real multi-process load.
"""
from __future__ import annotations

import asyncio
import os
import secrets

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_cp002_unit")
os.environ["PASSPORT_TRANSACTIONS_AVAILABLE"] = "0"

from nextgen import governed_publish_service, passport_service  # noqa: E402
from nextgen.passport_errors import StaleExpectedStateError  # noqa: E402
from fake_mongo import install_fake_collections  # noqa: E402


@pytest.fixture
def fake(monkeypatch):
    fc = install_fake_collections(
        monkeypatch, passport_service, governed_publish_service,
    )
    # Also patch conflicts module used inside passport_service
    from nextgen import passport_conflicts
    monkeypatch.setattr(passport_conflicts, "nx_collections", fc)
    ver = "vstress"
    monkeypatch.setenv("PASSPORT_SEAL_KEY_VERSION", ver)
    monkeypatch.setenv(f"PASSPORT_SEAL_KEY_{ver}", secrets.token_hex(32))
    monkeypatch.setenv("PASSPORT_TRANSACTIONS_AVAILABLE", "0")
    monkeypatch.delenv("PASSPORT_REQUIRE_TRANSACTIONS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    return fc


@pytest.mark.asyncio
async def test_two_simultaneous_appends(fake):
    async def go(k):
        try:
            return await passport_service.append_entry(
                tenant_id="t1", property_id="p1", entry_type="X",
                payload={"k": k}, authored_by="u",
                expected_revision=0, idempotency_key=k,
                require_expected_state=True,
            )
        except StaleExpectedStateError as e:
            return e

    a, b = await asyncio.gather(go("a"), go("b"))
    statuses = []
    for r in (a, b):
        if isinstance(r, dict):
            statuses.append(r["status"])
        else:
            statuses.append("CONFLICT")
    assert statuses.count("COMMITTED") == 1
    assert statuses.count("CONFLICT") == 1
    assert await fake.passport_entries.count_documents({}) == 1


@pytest.mark.asyncio
async def test_ten_simultaneous_against_one_base(fake):
    async def go(i):
        try:
            return await passport_service.append_entry(
                tenant_id="t1", property_id="p1", entry_type="X",
                payload={"i": i}, authored_by="u",
                expected_revision=0, idempotency_key=f"k{i}",
                require_expected_state=True,
            )
        except StaleExpectedStateError as e:
            return e

    results = await asyncio.gather(*[go(i) for i in range(10)])
    committed = [r for r in results if isinstance(r, dict)]
    conflicts = [r for r in results if isinstance(r, StaleExpectedStateError)]
    assert len(committed) == 1
    assert len(conflicts) == 9
    seqs = [e["seq"] async for e in fake.passport_entries.find({})]
    assert seqs == [1]
    assert await fake.passport_conflicts.count_documents({}) == 9


@pytest.mark.asyncio
async def test_repeated_duplicate_delivery(fake):
    async def go():
        return await passport_service.append_entry(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u",
            expected_revision=0, idempotency_key="same",
            require_expected_state=True,
        )

    first = await go()
    assert first["status"] == "COMMITTED"
    results = await asyncio.gather(*[go() for _ in range(20)])
    assert all(r["status"] == "DUPLICATE_SAME_REQUEST" for r in results)
    assert await fake.passport_entries.count_documents({}) == 1
    assert await fake.passport_idempotency.count_documents({}) == 1


@pytest.mark.asyncio
async def test_concurrent_approval_same_source(fake):
    async def go():
        return await governed_publish_service.governed_publish(
            tenant_id="t1", property_id="p1",
            source_type="finding", source_id="f1",
            entry_type="INTELLIGENCE_APPROVED",
            payload={"finding_id": "f1"},
            actor_id="admin",
            idempotency_key="finding.publish:f1",
            expected_revision=0, expected_head_hash=None,
        )

    results = await asyncio.gather(*[go() for _ in range(8)], return_exceptions=True)
    committed = [r for r in results if isinstance(r, dict) and r["status"] == "COMMITTED"]
    dupes = [r for r in results if isinstance(r, dict) and r["status"] == "DUPLICATE_SAME_REQUEST"]
    # Exactly one committed entry; others duplicates or rare races.
    assert len(committed) + len(dupes) >= 1
    assert await fake.passport_entries.count_documents({}) == 1
    assert await fake.passport_idempotency.count_documents({}) == 1


@pytest.mark.asyncio
async def test_concurrent_different_sources_one_passport(fake):
    # Prepare passport, then barrier so all racers share one base revision.
    head = await passport_service.get_passport_head(tenant_id="t1", property_id="p1")
    assert head["revision"] == 0
    barrier = asyncio.Barrier(5)

    async def go(i):
        await barrier.wait()
        try:
            return await governed_publish_service.governed_publish(
                tenant_id="t1", property_id="p1",
                source_type="finding", source_id=f"f{i}",
                entry_type="INTELLIGENCE_APPROVED",
                payload={"finding_id": f"f{i}"},
                actor_id="admin",
                idempotency_key=f"finding.publish:f{i}",
                expected_revision=0,
                expected_head_hash=None,
            )
        except StaleExpectedStateError as e:
            return e

    results = await asyncio.gather(*[go(i) for i in range(5)])
    committed = [r for r in results if isinstance(r, dict) and r.get("status") == "COMMITTED"]
    conflicts = [r for r in results if isinstance(r, StaleExpectedStateError)]
    assert len(committed) == 1
    assert len(conflicts) == 4
    # Every loser queued
    assert await fake.passport_conflicts.count_documents({}) == 4
    # Head points at existing entry
    passport = await fake.passports.find_one({"property_id": "p1"})
    entry = await fake.passport_entries.find_one({"canonical_id": passport["head_entry_id"]})
    assert entry is not None
    assert entry["content_hash"] == passport["head_hash"]


@pytest.mark.asyncio
async def test_idempotent_retry_after_transient_failure(fake, monkeypatch):
    calls = {"n": 0}
    real_insert = fake.passport_entries.insert_one

    async def flaky_insert(doc, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return await real_insert(doc, **kwargs)

    monkeypatch.setattr(fake.passport_entries, "insert_one", flaky_insert)

    with pytest.raises(Exception):
        await passport_service.append_entry(
            tenant_id="t1", property_id="p1", entry_type="X",
            payload={"a": 1}, authored_by="u",
            expected_revision=0, idempotency_key="retry-1",
            require_expected_state=True,
        )
    # Failed must not be reported committed
    idem = await fake.passport_idempotency.find_one({"idempotency_key": "retry-1"})
    if idem:
        assert idem.get("commit_status") != "COMMITTED"

    # Reset head if partial — ensure clean retry path
    # (CAS may not have advanced if insert failed first)
    r = await passport_service.append_entry(
        tenant_id="t1", property_id="p1", entry_type="X",
        payload={"a": 1}, authored_by="u",
        expected_revision=0, idempotency_key="retry-1",
        require_expected_state=True,
    )
    assert r["status"] == "COMMITTED"
    assert await fake.passport_entries.count_documents({}) == 1
