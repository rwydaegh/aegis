"""Route to time-sampled trajectory.

Turns a decoded route (local ENU XY polyline) into a constant-speed trajectory
sampled at the slot interval dt, with heading set to the path tangent. The entry
offset staggers an agent's start within the synchronized crowd window.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Trajectory:
    positions: np.ndarray  # (T, 2) local XY [m]
    headings_rad: np.ndarray  # (T,) path tangent azimuth
    t0_s: float  # entry time within the crowd window


def sample_trajectory(route_xy, speed_mps, dt_s, entry_offset_s=0.0) -> Trajectory:
    route = np.asarray(route_xy, dtype=float)
    if route.ndim != 2 or route.shape[1] != 2:
        raise ValueError("route_xy must be (N, 2)")
    if route.shape[0] == 1:
        return Trajectory(
            positions=route.copy(),
            headings_rad=np.zeros(1),
            t0_s=float(entry_offset_s),
        )

    seg = np.diff(route, axis=0)
    seg_len = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = float(cum[-1])

    step = speed_mps * dt_s
    if step <= 0:
        raise ValueError("speed_mps * dt_s must be positive")
    # +1e-6 absorbs float error so an exact-multiple length yields the last slot.
    n_intervals = int(np.floor(total / step + 1e-6))
    dists = np.minimum(np.arange(n_intervals + 1) * step, total)

    seg_dir = np.zeros_like(seg)
    nonzero = seg_len > 0
    seg_dir[nonzero] = seg[nonzero] / seg_len[nonzero, None]

    positions = np.empty((dists.size, 2))
    headings = np.empty(dists.size)
    for i, d in enumerate(dists):
        # segment index containing distance d
        k = int(np.searchsorted(cum, d, side="right") - 1)
        k = min(max(k, 0), len(seg) - 1)
        local = d - cum[k]
        positions[i] = route[k] + seg_dir[k] * local
        headings[i] = np.arctan2(seg_dir[k][1], seg_dir[k][0])

    return Trajectory(positions=positions, headings_rad=headings, t0_s=float(entry_offset_s))
