"""Estimator Construction Math Engine — E-001 / E-002.

Deterministic construction mathematics and assembly quantity expansion only.
No pricing, margins, Passport writes, or AI arithmetic authority.

Official law: Evidence supplies measurements. Deterministic engines calculate.
AI interprets/advises. Qualified humans approve.
"""
from __future__ import annotations

from .assemblies import (
    ASSEMBLY_ENGINE_VERSION,
    ASSEMBLY_FAMILIES,
    AssemblyExpansion,
    AssemblyLine,
    AssemblyQuantityEngine,
)
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
    ReplayStep,
    build_assembly_ledger,
    build_ledger,
    replay_is_deterministic,
)
from .materials import (
    MATERIALS_ENGINE_VERSION,
    MaterialConversionResult,
    MaterialsConversionEngine,
)
from .provenance import QuantityProvenance, QuantityResult
from .purchase_rules import (
    PURCHASE_RULES,
    PURCHASE_RULES_VERSION,
    PurchaseRule,
    PurchaseRulesRegistry,
    TransparentQuantities,
)
from .units import (
    Dimension,
    Length,
    Measurement,
    parse_feet_inches,
    parse_length_to_feet,
)
from .waste import WASTE_REGISTRY, WASTE_REGISTRY_VERSION, WastePolicy, WasteRegistry

__all__ = [
    "ASSEMBLY_ENGINE_VERSION",
    "ASSEMBLY_FAMILIES",
    "AssemblyExpansion",
    "AssemblyLine",
    "AssemblyQuantityEngine",
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
    "ReplayStep",
    "build_assembly_ledger",
    "build_ledger",
    "replay_is_deterministic",
    "MATERIALS_ENGINE_VERSION",
    "MaterialConversionResult",
    "MaterialsConversionEngine",
    "QuantityProvenance",
    "QuantityResult",
    "PURCHASE_RULES",
    "PURCHASE_RULES_VERSION",
    "PurchaseRule",
    "PurchaseRulesRegistry",
    "TransparentQuantities",
    "Dimension",
    "Length",
    "Measurement",
    "parse_feet_inches",
    "parse_length_to_feet",
    "WASTE_REGISTRY",
    "WASTE_REGISTRY_VERSION",
    "WastePolicy",
    "WasteRegistry",
]
