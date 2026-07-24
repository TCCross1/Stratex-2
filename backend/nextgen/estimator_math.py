"""Compatibility facade for E-001 / E-002 estimator engines.

Prefer importing from `nextgen.estimator`. This module exists so call sites
may use `from nextgen import estimator_math` as specified in the E-001 path.
"""
from __future__ import annotations

from nextgen.estimator import *  # noqa: F401,F403
from nextgen.estimator import (
    ASSEMBLY_ENGINE_VERSION,
    AssemblyQuantityEngine,
    ENGINE_VERSION,
    ConstructionMathEngine,
    EstimateCalculationLedger,
    FORMULA_REGISTRY,
    LEDGER_SCHEMA_VERSION,
    MATERIALS_ENGINE_VERSION,
    MaterialsConversionEngine,
    PURCHASE_RULES,
    WASTE_REGISTRY,
    build_assembly_ledger,
    build_ledger,
    parse_feet_inches,
)
