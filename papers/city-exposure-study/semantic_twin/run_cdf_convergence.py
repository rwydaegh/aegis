"""Run the frozen Korenmarkt full-walk replica stopping experiment."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.cdf_convergence import (
    CdfConvergenceConfig,
    archived_rooftop_diagnostic,
    run_campaign,
)

ROOT = pathlib.Path(__file__).resolve().parent


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=ROOT / "config" / "cdf_convergence_4096.json",
        help="campaign configuration JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and hash the frozen inputs, then write a plan without loading CUDA",
    )
    parser.add_argument(
        "--analyse-only",
        action="store_true",
        help="rebuild the analysis from the compact complete-replica checkpoint",
    )
    parser.add_argument(
        "--archived-rooftop-diagnostic",
        action="store_true",
        help="run the new bootstrap analysis on the existing eight-seed rooftop archive",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    config = CdfConvergenceConfig.load(args.config)
    if args.archived_rooftop_diagnostic:
        if args.dry_run or args.analyse_only:
            raise SystemExit("--archived-rooftop-diagnostic cannot be combined with another mode")
        result = archived_rooftop_diagnostic(config)
    else:
        result = run_campaign(config, dry_run=args.dry_run, analyse_only=args.analyse_only)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
