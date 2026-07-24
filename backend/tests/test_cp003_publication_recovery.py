"""C-P-003 publication recovery foundation tests.

Covers: outbox claim/delivery, backoff + dead-letter, inbox receipts,
safe replay, backlog health, projection reconciliation stubs, and
authority singularity (no second Passport/governed publisher).

FakeMongo evidence is simulation — not production transaction proof.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_cp003_unit")

from nextgen import (  # noqa: E402
    outbox,
    outbox_worker,
    projection_reconciliation,
)
from fake_mongo import install_fake_collections  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def fake(monkeypatch):
    fc = install_fake_collections(
        monkeypatch,
        outbox,
        outbox_worker,
        projection_reconciliation,
    )
    return fc


def _iso_offset(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


async def _emit(fake, *, key: str, event_type: str = "TEST_EVENT", payload=None):
    return await outbox.emit_outbox_event(
        tenant_id="t1",
        event_type=event_type,
        payload=payload or {"k": key},
        idempotency_key=key,
        producer_resource_kind="test",
        producer_resource_id="r1",
    )


# ── Emit API stability ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_emit_outbox_event_api_stable_and_idempotent(fake):
    r1 = await _emit(fake, key="idem-1")
    r2 = await _emit(fake, key="idem-1")
    assert r1["duplicate"] is False
    assert r2["duplicate"] is True
    assert r1["event_id"] == r2["event_id"]
    n = await fake.outbox_events.count_documents({})
    assert n == 1
    row = await fake.outbox_events.find_one({"idempotency_key": "idem-1"})
    assert row["leased_by"] is None
    assert row["attempts"] == 0


# ── Claim / deliver ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_claim_is_idempotent_across_workers(fake):
    await _emit(fake, key="c1")
    a = await outbox_worker.claim_next_event(worker_id="w1", lease_seconds=60)
    b = await outbox_worker.claim_next_event(worker_id="w2", lease_seconds=60)
    assert a is not None
    assert b is None  # still leased by w1
    assert a["leased_by"] == "w1"
    assert a["attempts"] == 1


@pytest.mark.asyncio
async def test_successful_delivery_writes_receipt_and_marks_delivered(fake):
    emitted = await _emit(fake, key="d1", payload={"hello": "world"})

    async def handler(event):
        assert event["event_id"] == emitted["event_id"]

    result = await outbox_worker.process_one(
        worker_id="w1", handler=handler, consumer_key="habitat.sync"
    )
    assert result["status"] == "delivered"
    assert result["receipt"]["duplicate"] is False

    row = await fake.outbox_events.find_one({"event_id": emitted["event_id"]})
    assert row["delivered_at"] is not None
    assert row["leased_by"] is None
    receipts = await fake.inbox_receipts.find({}).to_list(10)
    assert len(receipts) == 1
    assert receipts[0]["consumer_key"] == "habitat.sync"
    assert receipts[0]["event_id"] == emitted["event_id"]

    audits = await fake.audit_events.find({"event_type": "OUTBOX_DELIVERED"}).to_list(10)
    assert len(audits) == 1
    assert "secret" not in (audits[0].get("payload") or {})


@pytest.mark.asyncio
async def test_duplicate_receipt_is_idempotent(fake):
    emitted = await _emit(fake, key="dup-r")
    event = await fake.outbox_events.find_one({"event_id": emitted["event_id"]})
    r1 = await outbox_worker.mark_delivered(
        event=event, consumer_key="c", worker_id="w1"
    )
    event2 = await fake.outbox_events.find_one({"event_id": emitted["event_id"]})
    r2 = await outbox_worker.mark_delivered(
        event=event2, consumer_key="c", worker_id="w1"
    )
    assert r1["receipt"]["duplicate"] is False
    assert r2["receipt"]["duplicate"] is True
    n = await fake.inbox_receipts.count_documents({})
    assert n == 1


# ── Failure / backoff / dead-letter ──────────────────────────────────────

@pytest.mark.asyncio
async def test_delivery_failure_schedules_backoff(fake):
    await _emit(fake, key="fail-1")

    async def boom(_event):
        raise RuntimeError("transient")

    result = await outbox_worker.process_one(
        worker_id="w1", handler=boom, max_attempts=5
    )
    assert result["status"] == "retry_scheduled"
    assert result["backoff_seconds"] >= 2
    row = await fake.outbox_events.find_one({"idempotency_key": "fail-1"})
    assert row["dead_lettered_at"] is None
    assert row["delivered_at"] is None
    assert row["leased_by"] is None
    assert row["available_after"] > row["created_at"]
    assert row["last_error"]["failure_class"] == "RuntimeError"


@pytest.mark.asyncio
async def test_exhausted_attempts_dead_letter(fake):
    await _emit(fake, key="dl-1")

    async def boom(_event):
        raise ValueError("hard fail")

    last = None
    for _ in range(3):
        # Make immediately claimable again between attempts
        await fake.outbox_events.update_one(
            {"idempotency_key": "dl-1"},
            {"$set": {"available_after": _iso_offset(-1), "lease_until": None, "leased_by": None}},
        )
        last = await outbox_worker.process_one(
            worker_id="w1", handler=boom, max_attempts=3
        )
    assert last["status"] == "dead_lettered"
    row = await fake.outbox_events.find_one({"idempotency_key": "dl-1"})
    assert row["dead_lettered_at"] is not None
    dl = await fake.dead_letter_events.find({}).to_list(10)
    assert len(dl) == 1
    assert dl[0]["failure_class"] == "ValueError"
    audits = await fake.audit_events.find({"event_type": "OUTBOX_DEADLETTER"}).to_list(10)
    assert len(audits) == 1


# ── Replay ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_safe_replay_requeues_dead_letter(fake):
    await _emit(fake, key="rp-1")
    await fake.outbox_events.update_one(
        {"idempotency_key": "rp-1"},
        {"$set": {
            "attempts": 5,
            "dead_lettered_at": _iso_offset(-10),
            "last_error": {"failure_class": "X", "message": "x"},
        }},
    )
    row = await fake.outbox_events.find_one({"idempotency_key": "rp-1"})
    await fake.dead_letter_events.insert_one({
        "canonical_id": "dl1",
        "event_id": row["event_id"],
        "event_type": "TEST_EVENT",
        "payload": {},
        "failure_class": "X",
        "moved_at": _iso_offset(-10),
        "replayed_at": None,
        "replayed_by": None,
    })

    result = await outbox_worker.replay_dead_lettered_event(
        event_id=row["event_id"],
        operator_id="op1",
        reason="manual_retry",
    )
    assert result["status"] == "requeued"
    refreshed = await fake.outbox_events.find_one({"event_id": row["event_id"]})
    assert refreshed["dead_lettered_at"] is None
    assert refreshed["attempts"] == 0
    assert refreshed["replayed_by"] == "op1"
    dl = await fake.dead_letter_events.find_one({"event_id": row["event_id"]})
    assert dl["replayed_at"] is not None
    assert dl["replayed_by"] == "op1"

    delivered = {"ok": False}

    async def handler(_e):
        delivered["ok"] = True

    proc = await outbox_worker.process_one(worker_id="w2", handler=handler)
    assert proc["status"] == "delivered"
    assert delivered["ok"] is True


@pytest.mark.asyncio
async def test_replay_rejects_delivered_event(fake):
    emitted = await _emit(fake, key="rp-bad")
    await fake.outbox_events.update_one(
        {"event_id": emitted["event_id"]},
        {"$set": {"delivered_at": _iso_offset(-1)}},
    )
    with pytest.raises(ValueError, match="already delivered"):
        await outbox_worker.replay_dead_lettered_event(
            event_id=emitted["event_id"], operator_id="op1"
        )


# ── Health / readiness ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_outbox_backlog_health_and_readiness(fake):
    await _emit(fake, key="h1")
    await _emit(fake, key="h2")
    await fake.outbox_events.update_one(
        {"idempotency_key": "h2"},
        {"$set": {"dead_lettered_at": _iso_offset(-1)}},
    )
    snap = await outbox_worker.outbox_backlog_status(
        dead_letter_critical_threshold=1
    )
    assert snap["module"] == "nextgen.outbox_worker"
    assert snap["pending_count"] >= 1
    assert snap["dead_letter_count"] == 1
    assert snap["status"] == "critical"
    assert snap["ready"] is False

    ready = await outbox_worker.outbox_readiness()
    assert ready["ready"] is False
    assert ready["dead_letter_count"] == 1


# ── Projection reconciliation stubs ──────────────────────────────────────

@pytest.mark.asyncio
async def test_projection_reconcile_insufficient_without_marker(fake):
    await fake.passports.insert_one({
        "canonical_id": "pp1",
        "tenant_id": "t1",
        "property_id": "p1",
        "status": "active",
        "head_hash": "abc123hashvalue",
    })
    result = await projection_reconciliation.reconcile_property_stub(
        tenant_id="t1", property_id="p1"
    )
    assert result["status"] == projection_reconciliation.STATUS_INSUFFICIENT_DATA
    assert "invent" in result["notes"].lower() or "incomplete" in result["notes"].lower()


@pytest.mark.asyncio
async def test_projection_reconcile_matched_and_drift(fake):
    await fake.passports.insert_one({
        "canonical_id": "pp1",
        "tenant_id": "t1",
        "property_id": "p1",
        "status": "active",
        "head_hash": "hash-aaa",
    })
    await fake.passport_projection_markers.insert_one({
        "tenant_id": "t1",
        "property_id": "p1",
        "projected_head_hash": "hash-aaa",
    })
    matched = await projection_reconciliation.reconcile_property_stub(
        tenant_id="t1", property_id="p1"
    )
    assert matched["status"] == projection_reconciliation.STATUS_MATCHED

    await fake.passport_projection_markers.update_one(
        {"property_id": "p1"},
        {"$set": {"projected_head_hash": "hash-bbb"}},
    )
    drift = await projection_reconciliation.reconcile_property_stub(
        tenant_id="t1", property_id="p1"
    )
    assert drift["status"] == projection_reconciliation.STATUS_DRIFT_DETECTED


@pytest.mark.asyncio
async def test_projection_stub_never_writes_passport_entries(fake):
    await projection_reconciliation.reconcile_property_stub(
        tenant_id="t1", property_id="missing"
    )
    n = await fake.passport_entries.count_documents({})
    assert n == 0


# ── Concurrent claim ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_concurrent_claims_single_winner_per_event(fake):
    await _emit(fake, key="race-1")
    await _emit(fake, key="race-2")

    results = await asyncio.gather(
        outbox_worker.claim_next_event(worker_id="wa", lease_seconds=60),
        outbox_worker.claim_next_event(worker_id="wb", lease_seconds=60),
        outbox_worker.claim_next_event(worker_id="wc", lease_seconds=60),
    )
    claimed = [r for r in results if r is not None]
    assert len(claimed) == 2
    ids = {c["event_id"] for c in claimed}
    assert len(ids) == 2
    workers = {c["leased_by"] for c in claimed}
    assert workers <= {"wa", "wb", "wc"}


# ── Authority singularity ────────────────────────────────────────────────

def test_cp003_modules_do_not_become_passport_writers():
    worker = (BACKEND / "nextgen" / "outbox_worker.py").read_text(encoding="utf-8")
    recon = (BACKEND / "nextgen" / "projection_reconciliation.py").read_text(
        encoding="utf-8"
    )
    for text, name in ((worker, "outbox_worker"), (recon, "projection_reconciliation")):
        assert "passport_entries.insert_one" not in text, name
        assert "from .passport_service import" not in text, name
        assert "from .governed_publish_service import" not in text, name
        assert "await append_entry" not in text, name
        assert "await governed_publish" not in text, name


def test_sole_writer_and_publisher_still_singular():
    svc = (BACKEND / "nextgen" / "passport_service.py").read_text(encoding="utf-8")
    pub = (BACKEND / "nextgen" / "governed_publish_service.py").read_text(
        encoding="utf-8"
    )
    assert "async def append_entry" in svc
    assert "passport_entries.insert_one" in svc
    assert "from .passport_service import append_entry" in pub
    assert "await append_entry(" in pub
    assert 'MODULE_IDENTITY = "nextgen.governed_publish_service"' in pub

    # Exactly one NextGen module defines append_entry / governed_publish.
    nextgen = BACKEND / "nextgen"
    append_defs = []
    publish_defs = []
    for path in nextgen.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "async def append_entry" in text:
            append_defs.append(path.relative_to(BACKEND).as_posix())
        if "async def governed_publish" in text:
            publish_defs.append(path.relative_to(BACKEND).as_posix())
    assert append_defs == ["nextgen/passport_service.py"]
    assert publish_defs == ["nextgen/governed_publish_service.py"]


def test_mission_record_exists():
    mission = (
        Path(__file__).resolve().parents[2]
        / "engineering"
        / "px001"
        / "missions"
        / "LANE_1_CP003.md"
    )
    assert mission.is_file()
    text = mission.read_text(encoding="utf-8")
    assert "C-P-003" in text
    assert "outbox_worker" in text
    assert "append_entry" in text
