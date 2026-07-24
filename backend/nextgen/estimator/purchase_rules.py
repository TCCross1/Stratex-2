"""Versioned waste & purchase rules registry (E-002).

Transparent base / waste / purchase quantities only.
No pricing. No AI arithmetic authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
from typing import Dict, Literal, Optional

from .errors import DimensionalError, UnknownInputError
from .units import Dimension, require_known
from .waste import WASTE_REGISTRY, WasteRegistry

RoundingMode = Literal["ceil_packages", "ceil_increment", "exact"]

PURCHASE_RULES_VERSION = "e002.1.0.0"


@dataclass(frozen=True)
class PurchaseRule:
    """Named purchase conversion rule with waste + package rounding."""

    rule_id: str
    version: str
    family: str
    material_code: str
    description: str
    input_unit: str
    input_dimension: Dimension
    purchase_unit: str
    package_size: Decimal
    rounding: RoundingMode
    waste_policy_id: str
    # Multiply base quantity before packaging (e.g. cu_ft → cy = /27 → factor 1/27).
    unit_factor: Decimal = Decimal("1")
    notes: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "version": self.version,
            "family": self.family,
            "material_code": self.material_code,
            "description": self.description,
            "input_unit": self.input_unit,
            "input_dimension": self.input_dimension.value,
            "purchase_unit": self.purchase_unit,
            "package_size": str(self.package_size),
            "rounding": self.rounding,
            "waste_policy_id": self.waste_policy_id,
            "unit_factor": str(self.unit_factor),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class TransparentQuantities:
    """Base / waste / purchase breakdown — never a price."""

    base_quantity: Decimal
    waste_quantity: Decimal
    quantity_with_waste: Decimal
    purchase_quantity: Decimal
    base_unit: str
    purchase_unit: str
    waste_policy_id: str
    purchase_rule_id: str
    purchase_rule_version: str
    rounding_mode: str
    package_size: Decimal

    def as_dict(self) -> dict:
        return {
            "base_quantity": str(self.base_quantity),
            "waste_quantity": str(self.waste_quantity),
            "quantity_with_waste": str(self.quantity_with_waste),
            "purchase_quantity": str(self.purchase_quantity),
            "base_unit": self.base_unit,
            "purchase_unit": self.purchase_unit,
            "waste_policy_id": self.waste_policy_id,
            "purchase_rule_id": self.purchase_rule_id,
            "purchase_rule_version": self.purchase_rule_version,
            "rounding_mode": self.rounding_mode,
            "package_size": str(self.package_size),
        }


def _rule(
    rule_id: str,
    version: str,
    family: str,
    material_code: str,
    description: str,
    input_unit: str,
    input_dimension: Dimension,
    purchase_unit: str,
    package_size: str,
    rounding: RoundingMode,
    waste_policy_id: str,
    unit_factor: str = "1",
    notes: Optional[str] = None,
) -> PurchaseRule:
    size = Decimal(package_size)
    if size <= 0:
        raise DimensionalError(f"package_size must be > 0 for rule {rule_id}")
    return PurchaseRule(
        rule_id=rule_id,
        version=version,
        family=family,
        material_code=material_code,
        description=description,
        input_unit=input_unit,
        input_dimension=input_dimension,
        purchase_unit=purchase_unit,
        package_size=size,
        rounding=rounding,
        waste_policy_id=waste_policy_id,
        unit_factor=Decimal(unit_factor),
        notes=notes,
    )


class PurchaseRulesRegistry:
    """Immutable-by-convention purchase / packaging rules."""

    def __init__(
        self,
        rules: Dict[str, PurchaseRule],
        *,
        waste_registry: WasteRegistry | None = None,
        registry_version: str = PURCHASE_RULES_VERSION,
    ) -> None:
        self._rules = dict(rules)
        self.waste = waste_registry or WASTE_REGISTRY
        self.registry_version = registry_version

    def get(self, rule_id: Optional[str]) -> PurchaseRule:
        if rule_id is None:
            raise UnknownInputError("purchase_rule_id", "purchase rule id is required")
        if rule_id not in self._rules:
            raise UnknownInputError(
                "purchase_rule_id",
                f"unknown purchase rule {rule_id!r}",
            )
        return self._rules[rule_id]

    def list_ids(self) -> list[str]:
        return sorted(self._rules.keys())

    def list_by_family(self, family: str) -> list[str]:
        return sorted(r.rule_id for r in self._rules.values() if r.family == family)

    def as_dict(self) -> dict:
        return {k: v.as_dict() for k, v in sorted(self._rules.items())}

    def apply(
        self,
        rule_id: Optional[str],
        base_quantity: Optional[Decimal | int | float | str],
        *,
        input_unit: Optional[str] = None,
        input_dimension: Optional[Dimension] = None,
    ) -> TransparentQuantities:
        """Apply waste + unit conversion + package rounding transparently."""
        rule = self.get(rule_id)
        base = require_known(base_quantity, name="base_quantity")
        if base < 0:
            raise DimensionalError("base_quantity cannot be negative")
        if rule.package_size <= 0:
            raise DimensionalError("package_size must be > 0")
        if rule.unit_factor <= 0:
            raise DimensionalError("unit_factor must be > 0")

        if input_unit is not None and input_unit != rule.input_unit:
            raise DimensionalError(
                f"incompatible units: got {input_unit!r}, rule expects {rule.input_unit!r}"
            )
        if input_dimension is not None and input_dimension != rule.input_dimension:
            raise DimensionalError(
                f"incompatible dimension: got {input_dimension.value!r}, "
                f"rule expects {rule.input_dimension.value!r}"
            )

        with_waste = self.waste.apply(rule.waste_policy_id, base)
        waste_qty = with_waste - base

        # Convert into purchase-unit space before packaging.
        converted = with_waste * rule.unit_factor

        if rule.rounding == "exact":
            purchase = converted
        elif rule.rounding == "ceil_packages":
            if converted == 0:
                purchase = Decimal("0")
            else:
                packages = (converted / rule.package_size).to_integral_value(
                    rounding=ROUND_CEILING
                )
                purchase = packages  # purchase_unit is packages/pieces/bundles
        elif rule.rounding == "ceil_increment":
            if converted == 0:
                purchase = Decimal("0")
            else:
                units = (converted / rule.package_size).to_integral_value(
                    rounding=ROUND_CEILING
                )
                purchase = units * rule.package_size
        else:
            raise UnknownInputError(
                "rounding",
                f"unknown rounding mode {rule.rounding!r}",
            )

        return TransparentQuantities(
            base_quantity=base,
            waste_quantity=waste_qty,
            quantity_with_waste=with_waste,
            purchase_quantity=purchase,
            base_unit=rule.input_unit,
            purchase_unit=rule.purchase_unit,
            waste_policy_id=rule.waste_policy_id,
            purchase_rule_id=rule.rule_id,
            purchase_rule_version=rule.version,
            rounding_mode=rule.rounding,
            package_size=rule.package_size,
        )


# Locked E-002 starter purchase rules — change requires version bump + tests.
PURCHASE_RULES = PurchaseRulesRegistry(
    {
        "roofing.shingles.bundle.v1": _rule(
            "roofing.shingles.bundle.v1",
            "1.0.0",
            "roofing",
            "asphalt_shingles",
            "Asphalt shingle bundles (33.3 sq ft coverage)",
            "sq_ft",
            Dimension.AREA,
            "bundle",
            "33.3",
            "ceil_packages",
            "roofing.shingles.v1",
        ),
        "roofing.underlayment.roll.v1": _rule(
            "roofing.underlayment.roll.v1",
            "1.0.0",
            "roofing",
            "underlayment",
            "Felt / synthetic underlayment rolls (400 sq ft)",
            "sq_ft",
            Dimension.AREA,
            "roll",
            "400",
            "ceil_packages",
            "roofing.felt.v1",
        ),
        "roofing.ridge.bundle.v1": _rule(
            "roofing.ridge.bundle.v1",
            "1.0.0",
            "roofing",
            "ridge_cap",
            "Ridge cap bundles (20 LF coverage)",
            "ft",
            Dimension.LENGTH,
            "bundle",
            "20",
            "ceil_packages",
            "roofing.shingles.v1",
        ),
        "siding.panel.piece.v1": _rule(
            "siding.panel.piece.v1",
            "1.0.0",
            "siding",
            "siding_panel",
            "Fiber-cement / composite panels (32 sq ft)",
            "sq_ft",
            Dimension.AREA,
            "piece",
            "32",
            "ceil_packages",
            "siding.composite.v1",
        ),
        "concrete.ready_mix.cy.v1": _rule(
            "concrete.ready_mix.cy.v1",
            "1.0.0",
            "concrete",
            "ready_mix",
            "Ready-mix purchase CY rounded to 0.25 CY",
            "cu_ft",
            Dimension.VOLUME,
            "cu_yd",
            "0.25",
            "ceil_increment",
            "concrete.slab.v1",
            unit_factor=str(Decimal("1") / Decimal("27")),
            notes="unit_factor converts cu_ft to cu_yd; not a price",
        ),
        "flooring.plank.carton.v1": _rule(
            "flooring.plank.carton.v1",
            "1.0.0",
            "flooring",
            "flooring_plank",
            "Engineered plank cartons (22 sq ft)",
            "sq_ft",
            Dimension.AREA,
            "carton",
            "22",
            "ceil_packages",
            "flooring.plank.v1",
        ),
        "drywall.sheet.4x8.v1": _rule(
            "drywall.sheet.4x8.v1",
            "1.0.0",
            "drywall",
            "drywall_sheet",
            "4x8 drywall sheets (32 sq ft)",
            "sq_ft",
            Dimension.AREA,
            "sheet",
            "32",
            "ceil_packages",
            "drywall.sheet.v1",
        ),
        "insulation.batt.bag.v1": _rule(
            "insulation.batt.bag.v1",
            "1.0.0",
            "insulation",
            "batt_insulation",
            "Batt insulation bags (88 sq ft coverage)",
            "sq_ft",
            Dimension.AREA,
            "bag",
            "88",
            "ceil_packages",
            "insulation.batt.v1",
        ),
    }
)
