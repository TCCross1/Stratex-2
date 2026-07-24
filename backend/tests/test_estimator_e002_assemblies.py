"""E-002 Assembly Quantity Engine — deterministic tests.

Authority: AssemblyQuantityEngine + MaterialsConversionEngine only.
No LM arithmetic. No pricing. Transparent base/waste/purchase only.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from nextgen.estimator import (
    ASSEMBLY_ENGINE_VERSION,
    ASSEMBLY_FAMILIES,
    ENGINE_VERSION,
    FORMULA_REGISTRY,
    LEDGER_SCHEMA_VERSION,
    MATERIALS_ENGINE_VERSION,
    PURCHASE_RULES,
    PURCHASE_RULES_VERSION,
    WASTE_REGISTRY,
    WASTE_REGISTRY_VERSION,
    AssemblyQuantityEngine,
    ConstructionMathEngine,
    DimensionalError,
    EstimateCalculationLedger,
    MaterialsConversionEngine,
    PurchaseRule,
    PurchaseRulesRegistry,
    UnknownInputError,
    build_assembly_ledger,
    build_ledger,
    replay_is_deterministic,
)
from nextgen.estimator.units import Dimension


REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = REPO_ROOT / "engineering" / "estimator" / "PRODUCT_CONSTITUTION.md"
READINESS = REPO_ROOT / "engineering" / "px004" / "lane3" / "CONTRACT_READINESS.md"
LEDGER_SCHEMA = (
    REPO_ROOT
    / "engineering"
    / "contracts"
    / "schemas"
    / "EstimateCalculationLedger.proposed.json"
)


# ── artifacts / boundaries ──────────────────────────────────────────────


def test_contract_readiness_and_boundaries():
    assert READINESS.is_file()
    text = READINESS.read_text(encoding="utf-8")
    assert "E-002" in text
    assert "PROPOSED" in text
    assert "NOT_READY" in text or "not ready" in text.lower()
    assert "No language model may perform final authoritative arithmetic" in text
    assert "pricing" in text.lower()
    assert CONSTITUTION.is_file()


def test_ledger_schema_replay_is_proposed_0_2():
    schema = json.loads(LEDGER_SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["contract_status"]["const"] == "PROPOSED"
    assert schema["properties"]["schema_version"]["const"] == "0.2.0"
    assert schema["properties"]["schema_version"]["const"] == LEDGER_SCHEMA_VERSION
    assert "replay" in schema["properties"]
    assert "ReplayStep" in schema["$defs"]
    assert "FROZEN" not in schema["properties"]["contract_status"]["const"]


def test_engine_versions_pinned():
    assert ENGINE_VERSION == "e001.1.0.0"
    assert ASSEMBLY_ENGINE_VERSION == "e002.1.0.0"
    assert MATERIALS_ENGINE_VERSION == "e002.1.0.0"
    assert PURCHASE_RULES_VERSION == "e002.1.0.0"
    assert WASTE_REGISTRY_VERSION == "e002.1.0.0"
    assert FORMULA_REGISTRY.registry_version == "e002.1.0.0"
    assert ASSEMBLY_FAMILIES == frozenset(
        {"roofing", "siding", "concrete", "flooring", "drywall", "insulation"}
    )


# ── assembly families ───────────────────────────────────────────────────


def test_roofing_assembly_with_ridge_and_purchases():
    eng = AssemblyQuantityEngine()
    expansion = eng.expand(
        "roofing",
        {
            "roof_area_sqft": Decimal("2500"),
            "ridge_length_ft": Decimal("40"),
        },
        assembly_id="roof.main.v1",
    )
    assert expansion.family == "roofing"
    codes = {line.material_code for line in expansion.lines}
    assert codes == {"field_shingles", "underlayment", "ridge_cap"}

    # 2500 * 1.10 / 33.3 → ceil = 83 bundles
    shingle_conv = next(
        c
        for c in expansion.conversions
        if c.transparent.purchase_rule_id == "roofing.shingles.bundle.v1"
    )
    assert shingle_conv.transparent.base_quantity == Decimal("2500")
    assert shingle_conv.transparent.waste_quantity == Decimal("250")
    assert shingle_conv.transparent.purchase_quantity == Decimal("83")
    assert shingle_conv.transparent.purchase_unit == "bundle"
    # provenance carries formula/version/rounding/waste
    refs = shingle_conv.purchase_result.provenance.input_refs
    assert refs["rounding_mode"] == "ceil_packages"
    assert refs["waste_policy_id"] == "roofing.shingles.v1"
    assert refs["package_size"] == "33.3"
    assert shingle_conv.formula_id == "materials.convert.v1"


def test_siding_net_area_and_panels():
    eng = AssemblyQuantityEngine()
    expansion = eng.expand(
        "siding",
        {"wall_area_sqft": "1000", "opening_area_sqft": "120"},
    )
    line = expansion.lines[0]
    assert line.base_quantity == Decimal("880")
    conv = expansion.conversions[0]
    # 880 * 1.07 / 32 → ceil(29.425) = 30
    assert conv.transparent.purchase_quantity == Decimal("30")


def test_concrete_assembly_purchase_cy():
    eng = AssemblyQuantityEngine()
    expansion = eng.expand(
        "concrete",
        {"length": "10'", "width": "10'", "thickness": '4"'},
    )
    line = expansion.lines[0]
    # 10*10*(4/12) = 100/3 cu ft
    assert abs(line.base_quantity - Decimal("100") / Decimal("3")) < Decimal("0.0000001")
    conv = expansion.conversions[0]
    # with 8% waste, convert to CY, ceil to 0.25
    # (100/3)*1.08 / 27 ≈ 1.333... → 1.50 CY
    assert conv.transparent.purchase_quantity == Decimal("1.50")
    assert conv.transparent.purchase_unit == "cu_yd"
    assert "not a price" in (conv.purchase_result.provenance.notes or "").lower()


def test_flooring_drywall_insulation_families():
    eng = AssemblyQuantityEngine()

    floor = eng.expand("flooring", {"floor_area_sqft": Decimal("500")})
    assert floor.lines[0].base_quantity == Decimal("500")
    # 500 * 1.08 / 22 → ceil(24.545...) = 25 cartons
    assert floor.conversions[0].transparent.purchase_quantity == Decimal("25")

    dry = eng.expand(
        "drywall",
        {"wall_area_sqft": Decimal("800"), "ceiling_area_sqft": Decimal("400")},
    )
    assert dry.lines[0].base_quantity == Decimal("1200")
    # 1200 * 1.10 / 32 → ceil(41.25) = 42 sheets
    assert dry.conversions[0].transparent.purchase_quantity == Decimal("42")

    ins = eng.expand("insulation", {"area_sqft": Decimal("600")})
    assert ins.lines[0].base_quantity == Decimal("600")
    # 600 * 1.05 / 88 → ceil(7.159...) = 8 bags
    assert ins.conversions[0].transparent.purchase_quantity == Decimal("8")


# ── materials conversion engine ─────────────────────────────────────────


def test_materials_conversion_transparent_breakdown():
    mat = MaterialsConversionEngine()
    result = mat.convert(
        Decimal("1000"),
        purchase_rule_id="flooring.plank.carton.v1",
        input_unit="sq_ft",
        input_dimension=Dimension.AREA,
    )
    t = result.transparent
    assert t.base_quantity == Decimal("1000")
    assert t.waste_quantity == Decimal("80")
    assert t.quantity_with_waste == Decimal("1080")
    assert t.purchase_quantity == Decimal("50")  # 1080/22 = 49.09 → 50
    assert result.formula_version == "1.0.0"
    assert result.engine_version == MATERIALS_ENGINE_VERSION


# ── rejection rules ─────────────────────────────────────────────────────


def test_rejects_nan_inf_negative_incompatible_zero_package():
    eng = AssemblyQuantityEngine()
    mat = MaterialsConversionEngine()

    with pytest.raises(UnknownInputError):
        eng.expand("roofing", {"roof_area_sqft": float("nan")})
    with pytest.raises(UnknownInputError):
        eng.expand("roofing", {"roof_area_sqft": float("inf")})
    with pytest.raises(UnknownInputError):
        eng.expand("flooring", {"floor_area_sqft": Decimal("NaN")})
    with pytest.raises(DimensionalError):
        eng.expand("flooring", {"floor_area_sqft": Decimal("-1")})
    with pytest.raises(UnknownInputError):
        eng.expand(None, {"floor_area_sqft": 1})
    with pytest.raises(UnknownInputError):
        eng.expand("plumbing", {"floor_area_sqft": 1})
    with pytest.raises(UnknownInputError):
        eng.expand("siding", {"wall_area_sqft": 100})  # missing openings
    with pytest.raises(DimensionalError):
        eng.expand("siding", {"wall_area_sqft": 100, "opening_area_sqft": 150})

    with pytest.raises(DimensionalError):
        mat.convert(
            Decimal("100"),
            purchase_rule_id="siding.panel.piece.v1",
            input_unit="cu_ft",  # incompatible
        )
    with pytest.raises(DimensionalError):
        mat.convert(
            Decimal("100"),
            purchase_rule_id="siding.panel.piece.v1",
            input_dimension=Dimension.VOLUME,
        )
    with pytest.raises(DimensionalError):
        mat.convert(Decimal("-5"), purchase_rule_id="siding.panel.piece.v1")
    with pytest.raises(UnknownInputError):
        mat.convert(Decimal("10"), purchase_rule_id=None)
    with pytest.raises(UnknownInputError):
        mat.convert(None, purchase_rule_id="siding.panel.piece.v1")

    # Zero package size rejected at apply time
    bad = PurchaseRulesRegistry(
        {
            "bad.zero.pkg.v1": PurchaseRule(
                rule_id="bad.zero.pkg.v1",
                version="1.0.0",
                family="test",
                material_code="x",
                description="bad",
                input_unit="sq_ft",
                input_dimension=Dimension.AREA,
                purchase_unit="piece",
                package_size=Decimal("1"),  # construct ok; mutate via replace path
                rounding="ceil_packages",
                waste_policy_id="general.none.v1",
            )
        }
    )
    # Force zero package through object.__setattr__ on frozen dataclass bypass
    # by constructing a rule via registry apply after patching package_size check:
    rule = bad.get("bad.zero.pkg.v1")
    object.__setattr__(rule, "package_size", Decimal("0"))
    with pytest.raises(DimensionalError):
        bad.apply("bad.zero.pkg.v1", Decimal("10"))


def test_purchase_rules_registry_lists_families():
    assert "roofing.shingles.bundle.v1" in PURCHASE_RULES.list_ids()
    assert "drywall.sheet.4x8.v1" in PURCHASE_RULES.list_by_family("drywall")
    assert "flooring.plank.v1" in WASTE_REGISTRY.list_ids()
    with pytest.raises(UnknownInputError):
        PURCHASE_RULES.get("missing.rule")


# ── ledger replay ───────────────────────────────────────────────────────


def test_assembly_ledger_full_deterministic_replay():
    eng = AssemblyQuantityEngine()
    expansion = eng.expand(
        "roofing",
        {"roof_area_sqft": Decimal("1000"), "ridge_length_ft": Decimal("20")},
        assembly_id="roof.replay.v1",
    )
    ledger = build_assembly_ledger(
        ledger_id="led-e002-001",
        expansion=expansion,
        formula_registry_version=FORMULA_REGISTRY.registry_version,
        waste_registry_version=WASTE_REGISTRY_VERSION,
        purchase_rules_version=PURCHASE_RULES_VERSION,
        notes="E-002 assembly replay test",
    )
    assert isinstance(ledger, EstimateCalculationLedger)
    assert ledger.contract_status == "PROPOSED"
    assert ledger.schema_version == "0.2.0"
    assert ledger.provenance.assembly_engine_version == ASSEMBLY_ENGINE_VERSION
    assert ledger.provenance.purchase_rules_version == PURCHASE_RULES_VERSION
    assert len(ledger.entries) == len(ledger.replay)
    assert len(ledger.replay) >= 4  # 3 assembly lines + conversions
    assert replay_is_deterministic(ledger)

    kinds = {step.kind for step in ledger.replay}
    assert "assembly" in kinds
    assert "conversion" in kinds

    # Transparent quantities present on conversion entries
    conv_entries = [e for e in ledger.entries if e.purchase_quantity is not None]
    assert conv_entries
    assert all(e.base_quantity is not None for e in conv_entries)
    assert all(e.waste_quantity is not None for e in conv_entries)
    assert all(e.rounding_mode is not None for e in conv_entries)

    dumped = ledger.model_dump()
    restored = EstimateCalculationLedger.model_validate(dumped)
    assert restored.ledger_id == ledger.ledger_id
    assert len(restored.replay) == len(ledger.replay)
    assert restored.contract_status == "PROPOSED"


def test_e001_build_ledger_still_works_with_expanded_schema():
    math = ConstructionMathEngine()
    area = math.area_rectangle("20'", "15'")
    ledger = build_ledger(
        ledger_id="led-e001-compat",
        calculator_version=ENGINE_VERSION,
        formula_registry_version=FORMULA_REGISTRY.registry_version,
        input_package={"length_ft": "20", "width_ft": "15"},
        results=[area],
    )
    assert ledger.schema_version == LEDGER_SCHEMA_VERSION
    assert ledger.replay == []
    assert ledger.entries[0].output_value == str(area.value)


def test_no_pricing_surfaces_in_e002_modules():
    """Guard: E-002 modules must not invent unit prices or margins."""
    root = REPO_ROOT / "backend" / "nextgen" / "estimator"
    # Specific pricing identifiers — not the word "margins" in "no margins" docs.
    banned = (
        "unit_price",
        "unit_cost",
        "price_book",
        "sell_price",
        "margin_pct",
        "contractor_margin",
        "nationwide_price",
    )
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} contains pricing token {token!r}"
        # No currency / money fields on quantity results
        assert "currency" not in text or path.name in {"__init__.py"}
