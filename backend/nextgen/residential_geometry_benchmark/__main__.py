"""CLI for PX-006B residential geometry benchmark."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .corpus_suitability import audit_existing_corpus, write_corpus_suitability_artifacts
from .benchmark_runner import run_full_benchmark
from .reconstruction_bridge import run_benchmark_reconstruction


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m nextgen.residential_geometry_benchmark",
        description="Stratex PX-006B Residential Geometry Benchmark",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("audit-corpus", help="Audit existing PX-006A corpus suitability")
    p_recon = sub.add_parser("reconstruct", help="Run digest-pinned reconstruction")
    p_recon.add_argument("dataset_id")
    p_recon.add_argument("--profile", default="roof-detail")
    p_run = sub.add_parser("run-benchmark", help="Execute full residential geometry benchmark")
    p_run.add_argument("--dataset", action="append")
    p_run.add_argument("--no-reconstruct", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "audit-corpus":
            write_corpus_suitability_artifacts()
            _print(audit_existing_corpus())
        elif args.command == "reconstruct":
            _print(run_benchmark_reconstruction(args.dataset_id, profile=args.profile))
        elif args.command == "run-benchmark":
            _print(
                run_full_benchmark(
                    datasets=args.dataset,
                    reconstruct_missing=not args.no_reconstruct,
                )
            )
        else:
            parser.error(f"unknown command {args.command}")
            return 2
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
