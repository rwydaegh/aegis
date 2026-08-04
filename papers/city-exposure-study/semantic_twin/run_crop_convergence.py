"""Run the crop-radius convergence study."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.crop_convergence_study import CropConvergenceConfig, run_crop_convergence
from semantic_twin.paths import output
from semantic_twin.transport import DEFAULT_MAX_BOUNCES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--out", type=pathlib.Path, default=output("crop_convergence"))
    parser.add_argument("--locations", type=int, default=24)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=DEFAULT_MAX_BOUNCES)
    parser.add_argument("--observer-radius-m", type=float, default=40.0)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args(argv)
    run_crop_convergence(
        CropConvergenceConfig(
            site=args.site,
            out=args.out,
            locations=args.locations,
            rays=args.rays,
            max_bounces=args.max_bounces,
            observer_radius_m=args.observer_radius_m,
            frequency_hz=args.frequency_hz,
            seed=args.seed,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
