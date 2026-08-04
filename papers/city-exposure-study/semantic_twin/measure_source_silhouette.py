"""Command-line entry point for the silhouette-source study."""

import argparse

from semantic_twin.illumination.source_silhouette_study import coverage, run, thin

__all__ = ["coverage", "main", "thin"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=["korenmarkt", "brussels_grandplace", "newyork_timessquare"])
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--cell-m", nargs="*", type=float, default=[8.0, 4.0, 2.0, 1.0, 0.5])
    ap.add_argument("--builders", nargs="*", type=int, default=[4, 8, 16, 32])
    ap.add_argument("--azimuths", nargs="*", type=int, default=[360, 720, 1440])
    ap.add_argument("--elevations", type=int, default=600)
    ap.add_argument(
        "--floor-m",
        type=float,
        default=0.0,
        help="drop silhouette hits nearer than this from the standpoint that found them",
    )
    ap.add_argument("--held-out", type=int, default=8)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="silhouette")
    ap.add_argument(
        "--pick",
        choices=["highest", "uniform"],
        default="highest",
        help="which member of an occupied cell becomes the site",
    )
    ap.add_argument(
        "--dims",
        type=int,
        choices=[2, 3],
        default=2,
        help="thin on a flat grid or a solid one",
    )
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
