"""
Evidence Ingest Stub — Field Test v1
Stratex Core

Accepts media items (RGB / thermal) from a completed capture session
and assembles them into a Canonical Mission Package ready for sealing.

This is the bridge between field capture (Matrice 4E / 4T) and the
sealing → governed publish path. It does not talk to Passport.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .mission_package_seal import create_empty_package


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_placeholder(label: str) -> str:
    """Deterministic placeholder hash for demo / test media."""
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def ingest_media_item(
    media_type: str,
    capture_timestamp: str,
    camera_model: str,
    size_bytes: int,
    content_hash: Optional[str] = None,
    geolocation: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Build a single evidence manifest entry."""
    return {
        "item_id": str(uuid.uuid4()),
        "content_hash": content_hash or _sha256_placeholder(f"{media_type}:{capture_timestamp}:{camera_model}"),
        "media_type": media_type,  # RGB | THERMAL | RADIOMETRIC | OTHER
        "capture_timestamp": capture_timestamp,
        "camera_model": camera_model,
        "size_bytes": size_bytes,
        "geolocation": geolocation,
    }


def assemble_package_from_capture(
    mission_id: str,
    tenant_id: str,
    property_id: str,
    capture_type: str,
    media_items: List[Dict[str, Any]],
    aircraft: str = "DJI Matrice 4E",
    pilot: Optional[str] = None,
    weather: Optional[str] = None,
    rtk_status: str = "UNKNOWN",
    geometry_candidate: Optional[Dict[str, Any]] = None,
    awe_candidate: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Assemble a full Canonical Mission Package from capture outputs.
    The returned package is ready to be passed to seal_package() / prepare_for_governed_publish().
    """
    pkg = create_empty_package(
        mission_id=mission_id,
        tenant_id=tenant_id,
        property_id=property_id,
        capture_type=capture_type,
    )

    pkg["mission_metadata"].update({
        "aircraft": aircraft,
        "pilot": pilot,
        "weather": weather,
        "rtk_status": rtk_status,
        "capture_date": _now_iso(),
        "media_count": len(media_items),
    })

    pkg["evidence_manifest"]["items"] = media_items

    if geometry_candidate:
        pkg["geometry_candidate"] = geometry_candidate
    if awe_candidate:
        pkg["awe_candidate"] = awe_candidate

    return pkg


def build_demo_capture_package(
    mission_id: str = "MISSION-FT-INGEST-001",
    tenant_id: str = "tenant-stratex-demo",
    property_id: str = "prop-1234-infinity-orlando",
) -> Dict[str, Any]:
    """Convenience: realistic demo package as if a 4E flight just completed."""
    items = [
        ingest_media_item("RGB", "2026-08-01T14:32:00Z", "Matrice 4E Wide", 12_400_000),
        ingest_media_item("RGB", "2026-08-01T14:33:15Z", "Matrice 4E Wide", 11_800_000),
        ingest_media_item("RGB", "2026-08-01T14:34:40Z", "Matrice 4E Medium Tele", 9_200_000),
    ]
    geometry = {
        "planes": [
            {"id": "front-slope", "confidence": 0.93, "area_sqft": 820, "pitch": "6/12"},
            {"id": "rear-slope", "confidence": 0.90, "area_sqft": 780, "pitch": "6/12"},
            {"id": "low-conf", "confidence": 0.44, "area_sqft": 30},
        ],
        "measurements": {
            "total_roof_area_sqft": 1630,
            "ridge_length_ft": 42,
            "eave_length_ft": 96,
        },
    }
    awe = {
        "findings": [
            {
                "id": "awe-g1",
                "severity": "HIGH",
                "category": "ROOF",
                "description": "Granule loss pattern on front slope",
                "location": "Front slope",
                "truth_classification": "ESTIMATED",
            }
        ]
    }
    return assemble_package_from_capture(
        mission_id=mission_id,
        tenant_id=tenant_id,
        property_id=property_id,
        capture_type="DAYTIME_PRECISION_MAPPING",
        media_items=items,
        aircraft="DJI Matrice 4E",
        pilot="Anthony Cross",
        weather="Clear, 79F",
        rtk_status="FIXED",
        geometry_candidate=geometry,
        awe_candidate=awe,
    )
