"""Command-line entry point for the near-clutter measurement."""

import argparse

from semantic_twin.illumination.near_clutter_study import run, term

# Kept literal because the site-registry regression test reads command metadata
# without importing optional tracing dependencies.
SITES = [
    "brussels_grandplace",
    "korenmarkt",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "milan_duomo",
    "newyork_timessquare",
    "prague_staromestske",
    "tokyo_hachiko",
    "toulouse_capitole",
]

__all__ = ["SITES", "main", "term"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=SITES)
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--standpoints", type=int, default=16)
    ap.add_argument("--azimuths", type=int, default=720)
    ap.add_argument("--elevations", type=int, default=400)
    ap.add_argument("--floors-m", nargs="*", type=float, default=[0.0, 3.0, 5.0, 8.0, 12.0])
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="near_clutter")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
