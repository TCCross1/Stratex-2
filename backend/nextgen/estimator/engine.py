"""Construction Math Engine — deterministic quantity calculations.

NO language model may perform final authoritative arithmetic.
This module is the sole E-001 calculator for construction quantities.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Optional, Sequence, Union

from .errors import DimensionalError, UnknownInputError
from .formulas import FORMULA_REGISTRY, FormulaRegistry
from .provenance import QuantityProvenance, QuantityResult
from .units import (
    Dimension,
    Length,
    Measurement,
    NumberLike,
    parse_feet_inches,
    require_known,
)
from .waste import WASTE_REGISTRY, WasteRegistry

ENGINE_VERSION = "e001.1.0.0"

LengthInput = Union[Length, NumberLike, str]


class ConstructionMathEngine:
    """Deterministic construction mathematics facade."""

    def __init__(
        self,
        *,
        formula_registry: FormulaRegistry | None = None,
        waste_registry: WasteRegistry | None = None,
        engine_version: str = ENGINE_VERSION,
    ) -> None:
        self.formulas = formula_registry or FORMULA_REGISTRY
        self.waste = waste_registry or WASTE_REGISTRY
        self.engine_version = engine_version

    # ── helpers ─────────────────────────────────────────────────────────

    def _resolve_feet(self, value: Optional[LengthInput], *, name: str) -> Decimal:
        if value is None:
            raise UnknownInputError(name, "missing length input")
        if isinstance(value, Length):
            return value.feet
        if isinstance(value, str):
            return parse_feet_inches(value).feet
        return require_known(value, name=name)

    def _result(
        self,
        *,
        formula_id: str,
        value: Decimal,
        unit: str,
        dimension: Dimension,
        input_refs: dict,
        waste_policy_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> QuantityResult:
        spec = self.formulas.get(formula_id)
        provenance = QuantityProvenance(
            formula_id=spec.formula_id,
            formula_version=spec.version,
            engine_version=self.engine_version,
            input_refs=input_refs,
            waste_policy_id=waste_policy_id,
            notes=notes,
        )
        return QuantityResult(
            quantity=Measurement(value, unit, dimension),
            provenance=provenance,
            confidence="deterministic",
            unknown_state=None,
        )

    # ── linear / area / volume ──────────────────────────────────────────

    def linear_sum(self, segments: Optional[Sequence[LengthInput]]) -> QuantityResult:
        if segments is None:
            raise UnknownInputError("segments", "segments sequence is required")
        if not isinstance(segments, (list, tuple)):
            raise UnknownInputError("segments", "segments must be a sequence")
        if len(segments) == 0:
            raise UnknownInputError("segments", "empty segments is unknown, not zero")

        feet_vals = []
        for i, seg in enumerate(segments):
            feet_vals.append(self._resolve_feet(seg, name=f"segments[{i}]"))
        total = sum(feet_vals, Decimal("0"))
        return self._result(
            formula_id="linear.sum.v1",
            value=total,
            unit="ft",
            dimension=Dimension.LENGTH,
            input_refs={"segments_ft": [str(v) for v in feet_vals]},
        )

    def area_rectangle(
        self,
        length: Optional[LengthInput],
        width: Optional[LengthInput],
    ) -> QuantityResult:
        l_ft = self._resolve_feet(length, name="length")
        w_ft = self._resolve_feet(width, name="width")
        area = l_ft * w_ft
        return self._result(
            formula_id="area.rectangle.v1",
            value=area,
            unit="sq_ft",
            dimension=Dimension.AREA,
            input_refs={"length_ft": str(l_ft), "width_ft": str(w_ft)},
        )

    def area_triangle(
        self,
        base: Optional[LengthInput],
        height: Optional[LengthInput],
    ) -> QuantityResult:
        b_ft = self._resolve_feet(base, name="base")
        h_ft = self._resolve_feet(height, name="height")
        area = (Decimal("0.5") * b_ft * h_ft)
        return self._result(
            formula_id="area.triangle.v1",
            value=area,
            unit="sq_ft",
            dimension=Dimension.AREA,
            input_refs={"base_ft": str(b_ft), "height_ft": str(h_ft)},
        )

    def volume_rectangular(
        self,
        length: Optional[LengthInput],
        width: Optional[LengthInput],
        depth: Optional[LengthInput],
    ) -> QuantityResult:
        l_ft = self._resolve_feet(length, name="length")
        w_ft = self._resolve_feet(width, name="width")
        d_ft = self._resolve_feet(depth, name="depth")
        vol = l_ft * w_ft * d_ft
        return self._result(
            formula_id="volume.rectangular.v1",
            value=vol,
            unit="cu_ft",
            dimension=Dimension.VOLUME,
            input_refs={
                "length_ft": str(l_ft),
                "width_ft": str(w_ft),
                "depth_ft": str(d_ft),
            },
        )

    # ── board-foot ──────────────────────────────────────────────────────

    def board_feet(
        self,
        *,
        thickness_in: Optional[NumberLike],
        width_in: Optional[NumberLike],
        length: Optional[LengthInput],
        piece_count: Optional[NumberLike] = 1,
    ) -> QuantityResult:
        """Board feet: (T_in * W_in * L_ft) / 12 * N."""
        t = require_known(thickness_in, name="thickness_in")
        w = require_known(width_in, name="width_in")
        n = require_known(piece_count, name="piece_count")
        if n < 0:
            raise DimensionalError("piece_count cannot be negative")
        l_ft = self._resolve_feet(length, name="length")
        bf = (t * w * l_ft) / Decimal("12") * n
        return self._result(
            formula_id="board_foot.v1",
            value=bf,
            unit="bf",
            dimension=Dimension.BOARD_FOOT,
            input_refs={
                "thickness_in": str(t),
                "width_in": str(w),
                "length_ft": str(l_ft),
                "piece_count": str(n),
            },
        )

    # ── roofing square ──────────────────────────────────────────────────

    def roofing_squares(
        self,
        area_sqft: Optional[NumberLike],
        *,
        waste_policy_id: Optional[str] = None,
    ) -> QuantityResult:
        """Convert area to roofing squares (1 square = 100 sq ft).

        Optional waste applies to area before square conversion.
        """
        area = require_known(area_sqft, name="area_sqft")
        if area < 0:
            raise DimensionalError("area_sqft cannot be negative")
        applied_area = area
        if waste_policy_id is not None:
            applied_area = self.waste.apply(waste_policy_id, area)
        squares = applied_area / Decimal("100")
        return self._result(
            formula_id="roofing_square.v1",
            value=squares,
            unit="square",
            dimension=Dimension.ROOFING_SQUARE,
            input_refs={
                "area_sqft": str(area),
                "area_after_waste_sqft": str(applied_area),
            },
            waste_policy_id=waste_policy_id,
        )

    # ── concrete ────────────────────────────────────────────────────────

    def concrete_volume_cu_ft(
        self,
        length: Optional[LengthInput],
        width: Optional[LengthInput],
        thickness: Optional[LengthInput],
        *,
        waste_policy_id: Optional[str] = None,
    ) -> QuantityResult:
        """Concrete volume in cubic feet (thickness as length input, e.g. 4\")."""
        l_ft = self._resolve_feet(length, name="length")
        w_ft = self._resolve_feet(width, name="width")
        t_ft = self._resolve_feet(thickness, name="thickness")
        vol = l_ft * w_ft * t_ft
        if waste_policy_id is not None:
            vol = self.waste.apply(waste_policy_id, vol)
        return self._result(
            formula_id="concrete.volume.v1",
            value=vol,
            unit="cu_ft",
            dimension=Dimension.VOLUME,
            input_refs={
                "length_ft": str(l_ft),
                "width_ft": str(w_ft),
                "thickness_ft": str(t_ft),
            },
            waste_policy_id=waste_policy_id,
        )

    def concrete_purchase_cy(
        self,
        cu_ft: Optional[NumberLike],
        *,
        purchase_increment_cy: Optional[NumberLike] = "0.25",
    ) -> QuantityResult:
        """Convert cubic feet to purchase cubic yards, rounding up to increment.

        Default purchase increment is 0.25 CY (common ready-mix step).
        """
        volume_cf = require_known(cu_ft, name="cu_ft")
        if volume_cf < 0:
            raise DimensionalError("cu_ft cannot be negative")
        increment = require_known(purchase_increment_cy, name="purchase_increment_cy")
        if increment <= 0:
            raise DimensionalError("purchase_increment_cy must be > 0")

        cy_exact = volume_cf / Decimal("27")
        # Round up to next increment: ceil(exact / increment) * increment
        units = (cy_exact / increment).to_integral_value(rounding=ROUND_CEILING)
        purchase_cy = units * increment
        # Zero volume remains zero (known zero), not unknown.
        if volume_cf == 0:
            purchase_cy = Decimal("0")

        return self._result(
            formula_id="concrete.purchase_cy.v1",
            value=purchase_cy,
            unit="cu_yd",
            dimension=Dimension.VOLUME,
            input_refs={
                "cu_ft": str(volume_cf),
                "cy_exact": str(cy_exact),
                "purchase_increment_cy": str(increment),
            },
            notes="purchase quantity rounded up to increment; not a price",
        )

    # ── piece / package rounding ────────────────────────────────────────

    def pieces_from_coverage(
        self,
        net_quantity: Optional[NumberLike],
        coverage_per_piece: Optional[NumberLike],
        *,
        waste_policy_id: Optional[str] = None,
    ) -> QuantityResult:
        """Ceil(net_with_waste / coverage_per_piece) → whole pieces/packages."""
        net = require_known(net_quantity, name="net_quantity")
        coverage = require_known(coverage_per_piece, name="coverage_per_piece")
        if coverage <= 0:
            raise DimensionalError("coverage_per_piece must be > 0")
        if net < 0:
            raise DimensionalError("net_quantity cannot be negative")

        adjusted = net
        if waste_policy_id is not None:
            adjusted = self.waste.apply(waste_policy_id, net)

        pieces = (adjusted / coverage).to_integral_value(rounding=ROUND_CEILING)
        if adjusted == 0:
            pieces = Decimal("0")

        return self._result(
            formula_id="piece.round.v1",
            value=pieces,
            unit="piece",
            dimension=Dimension.COUNT,
            input_refs={
                "net_quantity": str(net),
                "adjusted_quantity": str(adjusted),
                "coverage_per_piece": str(coverage),
            },
            waste_policy_id=waste_policy_id,
        )

    def apply_waste(
        self,
        net_quantity: Optional[NumberLike],
        waste_policy_id: Optional[str],
        *,
        unit: str = "unit",
        dimension: Dimension = Dimension.UNKNOWN,
    ) -> QuantityResult:
        net = require_known(net_quantity, name="net_quantity")
        policy = self.waste.get(waste_policy_id)
        gross = policy.apply(net)
        return self._result(
            formula_id="waste.apply.v1",
            value=gross,
            unit=unit,
            dimension=dimension,
            input_refs={
                "net_quantity": str(net),
                "multiplier": str(policy.multiplier),
            },
            waste_policy_id=policy.policy_id,
        )
