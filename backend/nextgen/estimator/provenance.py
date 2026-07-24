"""Quantity provenance structures for estimator math outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping, Optional

from .units import Dimension, Measurement


@dataclass(frozen=True)
class QuantityProvenance:
    """Provenance attached to every computed quantity."""

    formula_id: str
    formula_version: str
    engine_version: str
    input_refs: Mapping[str, Any] = field(default_factory=dict)
    waste_policy_id: Optional[str] = None
    source_type: str = "deterministic_engine"
    notes: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "formula_id": self.formula_id,
            "formula_version": self.formula_version,
            "engine_version": self.engine_version,
            "input_refs": dict(self.input_refs),
            "waste_policy_id": self.waste_policy_id,
            "source_type": self.source_type,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class QuantityResult:
    """Computed quantity with provenance, confidence, and unknown_state."""

    quantity: Measurement
    provenance: QuantityProvenance
    confidence: str = "deterministic"
    unknown_state: Optional[str] = None  # None means fully known

    @property
    def value(self) -> Decimal:
        return self.quantity.value

    @property
    def unit(self) -> str:
        return self.quantity.unit

    @property
    def dimension(self) -> Dimension:
        return self.quantity.dimension

    def as_dict(self) -> dict:
        return {
            "quantity": self.quantity.as_dict(),
            "provenance": self.provenance.as_dict(),
            "confidence": self.confidence,
            "unknown_state": self.unknown_state,
        }

    def to_mapping(self) -> dict:
        return self.as_dict()
