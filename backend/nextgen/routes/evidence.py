"""NextGen Evidence + Mission Package endpoints — Wave 2A (Directive 006).

Route surface lives under `/api/nextgen/v1/`. All routes are tenant-scoped
via `nx_session` and mission-authorized by `_authorize_mission`.

Design decisions (Directive 005 · make-and-document):
- Upload strategy: backend-proxied multipart. Signed pre-URL uploads land
  when we switch storage adapters (S3/GCS) in a later block.
- Content addressing: SHA-256 over the streamed body, computed inside the
  storage adapter, is the canonical dedup key.
- Immutability: `evidence_items.role = "original"` is `imm`; corrections
  create a new item and use `evidence_relationships.replaced_by`.
- Package versioning: `mission_packages` is append-safe. Finalized packages
  cannot be silently overwritten; a new version is appended.
"""
from __future__ import annotations

import mimetypes
import os
import re
from typing import Any, Dict, List, Optional

from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..auth import NxSession, nx_session
from ..db import now_iso_utc, nx_collections, nx_id, strip_mongo_id
from ..evidence_profiles import (
    ALLOWED_CATEGORIES, ALLOWED_MIME_PREFIXES, BLOCKED_EXTENSIONS,
    DERIVATIVE_CATEGORIES, ORIGINAL_CATEGORIES, PROFILES,
)
from ..metadata import extract_image_metadata
from ..outbox import emit_outbox_event
from ..storage import storage
from ._router import nextgen_r


V1 = "/v1"
MAX_UPLOAD_BYTES = int(os.environ.get("NEXTGEN_MAX_UPLOAD_BYTES", 256 * 1024 * 1024))
FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._\- ]")


# ── Helpers ──────────────────────────────────────────────────────────────
async def _authorize_mission(session: NxSession, mission_id: str) -> Dict[str, Any]:
    m = await nx_collections.missions.find_one({
        "canonical_id": mission_id,
        "tenant_id": session.tenant_id,
    })
    if not m:
        raise HTTPException(404, "Mission not found on your tenant")
    return m


def _sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "")[:200]
    return FILENAME_SAFE.sub("_", base) or "unnamed"


def _validate_mime_and_ext(filename: str, mime: str) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(415, f"Blocked file extension: {ext}")
    if mime and not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(415, f"Disallowed MIME type: {mime}")


async def _write_audit(session: NxSession, event_type: str, resource_kind: str,
                        resource_id: str, payload: Optional[dict] = None):
    await nx_collections.audit_events.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "event_type": event_type,
        "actor_id": session.user_id,
        "resource_kind": resource_kind,
        "resource_id": resource_id,
        "at": now_iso_utc(),
        "payload": payload or {},
    })


# ── Requirement profile endpoint ─────────────────────────────────────────
@nextgen_r.get(V1 + "/evidence-profiles/{product_key}")
async def get_profile(product_key: str):
    p = PROFILES.get(product_key)
    if not p:
        raise HTTPException(404, f"Unknown product profile: {product_key}")
    return p


@nextgen_r.get(V1 + "/evidence-profiles")
async def list_profiles():
    return {"profiles": list(PROFILES.values())}


