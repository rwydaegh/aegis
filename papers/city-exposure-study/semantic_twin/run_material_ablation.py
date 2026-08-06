"""Trace one walk under alternative facade material models."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.material_ablation_study import MaterialAblationConfig, run_material_ablation
from semantic_twin.paths import output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=output("material_vlm"))
    parser.add_argument("--locations", type=int, default=120)
    parser.add_argument("--rays", type=int, default=400_000)
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--material-seeds", type=int, nargs="+", default=[0])
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args(argv)
    run_material_ablation(
        MaterialAblationConfig(
            out=args.out,
            locations=args.locations,
            rays=args.rays,
            frequency_ghz=args.frequency_ghz,
            seed=args.seed,
            material_seeds=tuple(args.material_seeds),
            only=tuple(args.only) if args.only else None,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
