"""Plot the material VLM evidence and ablations."""

import argparse
import pathlib

from semantic_twin.viz.material_vlm import HERO_CROP, plot_material_vlm

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=SCRIPT_DIR / "outputs" / "material_vlm")
    parser.add_argument("--crop", default=HERO_CROP)
    parser.add_argument("--mode", choices=("png", "pdf"), default="png")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    plot_material_vlm(args.out, args.crop, args.mode)


if __name__ == "__main__":
    main()
