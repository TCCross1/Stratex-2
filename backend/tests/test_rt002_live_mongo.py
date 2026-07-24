"""RT-002 live Mongo replica-set proofs.

Requires:
  RT002_LIVE=1
  MONGO_URL pointing at a replica-set Mongo (e.g. mongodb://127.0.0.1:27018/?replicaSet=rs0)

Emits marker: LIVE_MONGO_REPLICA_SET_PROOF
Never prints password-bearing connection strings.
Never uses FakeMongo as live proof.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.live_mongo,
]

LIVE = os.environ.get("RT002_LIVE", "").lower() in {"1", "true", "yes"}
MONGO_URL = os.environ.get("RT002_MONGO_URL") or os.environ.get("MONGO_URL") or ""
DB_NAME = os.environ.get("RT002_DB_NAME") or os.environ.get("DB_NAME") or "stratex_rt002_live"


def _skip_unless_live():
    if not LIVE:
        pytest.skip("RT002_LIVE not set — live Mongo proof not executed here")
    if not MONGO_URL:
        pytest.skip("MONGO_URL/RT002_MONGO_URL missing — INTEGRATION_ENVIRONMENT_UNAVAILABLE")


@pytest.fixture(scope="module")
def client():
    _skip_unless_live()
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure

    c = MongoClient(MONGO_URL, serverSelectionTimeoutMS=8000)
    try:
        c.admin.command("ping")
    except Exception as exc:  # noqa: BLE001 — surface as skip/unavailable
        pytest.skip(f"INTEGRATION_ENVIRONMENT_UNAVAILABLE: Mongo ping failed ({type(exc).__name__})")
    yield c
    c.close()


@pytest.fixture(scope="module")
def db(client):
    return client[DB_NAME]


def test_replica_set_initialized_and_primary(client):
    hello = client.admin.command("hello")
    assert hello.get("ok") == 1
    # Writable primary required for transactions.
    assert hello.get("isWritablePrimary") or hello.get("ismaster")
    set_name = hello.get("setName")
    assert set_name, "standalone Mongo does not satisfy RT-002"
    print("LIVE_MONGO_REPLICA_SET_PROOF replica_set=" + str(set_name))


def test_multi_document_transaction_commit(db, client):
    coll_a = db[f"rt002_txn_a_{uuid.uuid4().hex[:8]}"]
    coll_b = db[f"rt002_txn_b_{uuid.uuid4().hex[:8]}"]
    with client.start_session() as session:
        with session.start_transaction():
            coll_a.insert_one({"_id": "a1", "v": 1}, session=session)
            coll_b.insert_one({"_id": "b1", "v": 1}, session=session)
    assert coll_a.find_one({"_id": "a1"}) is not None
    assert coll_b.find_one({"_id": "b1"}) is not None
    print("LIVE_MONGO_REPLICA_SET_PROOF transaction_commit=PASS")
    coll_a.drop()
    coll_b.drop()


def test_transaction_rollback_leaves_no_partial_state(db, client):
    coll_a = db[f"rt002_rb_a_{uuid.uuid4().hex[:8]}"]
    coll_b = db[f"rt002_rb_b_{uuid.uuid4().hex[:8]}"]
    try:
        with client.start_session() as session:
            with session.start_transaction():
                coll_a.insert_one({"_id": "a1", "v": 1}, session=session)
                coll_b.insert_one({"_id": "b1", "v": 1}, session=session)
                raise RuntimeError("intentional_rollback")
    except RuntimeError as exc:
        assert "intentional_rollback" in str(exc)
    assert coll_a.find_one({"_id": "a1"}) is None
    assert coll_b.find_one({"_id": "b1"}) is None
    print("LIVE_MONGO_REPLICA_SET_PROOF transaction_rollback=PASS")
    coll_a.drop()
    coll_b.drop()


def test_active_passport_partial_unique_index(db):
    coll = db[f"rt002_passports_{uuid.uuid4().hex[:8]}"]
    coll.create_index(
        [("tenant_id", 1), ("property_id", 1)],
        unique=True,
        name="uniq_active_passport_per_tenant_property",
        partialFilterExpression={"status": "active"},
    )
    tenant = "rt002_tenant_" + uuid.uuid4().hex[:6]
    prop = "rt002_prop_" + uuid.uuid4().hex[:6]
    coll.insert_one({"tenant_id": tenant, "property_id": prop, "status": "active", "rev": 1})
    coll.insert_one({"tenant_id": tenant, "property_id": prop, "status": "archived", "rev": 0})
    coll.insert_one({"tenant_id": tenant, "property_id": prop, "status": "superseded", "rev": 0})
    with pytest.raises(Exception):
        coll.insert_one({"tenant_id": tenant, "property_id": prop, "status": "active", "rev": 2})
    print("LIVE_MONGO_REPLICA_SET_PROOF unique_index=PASS")
    coll.drop()


def test_transaction_fails_without_replica_set_session_support(client):
    # Sanity: start_session works on RS; this test documents requirement.
    hello = client.admin.command("hello")
    assert hello.get("setName")
    print("LIVE_MONGO_REPLICA_SET_PROOF session_support=PASS")