# ── Evidence upload (single-shot, backend-proxied) ───────────────────────
@nextgen_r.post(V1 + "/missions/{mission_id}/evidence")
async def upload_evidence(
    mission_id: str,
    file: UploadFile = File(...),
    category: str = Form(...),
    is_original: bool = Form(True),
    intended_duplicate: bool = Form(False),
    operator_note: Optional[str] = Form(None),
    mode: str = Form("DEMO"),
    session: NxSession = Depends(nx_session),
):
    mission = await _authorize_mission(session, mission_id)
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(400, f"Unknown evidence category: {category}")
    if mode not in {"DEMO", "PILOT", "OPERATIONAL"}:
        raise HTTPException(400, "mode must be DEMO, PILOT, or OPERATIONAL")

    # OPERATIONAL is gated (Directive 006 §17): capability must have passed validation.
    if mode == "OPERATIONAL":
        raise HTTPException(
            403,
            "OPERATIONAL mode is not yet available. Capability must complete "
            "the validation program (Blueprint §17) before operational use.",
        )

    filename = _sanitize_filename(file.filename or "file")
    mime = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    _validate_mime_and_ext(filename, mime)

    # Role must match category expectation.
    role = "original" if is_original else "derivative"
    if is_original and category in DERIVATIVE_CATEGORIES:
        raise HTTPException(400, "Category is derivative-only; is_original must be false")
    if not is_original and category in ORIGINAL_CATEGORIES:
        # Allow derivative for otherwise-original categories only when linked to a source (future block).
        pass

    # Stream to storage with SHA-256; enforce size cap.
    try:
        digest, size, object_key = storage.put(
            tenant_id=session.tenant_id,
            mission_id=mission_id,
            source=file.file,
            max_bytes=MAX_UPLOAD_BYTES,
        )
    except ValueError as e:
        raise HTTPException(413, str(e))

    # Duplicate detection within tenant.
    existing = await nx_collections.evidence_items.find_one({
        "tenant_id": session.tenant_id,
        "content_sha256": digest,
    })
    duplicate = None
    if existing:
        duplicate = {
            "scope": (
                "same_mission" if existing["mission_id"] == mission_id
                else ("same_property" if existing.get("property_id") == mission["property_id"]
                      else "same_tenant")
            ),
            "existing_evidence_id": existing["canonical_id"],
            "existing_mission_id": existing["mission_id"],
        }
        if not intended_duplicate:
            # Return a 409 with the duplicate info; client can retry with intended_duplicate=true
            # or call the /link endpoint. We keep the object bytes since content-addressed
            # storage means they are already present.
            raise HTTPException(409, {"code": "duplicate_detected", **duplicate})

    now = now_iso_utc()
    ev_id = nx_id()

    # Best-effort metadata extraction for images.
    metadata_blob = {"errors": []}
    if role == "original" and mime.startswith("image/"):
        try:
            with storage.open_read(session.tenant_id, mission_id, digest) as f:
                metadata_blob = extract_image_metadata(f.read(), mime)
        except Exception as e:  # pragma: no cover
            metadata_blob = {"errors": [f"reopen:{type(e).__name__}"]}

    evidence = {
        "canonical_id": ev_id,
        "tenant_id": session.tenant_id,
        "mission_id": mission_id,
        "property_id": mission["property_id"],
        "kind": category,
        "role": role,
        "content_sha256": digest,
        "object_key": object_key,
        "size_bytes": size,
        "mime": mime,
        "original_filename": filename,
        "verification_status": "unreviewed",
        "implementation_state": "operational" if role == "derivative" else "operational",
        "availability": "complete",
        "mode": mode,
        "captured_at": None,  # derived from metadata below when present
        "created_by": session.user_id,
        "created_at": now,
        "updated_at": now,
        "version": 1,
    }
    if metadata_blob.get("capture_time"):
        evidence["captured_at"] = metadata_blob["capture_time"]

    await nx_collections.evidence_items.insert_one(dict(evidence))
    await nx_collections.evidence_files.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "evidence_item_id": ev_id,
        "object_key": object_key,
        "size_bytes": size,
        "sha256": digest,
        "created_at": now,
    })
    await nx_collections.evidence_metadata.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "evidence_item_id": ev_id,
        "extracted": metadata_blob,
        "created_at": now,
    })

    if intended_duplicate and existing:
        await nx_collections.evidence_relationships.insert_one({
            "canonical_id": nx_id(),
            "tenant_id": session.tenant_id,
            "left_id": ev_id,
            "right_id": existing["canonical_id"],
            "relationship": "intentional_duplicate_of",
            "created_at": now,
        })

    if operator_note:
        await nx_collections.evidence_metadata.update_one(
            {"evidence_item_id": ev_id},
            {"$set": {"operator_note": operator_note[:2000]}},
        )

    await _write_audit(
        session,
        "evidence.uploaded",
        "evidence_item", ev_id,
        {
            "mission_id": mission_id, "category": category, "role": role,
            "size_bytes": size, "sha256": digest, "duplicate": duplicate,
            "mode": mode,
        },
    )
    return {
        "evidence": strip_mongo_id(evidence),
        "duplicate": duplicate,
        "metadata": metadata_blob,
    }


# ── Evidence list + detail ───────────────────────────────────────────────
@nextgen_r.get(V1 + "/missions/{mission_id}/evidence")
async def list_evidence(
    mission_id: str,
    session: NxSession = Depends(nx_session),
):
    await _authorize_mission(session, mission_id)
    cursor = nx_collections.evidence_items.find({
        "tenant_id": session.tenant_id,
        "mission_id": mission_id,
    }).sort("created_at", -1)
    items = [strip_mongo_id(d) async for d in cursor]
    return {"items": items, "count": len(items)}


