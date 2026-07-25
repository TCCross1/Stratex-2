"""CLI: python -m nextgen.dataset_lab <command> ..."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m nextgen.dataset_lab",
        description="Stratex External Drone Dataset Laboratory (PX-006A)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_acq = sub.add_parser("acquire", help="Acquire allowlisted dataset")
    p_acq.add_argument("dataset_id")
    p_acq.add_argument("--dry-run", action="store_true")
    p_acq.add_argument("--verify-only", action="store_true")
    p_acq.add_argument("--timeout", type=int, default=600)

    p_lic = sub.add_parser("license-check", help="Conservative license gate")
    p_lic.add_argument("dataset_id")

    p_inv = sub.add_parser("inventory", help="Inventory and metadata extraction")
    p_inv.add_argument("dataset_id")

    p_cand = sub.add_parser("candidate", help="Build development candidate package")
    p_cand.add_argument("dataset_id")

    p_fault = sub.add_parser("faults", help="Generate local fault matrix")
    p_fault.add_argument("dataset_id")

    p_recon = sub.add_parser("reconstruct", help="Optional ODM reconstruction")
    p_recon.add_argument("dataset_id")
    p_recon.add_argument("--profile", default="smoke")

    p_run = sub.add_parser("run", help="Repeatable experiment runner")
    p_run.add_argument("--dataset", required=True)
    p_run.add_argument("--profile", default="smoke")

    p_reh = sub.add_parser("rehearse", help="Pipeline rehearsal")
    p_reh.add_argument("dataset_id")

    args = parser.parse_args(argv)

    try:
        if args.command == "acquire":
            from .acquire import acquire_dataset

            _print(
                acquire_dataset(
                    args.dataset_id,
                    dry_run=args.dry_run,
                    verify_only=args.verify_only,
                    timeout=args.timeout,
                )
            )
        elif args.command == "license-check":
            from .license_check import license_check

            _print(license_check(args.dataset_id))
        elif args.command == "inventory":
            from .inventory import inventory_dataset

            out = inventory_dataset(args.dataset_id)
            _print(
                {
                    "dataset_id": args.dataset_id,
                    "artifact_dir": out.get("artifact_dir"),
                    "validation": out.get("validation"),
                    "inventory_summary": {
                        "total_files": out["inventory"]["total_files"],
                        "total_images": out["inventory"]["total_images"],
                        "total_bytes": out["inventory"]["total_bytes"],
                        "gps_status": out["inventory"]["gps_status"],
                        "gcp_present": out["inventory"]["gcp_present"],
                    },
                }
            )
        elif args.command == "candidate":
            from .corpus import build_candidate_package

            _print(build_candidate_package(args.dataset_id))
        elif args.command == "faults":
            from .faults import generate_fault_matrix

            _print(generate_fault_matrix(args.dataset_id))
        elif args.command == "reconstruct":
            from .reconstruction import run_odm_reconstruction

            _print(run_odm_reconstruction(args.dataset_id, profile=args.profile))
        elif args.command == "run":
            from .runner import run_experiment

            _print(run_experiment(args.dataset, profile=args.profile))
        elif args.command == "rehearse":
            from .rehearsal import rehearse_pipeline

            _print(rehearse_pipeline(args.dataset_id))
        else:
            parser.error(f"unknown command {args.command}")
            return 2
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
