"""Pedestrian observation points on the support mesh.

A walk is a chain of head height points on walkable ground. Walkable is decided
by ray casting, not by any map layer: drop a ray from above, keep the sample if
it lands on a near horizontal face close to the square's ground datum, and
require a small standoff from the nearest obstruction so the head is not inside
a wall or a market stall.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .directions import sample_sphere

SKY_PROBE = 1.0e4


@dataclass(frozen=True)
class Walk:
    """Ordered observation points with their ground datum."""

    points: np.ndarray  # (P, 3) head height positions
    ground_z_m: np.ndarray  # (P,)
    step_m: np.ndarray  # (P,) distance from the previous point
    provenance: dict[str, Any]

    def __len__(self) -> int:
        return int(self.points.shape[0])


def ground_height(geometry: Any, xy: np.ndarray, probe_z: float) -> tuple[np.ndarray, np.ndarray]:
    """Height and up-facing normal component of the surface under each xy."""
    count = xy.shape[0]
    origins = np.column_stack([xy, np.full(count, probe_z)])
    directions = np.tile(np.array([0.0, 0.0, -1.0]), (count, 1))
    hit, distance, normal, _ = geometry.intersect(origins, directions)
    z = np.where(hit, probe_z - distance, np.nan)
    return z, np.abs(normal[:, 2])


def clearance(geometry: Any, points: np.ndarray, samples: int, rng: np.random.Generator) -> np.ndarray:
    """Median distance to the nearest surface over random directions.

    A crude free space radius. It rejects points buried inside geometry, which a
    photogrammetric mesh of a market square has plenty of.
    """
    out = np.zeros(points.shape[0])
    for i, point in enumerate(points):
        directions = sample_sphere(samples, rng)
        origins = np.tile(point, (samples, 1))
        hit, distance, _, _ = geometry.intersect(origins, directions)
        distance = np.where(hit, distance, SKY_PROBE)
        out[i] = float(np.median(distance))
    return out


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
    head_height_m: float = 1.5,
    max_step_m: float = 8.0,
    clearance_samples: int = 96,
    seed: int = 0,
) -> Walk:
    """Greedy nearest neighbour chain through walkable candidates."""
    rng = np.random.default_rng(seed)
    axis = np.arange(-radius_m, radius_m + spacing_m, spacing_m)
    grid_x, grid_y = np.meshgrid(axis + centre_xy[0], axis + centre_xy[1])
    xy = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    inside = np.linalg.norm(xy - np.asarray(centre_xy), axis=1) <= radius_m
    xy = xy[inside]

    probe_z = ground_datum_m + 200.0
    z, up = ground_height(geometry, xy, probe_z)
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
            "candidates_before_clearance": int(walkable.sum()),
            "candidates_after_clearance": int(heads.shape[0]),
        },
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


def stratified_subset(walk: Walk, count: int) -> np.ndarray:
    """Evenly spaced indices along the walk, for a pilot run."""
    if count >= len(walk):
        return np.arange(len(walk))
    return np.unique(np.linspace(0, len(walk) - 1, count).round().astype(int))
