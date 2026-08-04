"""Command-line entry point for the skyline measurement."""

import argparse

from semantic_twin.illumination.skyline_study import direct_term, run, skyline

__all__ = ["direct_term", "main", "skyline"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=None)
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--standpoints", type=int, default=24)
    ap.add_argument("--azimuths", type=int, default=720)
    ap.add_argument("--elevations", type=int, default=400)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="skyline")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
