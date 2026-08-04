"""Plot the crop-radius convergence study."""

import argparse
import pathlib

from semantic_twin.viz.crop_convergence import plot_crop_convergence

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--out", type=pathlib.Path, default=SCRIPT_DIR / "outputs/crop_convergence")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    plot_crop_convergence(args.site, args.out)


if __name__ == "__main__":
    main()
