"""Formula / version registry for Construction Math Engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .errors import UnknownInputError


@dataclass(frozen=True)
class FormulaSpec:
    formula_id: str
    version: str
    name: str
    description: str
    dimension: str
    expression: str

    def as_dict(self) -> dict:
        return {
            "formula_id": self.formula_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "dimension": self.dimension,
            "expression": self.expression,
        }


class FormulaRegistry:
    def __init__(self, formulas: Dict[str, FormulaSpec]) -> None:
        self._formulas = dict(formulas)

    def get(self, formula_id: Optional[str]) -> FormulaSpec:
        if formula_id is None:
            raise UnknownInputError("formula_id", "formula id is required")
        if formula_id not in self._formulas:
            raise UnknownInputError("formula_id", f"unknown formula {formula_id!r}")
        return self._formulas[formula_id]

    def list_ids(self) -> list[str]:
        return sorted(self._formulas.keys())

    @property
    def registry_version(self) -> str:
        # Aggregate version for ledger provenance — bump when any formula changes.
        return "e001.1.0.0"

    def as_dict(self) -> dict:
        return {k: v.as_dict() for k, v in sorted(self._formulas.items())}


def _f(
    formula_id: str,
    version: str,
    name: str,
    description: str,
    dimension: str,
    expression: str,
) -> FormulaSpec:
    return FormulaSpec(
        formula_id=formula_id,
        version=version,
        name=name,
        description=description,
        dimension=dimension,
        expression=expression,
    )


FORMULA_REGISTRY = FormulaRegistry(
    {
        "linear.sum.v1": _f(
            "linear.sum.v1",
            "1.0.0",
            "Linear sum",
            "Sum of length segments in feet",
            "length",
            "sum(length_i_ft)",
        ),
        "area.rectangle.v1": _f(
            "area.rectangle.v1",
            "1.0.0",
            "Rectangular area",
            "length_ft * width_ft",
            "area",
            "length_ft * width_ft",
        ),
        "area.triangle.v1": _f(
            "area.triangle.v1",
            "1.0.0",
            "Triangular area",
            "0.5 * base_ft * height_ft",
            "area",
            "0.5 * base_ft * height_ft",
        ),
        "volume.rectangular.v1": _f(
            "volume.rectangular.v1",
            "1.0.0",
            "Rectangular volume",
            "length_ft * width_ft * depth_ft",
            "volume",
            "length_ft * width_ft * depth_ft",
        ),
        "board_foot.v1": _f(
            "board_foot.v1",
            "1.0.0",
            "Board feet",
            "(thickness_in * width_in * length_ft) / 12 * piece_count",
            "board_foot",
            "(T_in * W_in * L_ft) / 12 * N",
        ),
        "roofing_square.v1": _f(
            "roofing_square.v1",
            "1.0.0",
            "Roofing squares",
            "area_sqft / 100",
            "roofing_square",
            "area_sqft / 100",
        ),
        "concrete.volume.v1": _f(
            "concrete.volume.v1",
            "1.0.0",
            "Concrete cubic feet",
            "length_ft * width_ft * thickness_ft",
            "volume",
            "L_ft * W_ft * T_ft",
        ),
        "concrete.purchase_cy.v1": _f(
            "concrete.purchase_cy.v1",
            "1.0.0",
            "Concrete purchase cubic yards",
            "ceil_to_increment(cu_ft / 27)",
            "volume",
            "ceil_to_inc(cu_ft / 27, increment_cy)",
        ),
        "piece.round.v1": _f(
            "piece.round.v1",
            "1.0.0",
            "Piece / package rounding",
            "ceil(net / coverage_per_piece) pieces",
            "count",
            "ceil(net / coverage)",
        ),
        "waste.apply.v1": _f(
            "waste.apply.v1",
            "1.0.0",
            "Apply waste/overage",
            "net * waste_multiplier",
            "unknown",
            "net * policy.multiplier",
        ),
    }
)