@nextgen_r.get(V1 + "/evidence/{evidence_id}")
async def get_evidence(evidence_id: str, session: NxSession = Depends(nx_session)):
    ev = await nx_collections.evidence_items.find_one({
        "canonical_id": evidence_id,
        "tenant_id": session.tenant_id,
    })
    if not ev:
        raise HTTPException(404, "Evidence not found")
    meta = await nx_collections.evidence_metadata.find_one({
        "evidence_item_id": evidence_id,
    })
    rels = [strip_mongo_id(r) async for r in nx_collections.evidence_relationships.find({
        "$or": [{"left_id": evidence_id}, {"right_id": evidence_id}],
        "tenant_id": session.tenant_id,
    })]
    return {
        "evidence": strip_mongo_id(ev),
        "metadata": strip_mongo_id(meta),
        "relationships": rels,
    }


@nextgen_r.get(V1 + "/evidence/{evidence_id}/download")
async def download_evidence(evidence_id: str, session: NxSession = Depends(nx_session)):
    ev = await nx_collections.evidence_items.find_one({
        "canonical_id": evidence_id,
        "tenant_id": session.tenant_id,
    })
    if not ev:
        raise HTTPException(404, "Evidence not found")

    def stream():
        with storage.open_read(ev["tenant_id"], ev["mission_id"], ev["content_sha256"]) as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        stream(),
        media_type=ev.get("mime", "application/octet-stream"),
        headers={
            "Content-Disposition": f'attachment; filename="{ev["original_filename"]}"',
            "X-Content-SHA256": ev["content_sha256"],
        },
    )


# ── Delete pending evidence (only unfinalized) ───────────────────────────
@nextgen_r.delete(V1 + "/evidence/{evidence_id}")
async def delete_evidence(evidence_id: str, session: NxSession = Depends(nx_session)):
    ev = await nx_collections.evidence_items.find_one({
        "canonical_id": evidence_id,
        "tenant_id": session.tenant_id,
    })
    if not ev:
        raise HTTPException(404, "Evidence not found")

    # Refuse deletion if this evidence is part of a finalized package.
    finalized = await nx_collections.mission_packages.find_one({
        "tenant_id": session.tenant_id,
        "mission_id": ev["mission_id"],
        "status": "finalized",
        "evidence_ids": ev["canonical_id"],
    })
    if finalized:
        raise HTTPException(409, "Evidence is part of a finalized package; cannot delete")

    await nx_collections.evidence_items.delete_one({"canonical_id": evidence_id})
    await nx_collections.evidence_files.delete_many({"evidence_item_id": evidence_id})
    await nx_collections.evidence_metadata.delete_many({"evidence_item_id": evidence_id})
    await nx_collections.evidence_relationships.delete_many({
        "$or": [{"left_id": evidence_id}, {"right_id": evidence_id}],
    })
    storage.delete_pending(ev["tenant_id"], ev["mission_id"], ev["content_sha256"])
    await _write_audit(session, "evidence.deleted_pending", "evidence_item", evidence_id, {})
    return {"ok": True}


# ── Link duplicate ───────────────────────────────────────────────────────
class LinkDupBody(BaseModel):
    left_id: str
    right_id: str
    relationship: str = "intentional_duplicate_of"


@nextgen_r.post(V1 + "/evidence/link-duplicate")
async def link_duplicate(body: LinkDupBody, session: NxSession = Depends(nx_session)):
    for eid in (body.left_id, body.right_id):
        ok = await nx_collections.evidence_items.find_one({
            "canonical_id": eid, "tenant_id": session.tenant_id,
        })
        if not ok:
            raise HTTPException(404, f"Evidence not found on tenant: {eid}")
    now = now_iso_utc()
    await nx_collections.evidence_relationships.insert_one({
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "left_id": body.left_id,
        "right_id": body.right_id,
        "relationship": body.relationship,
        "created_at": now,
    })
    await _write_audit(session, "evidence.linked", "evidence_relationships",
                       body.left_id, {"right_id": body.right_id, "relationship": body.relationship})
    return {"ok": True}


# ── Retry metadata extraction ────────────────────────────────────────────
@nextgen_r.post(V1 + "/evidence/{evidence_id}/retry-metadata")
async def retry_metadata(evidence_id: str, session: NxSession = Depends(nx_session)):
    ev = await nx_collections.evidence_items.find_one({
        "canonical_id": evidence_id, "tenant_id": session.tenant_id,
    })
    if not ev:
        raise HTTPException(404, "Evidence not found")
    blob = {"errors": []}
    if ev.get("mime", "").startswith("image/"):
        try:
            with storage.open_read(ev["tenant_id"], ev["mission_id"], ev["content_sha256"]) as f:
                blob = extract_image_metadata(f.read(), ev["mime"])
        except Exception as e:
            blob = {"errors": [f"reopen:{type(e).__name__}"]}
    await nx_collections.evidence_metadata.update_one(
        {"evidence_item_id": evidence_id},
        {"$set": {"extracted": blob, "updated_at": now_iso_utc()}},
        upsert=True,
    )
    await _write_audit(session, "evidence.metadata_reextracted", "evidence_item",
                       evidence_id, {"errors": blob.get("errors", [])})
    return {"metadata": blob}


