"""Placement optimizer via grid search.

Evaluates dosimetry at each point in a 2D grid (constrained to a plane),
tracking the best position found. The evaluate_fn callback performs
the actual RT + dosimetry computation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np


def setup(
    *,
    center: np.ndarray,
    grid_size: int = 5,
    grid_spacing: float = 2.0,
    constraint_axis: str | None = None,
    constraint_value: float | None = None,
    evaluate_fn: Callable | None = None,
) -> dict[str, Any]:
    """Initialize grid search state.

    Parameters
    ----------
    center : (3,) center of the search grid
    grid_size : number of points per axis (grid_size x grid_size)
    grid_spacing : distance between grid points in meters
    constraint_axis : 'x', 'y', or 'z' to constrain one axis
    constraint_value : value for the constrained axis
    evaluate_fn : callback(pos) -> {"peak_sab": float, "sab": array, "stats": dict}
    """
    if grid_size < 1:
        raise ValueError("grid_size must be at least 1")

    half = (grid_size - 1) / 2
    offsets = (np.arange(grid_size) - half) * grid_spacing

    if constraint_axis == "x":
        free_axes = (1, 2)
    elif constraint_axis == "y":
        free_axes = (0, 2)
    elif constraint_axis == "z":
        free_axes = (0, 1)
    else:
        free_axes = (0, 2)  # default: vary X and Z, keep Y fixed

    grid_points = []
    for a in offsets:
        for b in offsets:
            pt = np.array(center, dtype=np.float64)
            pt[free_axes[0]] = center[free_axes[0]] + a
            pt[free_axes[1]] = center[free_axes[1]] + b
            if constraint_axis is not None and constraint_value is not None:
                axis_idx = {"x": 0, "y": 1, "z": 2}[constraint_axis]
                pt[axis_idx] = constraint_value
            grid_points.append(pt)

    return {
        "grid_points": np.array(grid_points),
        "current_idx": 0,
        "best_idx": -1,
        "best_peak": float("inf"),
        "best_result": None,
        "evaluate_fn": evaluate_fn,
        "iter": 0,
    }


def step(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate the next grid point. Returns (updated_state, result_dict)."""
    idx = state["current_idx"]
    grid = state["grid_points"]
    it = state["iter"] + 1
    evaluate_fn = state.get("evaluate_fn")

    if evaluate_fn is None:
        raise ValueError("evaluate_fn is required for placement optimization")

    if idx >= len(grid):
        return state, {
            "iter": it,
            "done": True,
            "best": {
                "antenna_pos": grid[state["best_idx"]].tolist(),
                "peak_sab": state["best_peak"],
            },
            "sab": state["best_result"]["sab"],
            "params": {"antenna_pos": grid[state["best_idx"]].tolist()},
            "stats": state["best_result"]["stats"],
            "converged": True,
        }

    pos = grid[idx]
    eval_result = evaluate_fn(pos)

    peak = eval_result["peak_sab"]
    is_best = peak < state["best_peak"]

    new_state = {**state, "current_idx": idx + 1, "iter": it}
    if is_best:
        new_state["best_idx"] = idx
        new_state["best_peak"] = peak
        new_state["best_result"] = eval_result

    done = idx + 1 >= len(grid)

    result = {
        "iter": it,
        "objective": peak,
        "sab": eval_result["sab"],
        "params": {"antenna_pos": pos.tolist()},
        "stats": eval_result["stats"],
        "is_best": is_best,
        "done": done,
        "progress": (idx + 1) / len(grid),
    }
    if done:
        best_pos = grid[new_state["best_idx"]].tolist()
        result["best"] = {
            "antenna_pos": best_pos,
            "peak_sab": new_state["best_peak"],
        }
        result["sab"] = new_state["best_result"]["sab"]
        result["params"] = {"antenna_pos": best_pos}
        result["stats"] = new_state["best_result"]["stats"]
        result["converged"] = True

    return new_state, result
