"""Run Depth Anything V2 Metric Outdoor on panorama crops."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.depth_anything import axial_depth_to_ray_range, run_depth_anything

__all__ = ["axial_depth_to_ray_range"]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--model", default="depth-anything/Depth-Anything-V2-Metric-Outdoor-Large-hf")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    run_depth_anything(args.views, args.out, model_name=args.model)


if __name__ == "__main__":
    main()
