"""Materials conversion engine (E-002).

Deterministic base → waste → purchase conversion with formula / version /
rounding / waste provenance. No pricing. No AI arithmetic authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .errors import DimensionalError, UnknownInputError
from .formulas import FORMULA_REGISTRY, FormulaRegistry
from .provenance import QuantityProvenance, QuantityResult
from .purchase_rules import (
    PURCHASE_RULES,
    PURCHASE_RULES_VERSION,
    PurchaseRulesRegistry,
    TransparentQuantities,
)
from .units import Dimension, Measurement, NumberLike, require_known

MATERIALS_ENGINE_VERSION = "e002.1.0.0"
CONVERSION_FORMULA_ID = "materials.convert.v1"


@dataclass(frozen=True)
class MaterialConversionResult:
    """Full materials conversion with transparent quantities + provenance."""

    transparent: TransparentQuantities
    purchase_result: QuantityResult
    base_result: QuantityResult
    formula_id: str
    formula_version: str
    engine_version: str

    def as_dict(self) -> dict:
        return {
            "transparent": self.transparent.as_dict(),
            "purchase_result": self.purchase_result.as_dict(),
            "base_result": self.base_result.as_dict(),
            "formula_id": self.formula_id,
            "formula_version": self.formula_version,
            "engine_version": self.engine_version,
        }


class MaterialsConversionEngine:
    """Convert net material quantities into purchase packages with provenance."""

    def __init__(
        self,
        *,
        purchase_rules: PurchaseRulesRegistry | None = None,
        formula_registry: FormulaRegistry | None = None,
        engine_version: str = MATERIALS_ENGINE_VERSION,
    ) -> None:
        self.purchase_rules = purchase_rules or PURCHASE_RULES
        self.formulas = formula_registry or FORMULA_REGISTRY
        self.engine_version = engine_version

    def convert(
        self,
        base_quantity: Optional[NumberLike],
        *,
        purchase_rule_id: Optional[str],
        input_unit: Optional[str] = None,
        input_dimension: Optional[Dimension] = None,
    ) -> MaterialConversionResult:
        if purchase_rule_id is None:
            raise UnknownInputError("purchase_rule_id", "purchase rule id is required")

        rule = self.purchase_rules.get(purchase_rule_id)
        base = require_known(base_quantity, name="base_quantity")
        if base < 0:
            raise DimensionalError("base_quantity cannot be negative")

        # Zero package size must never produce a purchase quantity.
        if rule.package_size <= 0:
            raise DimensionalError("package_size must be > 0")

        unit = input_unit if input_unit is not None else rule.input_unit
        dim = input_dimension if input_dimension is not None else rule.input_dimension

        transparent = self.purchase_rules.apply(
            purchase_rule_id,
            base,
            input_unit=unit,
            input_dimension=dim,
        )

        spec = self.formulas.get(CONVERSION_FORMULA_ID)
        input_refs = {
            "base_quantity": str(transparent.base_quantity),
            "waste_quantity": str(transparent.waste_quantity),
            "quantity_with_waste": str(transparent.quantity_with_waste),
            "purchase_quantity": str(transparent.purchase_quantity),
            "purchase_rule_id": transparent.purchase_rule_id,
            "purchase_rule_version": transparent.purchase_rule_version,
            "waste_policy_id": transparent.waste_policy_id,
            "rounding_mode": transparent.rounding_mode,
            "package_size": str(transparent.package_size),
            "unit_factor": str(rule.unit_factor),
            "input_unit": unit,
            "base_unit": transparent.base_unit,
            "purchase_unit": transparent.purchase_unit,
            "material_code": transparent.material_code or rule.material_code,
            "measured_area_sqft": (
                None
                if transparent.measured_area_sqft is None
                else str(transparent.measured_area_sqft)
            ),
            "base_squares": (
                None if transparent.base_squares is None else str(transparent.base_squares)
            ),
            "waste_squares": (
                None
                if transparent.waste_squares is None
                else str(transparent.waste_squares)
            ),
            "purchase_squares": (
                None
                if transparent.purchase_squares is None
                else str(transparent.purchase_squares)
            ),
            "purchase_rules_version": self.purchase_rules.registry_version
            or PURCHASE_RULES_VERSION,
        }

        base_result = QuantityResult(
            quantity=Measurement(transparent.base_quantity, unit, dim),
            provenance=QuantityProvenance(
                formula_id=spec.formula_id,
                formula_version=spec.version,
                engine_version=self.engine_version,
                input_refs={"stage": "base", **input_refs},
                waste_policy_id=transparent.waste_policy_id,
                notes="base quantity before waste/purchase conversion",
            ),
            confidence="deterministic",
            unknown_state=None,
        )

        purchase_dim = (
            Dimension.VOLUME
            if transparent.purchase_unit == "cu_yd"
            else Dimension.COUNT
        )
        purchase_result = QuantityResult(
            quantity=Measurement(
                transparent.purchase_quantity,
                transparent.purchase_unit,
                purchase_dim,
            ),
            provenance=QuantityProvenance(
                formula_id=spec.formula_id,
                formula_version=spec.version,
                engine_version=self.engine_version,
                input_refs=input_refs,
                waste_policy_id=transparent.waste_policy_id,
                notes="purchase quantity after waste + package rounding; not a price",
            ),
            confidence="deterministic",
            unknown_state=None,
        )

        return MaterialConversionResult(
            transparent=transparent,
            purchase_result=purchase_result,
            base_result=base_result,
            formula_id=spec.formula_id,
            formula_version=spec.version,
            engine_version=self.engine_version,
        )
