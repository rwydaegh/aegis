"""Archived command-line entry point for the source-thickness study."""

from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from archive.studies.source_thickness_study import coverage, prepare, run  # noqa: E402

__all__ = ["coverage", "main", "prepare"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace", "newyork_timessquare"])
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--thickness-m", nargs="*", type=float, default=[0.5, 1.0, 2.0, 3.0, 5.0, 8.0])
    ap.add_argument("--samples", type=int, default=2_000_000)
    ap.add_argument("--standpoints", type=int, default=8)
    ap.add_argument("--azimuths", type=int, default=360)
    ap.add_argument("--elevations", type=int, default=400)
    ap.add_argument("--edge-radius-m", type=float, default=2.0)
    ap.add_argument("--edge-drop-m", type=float, default=3.0)
    ap.add_argument("--min-height-m", type=float, default=4.0)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="thickness")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
