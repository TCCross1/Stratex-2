"""RT-002 live C-P-003 claim/lease proofs against real Mongo.

Does NOT modify PR #7. Loads ``outbox_worker.py`` from a temporary worktree of
``cursor/lane1-cp003-publication-recovery`` (RT002_CP003_ROOT) with a thin db
shim over real pymongo — proving the audited claim algorithm on a replica set.

Requires RT002_LIVE=1 and replica-set MONGO_URL.
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
        pytest.skip("INTEGRATION_ENVIRONMENT_UNAVAILABLE: MONGO_URL missing")
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
        # Motor uses return_document=True; pymongo wants ReturnDocument.AFTER.
        rd = kwargs.pop("return_document", None)
        if rd is True:
            kwargs["return_document"] = ReturnDocument.AFTER
        elif rd is False:
            kwargs["return_document"] = ReturnDocument.BEFORE
        return self._c.find_one_and_update(filt, update, **kwargs)

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
        outbox_dead_letters = _AsyncColl(db["nextgen_outbox_dead_letters"])
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


def _seed_event(db, *, lease_until=None, lease_owner=None):
    now = datetime.now(timezone.utc).isoformat()
    event_id = "evt_" + uuid.uuid4().hex
    doc = {
        "event_id": event_id,
        "tenant_id": "t_rt002",
        "event_type": "rt002.test",
        "payload": {"n": 1},
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
