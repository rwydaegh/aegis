"""Run UniDepthV2 on perspective panorama crops."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.depth_models import (
    DEFAULT_REFERENCE_LOG_SIGMA,
    UNCERTAINTY_FIELD,
    depth_visual,
    pinhole_intrinsics,
    relative_error_to_log_sigma,
    run_unidepth,
    uncertainty_visual,
)

__all__ = [
    "DEFAULT_REFERENCE_LOG_SIGMA",
    "UNCERTAINTY_FIELD",
    "depth_visual",
    "pinhole_intrinsics",
    "relative_error_to_log_sigma",
    "uncertainty_visual",
]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--model", default="unidepth-v2-vitl14")
    parser.add_argument("--resolution-level", type=float, default=7.0)
    parser.add_argument("--reference-log-sigma", type=float, default=DEFAULT_REFERENCE_LOG_SIGMA)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    run_unidepth(
        args.views,
        args.out,
        model_name=args.model,
        resolution_level=args.resolution_level,
        reference_log_sigma=args.reference_log_sigma,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
