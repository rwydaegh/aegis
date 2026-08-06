"""Plot the panorama, mesh, and ray-traced skyline functions."""

import argparse
import pathlib

from semantic_twin.viz.skyline_function import ROOT, SITES, plot_skyline_functions


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sites", nargs="*", default=SITES)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--bins", type=int, default=1440)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "outputs" / "skyline_function")
    return parser.parse_args()


def main() -> None:
    plot_skyline_functions(arguments())


if __name__ == "__main__":
    main()
