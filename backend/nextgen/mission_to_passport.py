"""
Mission Package → Passport Handoff
Stratex Core — Field Test v1

Takes a sealed Canonical Mission Package and prepares it
for the single governed publisher → Passport writer path.
Never writes to Passport itself.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .mission_package_seal import seal_package, verify_seal, SealingError


class HandoffError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def prepare_for_governed_publish(
    raw_package: Dict[str, Any],
    expected_revision: Optional[int] = None,
    expected_head_hash: Optional[str] = None,
    seal_key: Optional[bytes] = None,
) -> Dict[str, Any]:
    """
    1. Seal the package (or verify if already sealed)
    2. Build the payload that governed_publish expects
    3. Return a ready-to-submit publication request

    Does NOT call governed_publish or append_entry.
    That remains the sole responsibility of the governed publisher.
    """
    # Seal if not already sealed
    if not raw_package.get("seal_record") or not raw_package["seal_record"].get("signature"):
        try:
            sealed = seal_package(raw_package, seal_key=seal_key)
        except SealingError as e:
            raise HandoffError(e.code, e.message)
    else:
        sealed = raw_package
        if not verify_seal(sealed, seal_key=seal_key):
            raise HandoffError("SEAL_INVALID", "Package seal verification failed")

    # Build the publication payload
    # This is what gets handed to governed_publish → append_entry
    publication_request = {
        "source_type": "mission_package",
        "source_id": sealed["package_id"],
        "entry_type": "MISSION_EVIDENCE",
        "tenant_id": sealed["tenant_id"],
        "property_id": sealed["property_id"],
        "payload": {
            "package_id": sealed["package_id"],
            "mission_id": sealed["mission_id"],
            "content_hash": sealed["content_hash"],
            "capture_type": sealed.get("mission_metadata", {}).get("capture_type"),
            "geometry_summary": {
                "plane_count": len(
                    [p for p in sealed.get("geometry_candidate", {}).get("planes", [])
                     if p.get("truth_classification") != "WITHHELD"]
                ),
                "withheld_count": len(
                    [p for p in sealed.get("geometry_candidate", {}).get("planes", [])
                     if p.get("truth_classification") == "WITHHELD"]
                ),
            },
            "awe_summary": {
                "finding_count": len(sealed.get("awe_candidate", {}).get("findings", [])),
            },
            "seal": sealed["seal_record"],
        },
        "idempotency_key": f"mission_package:{sealed['package_id']}:{sealed['content_hash'][:16]}",
        "expected_revision": expected_revision,
        "expected_head_hash": expected_head_hash,
        "require_expected_state": True,
    }

    return {
        "status": "READY_FOR_GOVERNED_PUBLISH",
        "sealed_package": sealed,
        "publication_request": publication_request,
    }
