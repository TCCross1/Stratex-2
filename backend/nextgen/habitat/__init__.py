"""Habitat read-model consumer package (HABITAT-P-002).

Read-only homeowner-safe projection consumer. Habitat never writes canonical
Passport truth — no ledger append/publish helpers and no ledger inserts.
"""
from __future__ import annotations

from .privacy import redact_homeowner_secrets
from .read_model import (
    MODULE_IDENTITY,
    HabitatPropertyReadSource,
    HabitatReadModelConsumer,
    build_homeowner_property_read_model,
)
from .reality_model import (
    RealityLayerKind,
    RealityModelBundle,
    RealityReferenceState,
    build_reality_model,
)

__all__ = [
    "MODULE_IDENTITY",
    "HabitatPropertyReadSource",
    "HabitatReadModelConsumer",
    "RealityLayerKind",
    "RealityModelBundle",
    "RealityReferenceState",
    "build_homeowner_property_read_model",
    "build_reality_model",
    "redact_homeowner_secrets",
]
