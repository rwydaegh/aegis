"""Reusable calculations for the facade-tip source construction studies.

The command-line studies compare several deliberately different ways to turn a
photogrammetric surface into placed sources.  This module holds the calculations
shared by those studies.  The commands retain their experimental setup and
output writing so the negative results remain reproducible.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from .roofline import UP_EPSILON_M, _neighbourhood_extremes, sample_surface

SOURCE_LIFT_M = 0.05
COVERAGE_RADIUS_M = 2.0
RANGE_EDGES_M = (0.0, 5.0, 10.0, 20.0, 40.0, 80.0, np.inf)


def coverage(points: np.ndarray, reference: np.ndarray, *, radius_m: float = COVERAGE_RADIUS_M) -> float:
    """Fraction of reference points with a candidate point inside ``radius_m``."""
    if points.shape[0] == 0 or reference.shape[0] == 0:
        return float("nan")
    distance, _ = cKDTree(points).query(reference, distance_upper_bound=radius_m)
    return float(np.mean(np.isfinite(distance)))


def prepare_source_band(
    geometry: Any,
    *,
    samples: int,
    rng: np.random.Generator,
    edge_radius_m: float,
    min_height_above_ground_m: float,
    ground_datum_m: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample and measure the surface once before sweeping source thickness."""
    points = sample_surface(geometry.vertices, geometry.faces, samples, rng)
    up = np.tile(np.array([0.0, 0.0, 1.0]), (points.shape[0], 1))
    hit, _, _, _ = geometry.intersect(points + UP_EPSILON_M * up, up)
    keep = (~hit) & (points[:, 2] - ground_datum_m >= min_height_above_ground_m)
    kept = points[keep]
    if kept.shape[0] == 0:
        raise RuntimeError("no sky exposed samples above the ground, check the datum")
    lowest, highest = _neighbourhood_extremes(kept, edge_radius_m)
    return kept, lowest, highest


def facade_votes(
    geometry: Any,
    *,
    samples: int,
    rng: np.random.Generator,
    drop_radius_m: float,
    drop_m: float,
    min_height_above_ground_m: float,
    ground_datum_m: float,
) -> np.ndarray:
    """Surface samples that show a facade exists, before lifting to its top."""
    points = sample_surface(geometry.vertices, geometry.faces, samples, rng)
    up = np.tile(np.array([0.0, 0.0, 1.0]), (points.shape[0], 1))
    hit, _, _, _ = geometry.intersect(points + UP_EPSILON_M * up, up)
    keep = (~hit) & (points[:, 2] - ground_datum_m >= min_height_above_ground_m)
    kept = points[keep]
    if kept.shape[0] == 0:
        raise RuntimeError("no sky exposed samples above the ground, check the datum")

    lowest = cell_extreme(kept, drop_radius_m, np.minimum, np.inf, neighbours=True)
    return kept[kept[:, 2] - lowest >= drop_m]


def cell_extreme(
    points: np.ndarray,
    cell_m: float,
    operation: Any,
    fill: float,
    *,
    neighbours: bool,
) -> np.ndarray:
    """Extreme height in each point's cell or the nine touching cells."""
    key = np.floor(points[:, :2] / cell_m).astype(np.int64)
    key -= key.min(axis=0)
    width = int(key[:, 1].max()) + 1
    flat = key[:, 0] * width + key[:, 1]
    cells = int(key[:, 0].max() + 1) * width

    grid = np.full(cells, fill)
    operation.at(grid, flat, points[:, 2])
    if not neighbours:
        return grid[flat]

    grid = grid.reshape(-1, width)
    padded = np.pad(grid, 1, constant_values=fill)
    out = np.full_like(grid, fill)
    for dx in range(3):
        for dy in range(3):
            out = operation(out, padded[dx : dx + grid.shape[0], dy : dy + width])
    return out.reshape(-1)[flat]