# ── Mission package: validate + finalize ─────────────────────────────────
async def _validate_package(session: NxSession, mission: Dict[str, Any]) -> Dict[str, Any]:
    profile = PROFILES.get(mission["product"])
    if not profile:
        return {"overall": "FAIL", "results": [{"key": "profile", "result": "FAIL", "message": "unknown product"}]}

    items = [d async for d in nx_collections.evidence_items.find({
        "tenant_id": session.tenant_id, "mission_id": mission["canonical_id"],
    })]
    metas = {m["evidence_item_id"]: m async for m in nx_collections.evidence_metadata.find({
        "tenant_id": session.tenant_id,
    })}

    results: List[Dict[str, Any]] = []
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        by_cat.setdefault(it["kind"], []).append(it)

    all_pass = True
    for req in profile["requirements"]:
        count = sum(1 for x in by_cat.get(req["category"], []) if x["role"] == "original") \
            if req["category"] in ORIGINAL_CATEGORIES else len(by_cat.get(req["category"], []))
        ok = count >= req["min_count"]
        result = "PASS" if ok else ("FAIL" if req.get("required") else "WARNING")
        if not ok and req.get("required"):
            all_pass = False
        results.append({
            "key": f"required:{req['category']}",
            "result": result,
            "message": f"{req['label']} · required {req['min_count']} · got {count}",
        })

    # Metadata extraction present for images
    missing_meta = [it for it in items if it["mime"].startswith("image/")
                    and (not metas.get(it["canonical_id"], {}).get("extracted"))]
    results.append({
        "key": "metadata_present",
        "result": "PASS" if not missing_meta else "WARNING",
        "message": f"{len(missing_meta)} images missing metadata extraction",
    })

    # Checksums must be complete (invariant).
    missing_hash = [it for it in items if not it.get("content_sha256")]
    results.append({
        "key": "checksums_complete",
        "result": "PASS" if not missing_hash else "FAIL",
        "message": f"{len(missing_hash)} items missing checksum",
    })
    if missing_hash:
        all_pass = False

    # AWE-specific: at least one WEATHER_RECORD if product is awe_scan or elite.
    if mission["product"] in ("awe_scan", "elite"):
        env_count = sum(1 for x in by_cat.get("WEATHER_RECORD", []) if x["role"] == "original")
        ok = env_count >= 1
        results.append({
            "key": "awe_environmental_present",
            "result": "PASS" if ok else "FAIL",
            "message": f"WEATHER_RECORD required · found {env_count}",
        })
        if not ok:
            all_pass = False

    # Elite-specific: canonical property must exist (SD-010).
    if mission["product"] == "elite":
        # Placeholder: SD-010 cross-linkage check will validate matched DayScan+AWE.
        results.append({
            "key": "elite_property_link_valid",
            "result": "WARNING",
            "message": "Cross-mission DayScan/AWE pairing check arrives in Wave 2B",
        })

    return {"overall": "PASS" if all_pass else "FAIL", "results": results,
             "counts": {c: len(v) for c, v in by_cat.items()},
             "total_items": len(items)}


@nextgen_r.post(V1 + "/missions/{mission_id}/package/validate")
async def validate_package(mission_id: str, session: NxSession = Depends(nx_session)):
    mission = await _authorize_mission(session, mission_id)
    validation = await _validate_package(session, mission)
    return validation


class FinalizeBody(BaseModel):
    operator_notes: Optional[str] = None


