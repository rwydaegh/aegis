"""A lattice over the walkable ground of a square.

This is the rule every published number in the study was computed under, and it
is not a walk. It lays a configurable regular grid over a disc, keeps the squares whose
ground passes the gates in :mod:`~semantic_twin.walk.ground`, and joins the
survivors nearest neighbour first. That is a flood fill of the open ground. It
gives an ordering, which is what :func:`~semantic_twin.walk.model.stratified_subset`
needs, and it does not give a route anybody took.

It is kept because it is what the numbers rest on, and because as a sampling
design it is defensible: it covers the square evenly rather than following the
street a survey vehicle happened to drive. What it costs is evidence. The
guarantee behind the method is that a photograph taken at a point sees the
surfaces that scatter energy into that point, and BOUNCE_BUDGET.md measures how
far that guarantee travels. At Korenmarkt the grid's mean distance from a
standpoint to the nearest camera is 44.3 m, where the capture route's is 2.8 m.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .ground import SKY_PROBE, clearance, ground_height, sky_visibility
from .model import GRID, Walk


def build_walk(
    geometry: Any,
    *,
    ground_datum_m: float,
    centre_xy: tuple[float, float] = (0.0, 0.0),
    radius_m: float = 90.0,
    spacing_m: float = 3.0,
    datum_tolerance_m: float = 2.5,
    min_up_cosine: float = 0.85,
    min_clearance_m: float = 2.0,
    min_sky_fraction: float = 0.01,
    head_height_m: float = 1.5,
    max_step_m: float = 8.0,
    clearance_samples: int = 96,
    seed: int = 0,
    probe_z_m: float = SKY_PROBE,
) -> Walk:
    """Greedy nearest neighbour chain through walkable candidates.

    ``probe_z_m`` is the height the downward casts start from and it is
    exposed for one reason: every run published before 3 August started them at
    the ground datum plus 200 m, and a rerun that has to extend or repair one of
    those runs has to select the same standpoints it did. The value is recorded
    in the provenance, so which rule a walk was built under is readable off the
    manifest rather than inferred from a timestamp. New work wants the default.
    """
    rng = np.random.default_rng(seed)
    axis = np.arange(-radius_m, radius_m + spacing_m, spacing_m)
    grid_x, grid_y = np.meshgrid(axis + centre_xy[0], axis + centre_xy[1])
    xy = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    inside = np.linalg.norm(xy - np.asarray(centre_xy), axis=1) <= radius_m
    xy = xy[inside]

    z, up = ground_height(geometry, xy, probe_z_m)
    walkable = np.isfinite(z) & (np.abs(z - ground_datum_m) <= datum_tolerance_m) & (up >= min_up_cosine)
    xy = xy[walkable]
    z = z[walkable]
    if xy.shape[0] == 0:
        raise RuntimeError("no walkable candidates, check the ground datum")

    heads = np.column_stack([xy, z + head_height_m])
    free = clearance(geometry, heads, clearance_samples, rng)
    keep = free >= min_clearance_m
    heads = heads[keep]
    z = z[keep]
    if heads.shape[0] == 0:
        raise RuntimeError("every walkable candidate failed the clearance test")

    sky = sky_visibility(geometry, heads, clearance_samples, rng)
    open_air = sky >= min_sky_fraction
    enclosed = int(np.count_nonzero(~open_air))
    heads = heads[open_air]
    z = z[open_air]
    if heads.shape[0] == 0:
        raise RuntimeError("every walkable candidate was enclosed")

    order = _chain(heads[:, :2], max_step_m)
    heads = heads[order]
    z = z[order]
    step = np.zeros(heads.shape[0])
    step[1:] = np.linalg.norm(np.diff(heads[:, :2], axis=0), axis=1)
    return Walk(
        points=heads,
        ground_z_m=z,
        step_m=step,
        provenance={
            "ground_datum_m": ground_datum_m,
            "centre_xy": list(centre_xy),
            "radius_m": radius_m,
            "spacing_m": spacing_m,
            "datum_tolerance_m": datum_tolerance_m,
            "min_up_cosine": min_up_cosine,
            "min_clearance_m": min_clearance_m,
            "head_height_m": head_height_m,
            "clearance_samples": clearance_samples,
            "probe_z_m": probe_z_m,
            "candidates_before_clearance": int(walkable.sum()),
            "min_sky_fraction": min_sky_fraction,
            "candidates_rejected_as_enclosed": enclosed,
            "candidates_after_clearance": int(heads.shape[0]),
        },
        kind=GRID,
    )


def _chain(xy: np.ndarray, max_step_m: float) -> np.ndarray:
    """Greedy nearest neighbour ordering, restarting when the gap is too wide."""
    remaining = list(range(xy.shape[0]))
    start = int(np.argmin(xy[:, 0] + xy[:, 1]))
    remaining.remove(start)
    order = [start]
    current = start
    while remaining:
        distances = np.linalg.norm(xy[remaining] - xy[current], axis=1)
        pick = int(np.argmin(distances))
        if distances[pick] > max_step_m:
            pick = int(np.argmin(np.linalg.norm(xy[remaining] - xy[order[0]], axis=1)))
        current = remaining.pop(pick)
        order.append(current)
    return np.asarray(order, dtype=np.int64)
