"""Estimator Construction Math Engine — E-001 foundation.

Deterministic construction mathematics only. No pricing, margins, Passport
writes, or AI arithmetic authority.

Official law: Evidence supplies measurements. Deterministic engines calculate.
AI interprets/advises. Qualified humans approve.
"""
from __future__ import annotations

from .engine import ConstructionMathEngine, ENGINE_VERSION
from .errors import (
    DimensionalError,
    EstimatorMathError,
    ParseError,
    UnknownInputError,
)
from .formulas import FORMULA_REGISTRY, FormulaRegistry, FormulaSpec
from .ledger import (
    EstimateCalculationLedger,
    LedgerEntry,
    LEDGER_SCHEMA_VERSION,
    build_ledger,
)
from .provenance import QuantityProvenance, QuantityResult
from .units import (
    Dimension,
    Length,
    Measurement,
    parse_feet_inches,
    parse_length_to_feet,
)
from .waste import WASTE_REGISTRY, WastePolicy, WasteRegistry

__all__ = [
    "ConstructionMathEngine",
    "ENGINE_VERSION",
    "DimensionalError",
    "EstimatorMathError",
    "ParseError",
    "UnknownInputError",
    "FORMULA_REGISTRY",
    "FormulaRegistry",
    "FormulaSpec",
    "EstimateCalculationLedger",
    "LedgerEntry",
    "LEDGER_SCHEMA_VERSION",
    "build_ledger",
    "QuantityProvenance",
    "QuantityResult",
    "Dimension",
    "Length",
    "Measurement",
    "parse_feet_inches",
    "parse_length_to_feet",
    "WASTE_REGISTRY",
    "WastePolicy",
    "WasteRegistry",
]
