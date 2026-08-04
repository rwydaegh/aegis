"""Run the corrected-versus-fixed-height illumination law comparison."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.law_comparison_study import LawComparisonConfig, run_law_comparison
from semantic_twin.paths import output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crops", type=int, nargs="+", default=[130, 250])
    parser.add_argument("--anchor-crop-m", type=int, default=130)
    parser.add_argument("--locations", type=int, default=40)
    parser.add_argument("--walk-radius-m", type=float, default=60.0)
    parser.add_argument("--rays", type=int, default=150_000)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=pathlib.Path, default=output("law_comparison"))
    args = parser.parse_args(argv)
    run_law_comparison(
        LawComparisonConfig(
            site=args.site,
            crops=tuple(args.crops),
            anchor_crop_m=args.anchor_crop_m,
            locations=args.locations,
            walk_radius_m=args.walk_radius_m,
            rays=args.rays,
            frequency_hz=args.frequency_hz,
            seed=args.seed,
            out=args.out,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
