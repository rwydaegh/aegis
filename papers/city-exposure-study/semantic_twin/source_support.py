"""Shared pieces of the two source construction measurements.

`measure_source_thickness.py` and `measure_source_construction.py` compare two
ways of placing base station sites on a mesh. The comparison is only worth
reading if both run through the same estimator, so the estimator lives here and
neither script owns a copy of it.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


def direct_from_sites(
    geometry: Any,
    origins: np.ndarray,
    sites: np.ndarray,
    *,
    epsilon_m: float = 1.0e-3,
    chunk: int = 400_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Direct term and visible fraction, one shadow ray per standpoint per site.

    The estimator is the mean over all sites of ``visible / r**2``, with ``r`` the
    slant range. It is exact over the set rather than sampled from it, so a
    comparison between two site sets is not read through the noise of a draw.

    The mean is over every site and not only the visible ones. That is what makes
    the number independent of how densely the set is sampled: twice as many sites
    each stand for half as many antennas. It follows from taking antennas per
    square kilometre to be equal across cities, which fixes the count in a crop of
    given radius whatever the roofline does.

    Returns one value per standpoint.
    """
    direct = np.zeros(origins.shape[0], dtype=np.float64)
    seen = np.zeros(origins.shape[0], dtype=np.float64)
    if sites.shape[0] == 0:
        return direct, seen

    for i, origin in enumerate(origins):
        total = 0.0
        visible_count = 0
        for start in range(0, sites.shape[0], chunk):
            target = sites[start : start + chunk]
            delta = target - origin
            distance = np.linalg.norm(delta, axis=1)
            direction = delta / np.maximum(distance, 1.0e-12)[:, None]
            hit, travel, _, _ = geometry.intersect(
                np.broadcast_to(origin, direction.shape) + epsilon_m * direction, direction
            )
            # A site on the mesh is hit by its own connecting ray at the far end,
            # and a site lifted just clear of the roof is not hit at all. Both are
            # clear connections, so the test is on range and not on the hit flag.
            visible = (~hit) | (travel >= distance - 2.0 * epsilon_m)
            good = visible & (distance > 0.0)
            total += float(np.sum(1.0 / distance[good] ** 2))
            visible_count += int(good.sum())
        direct[i] = total / sites.shape[0]
        seen[i] = visible_count / sites.shape[0]
    return direct, seen


def silhouette_cloud(
    geometry: Any,
    origins: np.ndarray,
    silhouette: Callable[..., tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    azimuths: int,
    elevations: int,
) -> np.ndarray:
    """Where the visible skyline actually is, found by casting and nothing else.

    A ray fan goes up each azimuth from each standpoint and the topmost hit is the
    silhouette. This reads no site set and no threshold, which is what lets it
    judge one: a construction that misses much of this cloud is missing roofline
    that a pedestrian can see.
    """
    out = []
    azimuth = (np.arange(azimuths) + 0.5) * (2.0 * np.pi / azimuths)
    for origin in origins:
        alpha, horizontal, found = silhouette(
            geometry, origin, azimuths=azimuths, elevations=elevations
        )
        good = found & np.isfinite(horizontal) & (horizontal > 0.0)
        if not good.any():
            continue
        slant = horizontal[good] / np.maximum(np.cos(alpha[good]), 1.0e-9)
        direction = np.stack(
            [
                np.cos(alpha[good]) * np.cos(azimuth[good]),
                np.cos(alpha[good]) * np.sin(azimuth[good]),
                np.sin(alpha[good]),
            ],
            axis=-1,
        )
        out.append(origin + slant[:, None] * direction)
    return np.concatenate(out) if out else np.empty((0, 3))
