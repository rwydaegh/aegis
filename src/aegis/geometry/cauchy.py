"""Cauchy surface area formula: A_ab = A_total / 4 for convex bodies.

For non-convex bodies, A_ab = mean(A_perp) which equals A_total/4 only
in the convex case.
"""

from __future__ import annotations

import numpy as np


def cauchy_projected_area(total_area: float) -> float:
    """Cauchy formula: mean projected area of a convex body = total_area / 4."""
    return total_area / 4.0


def mean_projected_area(A_perp: np.ndarray) -> float:
    """Mean projected area from a sampled LUT. Works for non-convex bodies."""
    return float(np.mean(A_perp))


def cauchy_relative_error(A_perp: np.ndarray, total_area: float) -> float:
    """Relative deviation of mean(A_perp) from the Cauchy value A_total/4.

    Positive means the body "exposes more" than a convex body of the same
    surface area (self-occlusion reduces this for non-convex bodies).
    """
    cauchy = cauchy_projected_area(total_area)
    if cauchy == 0:
        return 0.0
    return (mean_projected_area(A_perp) - cauchy) / cauchy
