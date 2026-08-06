"""Compatibility entry point for the package depth-comparison pipeline."""

from __future__ import annotations

from semantic_twin.cli import depth_comparison as _depth_cli
from semantic_twin.vision import depth_comparison as _depth_comparison
from semantic_twin.vision.depth_comparison import (
    AGREEMENT_Z,
    BLOCKER_Z,
    COLOURS,
    DECISIONS,
    DEFAULT_REFERENCE_LOG_SIGMA,
    DYNAMIC_OBJECT_LABELS,
    MAX_CROSS_VIEW_SCALE_SPREAD,
    MIN_DISAGREEMENT_LOG_SIGMA,
    OBJECT_IDS,
    PLAUSIBLE_SCALE_BAND,
    SECOND_OPINION_LOG_SIGMA,
    STATIC_CALIBRATION_IDS,
    STATIC_CALIBRATION_LABELS,
    classify,
    compare_mesh_depth,
    depth_log_sigma,
    fit_log_scale,
    scale_plausibility,
)

# Keep the two historical module attributes available to direct importers.
DepthComparisonConfig = _depth_comparison.DepthComparisonConfig
arguments = _depth_cli.arguments

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


def main(argv=None) -> None:
    """Delegate the historical script command to the package implementation."""
    _depth_cli.main(argv, runner=compare_mesh_depth)


if __name__ == "__main__":
    main()
