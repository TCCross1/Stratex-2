"""E-001 Construction Mathematics Foundation — deterministic tests.

Authority: Construction Math Engine only. No LM arithmetic.
Unknown inputs must fail explicitly — never silent zero-fill.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from nextgen.estimator import (
    ENGINE_VERSION,
    FORMULA_REGISTRY,
    LEDGER_SCHEMA_VERSION,
    WASTE_REGISTRY,
    ConstructionMathEngine,
    DimensionalError,
    EstimateCalculationLedger,
    ParseError,
    UnknownInputError,
    build_ledger,
    parse_feet_inches,
)
from nextgen import estimator_math


REPO_ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = REPO_ROOT / "engineering" / "estimator" / "PRODUCT_CONSTITUTION.md"
MISSION = REPO_ROOT / "engineering" / "px001" / "missions" / "LANE_3_ESTIMATOR_E001.md"
LEDGER_SCHEMA = (
    REPO_ROOT
    / "engineering"
    / "contracts"
    / "schemas"
    / "EstimateCalculationLedger.proposed.json"
)
REGISTRY = REPO_ROOT / "engineering" / "contracts" / "registry.yaml"


# ── artifacts ───────────────────────────────────────────────────────────


def test_constitution_and_mission_exist():
    assert CONSTITUTION.is_file()
    text = CONSTITUTION.read_text(encoding="utf-8")
    assert "No language model may perform final authoritative arithmetic" in text
    assert "Evidence supplies measurements" in text
    assert MISSION.is_file()
    mission = MISSION.read_text(encoding="utf-8")
    assert "E-001" in mission
    assert "PROPOSED" in mission
    assert "FROZEN" in mission  # explicitly forbidden / not done


def test_ledger_schema_is_proposed_not_frozen():
    assert LEDGER_SCHEMA.is_file()
    raw = LEDGER_SCHEMA.read_text(encoding="utf-8")
    schema = json.loads(raw)
    assert schema["properties"]["contract_status"]["const"] == "PROPOSED"
    assert schema["properties"]["contract_status"]["const"] != "FROZEN"
    assert "Not FROZEN" in raw or "not FROZEN" in raw or "NOT FROZEN" in raw.upper()
    reg = REGISTRY.read_text(encoding="utf-8")
    assert "EstimateCalculationLedger" in reg
    # status PROPOSED under the ledger block
    block_start = reg.index("name: EstimateCalculationLedger")
    block = reg[block_start : block_start + 400]
    assert "status: PROPOSED" in block
    assert "version: \"0.0.0\"" in block or 'version: "0.0.0"' in block
    assert "status: FROZEN" not in block
    assert "status: ACCEPTED" not in block
    assert schema["properties"]["schema_version"]["const"] == "0.1.0"


def test_estimator_math_facade_exports_engine():
    assert estimator_math.ENGINE_VERSION == ENGINE_VERSION
    assert estimator_math.ConstructionMathEngine is ConstructionMathEngine


# ── feet / inches / fraction parsing ────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected_feet",
    [
        ("12'", Decimal("12")),
        ("12 ft", Decimal("12")),
        ("12.5'", Decimal("12.5")),
        ("12'-6\"", Decimal("12.5")),
        ("12' 6\"", Decimal("12.5")),
        ("12 ft 6 in", Decimal("12.5")),
        ("12'-6 1/2\"", Decimal("12.54166666666666666666666667")),
        ("6 1/2\"", Decimal("6.5") / Decimal("12")),
        ("78\"", Decimal("78") / Decimal("12")),
        ("10' - 3-3/4\"", Decimal("10") + Decimal("3.75") / Decimal("12")),
        ("0'", Decimal("0")),
        ("1/2\"", Decimal("0.5") / Decimal("12")),
    ],
)
def test_parse_feet_inches(raw, expected_feet):
    got = parse_feet_inches(raw).feet
    assert abs(got - expected_feet) < Decimal("0.0000001")


def test_parse_rejects_bare_number_and_empty():
    with pytest.raises(ParseError):
        parse_feet_inches("12")
    with pytest.raises(UnknownInputError):
        parse_feet_inches("")
    with pytest.raises(UnknownInputError):
        parse_feet_inches(None)


# ── linear / area / volume ──────────────────────────────────────────────


def test_linear_area_volume_math():
    eng = ConstructionMathEngine()
    linear = eng.linear_sum(["10'", "2'-6\"", Decimal("1.5")])
    assert linear.value == Decimal("14")
    assert linear.unit == "ft"
    assert linear.provenance.formula_id == "linear.sum.v1"

    area = eng.area_rectangle("12'", "10'")
    assert area.value == Decimal("120")
    assert area.dimension.value == "area"

    tri = eng.area_triangle("10'", "8'")
    assert tri.value == Decimal("40")

    vol = eng.volume_rectangular("10'", "10'", "1'")
    assert vol.value == Decimal("100")
    assert vol.unit == "cu_ft"


def test_linear_sum_rejects_empty_and_none():
    eng = ConstructionMathEngine()
    with pytest.raises(UnknownInputError):
        eng.linear_sum([])
    with pytest.raises(UnknownInputError):
        eng.linear_sum(None)
    with pytest.raises(UnknownInputError):
        eng.area_rectangle(None, "10'")
    with pytest.raises(UnknownInputError):
        eng.area_rectangle("10'", None)


# ── board-foot / roofing-square / concrete ──────────────────────────────


def test_board_feet():
    eng = ConstructionMathEngine()
    # 2x4x8: (2*4*8)/12 = 5.333... bf each; 10 pieces → 53.333...
    bf = eng.board_feet(
        thickness_in=2,
        width_in=4,
        length="8'",
        piece_count=10,
    )
    assert bf.value == Decimal("160") / Decimal("3")
    assert bf.unit == "bf"
    assert bf.provenance.formula_version == "1.0.0"


def test_roofing_squares_with_and_without_waste():
    eng = ConstructionMathEngine()
    net = eng.roofing_squares(Decimal("2500"))
    assert net.value == Decimal("25")

    with_waste = eng.roofing_squares(
        Decimal("2500"),
        waste_policy_id="roofing.shingles.v1",
    )
    # 2500 * 1.10 / 100 = 27.5
    assert with_waste.value == Decimal("27.5")
    assert with_waste.provenance.waste_policy_id == "roofing.shingles.v1"


def test_concrete_volume_and_purchase_conversion():
    eng = ConstructionMathEngine()
    # 10' x 10' x 4" = 10*10*(4/12) = 33.333... cu ft
    vol = eng.concrete_volume_cu_ft("10'", "10'", '4"')
    assert abs(vol.value - Decimal("100") / Decimal("3")) < Decimal("0.0000001")

    with_overage = eng.concrete_volume_cu_ft(
        "10'",
        "10'",
        '4"',
        waste_policy_id="concrete.slab.v1",
    )
    assert with_overage.value == vol.value * Decimal("1.08")

    # 27 cu ft = 1.0 CY exact → purchase 1.00 at 0.25 increment
    purchase_exact = eng.concrete_purchase_cy(Decimal("27"))
    assert purchase_exact.value == Decimal("1.00") or purchase_exact.value == Decimal("1")

    # 28 cu ft = 1.037... CY → rounds up to 1.25 CY
    purchase = eng.concrete_purchase_cy(Decimal("28"), purchase_increment_cy="0.25")
    assert purchase.value == Decimal("1.25")
    assert purchase.unit == "cu_yd"


def test_concrete_purchase_rejects_unknown_increment():
    eng = ConstructionMathEngine()
    with pytest.raises(UnknownInputError):
        eng.concrete_purchase_cy(Decimal("27"), purchase_increment_cy=None)
    with pytest.raises(DimensionalError):
        eng.concrete_purchase_cy(Decimal("27"), purchase_increment_cy="0")


# ── piece/package rounding + waste registry ─────────────────────────────


def test_piece_package_rounding():
    eng = ConstructionMathEngine()
    # 1000 sqft / 33.3 coverage with 10% waste → ceil(1100/33.3)=34
    pieces = eng.pieces_from_coverage(
        Decimal("1000"),
        Decimal("33.3"),
        waste_policy_id="roofing.shingles.v1",
    )
    assert pieces.value == Decimal("34")
    assert pieces.dimension.value == "count"

    zero = eng.pieces_from_coverage(Decimal("0"), Decimal("10"))
    assert zero.value == Decimal("0")


def test_waste_and_formula_registries():
    assert "roofing.shingles.v1" in WASTE_REGISTRY.list_ids()
    policy = WASTE_REGISTRY.get("roofing.shingles.v1")
    assert policy.multiplier == Decimal("1.10")
    assert WASTE_REGISTRY.apply("general.none.v1", Decimal("50")) == Decimal("50")

    with pytest.raises(UnknownInputError):
        WASTE_REGISTRY.get(None)
    with pytest.raises(UnknownInputError):
        WASTE_REGISTRY.get("does.not.exist")

    assert "board_foot.v1" in FORMULA_REGISTRY.list_ids()
    assert FORMULA_REGISTRY.registry_version.startswith("e001.")
    with pytest.raises(UnknownInputError):
        FORMULA_REGISTRY.get("missing.formula")


# ── unknown-input behavior ──────────────────────────────────────────────


def test_unknown_inputs_never_silent_zero():
    eng = ConstructionMathEngine()
    with pytest.raises(UnknownInputError) as exc:
        eng.board_feet(thickness_in=None, width_in=4, length="8'")
    assert "thickness_in" in str(exc.value)

    with pytest.raises(UnknownInputError):
        eng.board_feet(thickness_in="", width_in=4, length="8'")

    with pytest.raises(UnknownInputError):
        eng.roofing_squares(None)

    with pytest.raises(UnknownInputError):
        eng.pieces_from_coverage(Decimal("100"), None)

    with pytest.raises(UnknownInputError):
        eng.apply_waste(Decimal("10"), None)

    with pytest.raises(UnknownInputError):
        eng.roofing_squares(float("nan"))

    with pytest.raises(UnknownInputError):
        eng.roofing_squares(float("inf"))

    with pytest.raises(UnknownInputError):
        eng.apply_waste(Decimal("NaN"), "roofing.shingles.v1")

    with pytest.raises(UnknownInputError):
        eng.apply_waste(Decimal("Infinity"), "roofing.shingles.v1")


# ── provenance + ledger ─────────────────────────────────────────────────


def test_quantity_provenance_and_ledger_contract():
    eng = ConstructionMathEngine()
    area = eng.area_rectangle("20'", "15'")
    squares = eng.roofing_squares(area.value, waste_policy_id="roofing.shingles.v1")
    bundles = eng.pieces_from_coverage(
        area.value,
        Decimal("33.3"),
        waste_policy_id="roofing.shingles.v1",
    )

    assert area.confidence == "deterministic"
    assert area.unknown_state is None
    assert area.provenance.engine_version == ENGINE_VERSION
    assert "length_ft" in area.provenance.input_refs

    input_package = {
        "geometry_revision": "test-geo-1",
        "length_ft": "20",
        "width_ft": "15",
    }
    ledger = build_ledger(
        ledger_id="led-e001-test-001",
        calculator_version=ENGINE_VERSION,
        formula_registry_version=FORMULA_REGISTRY.registry_version,
        input_package=input_package,
        results=[area, squares, bundles],
    )

    assert isinstance(ledger, EstimateCalculationLedger)
    assert ledger.contract_status == "PROPOSED"
    assert ledger.schema_version == LEDGER_SCHEMA_VERSION
    assert ledger.schema_name == "EstimateCalculationLedger"
    assert len(ledger.entries) == 3
    assert ledger.entries[0].sequence == 1
    assert ledger.provenance.input_package_hash
    assert len(ledger.provenance.input_package_hash) == 64
    assert ledger.breaking_change == "requires ATLAS_ARCHITECTURE_APPROVAL"

    # Round-trip via pydantic / dict
    dumped = ledger.model_dump()
    restored = EstimateCalculationLedger.model_validate(dumped)
    assert restored.ledger_id == ledger.ledger_id
    assert restored.contract_status == "PROPOSED"

    # Append pattern does not mutate original
    extra = eng.linear_sum(["5'"])
    from nextgen.estimator.ledger import entry_from_quantity_result

    appended = ledger.append_entry(
        entry_from_quantity_result(extra, entry_id="x", sequence=4)
    )
    assert len(ledger.entries) == 3
    assert len(appended.entries) == 4


def test_build_ledger_rejects_none_results():
    with pytest.raises(UnknownInputError):
        build_ledger(
            ledger_id="x",
            calculator_version=ENGINE_VERSION,
            formula_registry_version=FORMULA_REGISTRY.registry_version,
            input_package={},
            results=None,
        )


def test_engine_version_is_pinned():
    assert ENGINE_VERSION == "e001.1.0.0"
