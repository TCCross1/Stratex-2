"""RT-003 — observability foundation and bounded load verification (Lane 5).

Production readiness: NOT READY.
Law: PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.

Import submodules directly (e.g. `rt003.observability`) to avoid eager
side-effect imports of guards during lightweight tests.
"""

__all__ = [
    "SafeLogger",
    "SafeMetrics",
    "scrub_for_log",
    "LoadBudget",
    "run_bounded_synthetic_load",
    "run_security_failure_guards",
]


def __getattr__(name: str):
    if name in {"SafeLogger", "SafeMetrics", "scrub_for_log"}:
        from . import observability

        return getattr(observability, name)
    if name in {"LoadBudget", "run_bounded_synthetic_load"}:
        from . import load_harness

        return getattr(load_harness, name)
    if name == "run_security_failure_guards":
        from . import guards

        return getattr(guards, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
