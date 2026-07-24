"""Deterministic assembly quantity engine (E-002).

Families: roofing, siding, concrete, flooring, drywall, insulation.
Produces net / base material quantities only. No pricing.
No language model may perform final authoritative arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .engine import ConstructionMathEngine, LengthInput
from .errors import DimensionalError, UnknownInputError
from .formulas import FORMULA_REGISTRY, FormulaRegistry
from .materials import MaterialConversionResult, MaterialsConversionEngine
from .provenance import QuantityProvenance, QuantityResult
from .purchase_rules import PURCHASE_RULES, PurchaseRulesRegistry
from .units import Dimension, Measurement, NumberLike, require_known

ASSEMBLY_ENGINE_VERSION = "e002.1.0.0"

ASSEMBLY_FAMILIES = frozenset(
    {
        "roofing",
        "siding",
        "concrete",
        "flooring",
        "drywall",
        "insulation",
    }
)


@dataclass(frozen=True)
class AssemblyLine:
    """One material line produced by an assembly expansion."""

    material_code: str
    family: str
    base_quantity: Decimal
    unit: str
    dimension: Dimension
    formula_id: str
    formula_version: str
    default_purchase_rule_id: Optional[str] = None
    notes: Optional[str] = None
    input_refs: Mapping[str, Any] = field(default_factory=dict)

    def to_quantity_result(self, *, engine_version: str) -> QuantityResult:
        return QuantityResult(
            quantity=Measurement(self.base_quantity, self.unit, self.dimension),
            provenance=QuantityProvenance(
                formula_id=self.formula_id,
                formula_version=self.formula_version,
                engine_version=engine_version,
                input_refs=dict(self.input_refs),
                notes=self.notes,
            ),
            confidence="deterministic",
            unknown_state=None,
        )

    def as_dict(self) -> dict:
        return {
            "material_code": self.material_code,
            "family": self.family,
            "base_quantity": str(self.base_quantity),
            "unit": self.unit,
            "dimension": self.dimension.value,
            "formula_id": self.formula_id,
            "formula_version": self.formula_version,
            "default_purchase_rule_id": self.default_purchase_rule_id,
            "notes": self.notes,
            "input_refs": dict(self.input_refs),
        }


@dataclass(frozen=True)
class AssemblyExpansion:
    """Full assembly expansion with lines + optional purchase conversions."""

    assembly_id: str
    family: str
    assembly_version: str
    engine_version: str
    lines: Sequence[AssemblyLine]
    conversions: Sequence[MaterialConversionResult] = field(default_factory=tuple)
    input_package: Mapping[str, Any] = field(default_factory=dict)

    def quantity_results(self) -> List[QuantityResult]:
        results = [line.to_quantity_result(engine_version=self.engine_version) for line in self.lines]
        for conv in self.conversions:
            results.append(conv.purchase_result)
        return results

    def as_dict(self) -> dict:
        return {
            "assembly_id": self.assembly_id,
            "family": self.family,
            "assembly_version": self.assembly_version,
            "engine_version": self.engine_version,
            "lines": [line.as_dict() for line in self.lines],
            "conversions": [c.as_dict() for c in self.conversions],
            "input_package": dict(self.input_package),
        }


class AssemblyQuantityEngine:
    """Deterministic assembly → material quantity expander."""

    def __init__(
        self,
        *,
        math_engine: ConstructionMathEngine | None = None,
        materials_engine: MaterialsConversionEngine | None = None,
        purchase_rules: PurchaseRulesRegistry | None = None,
        formula_registry: FormulaRegistry | None = None,
        engine_version: str = ASSEMBLY_ENGINE_VERSION,
    ) -> None:
        self.math = math_engine or ConstructionMathEngine()
        self.materials = materials_engine or MaterialsConversionEngine(
            purchase_rules=purchase_rules
        )
        self.purchase_rules = purchase_rules or PURCHASE_RULES
        self.formulas = formula_registry or FORMULA_REGISTRY
        self.engine_version = engine_version

    def _formula(self, formula_id: str):
        return self.formulas.get(formula_id)

    def _require_family(self, family: Optional[str]) -> str:
        if family is None or (isinstance(family, str) and not family.strip()):
            raise UnknownInputError("family", "assembly family is required")
        fam = family.strip().lower()
        if fam not in ASSEMBLY_FAMILIES:
            raise UnknownInputError(
                "family",
                f"unsupported assembly family {family!r}; "
                f"supported: {sorted(ASSEMBLY_FAMILIES)}",
            )
        return fam

    def expand(
        self,
        family: Optional[str],
        inputs: Optional[Mapping[str, Any]],
        *,
        assembly_id: Optional[str] = None,
        convert_purchases: bool = True,
        purchase_rule_overrides: Optional[Mapping[str, str]] = None,
    ) -> AssemblyExpansion:
        fam = self._require_family(family)
        if inputs is None:
            raise UnknownInputError("inputs", "assembly inputs mapping is required")
        if not isinstance(inputs, Mapping):
            raise UnknownInputError("inputs", "assembly inputs must be a mapping")

        aid = assembly_id or f"{fam}.default.v1"
        overrides = dict(purchase_rule_overrides or {})

        if fam == "roofing":
            lines = self._expand_roofing(inputs)
        elif fam == "siding":
            lines = self._expand_siding(inputs)
        elif fam == "concrete":
            lines = self._expand_concrete(inputs)
        elif fam == "flooring":
            lines = self._expand_flooring(inputs)
        elif fam == "drywall":
            lines = self._expand_drywall(inputs)
        elif fam == "insulation":
            lines = self._expand_insulation(inputs)
        else:  # pragma: no cover — guarded by _require_family
            raise UnknownInputError("family", f"unsupported assembly family {fam!r}")

        conversions: List[MaterialConversionResult] = []
        if convert_purchases:
            for line in lines:
                rule_id = overrides.get(line.material_code, line.default_purchase_rule_id)
                if rule_id is None:
                    continue
                conversions.append(
                    self.materials.convert(
                        line.base_quantity,
                        purchase_rule_id=rule_id,
                        input_unit=line.unit,
                        input_dimension=line.dimension,
                    )
                )

        return AssemblyExpansion(
            assembly_id=aid,
            family=fam,
            assembly_version="1.0.0",
            engine_version=self.engine_version,
            lines=tuple(lines),
            conversions=tuple(conversions),
            input_package=dict(inputs),
        )

    # ── family expanders ────────────────────────────────────────────────

    def _expand_roofing(self, inputs: Mapping[str, Any]) -> List[AssemblyLine]:
        area = require_known(inputs.get("roof_area_sqft"), name="roof_area_sqft")
        if area < 0:
            raise DimensionalError("roof_area_sqft cannot be negative")

        squares_spec = self._formula("assembly.roofing.squares.v1")
        squares = area / Decimal("100")
        lines = [
            AssemblyLine(
                material_code="field_shingles",
                family="roofing",
                base_quantity=area,
                unit="sq_ft",
                dimension=Dimension.AREA,
                formula_id="assembly.roofing.field_area.v1",
                formula_version=self._formula("assembly.roofing.field_area.v1").version,
                default_purchase_rule_id="roofing.shingles.bundle.v1",
                input_refs={"roof_area_sqft": str(area), "squares": str(squares)},
                notes="field coverage area; squares recorded in input_refs",
            ),
            AssemblyLine(
                material_code="underlayment",
                family="roofing",
                base_quantity=area,
                unit="sq_ft",
                dimension=Dimension.AREA,
                formula_id="assembly.roofing.underlayment.v1",
                formula_version=self._formula("assembly.roofing.underlayment.v1").version,
                default_purchase_rule_id="roofing.underlayment.roll.v1",
                input_refs={"roof_area_sqft": str(area)},
            ),
        ]
        # Explicit ridge / starter lengths — missing means omit line (not zero-fill).
        if "ridge_length_ft" in inputs:
            ridge = require_known(inputs.get("ridge_length_ft"), name="ridge_length_ft")
            if ridge < 0:
                raise DimensionalError("ridge_length_ft cannot be negative")
            lines.append(
                AssemblyLine(
                    material_code="ridge_cap",
                    family="roofing",
                    base_quantity=ridge,
                    unit="ft",
                    dimension=Dimension.LENGTH,
                    formula_id="assembly.roofing.ridge.v1",
                    formula_version=self._formula("assembly.roofing.ridge.v1").version,
                    default_purchase_rule_id="roofing.ridge.bundle.v1",
                    input_refs={"ridge_length_ft": str(ridge)},
                )
            )
        # squares_spec referenced to keep formula registry exercised for replay
        _ = squares_spec
        return lines

    def _expand_siding(self, inputs: Mapping[str, Any]) -> List[AssemblyLine]:
        wall = require_known(inputs.get("wall_area_sqft"), name="wall_area_sqft")
        if wall < 0:
            raise DimensionalError("wall_area_sqft cannot be negative")
        if "opening_area_sqft" not in inputs:
            raise UnknownInputError(
                "opening_area_sqft",
                "opening_area_sqft is required (use 0 when none); never silent omit",
            )
        openings = require_known(inputs.get("opening_area_sqft"), name="opening_area_sqft")
        if openings < 0:
            raise DimensionalError("opening_area_sqft cannot be negative")
        if openings > wall:
            raise DimensionalError("opening_area_sqft cannot exceed wall_area_sqft")

        net = wall - openings
        spec = self._formula("assembly.siding.net_area.v1")
        return [
            AssemblyLine(
                material_code="siding_panel",
                family="siding",
                base_quantity=net,
                unit="sq_ft",
                dimension=Dimension.AREA,
                formula_id=spec.formula_id,
                formula_version=spec.version,
                default_purchase_rule_id="siding.panel.piece.v1",
                input_refs={
                    "wall_area_sqft": str(wall),
                    "opening_area_sqft": str(openings),
                    "net_area_sqft": str(net),
                },
            )
        ]

    def _expand_concrete(self, inputs: Mapping[str, Any]) -> List[AssemblyLine]:
        length: Optional[LengthInput] = inputs.get("length")
        width: Optional[LengthInput] = inputs.get("width")
        thickness: Optional[LengthInput] = inputs.get("thickness")
        vol = self.math.concrete_volume_cu_ft(length, width, thickness)
        spec = self._formula("assembly.concrete.volume.v1")
        return [
            AssemblyLine(
                material_code="ready_mix",
                family="concrete",
                base_quantity=vol.value,
                unit="cu_ft",
                dimension=Dimension.VOLUME,
                formula_id=spec.formula_id,
                formula_version=spec.version,
                default_purchase_rule_id="concrete.ready_mix.cy.v1",
                input_refs=dict(vol.provenance.input_refs),
                notes="net concrete volume before overage / purchase CY rounding",
            )
        ]

    def _expand_flooring(self, inputs: Mapping[str, Any]) -> List[AssemblyLine]:
        area = require_known(inputs.get("floor_area_sqft"), name="floor_area_sqft")
        if area < 0:
            raise DimensionalError("floor_area_sqft cannot be negative")
        spec = self._formula("assembly.flooring.area.v1")
        return [
            AssemblyLine(
                material_code="flooring_plank",
                family="flooring",
                base_quantity=area,
                unit="sq_ft",
                dimension=Dimension.AREA,
                formula_id=spec.formula_id,
                formula_version=spec.version,
                default_purchase_rule_id="flooring.plank.carton.v1",
                input_refs={"floor_area_sqft": str(area)},
            )
        ]

    def _expand_drywall(self, inputs: Mapping[str, Any]) -> List[AssemblyLine]:
        wall = require_known(inputs.get("wall_area_sqft"), name="wall_area_sqft")
        ceiling = require_known(inputs.get("ceiling_area_sqft"), name="ceiling_area_sqft")
        if wall < 0:
            raise DimensionalError("wall_area_sqft cannot be negative")
        if ceiling < 0:
            raise DimensionalError("ceiling_area_sqft cannot be negative")
        total = wall + ceiling
        spec = self._formula("assembly.drywall.area.v1")
        return [
            AssemblyLine(
                material_code="drywall_sheet",
                family="drywall",
                base_quantity=total,
                unit="sq_ft",
                dimension=Dimension.AREA,
                formula_id=spec.formula_id,
                formula_version=spec.version,
                default_purchase_rule_id="drywall.sheet.4x8.v1",
                input_refs={
                    "wall_area_sqft": str(wall),
                    "ceiling_area_sqft": str(ceiling),
                    "total_area_sqft": str(total),
                },
            )
        ]

    def _expand_insulation(self, inputs: Mapping[str, Any]) -> List[AssemblyLine]:
        area = require_known(inputs.get("area_sqft"), name="area_sqft")
        if area < 0:
            raise DimensionalError("area_sqft cannot be negative")
        spec = self._formula("assembly.insulation.area.v1")
        return [
            AssemblyLine(
                material_code="batt_insulation",
                family="insulation",
                base_quantity=area,
                unit="sq_ft",
                dimension=Dimension.AREA,
                formula_id=spec.formula_id,
                formula_version=spec.version,
                default_purchase_rule_id="insulation.batt.bag.v1",
                input_refs={"area_sqft": str(area)},
            )
        ]