def sites_from_votes(votes: np.ndarray, cell_m: float) -> np.ndarray:
    """Keep the highest vote in each occupied horizontal cell."""
    key = np.floor(votes[:, :2] / cell_m).astype(np.int64)
    key -= key.min(axis=0)
    width = int(key[:, 1].max()) + 1
    flat = key[:, 0] * width + key[:, 1]

    order = np.lexsort((-votes[:, 2], flat))
    flat_sorted = flat[order]
    first = np.concatenate(([True], flat_sorted[1:] != flat_sorted[:-1]))
    return votes[order][first]


def lift_to_top(geometry: Any, points: np.ndarray, *, lift_m: float = SOURCE_LIFT_M) -> np.ndarray:
    """Raise each point to the highest surface at its horizontal position."""
    ceiling = float(geometry.vertices[:, 2].max()) + 10.0
    above = points.copy()
    above[:, 2] = ceiling
    down = np.tile(np.array([0.0, 0.0, -1.0]), (points.shape[0], 1))
    hit, distance, _, _ = geometry.intersect(above, down)

    top = points.copy()
    found = hit & np.isfinite(distance)
    top[found, 2] = ceiling - distance[found]
    top[:, 2] = np.maximum(top[:, 2], points[:, 2])
    top[:, 2] += lift_m
    return top


def direct_by_range_band(
    geometry: Any,
    origins: np.ndarray,
    sites: np.ndarray,
    *,
    edges_m: tuple[float, ...] = RANGE_EDGES_M,
    epsilon_m: float = 1.0e-3,
    chunk: int = 400_000,
) -> np.ndarray:
    """Direct estimator split by source range, with one shared denominator."""
    out = np.zeros((origins.shape[0], len(edges_m) - 1), dtype=np.float64)
    if sites.shape[0] == 0:
        return out
    for row, origin in enumerate(origins):
        for start in range(0, sites.shape[0], chunk):
            target = sites[start : start + chunk]
            delta = target - origin
            distance = np.linalg.norm(delta, axis=1)
            direction = delta / np.maximum(distance, 1.0e-12)[:, None]
            hit, travel, _, _ = geometry.intersect(
                np.broadcast_to(origin, direction.shape) + epsilon_m * direction,
                direction,
            )
            visible = (~hit) | (travel >= distance - 2.0 * epsilon_m)
            radial = distance[visible & (distance > 0.0)]
            weight = 1.0 / radial**2
            for band, (lower, upper) in enumerate(zip(edges_m[:-1], edges_m[1:], strict=True)):
                inside = (radial >= lower) & (radial < upper)
                out[row, band] += float(np.sum(weight[inside]))
    return out / sites.shape[0]


def skyline_term(
    alpha: np.ndarray,
    horizontal: np.ndarray,
    found: np.ndarray,
    *,
    floor_m: float = 0.0,
) -> float:
    """Mean facade-tip direct term after dropping tips inside a range floor."""
    good = found & np.isfinite(horizontal) & (horizontal > floor_m)
    weight = np.zeros_like(alpha)
    weight[good] = np.cos(alpha[good]) ** 2 / horizontal[good]
    return float(weight.mean())


def skyline_summary(alpha: np.ndarray, horizontal: np.ndarray, found: np.ndarray) -> dict[str, float]:
    """Direct skyline term and the geometric values needed to interpret it."""
    good = found & np.isfinite(horizontal) & (horizontal > 0.0)
    return {
        "direct_term": skyline_term(alpha, horizontal, found),
        "open_azimuth_fraction": float(1.0 - good.mean()),
        "alpha_deg_median": float(np.degrees(np.median(alpha[good]))) if good.any() else float("nan"),
        "distance_m_median": float(np.median(horizontal[good])) if good.any() else float("nan"),
        "distance_m_p05": float(np.percentile(horizontal[good], 5)) if good.any() else float("nan"),
        "distance_m_p95": float(np.percentile(horizontal[good], 95)) if good.any() else float("nan"),
    }


# The callback annotation is kept broad because the geometry backends are optional.
Silhouette = Callable[..., tuple[np.ndarray, np.ndarray, np.ndarray]]
