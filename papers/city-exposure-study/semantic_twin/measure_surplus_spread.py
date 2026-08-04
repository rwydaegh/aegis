"""Command-line entry point for the next-event seed-spread study."""

import argparse

from semantic_twin.illumination.sources import SITE_LIFT_M
from semantic_twin.illumination.surplus_spread_study import one_seed, run

__all__ = ["main", "one_seed"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace"])
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--rays", type=int, default=200_000)
    ap.add_argument("--builders", type=int, default=128)
    ap.add_argument("--held-out-fraction", type=float, default=0.2)
    ap.add_argument("--azimuths", type=int, default=1440)
    ap.add_argument("--elevations", type=int, default=600)
    ap.add_argument("--cell-m", type=float, default=1.0)
    ap.add_argument("--site-lift-m", type=float, default=SITE_LIFT_M)
    ap.add_argument("--connections", type=int, default=1)
    ap.add_argument("--frequency-hz", type=float, default=15.0e9)
    ap.add_argument("--max-bounces", type=int, default=3)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--walk-stride-m", type=float, default=6.0)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
