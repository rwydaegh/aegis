"""Cut matched facade crops from panorama and tile texture sources."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.facade_crop_study import FacadeCropConfig, build_facade_crops

ROOT = pathlib.Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=ROOT / "outputs" / "material_vlm")
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--stride", type=int, default=128)
    parser.add_argument("--min-building-fraction", type=float, default=0.9)
    parser.add_argument("--per-view", type=int, default=4)
    parser.add_argument("--per-wall", type=int, default=5)
    parser.add_argument("--per-patch", type=int, default=2)
    parser.add_argument("--patch-separation-m", type=float, default=6.0)
    parser.add_argument("--crop-radius-m", type=float, default=130.0)
    parser.add_argument("--max-range-m", type=float, default=90.0)
    build_facade_crops(FacadeCropConfig(**vars(parser.parse_args())))


if __name__ == "__main__":
    main()
