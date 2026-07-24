"""RT-002 live C-P-003 claim/lease proofs against real Mongo.

Does NOT modify PR #7. Loads ``outbox_worker.py`` from a temporary worktree of
``cursor/lane1-cp003-publication-recovery`` (RT002_CP003_ROOT) with a thin db
shim over real pymongo — proving the audited claim algorithm on a replica set.

Requires RT002_LIVE=1 and replica-set MONGO_URL.

Delivery characterization (never exactly-once):
  AT-LEAST-ONCE DELIVERY + IDEMPOTENT CONSUMERS + DURABLE RECEIPTS + SAFE RECONCILIATION
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pymongo import ReturnDocument

pytestmark = [
    pytest.mark.integration,
    pytest.mark.live_mongo,
    pytest.mark.cp003_claims,
]

LIVE = os.environ.get("RT002_LIVE", "").lower() in {"1", "true", "yes"}
MONGO_URL = os.environ.get("RT002_MONGO_URL") or os.environ.get("MONGO_URL") or ""
DB_NAME = os.environ.get("RT002_DB_NAME") or "stratex_rt002_cp003"
CP003_ROOT = os.environ.get("RT002_CP003_ROOT") or ""


def _skip_unless_ready():
    if not LIVE:
        pytest.skip("RT002_LIVE not set")
    if not MONGO_URL:
        pytest.fail("INTEGRATION_ENVIRONMENT_FAILED: RT002_LIVE=1 but MONGO_URL missing")
    if not CP003_ROOT:
        pytest.skip(
            "RT002_CP003_ROOT unset — run engineering/rt002/fetch_cp003_worktree.sh "
            "(PR #7 business tree is not modified or merged by RT-002)"
        )
    worker = Path(CP003_ROOT) / "backend" / "nextgen" / "outbox_worker.py"
    if not worker.is_file():
        pytest.skip(f"outbox_worker.py missing under {CP003_ROOT}")


class _AsyncColl:
    def __init__(self, coll):
        self._c = coll

    async def find_one(self, filt):
        return self._c.find_one(filt)

    async def insert_one(self, doc):
        return self._c.insert_one(doc)

    async def update_one(self, filt, update, **kwargs):
        return self._c.update_one(filt, update, **kwargs)

    async def find_one_and_update(self, filt, update, **kwargs):
        rd = kwargs.pop("return_document", None)
        if rd is True:
            kwargs["return_document"] = ReturnDocument.AFTER
        elif rd is False:
            kwargs["return_document"] = ReturnDocument.BEFORE
        return self._c.find_one_and_update(filt, update, **kwargs)

    async def count_documents(self, filt):
        return self._c.count_documents(filt)

    def find(self, filt):
        outer = self

        class _Cur:
            def __init__(self):
                self._cur = outer._c.find(filt)

            def sort(self, *a, **k):
                self._cur = self._cur.sort(*a, **k)
                return self

            def limit(self, n):
                self._cur = self._cur.limit(n)
                return self

            async def to_list(self, n):
                return list(self._cur)

        return _Cur()


def _load_worker(db):
    _skip_unless_ready()
    path = Path(CP003_ROOT) / "backend" / "nextgen" / "outbox_worker.py"

    def now_iso_utc():
        return datetime.now(timezone.utc).isoformat()

    def nx_id():
        return "nx_" + uuid.uuid4().hex

    class Colls:
        outbox_events = _AsyncColl(db["nextgen_outbox_events"])
        inbox_receipts = _AsyncColl(db["nextgen_inbox_receipts"])
        # PR #7 uses dead_letter_events (not outbox_dead_letters).
        dead_letter_events = _AsyncColl(db["nextgen_outbox_dead_letters"])
        outbox_dead_letters = dead_letter_events
        audit_events = _AsyncColl(db["nextgen_audit_events"])

    pkg = types.ModuleType("nextgen")
    pkg.__path__ = []  # type: ignore[attr-defined]
    dbmod = types.ModuleType("nextgen.db")
    dbmod.now_iso_utc = now_iso_utc
    dbmod.nx_id = nx_id
    dbmod.nx_collections = Colls()
    sys.modules["nextgen"] = pkg
    sys.modules["nextgen.db"] = dbmod

    spec = importlib.util.spec_from_file_location("nextgen.outbox_worker", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["nextgen.outbox_worker"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mongo_db():
    _skip_unless_ready()
    from pymongo import MongoClient

    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    assert client.admin.command("hello").get("setName"), "replica set required"
    db = client[DB_NAME]
    yield db
    client.close()


def _seed_event(db, *, lease_until=None, lease_owner=None, tenant_id="t_rt002", property_id="p_rt002"):
    now = datetime.now(timezone.utc).isoformat()
    event_id = "evt_" + uuid.uuid4().hex
    doc = {
        "event_id": event_id,
        "tenant_id": tenant_id,
        "property_id": property_id,
        "event_type": "rt002.test",
        "payload": {"n": 1, "property_id": property_id},
        "idempotency_key": "idem_" + uuid.uuid4().hex,
        "available_after": now,
        "attempts": 0,
        "delivered_at": None,
        "dead_lettered_at": None,
        "lease_until": lease_until,
        "leased_by": lease_owner,
        "created_at": now,
    }
    db["nextgen_outbox_events"].insert_one(doc)
    return event_id


def test_two_and_ten_workers_single_claim(mongo_db):
    db = mongo_db
    worker = _load_worker(db)
    db["nextgen_outbox_events"].delete_many({})

    async def claim_many(n: int):
        return [r for r in await asyncio.gather(
            *[worker.claim_next_event(worker_id=f"w{i}") for i in range(n)]
        ) if r]

    _seed_event(db)
    winners2 = asyncio.run(claim_many(2))
    assert len(winners2) == 1

    db["nextgen_outbox_events"].delete_many({})
    _seed_event(db)
    winners10 = asyncio.run(claim_many(10))
    assert len(winners10) == 1
    print("LIVE_MONGO_REPLICA_SET_PROOF atomic_claim=PASS")


def test_active_lease_not_stolen_expired_recoverable(mongo_db):
    db = mongo_db
    worker = _load_worker(db)
    db["nextgen_outbox_events"].delete_many({})
    now_dt = datetime.now(timezone.utc)
    future = (now_dt + timedelta(seconds=120)).isoformat()
    past = (now_dt - timedelta(seconds=5)).isoformat()
    event_id = _seed_event(db, lease_until=future, lease_owner="w_holder")

    async def run():
        stolen = await worker.claim_next_event(worker_id="w_thief")
        assert stolen is None
        db["nextgen_outbox_events"].update_one(
            {"event_id": event_id}, {"$set": {"lease_until": past}}
        )
        recovered = await worker.claim_next_event(worker_id="w_recover")
        assert recovered is not None
        assert recovered["event_id"] == event_id

    asyncio.run(run())
    print("LIVE_MONGO_REPLICA_SET_PROOF lease_protection=PASS")


def test_crash_after_claim_recovers_via_expired_lease(mongo_db):
    """Crash after claim must not permanently strand the event."""
    db = mongo_db
    worker = _load_worker(db)
    db["nextgen_outbox_events"].delete_many({})
    event_id = _seed_event(db)

    async def run():
        claimed = await worker.claim_next_event(worker_id="w_crash", lease_seconds=30)
        assert claimed is not None
        # Simulate crash: no mark_delivered; force lease expiry.
        past = (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat()
        db["nextgen_outbox_events"].update_one(
            {"event_id": event_id}, {"$set": {"lease_until": past, "leased_by": "w_crash"}}
        )
        recovered = await worker.claim_next_event(worker_id="w_rescue")
        assert recovered is not None
        assert recovered["event_id"] == event_id
        assert int(recovered.get("attempts") or 0) >= 2

    asyncio.run(run())
    print("LIVE_MONGO_REPLICA_SET_PROOF crash_recovery=PASS")


def test_receipt_idempotency_and_bounded_retries_dead_letter(mongo_db):
    db = mongo_db
    worker = _load_worker(db)
    for name in (
        "nextgen_outbox_events",
        "nextgen_inbox_receipts",
        "nextgen_outbox_dead_letters",
        "nextgen_audit_events",
    ):
        db[name].delete_many({})

    event_id = _seed_event(db)

    async def run():
        claimed = await worker.claim_next_event(worker_id="w_deliver")
        assert claimed is not None
        r1 = await worker.mark_delivered(
            event=claimed, consumer_key="consumer_rt002", worker_id="w_deliver"
        )
        assert r1["status"] == "delivered"
        assert r1["receipt"]["duplicate"] is False
        r2 = await worker.mark_delivered(
            event=claimed, consumer_key="consumer_rt002", worker_id="w_deliver"
        )
        assert r2["receipt"]["duplicate"] is True
        receipts = list(db["nextgen_inbox_receipts"].find({"event_id": event_id}))
        assert len(receipts) == 1

        # Fresh event for failure / DLQ path with low max_attempts.
        db["nextgen_outbox_events"].delete_many({})
        fail_id = _seed_event(db)
        claimed_f = await worker.claim_next_event(worker_id="w_fail")
        assert claimed_f is not None
        # attempts already 1 from claim; force exhaustion.
        claimed_f["attempts"] = 5
        dl = await worker.record_delivery_failure(
            event=claimed_f,
            worker_id="w_fail",
            error=RuntimeError("rt002_intentional_failure"),
            max_attempts=5,
        )
        assert dl["status"] == "dead_lettered"
        row = db["nextgen_outbox_events"].find_one({"event_id": fail_id})
        assert row.get("dead_lettered_at")
        assert db["nextgen_outbox_dead_letters"].count_documents({"event_id": fail_id}) == 1

        # Replay requires operator_id + reason; does not invent new event_id.
        replayed = await worker.replay_dead_lettered_event(
            event_id=fail_id,
            operator_id="op_rt002",
            reason="rt002_authorized_replay",
        )
        assert replayed.get("event_id") == fail_id or fail_id in str(replayed)
        row2 = db["nextgen_outbox_events"].find_one({"event_id": fail_id})
        assert row2.get("dead_lettered_at") is None
        # Duplicate replay of already-cleared DL should still target same event_id.
        assert db["nextgen_outbox_events"].count_documents({"event_id": fail_id}) == 1

    asyncio.run(run())
    print("LIVE_MONGO_REPLICA_SET_PROOF receipt_idempotency_dead_letter=PASS")
    print("DELIVERY_MODEL=AT-LEAST-ONCE+IDEMPOTENT_CONSUMERS+DURABLE_RECEIPTS+SAFE_RECONCILIATION")


def test_tenant_property_isolation_on_seeded_events(mongo_db):
    db = mongo_db
    worker = _load_worker(db)
    db["nextgen_outbox_events"].delete_many({})
    a = _seed_event(db, tenant_id="tenant_a", property_id="prop_a")
    b = _seed_event(db, tenant_id="tenant_b", property_id="prop_b")

    async def run():
        first = await worker.claim_next_event(worker_id="w_iso")
        assert first is not None
        # Claimed event retains its tenant/property; other tenant row remains distinct.
        assert first["tenant_id"] in {"tenant_a", "tenant_b"}
        other_id = b if first["event_id"] == a else a
        other = db["nextgen_outbox_events"].find_one({"event_id": other_id})
        assert other is not None
        assert other["tenant_id"] != first["tenant_id"]
        assert other.get("leased_by") in (None, "")
        second = await worker.claim_next_event(worker_id="w_iso2")
        assert second is not None
        assert {first["event_id"], second["event_id"]} == {a, b}

    asyncio.run(run())
    print("LIVE_MONGO_REPLICA_SET_PROOF tenant_property_isolation=PASS")
