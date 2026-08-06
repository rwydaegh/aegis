"""Measure image-evidence coverage and the cost of bounce budgets."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.transport.bounce_evidence_study import OUTPUT, BounceEvidenceConfig, execute


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", nargs="+", default=["korenmarkt"])
    parser.add_argument("--crop-m", type=int, nargs="+", default=[130, 250])
    parser.add_argument("--locations", type=int, default=24)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--walk-spacing-m", type=float, default=3.0)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variance-seeds", type=int, default=8)
    parser.add_argument("--variance-standpoints", type=int, default=4)
    parser.add_argument("--tag", default="")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    return execute(
        BounceEvidenceConfig(
            sites=tuple(args.site),
            crops_m=tuple(args.crop_m),
            locations=args.locations,
            rays=args.rays,
            local_cells=args.local_cells,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            frequency_hz=args.frequency_hz,
            variant=args.variant,
            seed=args.seed,
            variance_seeds=args.variance_seeds,
            variance_standpoints=args.variance_standpoints,
            tag=args.tag,
            out=args.out,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
