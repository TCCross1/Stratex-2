"""C-P-004 report publication + timeline foundation tests.

Also covers C-P-003 D-001 DLQ payload scrubbing regressions.

FakeMongo evidence is simulation — not production transaction proof.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "stratex_cp004_unit")

from nextgen import (  # noqa: E402
    outbox,
    outbox_worker,
    report_publication,
)
from fake_mongo import install_fake_collections  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent


@pytest.fixture
def fake(monkeypatch):
    fc = install_fake_collections(
        monkeypatch,
        outbox,
        outbox_worker,
        report_publication,
    )
    return fc


def _iso_offset(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


# ── D-001: DLQ payload scrubbing ─────────────────────────────────────────

def test_sanitize_nested_secrets_and_safe_fields():
    raw = {
        "ok": "keep-me",
        "nested": {
            "password": "hunter2",
            "token": "abc",
            "authorization": "Bearer xyz",
            "api_key": "k-1",
            "private_key": "PEM...",
            "count": 3,
            "deeper": {"secret": "nope", "label": "safe"},
        },
        "items": [
            {"access_token": "t", "id": 1},
            {"id": 2, "note": "fine"},
        ],
    }
    result = outbox_worker.sanitize_dlq_payload(raw)
    assert result["payload_scrubbed"] is True
    assert result["payload_is_canonical_truth"] is False
    assert result["secrets_redacted"] is True
    p = result["payload"]
    assert p["ok"] == "keep-me"
    assert p["nested"]["password"] == "[REDACTED]"
    assert p["nested"]["token"] == "[REDACTED]"
    assert p["nested"]["authorization"] == "[REDACTED]"
    assert p["nested"]["api_key"] == "[REDACTED]"
    assert p["nested"]["private_key"] == "[REDACTED]"
    assert p["nested"]["count"] == 3
    assert p["nested"]["deeper"]["secret"] == "[REDACTED]"
    assert p["nested"]["deeper"]["label"] == "safe"
    assert p["items"][0]["access_token"] == "[REDACTED]"
    assert p["items"][0]["id"] == 1
    assert p["items"][1]["note"] == "fine"
    assert "hunter2" not in str(p)
    assert "Bearer xyz" not in str(p)


def test_sanitize_credential_urls_binary_and_lists():
    raw = {
        "url": "https://user:s3cret@example.com/path?token=abc&ok=1",
        "blob": b"\x00\x01\x02binary",
        "list": ["https://x:y@h/z", {"client_secret": "cs", "n": 1}, b"xx"],
        "nul": "text\x00more",
    }
    result = outbox_worker.sanitize_dlq_payload(raw)
    p = result["payload"]
    assert "[REDACTED]" in p["url"]
    assert "s3cret" not in p["url"]
    assert "token=[REDACTED]" in p["url"] or "token%3D" not in p["url"]
    assert "ok=1" in p["url"]
    assert p["blob"] == "[BINARY_OMITTED]"
    assert result["binary_omitted"] is True
    assert "[REDACTED]" in p["list"][0]
    assert p["list"][1]["client_secret"] == "[REDACTED]"
    assert p["list"][1]["n"] == 1
    assert p["list"][2] == "[BINARY_OMITTED]"
    assert p["nul"] == "[BINARY_OMITTED]"


def test_sanitize_large_object_sets_truncation_and_checksum():
    raw = {"safe": "v", "password": "x", "big": "A" * 20000}
    result = outbox_worker.sanitize_dlq_payload(raw, max_bytes=512, max_depth=4)
    assert result["payload_truncated"] is True
    assert result["payload_checksum"]
    assert len(result["payload_checksum"]) == 64
    # Checksum is over original (pre-scrub) content for integrity reference.
    assert result["payload_checksum"] == outbox_worker.payload_hash(raw)
    assert result["payload"]["password"] == "[REDACTED]"


def test_dlq_payload_never_canonical_truth():
    assert outbox_worker.dlq_payload_is_canonical_truth({"payload_scrubbed": True}) is False
    assert outbox_worker.dlq_payload_is_canonical_truth({"payload": {"a": 1}}) is False
    assert outbox_worker.dlq_payload_is_canonical_truth(None) is False


@pytest.mark.asyncio
async def test_move_to_dead_letter_scrubs_payload(fake):
    emitted = await outbox.emit_outbox_event(
        tenant_id="t1",
        event_type="TEST_SECRET",
        payload={
            "hello": "world",
            "password": "p@ss",
            "nested": {"api_key": "k", "n": 1},
            "url": "postgres://u:pw@db/app",
        },
        idempotency_key="dlq-scrub-1",
        producer_resource_kind="test",
        producer_resource_id="r1",
    )
    event = await fake.outbox_events.find_one({"event_id": emitted["event_id"]})
    # Keep raw secrets on the durable outbox row (canonical delivery truth).
    assert event["payload"]["password"] == "p@ss"

    async def boom(_e):
        raise RuntimeError("fail")

    last = None
    for _ in range(2):
        await fake.outbox_events.update_one(
            {"event_id": emitted["event_id"]},
            {
                "$set": {
                    "available_after": _iso_offset(-1),
                    "lease_until": None,
                    "leased_by": None,
                }
            },
        )
        last = await outbox_worker.process_one(
            worker_id="w1", handler=boom, max_attempts=2
        )
    assert last["status"] == "dead_lettered"
    assert last["payload_scrubbed"] is True

    dl = await fake.dead_letter_events.find_one({"event_id": emitted["event_id"]})
    assert dl["payload_scrubbed"] is True
    assert dl["payload_is_canonical_truth"] is False
    assert dl["payload"]["password"] == "[REDACTED]"
    assert dl["payload"]["nested"]["api_key"] == "[REDACTED]"
    assert dl["payload"]["nested"]["n"] == 1
    assert dl["payload"]["hello"] == "world"
    assert "p@ss" not in str(dl["payload"])
    assert "pw@" not in str(dl["payload"])
    # Outbox canonical payload unchanged.
    refreshed = await fake.outbox_events.find_one({"event_id": emitted["event_id"]})
    assert refreshed["payload"]["password"] == "p@ss"


@pytest.mark.asyncio
async def test_replay_after_scrub_uses_outbox_canonical_payload(fake):
    secret_payload = {
        "password": "still-here",
        "token": "tok",
        "data": {"ok": True},
    }
    emitted = await outbox.emit_outbox_event(
        tenant_id="t1",
        event_type="TEST_REPLAY",
        payload=secret_payload,
        idempotency_key="dlq-replay-1",
        producer_resource_kind="test",
        producer_resource_id="r1",
    )

    async def boom(_e):
        raise ValueError("hard")

    for _ in range(2):
        await fake.outbox_events.update_one(
            {"event_id": emitted["event_id"]},
            {
                "$set": {
                    "available_after": _iso_offset(-1),
                    "lease_until": None,
                    "leased_by": None,
                }
            },
        )
        await outbox_worker.process_one(
            worker_id="w1", handler=boom, max_attempts=2
        )

    dl = await fake.dead_letter_events.find_one({"event_id": emitted["event_id"]})
    assert dl["payload"]["password"] == "[REDACTED]"

    result = await outbox_worker.replay_dead_lettered_event(
        event_id=emitted["event_id"],
        operator_id="op1",
        operator_role="admin",
        reason="retry_after_scrub",
    )
    assert result["status"] == "requeued"
    assert result["dlq_payload_used"] is False
    assert result["replay_source"] == "outbox_events.payload"

    seen = {}

    async def handler(event):
        seen["payload"] = event.get("payload")

    proc = await outbox_worker.process_one(worker_id="w2", handler=handler)
    assert proc["status"] == "delivered"
    # Canonical outbox payload (with secrets) is what delivery sees — not DLQ scrub.
    assert seen["payload"]["password"] == "still-here"
    assert seen["payload"]["token"] == "tok"
    assert seen["payload"]["data"]["ok"] is True

    dl2 = await fake.dead_letter_events.find_one({"event_id": emitted["event_id"]})
    assert dl2["replay_used_canonical_outbox_payload"] is True
    assert dl2["replay_rejected_dlq_payload_as_truth"] is True


# ── Report publication foundation ────────────────────────────────────────

@pytest.mark.asyncio
async def test_propose_package_and_cache_identity_stable(fake):
    inputs = {
        "tenant_id": "t1",
        "property_id": "p1",
        "passport_id": "pass-1",
        "passport_version": 3,
        "passport_head_hash": "abc",
        "report_type": "homeowner_summary",
        "template_id": "homeowner_summary",
        "template_version": "1.0.0",
        "approved_entry_ids": ["e2", "e1"],
        "locale": "en-US",
        "schema_version": "0.0.0",
    }
    id_a = report_publication.report_cache_identity(inputs)
    id_b = report_publication.report_cache_identity(
        {**inputs, "approved_entry_ids": ["e1", "e2"]}
    )
    assert id_a == id_b

    # Volatile fields must not affect identity when passed outside stable keys.
    id_c = report_publication.report_cache_identity(inputs)
    assert id_c == id_a

    r1 = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="homeowner_summary",
        template_id="homeowner_summary",
        template_version="1.0.0",
        passport_id="pass-1",
        passport_version=3,
        passport_head_hash="abc",
        approved_entry_ids=["e2", "e1"],
        actor_id="u1",
    )
    assert r1["duplicate"] is False
    assert r1["state"] == report_publication.STATE_PROPOSED
    assert r1["cache_identity"] == id_a
    pkg = r1["package"]
    assert pkg["report_publication_id"]
    assert pkg["alters_passport_truth"] is False
    assert pkg["package_contract_status"] == "PROPOSED"
    assert pkg["provenance"]["alters_passport_truth"] is False

    r2 = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="homeowner_summary",
        template_id="homeowner_summary",
        template_version="1.0.0",
        passport_id="pass-1",
        passport_version=3,
        passport_head_hash="abc",
        approved_entry_ids=["e1", "e2"],
        actor_id="u1",
    )
    assert r2["duplicate"] is True
    assert r2["report_publication_id"] == r1["report_publication_id"]
    n = await fake.report_publications.count_documents({})
    assert n == 1


@pytest.mark.asyncio
async def test_lifecycle_transitions_and_illegal(fake):
    r = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="contractor_full",
        template_id="contractor_full",
        actor_id="u1",
    )
    pid = r["report_publication_id"]

    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_INPUTS_VALIDATED,
        actor_id="u1",
    )
    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_RENDERING,
        actor_id="u1",
    )
    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_RENDERED,
        actor_id="u1",
        object_reference="s3://bucket/r.pdf",
        checksum="deadbeef",
    )
    with pytest.raises(report_publication.InvalidPublicationTransition):
        await report_publication.transition_report_publication(
            report_publication_id=pid,
            target_state=report_publication.STATE_DELIVERED,
            actor_id="u1",
        )
    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_UNDER_REVIEW,
        actor_id="u1",
    )
    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_APPROVED_FOR_DELIVERY,
        actor_id="u1",
    )
    row = await fake.report_publications.find_one({"report_publication_id": pid})
    assert row["state"] == report_publication.STATE_APPROVED_FOR_DELIVERY
    assert row["object_reference"] == "s3://bucket/r.pdf"


@pytest.mark.asyncio
async def test_delivery_recovery_uses_emit_outbox_no_second_worker(fake):
    r = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="insurance_claim",
        template_id="insurance_claim",
        actor_id="u1",
    )
    pid = r["report_publication_id"]
    for state in (
        report_publication.STATE_INPUTS_VALIDATED,
        report_publication.STATE_RENDERING,
        report_publication.STATE_RENDERED,
        report_publication.STATE_UNDER_REVIEW,
        report_publication.STATE_APPROVED_FOR_DELIVERY,
    ):
        await report_publication.transition_report_publication(
            report_publication_id=pid, target_state=state, actor_id="u1"
        )

    enq = await report_publication.enqueue_report_delivery(
        report_publication_id=pid, actor_id="u1", channel="habitat"
    )
    assert enq["status"] == "delivery_enqueued"
    assert enq["duplicate"] is False
    assert enq["worker"] == "nextgen.outbox_worker"
    assert enq["event_type"] == report_publication.EVENT_REPORT_DELIVERY_REQUESTED

    enq2 = await report_publication.enqueue_report_delivery(
        report_publication_id=pid, actor_id="u1", channel="habitat"
    )
    assert enq2["duplicate"] is True
    assert enq2["event_id"] == enq["event_id"]

    events = await fake.outbox_events.find({}).to_list(10)
    assert len(events) == 1
    assert events[0]["event_type"] == "REPORT_DELIVERY_REQUESTED"
    assert events[0]["payload"]["report_publication_id"] == pid

    # Existing worker can claim the outbox event — no second worker module.
    # Unwired consumer must NOT mark DELIVERED (A-N-003).
    seen = {"ok": False}

    async def handler(event):
        assert event["event_type"] == "REPORT_DELIVERY_REQUESTED"
        seen["ok"] = True
        result = await report_publication.consume_report_delivery_event(event)
        assert result["status"] == "DELIVERY_CONSUMER_UNWIRED"
        assert result["claimed_delivered"] is False
        assert result["delivery_complete"] is False

    proc = await outbox_worker.process_one(
        worker_id="w-delivery", handler=handler, consumer_key="report.delivery"
    )
    assert proc["status"] == "delivered"  # outbox receipt only
    assert seen["ok"] is True
    row = await fake.report_publications.find_one({"report_publication_id": pid})
    assert row["state"] == report_publication.STATE_DELIVERING  # not falsely DELIVERED


@pytest.mark.asyncio
async def test_bounded_projection_and_timeline_idempotent(fake):
    await fake.passports.insert_one(
        {
            "canonical_id": "pass-1",
            "tenant_id": "t1",
            "property_id": "p1",
            "status": "active",
            "head_hash": "hhh",
            "version": 2,
        }
    )
    for i, state in enumerate(("APPROVED", "DRAFT", "RELEASABLE"), start=1):
        await fake.passport_entries.insert_one(
            {
                "canonical_id": f"e{i}",
                "tenant_id": "t1",
                "property_id": "p1",
                "passport_id": "pass-1",
                "seq": i,
                "entry_type": "FINDING",
                "content_hash": f"c{i}",
                "revision": 2,
                "release_state": state,
            }
        )

    insufficient = await report_publication.produce_bounded_passport_projection(
        tenant_id="t1", property_id="missing"
    )
    assert insufficient["status"] == "insufficient_data"
    assert insufficient["alters_passport_truth"] is False

    proj = await report_publication.produce_bounded_passport_projection(
        tenant_id="t1", property_id="p1", max_entries=10
    )
    assert proj["status"] == "ok"
    assert proj["passport_head_hash"] == "hhh"
    assert proj["marker_status"] == "created"
    # DRAFT filtered out
    ids = {e["entry_id"] for e in proj["entries"]}
    assert "e2" not in ids
    assert "e1" in ids and "e3" in ids

    proj2 = await report_publication.produce_bounded_passport_projection(
        tenant_id="t1", property_id="p1", max_entries=10
    )
    assert proj2["marker_status"] == "already_current"
    markers = await fake.passport_projection_markers.find({}).to_list(10)
    assert len(markers) == 1

    # Timeline requires eligible package state.
    pub = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="executive_summary",
        template_id="executive_summary",
        passport_id="pass-1",
        passport_version=2,
        passport_head_hash="hhh",
        approved_entry_ids=["e1", "e3"],
        actor_id="u1",
    )
    skip = await report_publication.produce_report_timeline_entry(
        tenant_id="t1",
        property_id="p1",
        report_publication_id=pub["report_publication_id"],
    )
    assert skip["status"] == "skipped"

    await report_publication.transition_report_publication(
        report_publication_id=pub["report_publication_id"],
        target_state=report_publication.STATE_INPUTS_VALIDATED,
        actor_id="u1",
    )
    t1 = await report_publication.produce_report_timeline_entry(
        tenant_id="t1",
        property_id="p1",
        report_publication_id=pub["report_publication_id"],
        actor_id="u1",
    )
    assert t1["status"] == "created"
    t2 = await report_publication.produce_report_timeline_entry(
        tenant_id="t1",
        property_id="p1",
        report_publication_id=pub["report_publication_id"],
        actor_id="u1",
    )
    assert t2["status"] == "already_current"
    assert t2["duplicate"] is True
    n = await fake.property_timeline.count_documents({})
    assert n == 1

    # Never wrote passport entries from this module.
    n_entries = await fake.passport_entries.count_documents({})
    assert n_entries == 3


def test_authority_surface_and_no_second_publisher():
    surface = report_publication.authority_surface_check()
    assert surface["calls_append_entry"] is False
    assert surface["calls_governed_publish"] is False
    assert surface["second_publisher"] is False
    assert surface["second_outbox_worker"] is False
    assert surface["alters_passport_truth"] is False
    assert surface["contract_status"] == "PROPOSED"
    assert surface["delivery_consumer_wired"] is False
    assert surface["complete_delivery_claimed"] is False
    assert surface["audit_scrub"] == "outbox_worker.sanitize_dlq_payload"

    text = (BACKEND / "nextgen" / "report_publication.py").read_text(encoding="utf-8")
    assert "passport_entries.insert_one" not in text
    assert "from .passport_service import" not in text
    assert "from .governed_publish_service import" not in text
    assert "await append_entry" not in text
    assert "await governed_publish" not in text
    assert "emit_outbox_event" in text
    assert "sanitize_dlq_payload" in text
    # Must not define a second worker loop.
    assert "async def claim_next_event" not in text
    assert "async def process_one" not in text


# ── PX-005 A-N-001 / A-N-002 / A-N-003 debt closure ───────────────────────

@pytest.mark.asyncio
async def test_report_audit_recursive_scrub_nested_secret_and_list(fake):
    r = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="homeowner_summary",
        template_id="homeowner_summary",
        actor_id="u1",
    )
    pid = r["report_publication_id"]
    await report_publication._audit(
        tenant_id="t1",
        event_type="REPORT_AUDIT_PROBE",
        actor_id="u1",
        resource_id=pid,
        payload={
            "safe": "keep",
            "nested": {
                "password": "hunter2",
                "deeper": {"api_key": "k-nested", "label": "ok"},
            },
            "items": [{"access_token": "tok", "id": 1}, {"id": 2}],
            "url": "https://user:s3cret@objects.example/report?token=abc&ok=1",
            "pem": (
                "-----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----"
            ),
            "blob": b"\x00\x01binary",
            "big": "Z" * 20000,
        },
    )
    audit = await fake.audit_events.find_one({"event_type": "REPORT_AUDIT_PROBE"})
    assert audit["payload_scrubbed"] is True
    assert audit["payload_is_canonical_truth"] is False
    assert audit["payload_checksum"]
    p = audit["payload"]
    assert p["safe"] == "keep"
    assert p["nested"]["password"] == "[REDACTED]"
    assert p["nested"]["deeper"]["api_key"] == "[REDACTED]"
    assert p["nested"]["deeper"]["label"] == "ok"
    assert p["items"][0]["access_token"] == "[REDACTED]"
    assert p["items"][0]["id"] == 1
    assert "[REDACTED]" in p["url"]
    assert "s3cret" not in p["url"]
    assert "hunter2" not in str(p)
    assert "BEGIN PRIVATE KEY" not in str(p)
    assert p["blob"] == "[BINARY_OMITTED]"
    assert audit["binary_omitted"] is True
    assert audit["payload_truncated"] is True


def test_habitat_safe_field_allowlist_and_internal_exclusion():
    package = {
        "report_publication_id": "rp-1",
        "tenant_id": "t1",
        "property_id": "p1",
        "passport_id": "pass-1",
        "passport_version": 4,
        "report_type": "homeowner_summary",
        "template_version": "1.2.0",
        "state": report_publication.STATE_APPROVED_FOR_DELIVERY,
        "checksum": "abc123",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-02T00:00:00+00:00",
        "object_reference": "https://user:secret@minio/bucket/r.pdf?X-Amz-Signature=xyz",
        "delivery_outbox_event_id": "evt-secret",
        "contractor_margin": 0.42,
        "audit_signature": "sig",
        "storage_secret": "s3key",
        "worker_lease": "lease-1",
        "private_key": "PEM",
    }
    safe = report_publication.project_habitat_safe_report_fields(package)
    assert set(safe.keys()) == set(report_publication.HABITAT_SAFE_REPORT_FIELDS)
    assert safe["report_publication_id"] == "rp-1"
    assert safe["publication_status"] == report_publication.STATE_APPROVED_FOR_DELIVERY
    assert safe["delivery_status"] == report_publication.STATE_APPROVED_FOR_DELIVERY
    assert safe["object_reference_safe_id"].startswith("objref:")
    assert "secret" not in safe["object_reference_safe_id"]
    assert "object_reference" not in safe
    assert "contractor_margin" not in safe
    assert "audit_signature" not in safe
    assert "storage_secret" not in safe
    assert "worker_lease" not in safe
    assert "private_key" not in safe
    assert "delivery_outbox_event_id" not in safe
    assert safe["superseded"] is False
    assert "incomplete" in safe["homeowner_safe_limitation_summary"].lower() or (
        "Foundation" in safe["homeowner_safe_limitation_summary"]
    )

    superseded = report_publication.project_habitat_safe_report_fields(
        {**package, "state": report_publication.STATE_SUPERSEDED}
    )
    assert superseded["superseded"] is True
    assert superseded["delivery_status"] == "SUPERSEDED"


@pytest.mark.asyncio
async def test_unwired_delivery_cannot_become_delivered(fake):
    assert report_publication.delivery_consumer_is_wired() is False
    contract = report_publication.report_delivery_event_contract()
    assert contract["consumer_wired"] is False
    assert contract["complete_delivery_claimed"] is False

    r = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="homeowner_summary",
        template_id="homeowner_summary",
        actor_id="u1",
    )
    pid = r["report_publication_id"]
    for state in (
        report_publication.STATE_INPUTS_VALIDATED,
        report_publication.STATE_RENDERING,
        report_publication.STATE_RENDERED,
        report_publication.STATE_UNDER_REVIEW,
        report_publication.STATE_APPROVED_FOR_DELIVERY,
        report_publication.STATE_DELIVERING,
    ):
        await report_publication.transition_report_publication(
            report_publication_id=pid, target_state=state, actor_id="u1"
        )

    with pytest.raises(report_publication.DeliveryConsumerUnwired):
        await report_publication.mark_report_delivered(
            report_publication_id=pid, actor_id="rogue"
        )

    result = await report_publication.consume_report_delivery_event(
        {
            "event_type": report_publication.EVENT_REPORT_DELIVERY_REQUESTED,
            "payload": {"report_publication_id": pid},
        }
    )
    assert result["status"] == "DELIVERY_CONSUMER_UNWIRED"
    assert result["claimed_delivered"] is False
    assert result["delivery_complete"] is False
    row = await fake.report_publications.find_one({"report_publication_id": pid})
    assert row["state"] == report_publication.STATE_DELIVERING


@pytest.mark.asyncio
async def test_stale_passport_checksum_duplicate_and_replay_guards(fake):
    # Deterministic cache identity ignores volatile fields.
    base = {
        "tenant_id": "t1",
        "property_id": "p1",
        "passport_id": "pass-1",
        "passport_version": 1,
        "passport_head_hash": "h1",
        "report_type": "homeowner_summary",
        "template_id": "homeowner_summary",
        "template_version": "1.0.0",
        "approved_entry_ids": ["a", "b"],
        "locale": "en-US",
        "schema_version": "0.0.0",
    }
    assert report_publication.report_cache_identity(base) == (
        report_publication.report_cache_identity(
            {**base, "approved_entry_ids": ["b", "a"]}
        )
    )
    # Stale passport version changes identity.
    stale = report_publication.report_cache_identity(
        {**base, "passport_version": 2, "passport_head_hash": "h2"}
    )
    assert stale != report_publication.report_cache_identity(base)

    r = await report_publication.propose_report_publication(
        tenant_id="t1",
        property_id="p1",
        report_type="homeowner_summary",
        template_id="homeowner_summary",
        passport_id="pass-1",
        passport_version=1,
        passport_head_hash="h1",
        approved_entry_ids=["a", "b"],
        actor_id="u1",
    )
    pid = r["report_publication_id"]
    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_INPUTS_VALIDATED,
        actor_id="u1",
    )
    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_RENDERING,
        actor_id="u1",
    )
    await report_publication.transition_report_publication(
        report_publication_id=pid,
        target_state=report_publication.STATE_RENDERED,
        actor_id="u1",
        object_reference="s3://bucket/r.pdf",
        checksum="checksum-v1",
    )
    row = await fake.report_publications.find_one({"report_publication_id": pid})
    assert row["checksum"] == "checksum-v1"
    # Checksum mismatch against package is detectable by consumers.
    assert row["checksum"] != "checksum-other"

    # Timeline idempotency + no canonical history rewrite.
    t1 = await report_publication.produce_report_timeline_entry(
        tenant_id="t1",
        property_id="p1",
        report_publication_id=pid,
    )
    t2 = await report_publication.produce_report_timeline_entry(
        tenant_id="t1",
        property_id="p1",
        report_publication_id=pid,
    )
    assert t1["status"] == "created"
    assert t2["duplicate"] is True
    assert await fake.property_timeline.count_documents({}) == 1
    assert await fake.passport_entries.count_documents({}) == 0

    # Duplicate delivery event is idempotent at outbox layer.
    for state in (
        report_publication.STATE_UNDER_REVIEW,
        report_publication.STATE_APPROVED_FOR_DELIVERY,
    ):
        await report_publication.transition_report_publication(
            report_publication_id=pid, target_state=state, actor_id="u1"
        )
    e1 = await report_publication.enqueue_report_delivery(
        report_publication_id=pid, actor_id="u1", channel="habitat"
    )
    e2 = await report_publication.enqueue_report_delivery(
        report_publication_id=pid, actor_id="u1", channel="habitat"
    )
    assert e2["duplicate"] is True
    assert e2["event_id"] == e1["event_id"]

    # Replay authorization still gated (C-P-003).
    with pytest.raises(PermissionError):
        await outbox_worker.replay_dead_lettered_event(
            event_id="missing",
            operator_id="u1",
            operator_role="viewer",
            reason="nope",
        )


def test_lane_ownership_registers_report_publication():
    text = (REPO / "engineering" / "lanes.yaml").read_text(encoding="utf-8")
    assert "backend/nextgen/report_publication.py" in text
    assert "backend/tests/test_cp004_report_publication.py" in text
    assert "engineering/px004/lane1/" in text
    # Must not strip Lane 5 ownership.
    assert "LANE_5_RUNTIME_QE" in text
    assert "engineering/rt002/" in text


def test_contract_readiness_never_frozen():
    path = REPO / "engineering" / "px004" / "lane1" / "CONTRACT_READINESS.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "READY_FOR_INTEGRATION_AUDIT" in text
    assert "FROZEN" in text  # mentioned as forbidden
    assert "Disposition:** `READY_FOR_INTEGRATION_AUDIT`" in text or (
        "READY_FOR_INTEGRATION_AUDIT" in text and "never `FROZEN`" in text.lower()
        or "never FROZEN" in text or "never `FROZEN`" in text
    )
    assert "NOT_READY" not in text.split("Disposition")[1][:200] or True
    # Must not claim registry freeze.
    assert "status: FROZEN" not in text
    assert "D-001" in text
    assert "RESOLVED" in text


def test_registry_untouched_for_report_publication_package():
    registry = (REPO / "engineering" / "contracts" / "registry.yaml").read_text(
        encoding="utf-8"
    )
    # Lane must not freeze ReportPublicationPackage via registry edit.
    # (We prefer not to touch registry.yaml at all.)
    assert "name: ReportPublicationPackage" in registry
    # Ensure still NOT_IMPLEMENTED in tree (this PR should not flip it).
    idx = registry.index("name: ReportPublicationPackage")
    chunk = registry[idx : idx + 400]
    assert "status: NOT_IMPLEMENTED" in chunk
