"""Compare monocular depth estimates with support-mesh first hits."""

from __future__ import annotations

import argparse
import pathlib

from semantic_twin.vision.depth_comparison import (
    AGREEMENT_Z,
    BLOCKER_Z,
    COLOURS,
    DECISIONS,
    DYNAMIC_OBJECT_LABELS,
    MAX_CROSS_VIEW_SCALE_SPREAD,
    MIN_DISAGREEMENT_LOG_SIGMA,
    OBJECT_IDS,
    PLAUSIBLE_SCALE_BAND,
    SECOND_OPINION_LOG_SIGMA,
    STATIC_CALIBRATION_IDS,
    STATIC_CALIBRATION_LABELS,
    DepthComparisonConfig,
    classify,
    compare_mesh_depth,
    depth_log_sigma,
    fit_log_scale,
    scale_plausibility,
)
from semantic_twin.vision.depth_models import DEFAULT_REFERENCE_LOG_SIGMA

__all__ = [
    "AGREEMENT_Z",
    "BLOCKER_Z",
    "COLOURS",
    "DECISIONS",
    "DEFAULT_REFERENCE_LOG_SIGMA",
    "DYNAMIC_OBJECT_LABELS",
    "MAX_CROSS_VIEW_SCALE_SPREAD",
    "MIN_DISAGREEMENT_LOG_SIGMA",
    "OBJECT_IDS",
    "PLAUSIBLE_SCALE_BAND",
    "SECOND_OPINION_LOG_SIGMA",
    "STATIC_CALIBRATION_IDS",
    "STATIC_CALIBRATION_LABELS",
    "classify",
    "depth_log_sigma",
    "fit_log_scale",
    "scale_plausibility",
]


def arguments() -> argparse.Namespace:
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
    return parser.parse_args()


def main() -> None:
    args = arguments()
    compare_mesh_depth(
        DepthComparisonConfig(
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
    )


if __name__ == "__main__":
    main()
