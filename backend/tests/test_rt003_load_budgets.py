"""RT-003 performance budgets + bounded synthetic load tests.

CI-safe — no live Mongo/MinIO. Production readiness: NOT READY.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENG = ROOT / "engineering"
if str(ENG) not in sys.path:
    sys.path.insert(0, str(ENG))

from rt003.load_harness import (  # noqa: E402
    DEFAULT_BUDGETS,
    LoadBudget,
    run_bounded_synthetic_load,
)


def test_performance_budgets_document_present():
    doc = ROOT / "engineering" / "rt003" / "PERFORMANCE_BUDGETS.md"
    text = doc.read_text(encoding="utf-8")
    assert "NOT READY" in text
    assert "json_hash_roundtrip" in text
    assert "synthetic" in text.lower()
    assert "production capacity" in text.lower() or "not production" in text.lower()


def test_default_budgets_are_bounded():
    for name, budget in DEFAULT_BUDGETS.items():
        assert budget.max_iterations <= 1000, name
        assert budget.max_wall_ms <= 30_000, name
        assert budget.max_ops_per_sec > 0, name
        assert budget.as_public_dict()["production_readiness"] == "NOT_READY"


def test_bounded_synthetic_load_stays_within_hard_ceilings():
    result = run_bounded_synthetic_load(DEFAULT_BUDGETS["json_hash_roundtrip"], iterations=50)
    public = result.as_public_dict()
    assert public["production_readiness"] == "NOT_READY"
    assert result.iterations <= DEFAULT_BUDGETS["json_hash_roundtrip"].max_iterations
    assert result.wall_ms <= DEFAULT_BUDGETS["json_hash_roundtrip"].max_wall_ms
    assert result.errors == 0
    assert result.within_budget is True
    # ops/sec may exceed the documented cap for cheap CPU ops; hard fail is wall/errors.


def test_load_harness_caps_requested_iterations():
    tiny = LoadBudget(
        name="tiny",
        max_iterations=10,
        max_wall_ms=2_000.0,
        max_ops_per_sec=100_000.0,
        target_p95_ms=100.0,
    )
    result = run_bounded_synthetic_load(tiny, iterations=10_000)
    assert result.iterations <= 10


def test_json_serialize_hash_microbench_budget_runs():
    assert "scrub_throughput" not in DEFAULT_BUDGETS
    budget = DEFAULT_BUDGETS["json_serialize_hash_microbench"]
    assert budget.name == "json_serialize_hash_microbench"
    result = run_bounded_synthetic_load(budget, iterations=25)
    assert result.errors == 0
    assert result.within_budget is True
    assert result.budget_name == "json_serialize_hash_microbench"
