"""NextGen pydantic models — Phase 1a seed set.

Covers organizations, users (bridge to legacy identity), properties, missions.
Full data-model coverage arrives incrementally in Phase 1b/1c/1d.

All models are aligned with Canonical Data Model v1.0 field pattern:
`canonical_id`, `tenant_id`, `created_at`, `updated_at`, `version`.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ── Shared value-object stubs (Data Model v1.0 §2) ──────────────────────
class Address(BaseModel):
    line1: str
    line2: Optional[str] = None
    city: str
    region: str
    postal_code: str
    country_iso: str = "US"
    normalized: bool = False
    normalization_source: Literal[
        "user", "geocoder", "parcel_service", "human_qa"
    ] = "user"


class GeoCoordinate(BaseModel):
    lat: float
    lon: float
    elevation_m: Optional[float] = None
    precision_m: float = 5.0  # precision floor per Blueprint §11.2
    crs: str = "EPSG:4326"
    source: Literal["gps", "rtk", "parcel", "geocoder", "manual"] = "manual"


class ParcelIdentifier(BaseModel):
    jurisdiction: str
    parcel_number: str
    source: Literal["county_gis", "contractor", "imported"] = "contractor"


class Money(BaseModel):
    amount_cents: int  # minor units
    currency: str = "USD"


# ── Domain 1 · Tenants and identity ─────────────────────────────────────
class OrganizationCreate(BaseModel):
    name: str
    legal_name: Optional[str] = None
    jurisdiction: str = "US"
    contact_email: str
    contact_phone: Optional[str] = None


class Organization(BaseModel):
    canonical_id: str
    name: str
    legal_name: Optional[str] = None
    jurisdiction: str
    status: Literal["active", "suspended", "closed"] = "active"
    contact_email: str
    contact_phone: Optional[str] = None
    billing_status: Literal["good", "hold", "delinquent"] = "good"
    created_at: str
    updated_at: str
    version: int = 1


# ── Domain 2 · Properties ───────────────────────────────────────────────
class PropertyCreate(BaseModel):
    address: Address
    coordinate: Optional[GeoCoordinate] = None
    parcel: Optional[ParcelIdentifier] = None
    unit_label: Optional[str] = None


class PropertyIdentityCandidate(BaseModel):
    candidate_property_id: str
    score: float
    matched_slots: List[str] = Field(default_factory=list)


class Property(BaseModel):
    canonical_id: str
    tenant_id: str
    status: Literal["active", "superseded", "merged_into", "split_from"] = "active"
    truth_score_band: int = 5  # 10-point band (bands 1..10)
    address: Address
    coordinate: Optional[GeoCoordinate] = None
    parcel: Optional[ParcelIdentifier] = None
    unit_label: Optional[str] = None
    superseded_by_id: Optional[str] = None
    created_at: str
    updated_at: str
    version: int = 1


# ── Domain 3 · Missions ─────────────────────────────────────────────────
ProductKey = Literal["dayscan", "awe_scan", "elite"]

MissionState = Literal[
    "planned", "validated", "in_flight", "capture_finalized",
    "processing", "awaiting_qa", "reported", "closed", "failed", "canceled",
]


class MissionCreate(BaseModel):
    property_id: str
    product: ProductKey
    scheduled_for: Optional[str] = None
    notes: Optional[str] = None


class Mission(BaseModel):
    canonical_id: str
    tenant_id: str
    property_id: str
    product: ProductKey
    state: MissionState = "planned"
    stage: int = 1  # Blueprint §22 stage 1..15
    dispatcher_user_id: str
    pilot_user_id: Optional[str] = None
    scheduled_for: Optional[str] = None
    notes: Optional[str] = None
    price: Money
    estimated_cost: Money
    parent_failed_mission_id: Optional[str] = None
    created_at: str
    updated_at: str
    version: int = 1
