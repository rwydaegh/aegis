"""Archived command-line entry point for the escape-range diagnostic."""

import argparse

from semantic_twin.illumination.escape_range_study import run, surplus_db, trace_both_ways

__all__ = ["main", "surplus_db", "trace_both_ways"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace"])
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--locations", type=int, default=12)
    ap.add_argument("--rays", type=int, default=200_000)
    ap.add_argument("--max-bounces", type=int, default=3)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--walk-stride-m", type=float, default=6.0)
    ap.add_argument("--frequency-hz", type=float, default=15.0e9)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
