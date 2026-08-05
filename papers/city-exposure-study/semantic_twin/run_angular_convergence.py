"""Run the frozen 4096-cell rooftop angular convergence experiment."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.angular_convergence import AngularConvergenceConfig, run_study

ROOT = pathlib.Path(__file__).resolve().parent


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        help="configuration JSON; defaults to the production 4096-cell profile",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="use the 32/64-cell, 1000/2000-ray GPU smoke-test profile",
    )
    parser.add_argument(
        "--extended-seeds",
        action="store_true",
        help="use seeds 7 through 14 instead of the initial seeds 7 through 10",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and hash the frozen inputs, then write the run plan without loading CUDA",
    )
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="rebuild aggregate metrics from complete raw run directories without tracing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    if args.quick and args.config is not None:
        raise SystemExit("--quick and --config are mutually exclusive")
    config_path = args.config or ROOT / "config" / (
        "angular_convergence_quick.json" if args.quick else "angular_convergence_4096.json"
    )
    config = AngularConvergenceConfig.load(config_path)
    result = run_study(
        config,
        extended_seeds=args.extended_seeds,
        dry_run=args.dry_run,
        aggregate_only=args.aggregate_only,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
