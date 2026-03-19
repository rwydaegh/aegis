"""ICNIRP 4 cm^2 spatial averaging for absorbed power density.

Extracted from scripts/sab_demo.py.
"""

from __future__ import annotations

import numpy as np


def apply_spatial_averaging(
    sab: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    target_area_m2: float = 4e-4,
) -> np.ndarray:
    """Apply ICNIRP 4 cm^2 spatial averaging to per-triangle S_ab.

    For each triangle, find the minimal set of neighbours (sorted by
    distance) whose cumulative area reaches target_area. The averaged
    S_ab is the area-weighted mean over that patch.

    Parameters
    ----------
    sab : (M,) per-triangle absorbed power density
    centroids : (M, 3) triangle centroids
    areas : (M,) triangle areas
    target_area_m2 : target averaging area (default 4e-4 = 4 cm^2)

    Returns
    -------
    sab_avg : (M,) spatially averaged S_ab
    """
    from scipy.spatial import cKDTree

    M = len(sab)
    sab_avg = np.empty(M)

    tree = cKDTree(centroids)

    # Estimate search radius for ~4 cm^2 patch
    r_est = np.sqrt(target_area_m2 / np.pi) * 2.5

    for i in range(M):
        idx = tree.query_ball_point(centroids[i], r_est)

        if len(idx) == 0:
            sab_avg[i] = sab[i]
            continue

        idx = np.array(idx)

        # Sort by distance
        dists = np.linalg.norm(centroids[idx] - centroids[i], axis=1)
        order = np.argsort(dists)
        idx_sorted = idx[order]

        # Accumulate area until target
        cum_area = np.cumsum(areas[idx_sorted])
        cutoff = np.searchsorted(cum_area, target_area_m2, side="right")
        cutoff = max(cutoff, 1)
        cutoff = min(cutoff, len(idx_sorted))

        patch_idx = idx_sorted[:cutoff]
        patch_areas = areas[patch_idx]
        patch_sab = sab[patch_idx]

        sab_avg[i] = np.average(patch_sab, weights=patch_areas)

    return sab_avg
