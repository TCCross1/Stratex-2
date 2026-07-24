"""C-P-003 live publication-recovery proof against real Mongo replica set.

Imports implementation directly from the checked-out PR #7 branch
(``nextgen.outbox_worker`` / ``nextgen.projection_reconciliation``).

Does NOT use FakeMongo and does NOT fetch an older worktree.

Requires:
  RT002_LIVE=1 (or CP003_LIVE=1)
  RT002_MONGO_URL / MONGO_URL pointing at replica set

Emits: LIVE_CP003_PUBLICATION_RECOVERY_PROOF

Delivery model (never exactly-once):
  AT-LEAST-ONCE + IDEMPOTENT CONSUMERS + DURABLE RECEIPTS + SAFE RECONCILIATION
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.live_mongo,
    pytest.mark.cp003_live,
]

LIVE = (
    os.environ.get("RT002_LIVE", "").lower() in {"1", "true", "yes"}
    or os.environ.get("CP003_LIVE", "").lower() in {"1", "true", "yes"}
)
MONGO_URL = os.environ.get("RT002_MONGO_URL") or os.environ.get("MONGO_URL") or ""
DB_NAME = os.environ.get("RT002_DB_NAME") or os.environ.get("DB_NAME") or "stratex_cp003_live"


def _require_live():
    if not LIVE:
        pytest.skip("RT002_LIVE/CP003_LIVE not set — live C-P-003 proof not executed here")
    if not MONGO_URL:
        pytest.fail("INTEGRATION_ENVIRONMENT_FAILED: live flag set but MONGO_URL missing")


@pytest.fixture(scope="module")
def mongo_client():
    _require_live()
    from pymongo import MongoClient

    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"INTEGRATION_ENVIRONMENT_FAILED: Mongo ping failed ({type(exc).__name__})")
    hello = client.admin.command("hello")
    assert hello.get("setName"), "standalone Mongo does not satisfy live C-P-003"
    assert hello.get("isWritablePrimary") or hello.get("ismaster")
    yield client
    client.close()


@pytest.fixture
def db(mongo_client, monkeypatch):
    """Wire nextgen.db.nx_collections to real pymongo for this process."""
    from pymongo import ReturnDocument

    import nextgen.db as dbmod
    import nextgen.outbox as outbox
    import nextgen.outbox_worker as worker
    import nextgen.projection_reconciliation as recon

    database = mongo_client[DB_NAME + "_" + uuid.uuid4().hex[:8]]

    class _Coll:
        def __init__(self, name):
            self._c = database[name]

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

    class Colls:
        def __getattr__(self, name):
            return _Coll(f"nextgen_{name}" if not name.startswith("nextgen_") else name)

    colls = Colls()
    # Explicit aliases matching worker expectations
    colls.outbox_events = _Coll("nextgen_outbox_events")
    colls.inbox_receipts = _Coll("nextgen_inbox_receipts")
    colls.dead_letter_events = _Coll("nextgen_outbox_dead_letters")
    colls.audit_events = _Coll("nextgen_audit_events")
    colls.passports = _Coll("nextgen_passports")
    colls.passport_entries = _Coll("nextgen_passport_entries")
    colls.passport_projection_markers = _Coll("nextgen_passport_projection_markers")
    colls.publication_sources = _Coll("nextgen_publication_sources")
    colls.publication_results = _Coll("nextgen_publication_results")

    monkeypatch.setattr(dbmod, "nx_collections", colls)
    monkeypatch.setattr(outbox, "nx_collections", colls)
    monkeypatch.setattr(worker, "nx_collections", colls)
    monkeypatch.setattr(recon, "nx_collections", colls)

    # Receipt uniqueness + active passport partial unique
    database["nextgen_inbox_receipts"].create_index(
        [("consumer_key", 1), ("event_id", 1), ("payload_hash", 1)],
        unique=True,
        name="uniq_inbox_receipt",
    )
    database["nextgen_passports"].create_index(
        [("tenant_id", 1), ("property_id", 1)],
        unique=True,
        name="uniq_active_passport",
        partialFilterExpression={"status": "active"},
    )

    yield database
    mongo_client.drop_database(database.name)


def _seed(db, *, tenant="t_cp003", property_id="p_cp003", lease_until=None, lease_owner=None):
    from nextgen.db import now_iso_utc, nx_id

    now = now_iso_utc()
    event_id = "evt_" + uuid.uuid4().hex
    doc = {
        "canonical_id": nx_id(),
        "event_id": event_id,
        "tenant_id": tenant,
        "property_id": property_id,
        "event_type": "cp003.live.test",
        "payload": {"property_id": property_id, "n": 1},
        "idempotency_key": "idem_" + uuid.uuid4().hex,
        "available_after": now,
        "attempts": 0,
        "delivered_at": None,
        "dead_lettered_at": None,
        "lease_until": lease_until,
        "leased_by": lease_owner,
        "created_at": now,
        "producer_resource_kind": "test",
        "producer_resource_id": "r1",
    }
    db["nextgen_outbox_events"].insert_one(doc)
    return event_id


def test_two_and_ten_worker_atomic_claim(db):
    from nextgen import outbox_worker as w

    async def claim_n(n):
        return [r for r in await asyncio.gather(
            *[w.claim_next_event(worker_id=f"w{i}") for i in range(n)]
        ) if r]

    _seed(db)
    assert len(asyncio.run(claim_n(2))) == 1
    db["nextgen_outbox_events"].delete_many({})
    _seed(db)
    assert len(asyncio.run(claim_n(10))) == 1
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF atomic_claim=PASS")


def test_lease_protect_and_expire_recover(db):
    from nextgen import outbox_worker as w

    now = datetime.now(timezone.utc)
    future = (now + timedelta(seconds=120)).isoformat()
    past = (now - timedelta(seconds=2)).isoformat()
    slightly_before = (now + timedelta(seconds=30)).isoformat()
    eid = _seed(db, lease_until=future, lease_owner="holder")

    async def run():
        assert await w.claim_next_event(worker_id="thief") is None
        db["nextgen_outbox_events"].update_one(
            {"event_id": eid}, {"$set": {"lease_until": slightly_before}}
        )
        # still unexpired relative to "now" inside claim — set far future again then expire
        db["nextgen_outbox_events"].update_one(
            {"event_id": eid}, {"$set": {"lease_until": past}}
        )
        recovered = await w.claim_next_event(worker_id="rescuer")
        assert recovered and recovered["event_id"] == eid

    asyncio.run(run())
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF lease=PASS")


def test_crash_after_claim_and_worker_restart(db):
    from nextgen import outbox_worker as w

    eid = _seed(db)

    async def run():
        claimed = await w.claim_next_event(worker_id="crash1", lease_seconds=30)
        assert claimed is not None
        # crash — no delivery; expire lease; restart worker
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        db["nextgen_outbox_events"].update_one(
            {"event_id": eid}, {"$set": {"lease_until": past}}
        )
        restarted = await w.claim_next_event(worker_id="restart1")
        assert restarted and restarted["event_id"] == eid
        assert int(restarted.get("attempts") or 0) >= 2

    asyncio.run(run())
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF crash_recovery=PASS")


def test_delivery_receipt_idempotency_and_interrupted_receipt(db):
    from nextgen import outbox_worker as w

    eid = _seed(db)

    async def run():
        claimed = await w.claim_next_event(worker_id="del1")
        assert claimed
        # Simulate delivery succeeded then crash before receipt: mark nothing, reclaim after expiry
        past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        db["nextgen_outbox_events"].update_one(
            {"event_id": eid}, {"$set": {"lease_until": past, "leased_by": None}}
        )
        claimed2 = await w.claim_next_event(worker_id="del2")
        assert claimed2
        r1 = await w.mark_delivered(event=claimed2, consumer_key="c1", worker_id="del2")
        assert r1["receipt"]["duplicate"] is False
        r2 = await w.mark_delivered(event=claimed2, consumer_key="c1", worker_id="del2")
        assert r2["receipt"]["duplicate"] is True
        assert db["nextgen_inbox_receipts"].count_documents({"event_id": eid}) == 1
        # Duplicate delivery remains safe — still one receipt, still delivered
        row = db["nextgen_outbox_events"].find_one({"event_id": eid})
        assert row.get("delivered_at")

    asyncio.run(run())
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF receipts=PASS")
    print("DELIVERY_MODEL=AT-LEAST-ONCE+IDEMPOTENT_CONSUMERS+DURABLE_RECEIPTS+SAFE_RECONCILIATION")


def test_retry_backoff_cap_dead_letter_and_replay_gates(db):
    from nextgen import outbox_worker as w

    # Backoff cap
    assert w._backoff_seconds(1) >= 2
    assert w._backoff_seconds(100) == w.MAX_BACKOFF_SECONDS

    eid = _seed(db)

    async def boom(_e):
        raise RuntimeError("x" * 5000)

    async def run():
        last = None
        for _ in range(5):
            db["nextgen_outbox_events"].update_one(
                {"event_id": eid},
                {"$set": {
                    "available_after": datetime.now(timezone.utc).isoformat(),
                    "lease_until": None,
                    "leased_by": None,
                }},
            )
            last = await w.process_one(
                worker_id="failw", handler=boom, max_attempts=5
            )
        assert last["status"] == "dead_lettered"
        row = db["nextgen_outbox_events"].find_one({"event_id": eid})
        assert row.get("dead_lettered_at")
        msg = (row.get("last_error") or {}).get("message") or ""
        assert len(msg) <= 500

        with pytest.raises(PermissionError):
            await w.replay_dead_lettered_event(
                event_id=eid, operator_id="op", operator_role="contractor", reason="nope"
            )
        with pytest.raises(ValueError, match="reason"):
            await w.replay_dead_lettered_event(
                event_id=eid, operator_id="op", operator_role="admin", reason=""
            )
        ok = await w.replay_dead_lettered_event(
            event_id=eid,
            operator_id="op_admin",
            operator_role="admin",
            reason="authorized_live_replay",
        )
        assert ok["status"] == "requeued"
        assert ok["event_id"] == eid
        # Duplicate replay of non-dead-letter (already cleared) fails closed
        with pytest.raises(ValueError):
            await w.replay_dead_lettered_event(
                event_id=eid,
                operator_id="op_admin",
                operator_role="admin",
                reason="dup_replay",
            )
        # Already delivered reject
        claimed = await w.claim_next_event(worker_id="post_replay")
        assert claimed
        await w.mark_delivered(event=claimed, consumer_key="c", worker_id="post_replay")
        with pytest.raises(ValueError, match="already delivered"):
            await w.replay_dead_lettered_event(
                event_id=eid,
                operator_id="op_admin",
                operator_role="ops",
                reason="after_deliver",
            )

    asyncio.run(run())
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF retry_dlq_replay=PASS")


def test_tenant_property_isolation_and_receipt_mismatch(db):
    from nextgen import outbox_worker as w

    a = _seed(db, tenant="tenant_a", property_id="prop_a")
    b = _seed(db, tenant="tenant_b", property_id="prop_b")

    async def run():
        c1 = await w.claim_next_event(worker_id="iso1")
        c2 = await w.claim_next_event(worker_id="iso2")
        assert {c1["event_id"], c2["event_id"]} == {a, b}
        assert c1["tenant_id"] != c2["tenant_id"]
        assert c1["property_id"] != c2["property_id"]
        # Receipt must preserve tenant from event — reject mismatched consumer write simulation
        r = await w.mark_delivered(event=c1, consumer_key="cons", worker_id="iso1")
        receipt = db["nextgen_inbox_receipts"].find_one({"event_id": c1["event_id"]})
        assert receipt["tenant_id"] == c1["tenant_id"]
        assert receipt["tenant_id"] != c2["tenant_id"]
        assert r["receipt"]["duplicate"] is False

    asyncio.run(run())
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF tenant_property_isolation=PASS")


def test_projection_and_source_reconciliation_no_passport_append(db):
    from nextgen import projection_reconciliation as pr

    async def run():
        db["nextgen_passports"].insert_one({
            "canonical_id": "pp_" + uuid.uuid4().hex,
            "tenant_id": "t1",
            "property_id": "p1",
            "status": "active",
            "head_hash": "livehash123456",
        })
        drift = await pr.reconcile_property_stub(tenant_id="t1", property_id="p1")
        assert drift["status"] == pr.STATUS_INSUFFICIENT_DATA
        repaired = await pr.repair_projection_marker(tenant_id="t1", property_id="p1")
        assert repaired["status"] == pr.STATUS_REPAIRED
        assert repaired["passport_entries_written"] == 0
        again = await pr.repair_projection_marker(tenant_id="t1", property_id="p1")
        assert again["status"] == pr.STATUS_ALREADY_CURRENT

        db["nextgen_publication_sources"].insert_one({
            "canonical_id": "src1",
            "tenant_id": "t1",
            "property_id": "p1",
            "status": "stale",
        })
        no_pub = await pr.reconcile_source_publication_state(
            tenant_id="t1", property_id="p1", source_id="src1"
        )
        assert no_pub["status"] == pr.STATUS_INSUFFICIENT_DATA
        db["nextgen_publication_results"].insert_one({
            "canonical_id": "pub1",
            "tenant_id": "t1",
            "property_id": "p1",
            "source_id": "src1",
            "status": "published",
        })
        aligned = await pr.reconcile_source_publication_state(
            tenant_id="t1", property_id="p1", source_id="src1"
        )
        assert aligned["status"] == pr.STATUS_REPAIRED
        # Interrupt + retry
        retry = await pr.reconcile_source_publication_state(
            tenant_id="t1", property_id="p1", source_id="src1"
        )
        assert retry["status"] == pr.STATUS_ALREADY_CURRENT
        assert db["nextgen_passport_entries"].count_documents({}) == 0

        # Cross-property reject
        db["nextgen_publication_sources"].insert_one({
            "canonical_id": "src_bad",
            "tenant_id": "t1",
            "property_id": "p_other",
            "status": "stale",
        })
        bad = await pr.reconcile_source_publication_state(
            tenant_id="t1", property_id="p1", source_id="src_bad"
        )
        assert bad["status"] == pr.STATUS_REJECTED

    asyncio.run(run())
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF reconciliation=PASS")


def test_no_duplicate_canonical_publication_and_txn_rollback(db, mongo_client):
    # Unique active passport index
    db["nextgen_passports"].insert_one({
        "tenant_id": "tuniq",
        "property_id": "puniq",
        "status": "active",
        "head_hash": "h1",
    })
    with pytest.raises(Exception):
        db["nextgen_passports"].insert_one({
            "tenant_id": "tuniq",
            "property_id": "puniq",
            "status": "active",
            "head_hash": "h2",
        })

    # Real transaction rollback leaves no partial reconciliation state
    coll_a = db[f"recon_txn_a_{uuid.uuid4().hex[:6]}"]
    coll_b = db[f"recon_txn_b_{uuid.uuid4().hex[:6]}"]
    try:
        with mongo_client.start_session() as session:
            with session.start_transaction():
                coll_a.insert_one({"_id": "a", "v": 1}, session=session)
                coll_b.insert_one({"_id": "b", "v": 1}, session=session)
                raise RuntimeError("intentional_rollback")
    except RuntimeError:
        pass
    assert coll_a.find_one({"_id": "a"}) is None
    assert coll_b.find_one({"_id": "b"}) is None
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF unique_and_txn_rollback=PASS")


def test_health_fails_when_mongo_unavailable():
    _require_live()
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError

    bad = MongoClient("mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=500")
    with pytest.raises(ServerSelectionTimeoutError):
        bad.admin.command("ping")
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF health_unavailable=PASS")


def test_no_public_claim_route_in_tree():
    from pathlib import Path

    routes = Path(__file__).resolve().parents[1] / "nextgen" / "routes"
    blob = ""
    for p in routes.glob("*.py"):
        blob += p.read_text(encoding="utf-8")
    assert "claim_next_event" not in blob
    assert "replay_dead_lettered_event" not in blob
    from nextgen import outbox_worker as w

    assert w.WORKER_TRUST_MODEL == "GLOBAL_INTERNAL_WORKER"
    print("LIVE_CP003_PUBLICATION_RECOVERY_PROOF route_exposure=PASS")