@nextgen_r.post(V1 + "/missions/{mission_id}/package/finalize")
async def finalize_package(
    mission_id: str,
    body: FinalizeBody,
    session: NxSession = Depends(nx_session),
):
    mission = await _authorize_mission(session, mission_id)
    validation = await _validate_package(session, mission)
    if validation["overall"] != "PASS":
        raise HTTPException(422, {
            "code": "package_validation_failed",
            "validation": validation,
        })

    now = now_iso_utc()
    # Determine next package version.
    latest = await nx_collections.mission_packages.find_one(
        {"tenant_id": session.tenant_id, "mission_id": mission_id},
        sort=[("package_version", -1)],
    )
    next_version = ((latest or {}).get("package_version") or 0) + 1
    if latest and latest.get("status") == "finalized" and next_version == latest["package_version"] + 1:
        pass  # amended version is permitted

    items = [d async for d in nx_collections.evidence_items.find({
        "tenant_id": session.tenant_id, "mission_id": mission_id,
    })]
    evidence_ids = [i["canonical_id"] for i in items]
    manifest = {
        "mission_id": mission_id,
        "property_id": mission["property_id"],
        "tenant_id": session.tenant_id,
        "product": mission["product"],
        "package_version": next_version,
        "originals": [
            {"id": i["canonical_id"], "category": i["kind"],
             "filename": i["original_filename"], "sha256": i["content_sha256"],
             "size_bytes": i["size_bytes"], "mime": i["mime"], "mode": i.get("mode", "DEMO")}
            for i in items if i["role"] == "original"
        ],
        "derivatives": [
            {"id": i["canonical_id"], "category": i["kind"],
             "filename": i["original_filename"], "sha256": i["content_sha256"],
             "size_bytes": i["size_bytes"], "mime": i["mime"], "mode": i.get("mode", "DEMO")}
            for i in items if i["role"] == "derivative"
        ],
        "validation": validation,
        "operator_notes": body.operator_notes or None,
        "finalized_by": session.user_id,
        "finalized_at": now,
    }
    import hashlib, json
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

    package = {
        "canonical_id": nx_id(),
        "tenant_id": session.tenant_id,
        "mission_id": mission_id,
        "property_id": mission["property_id"],
        "product": mission["product"],
        "package_version": next_version,
        "status": "finalized",
        "evidence_ids": evidence_ids,
        "manifest": manifest,
        "manifest_digest": manifest_digest,
        "created_by": session.user_id,
        "finalized_by": session.user_id,
        "finalized_at": now,
        "created_at": now,
        "updated_at": now,
        "operator_notes": body.operator_notes or None,
        "retention_class": "raw_evidence",
        "legal_hold_active": False,
    }
    await nx_collections.mission_packages.insert_one(dict(package))

    # Idempotent durable event.
    idem_key = f"evidence.finalized:{mission_id}:{next_version}"
    await emit_outbox_event(
        tenant_id=session.tenant_id,
        event_type="EVIDENCE_PACKAGE_FINALIZED",
        payload={
            "tenant_id": session.tenant_id,
            "property_id": mission["property_id"],
            "mission_id": mission_id,
            "package_id": package["canonical_id"],
            "package_version": next_version,
            "manifest_digest": manifest_digest,
            "product": mission["product"],
            "finalized_by": session.user_id,
            "finalized_at": now,
            "idempotency_key": idem_key,
        },
        idempotency_key=idem_key,
        producer_resource_kind="mission_package",
        producer_resource_id=package["canonical_id"],
    )
    await _write_audit(
        session, "evidence.package_finalized", "mission_package",
        package["canonical_id"],
        {"mission_id": mission_id, "version": next_version, "digest": manifest_digest},
    )

    # Advance mission from Capture Validation (stage 6) if applicable.
    if mission["stage"] < 7:
        await nx_collections.missions.update_one(
            {"canonical_id": mission_id},
            {"$set": {"stage": 7, "updated_at": now, "state": "processing"},
             "$inc": {"version": 1}},
        )
        await _write_audit(session, "mission.stage_advanced", "mission", mission_id,
                            {"from_stage": mission["stage"], "to_stage": 7,
                             "reason": "package_finalized"})

    return {"package": strip_mongo_id(package)}


@nextgen_r.get(V1 + "/missions/{mission_id}/packages")
async def list_packages(mission_id: str, session: NxSession = Depends(nx_session)):
    await _authorize_mission(session, mission_id)
    cursor = nx_collections.mission_packages.find({
        "tenant_id": session.tenant_id, "mission_id": mission_id,
    }).sort("package_version", -1)
    items = [strip_mongo_id(d) async for d in cursor]
    return {"items": items, "count": len(items)}


@nextgen_r.get(V1 + "/packages/{package_id}")
async def get_package(package_id: str, session: NxSession = Depends(nx_session)):
    p = await nx_collections.mission_packages.find_one({
        "canonical_id": package_id, "tenant_id": session.tenant_id,
    })
    if not p:
        raise HTTPException(404, "Package not found")
    return {"package": strip_mongo_id(p)}


@nextgen_r.get(V1 + "/packages/{package_id}/manifest.json")
async def get_manifest_json(package_id: str, session: NxSession = Depends(nx_session)):
    p = await nx_collections.mission_packages.find_one({
        "canonical_id": package_id, "tenant_id": session.tenant_id,
    })
    if not p:
        raise HTTPException(404, "Package not found")
    return p["manifest"]
