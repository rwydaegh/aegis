"""Compare monocular depth estimates with support-mesh first hits."""

from __future__ import annotations

import argparse
import pathlib
from collections.abc import Callable, Sequence

from semantic_twin.vision.depth_comparison import (
    DEFAULT_REFERENCE_LOG_SIGMA,
    MAX_CROSS_VIEW_SCALE_SPREAD,
    PLAUSIBLE_SCALE_BAND,
    SECOND_OPINION_LOG_SIGMA,
    DepthComparisonConfig,
    compare_mesh_depth,
)


def arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--mesh-depth", type=pathlib.Path, required=True)
    parser.add_argument("--unidepth", type=pathlib.Path, required=True)
    parser.add_argument("--depth-anything", type=pathlib.Path)
    parser.add_argument("--sam-labels", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    parser.add_argument("--reference-log-sigma", type=float, default=DEFAULT_REFERENCE_LOG_SIGMA)
    parser.add_argument(
        "--plausible-scale-band",
        type=float,
        nargs=2,
        default=list(PLAUSIBLE_SCALE_BAND),
        metavar=("LOW", "HIGH"),
    )
    parser.add_argument("--max-cross-view-scale-spread", type=float, default=MAX_CROSS_VIEW_SCALE_SPREAD)
    parser.add_argument("--second-opinion-log-sigma", type=float, default=SECOND_OPINION_LOG_SIGMA)
    parser.add_argument("--on-implausible-scale", choices=("stop", "degrade", "classify"), default="stop")
    return parser.parse_args(argv)


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: Callable[[DepthComparisonConfig], None] | None = None,
) -> None:
    args = arguments(argv)
    config = DepthComparisonConfig(
        views=args.views,
        mesh_depth=args.mesh_depth,
        unidepth=args.unidepth,
        depth_anything=args.depth_anything,
        sam_labels=args.sam_labels,
        semantics_json=args.semantics_json,
        out=args.out,
        yaws=tuple(args.yaws),
        reference_log_sigma=args.reference_log_sigma,
        plausible_scale_band=tuple(args.plausible_scale_band),
        max_cross_view_scale_spread=args.max_cross_view_scale_spread,
        second_opinion_log_sigma=args.second_opinion_log_sigma,
        on_implausible_scale=args.on_implausible_scale,
    )
    (compare_mesh_depth if runner is None else runner)(config)


if __name__ == "__main__":
    main()
