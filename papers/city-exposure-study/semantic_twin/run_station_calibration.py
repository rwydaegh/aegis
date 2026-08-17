"""Run exposure and first-interaction evidence at camera stations."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.exposure.station_calibration import OUTPUT, StationCalibrationConfig, execute

SITES: tuple[str, ...] = (
    "prague_staromestske",
    "mexico_zocalo",
    "korenmarkt",
    "brussels_grandplace",
    "madrid_plazamayor",
    "tokyo_hachiko",
    "milan_duomo",
    "london_trafalgar",
    "krakow_rynek",
    "toulouse_capitole",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", nargs="+", default=list(SITES))
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--stage", default="both", choices=("evidence", "exposure", "both", "report"))
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--max-bounces", type=int, default=3)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--seeds", default="7,8,9,10")
    parser.add_argument("--conventions", nargs="+", default=["pose", "pedestrian"])
    parser.add_argument("--rungs", nargs="+", default=["walk", "semantic"])
    parser.add_argument("--baseline", default="geometric")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--tag", default="")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)
    return execute(
        StationCalibrationConfig(
            sites=tuple(args.site),
            crop_m=args.crop_m,
            stage=args.stage,
            rays=args.rays,
            local_cells=args.local_cells,
            walk_radius_m=args.walk_radius_m,
            frequency_hz=args.frequency_hz,
            max_bounces=args.max_bounces,
            variant=args.variant,
            seeds=tuple(int(value) for value in args.seeds.split(",")),
            conventions=tuple(args.conventions),
            rungs=tuple(args.rungs),
            baseline=args.baseline,
            workers=args.workers,
            tag=args.tag,
            out=args.out,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
