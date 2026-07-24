"""Compatibility facade for E-001 Construction Math Engine.

Prefer importing from `nextgen.estimator`. This module exists so call sites
may use `from nextgen import estimator_math` as specified in the E-001 path.
"""
from __future__ import annotations

from nextgen.estimator import *  # noqa: F401,F403
from nextgen.estimator import (
    ENGINE_VERSION,
    ConstructionMathEngine,
    EstimateCalculationLedger,
    FORMULA_REGISTRY,
    LEDGER_SCHEMA_VERSION,
    WASTE_REGISTRY,
    build_ledger,
    parse_feet_inches,
)
