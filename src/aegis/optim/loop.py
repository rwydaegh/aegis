"""Mode-agnostic optimization dispatcher.

Dispatches to the appropriate optimizer based on mode, runs the loop,
yields iteration results, and handles cancellation.
"""

from __future__ import annotations

import threading
from collections.abc import Generator
from typing import Any


def run_optimization(
    config: dict[str, Any],
    cancel_event: threading.Event,
) -> Generator[dict[str, Any], None, None]:
    """Run the optimization loop, yielding result dicts per iteration.

    Parameters
    ----------
    config : dict with at minimum "mode" and mode-specific params
    cancel_event : set this to stop the loop early
    """
    mode = config.get("mode")
    max_iters = config.get("max_iters", 50)

    if mode == "mimo_peak":
        from aegis.optim.mimo_peak import setup, step

        state = setup(
            G_tilde=config["G_tilde"],
            x_init=config["x_init"],
            signal_threshold=config.get("signal_threshold", 0.0),
            p_max=config.get("p_max", 1.0),
            lr=config.get("lr", 0.005),
        )
    elif mode == "tilt_power":
        from aegis.optim.tilt_power import setup, step

        state = setup(
            paths=config["paths"],
            normals=config["normals"],
            antenna_direction=config["antenna_direction"],
            tilt_init_deg=config.get("tilt_init_deg", 0.0),
            power_init_dbm=config.get("power_init_dbm", 60.0),
            icnirp_limit=config.get("icnirp_limit", 20.0),
            T0=config.get("T0", 1.0),
        )
    elif mode == "placement":
        from aegis.optim.placement import setup, step

        state = setup(
            center=config["center"],
            grid_size=config.get("grid_size", 5),
            grid_spacing=config.get("grid_spacing", 2.0),
            constraint_axis=config.get("constraint_axis"),
            constraint_value=config.get("constraint_value"),
            evaluate_fn=config["evaluate_fn"],
        )
    else:
        raise ValueError(f"Unknown optimization mode: {mode!r}")

    state["mode"] = mode

    for _ in range(max_iters):
        if cancel_event.is_set():
            yield {"done": True, "cancelled": True, "iter": state.get("iter", 0)}
            return

        try:
            state, result = step(state)
        except Exception as e:
            yield {"error": True, "message": str(e), "iter": state.get("iter", 0)}
            return

        result["mode"] = mode
        yield result

        if result.get("converged") or result.get("done"):
            return

    yield {"done": True, "reason": "max_iters", "iter": state.get("iter", 0)}
