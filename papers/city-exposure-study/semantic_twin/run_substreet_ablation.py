"""Run the sub-street geometry exposure ablation."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.substreet_ablation_study import SubstreetAblationConfig, run_substreet_ablation
from semantic_twin.paths import output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="newyork_timessquare")
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--locations", type=int, default=40)
    parser.add_argument("--walk-radius-m", type=float, default=60.0)
    parser.add_argument("--rays", type=int, default=120_000)
    parser.add_argument("--floor-below-datum-m", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=pathlib.Path, default=output("substreet_ablation"))
    args = parser.parse_args(argv)
    run_substreet_ablation(
        SubstreetAblationConfig(
            site=args.site,
            crop_m=args.crop_m,
            locations=args.locations,
            walk_radius_m=args.walk_radius_m,
            rays=args.rays,
            floor_below_datum_m=args.floor_below_datum_m,
            seed=args.seed,
            out=args.out,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
