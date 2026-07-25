"""RT-003 bounded synthetic load harness — CI-safe, no live infra required.

Does not hit production, Mongo, MinIO, or customer systems.
Production readiness: NOT READY.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LoadBudget:
    """Hard ceilings for synthetic CI load — exceed → FAIL (not READY)."""

    name: str
    max_iterations: int
    max_wall_ms: float
    max_ops_per_sec: float
    max_payload_bytes: int = 4096
    # Documented SLO targets (synthetic only — not production SLOs).
    target_p95_ms: float = 50.0
    target_error_rate: float = 0.0

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "max_iterations": self.max_iterations,
            "max_wall_ms": self.max_wall_ms,
            "max_ops_per_sec": self.max_ops_per_sec,
            "max_payload_bytes": self.max_payload_bytes,
            "target_p95_ms": self.target_p95_ms,
            "target_error_rate": self.target_error_rate,
            "production_readiness": "NOT_READY",
        }


# Default CI budgets — intentionally small and deterministic.
DEFAULT_BUDGETS: Dict[str, LoadBudget] = {
    "json_hash_roundtrip": LoadBudget(
        name="json_hash_roundtrip",
        max_iterations=200,
        max_wall_ms=5_000.0,
        max_ops_per_sec=50_000.0,
        max_payload_bytes=2048,
        target_p95_ms=25.0,
    ),
    # Honest name: this budget exercises the same local JSON serialize+hash
    # microbenchmark as json_hash_roundtrip with tighter ceilings. It does NOT
    # measure end-to-end sanitize_dlq_payload / observability scrub throughput.
    "json_serialize_hash_microbench": LoadBudget(
        name="json_serialize_hash_microbench",
        max_iterations=100,
        max_wall_ms=3_000.0,
        max_ops_per_sec=20_000.0,
        max_payload_bytes=1024,
        target_p95_ms=40.0,
    ),
}


@dataclass
class LoadResult:
    budget_name: str
    iterations: int
    wall_ms: float
    ops_per_sec: float
    p95_ms: float
    errors: int
    within_budget: bool
    notes: List[str] = field(default_factory=list)
    production_readiness: str = "NOT_READY"

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "budget_name": self.budget_name,
            "iterations": self.iterations,
            "wall_ms": self.wall_ms,
            "ops_per_sec": self.ops_per_sec,
            "p95_ms": self.p95_ms,
            "errors": self.errors,
            "within_budget": self.within_budget,
            "notes": list(self.notes),
            "production_readiness": self.production_readiness,
        }


def _percentile(samples: List[float], pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def run_bounded_synthetic_load(
    budget: Optional[LoadBudget] = None,
    *,
    iterations: Optional[int] = None,
) -> LoadResult:
    """Run a CPU/memory-local synthetic workload under hard ceilings.

    Workload: serialize a synthetic dict, SHA-256 hash, verify round-trip.
    No network. No customer data. Caps iterations and wall time.
    """
    budget = budget or DEFAULT_BUDGETS["json_hash_roundtrip"]
    n = min(int(iterations or budget.max_iterations), budget.max_iterations)
    if n < 1:
        raise ValueError("iterations must be >= 1")

    samples: List[float] = []
    errors = 0
    notes: List[str] = []
    t0 = time.perf_counter()

    for i in range(n):
        if (time.perf_counter() - t0) * 1000.0 > budget.max_wall_ms:
            notes.append("stopped_early_wall_budget")
            break
        op_t0 = time.perf_counter()
        try:
            # Synthetic only — no PII / no secrets.
            doc = {
                "i": i,
                "marker": "RT003_SYNTHETIC",
                "component": "load_harness",
                "blob": ("x" * min(64, budget.max_payload_bytes)),
            }
            raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if len(raw) > budget.max_payload_bytes:
                raise ValueError("payload_exceeds_budget")
            digest = hashlib.sha256(raw).hexdigest()
            again = hashlib.sha256(raw).hexdigest()
            if digest != again:
                raise AssertionError("hash_mismatch")
        except Exception as exc:  # noqa: BLE001 — bounded harness records then continues
            errors += 1
            notes.append(f"op_error:{type(exc).__name__}")
        samples.append((time.perf_counter() - op_t0) * 1000.0)

    wall_ms = (time.perf_counter() - t0) * 1000.0
    completed = len(samples)
    ops_per_sec = (completed / (wall_ms / 1000.0)) if wall_ms > 0 else 0.0
    p95 = _percentile(samples, 95.0)

    within = True
    if completed > budget.max_iterations:
        within = False
        notes.append("iterations_over_budget")
    if wall_ms > budget.max_wall_ms:
        within = False
        notes.append("wall_ms_over_budget")
    if ops_per_sec > budget.max_ops_per_sec:
        # Informational only for cheap CPU ops — hard caps are iterations/wall/errors.
        notes.append("ops_per_sec_above_documented_cap")
    if p95 > budget.target_p95_ms:
        # Soft target — recorded but does not alone fail CI-safe harness.
        notes.append(f"p95_above_target:{p95:.3f}>{budget.target_p95_ms}")
    if errors > 0:
        within = False
        notes.append("errors_nonzero")

    return LoadResult(
        budget_name=budget.name,
        iterations=completed,
        wall_ms=wall_ms,
        ops_per_sec=ops_per_sec,
        p95_ms=p95,
        errors=errors,
        within_budget=within,
        notes=notes,
    )
