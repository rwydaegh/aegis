"""Collect station-calibration results into one table and JSON report."""

from __future__ import annotations

import argparse

from semantic_twin.report.station_calibration_summary import StationCalibrationSummaryConfig, execute

SITES: tuple[str, ...] = (
    "prague_staromestske",
    "mexico_zocalo",
    "korenmarkt",
    "brussels_grandplace",
    "madrid_plazamayor",
    "tokyo_hachiko",
    "milan_duomo",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", nargs="+", default=list(SITES))
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--seeds", default="7,8,9,10")
    parser.add_argument("--baseline", default="geometric")
    parser.add_argument("--tag", default="")
    args = parser.parse_args(argv)
    return execute(
        StationCalibrationSummaryConfig(
            sites=tuple(args.site),
            crop_m=args.crop_m,
            seeds=tuple(int(value) for value in args.seeds.split(",")),
            baseline=args.baseline,
            tag=args.tag,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
