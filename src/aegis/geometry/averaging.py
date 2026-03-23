"""ICNIRP 4 cm^2 spatial averaging for absorbed power density.

Extracted from scripts/sab_demo.py.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse


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


def precompute_averaging_matrix(
    centroids: np.ndarray,
    areas: np.ndarray,
    target_area_m2: float = 4e-4,
) -> sparse.csr_array:
    """Build a sparse area-weighted averaging matrix G.

    G is row-stochastic: each row sums to 1, so ``G @ sab`` gives the
    spatially averaged absorbed power density. Precomputing G lets us
    reuse the same geometry for many fields and, when converted to a
    dense JAX array, enables automatic differentiation through the
    averaging step.

    Parameters
    ----------
    centroids : (M, 3) triangle centroids
    areas : (M,) triangle areas in m^2
    target_area_m2 : target averaging area (default 4e-4 = 4 cm^2)

    Returns
    -------
    G : (M, M) sparse CSR matrix, row-stochastic
    """
    from scipy.spatial import cKDTree

    M = len(areas)
    tree = cKDTree(centroids)

    r_est = np.sqrt(target_area_m2 / np.pi) * 2.5

    # Batch query: get all neighbor lists at once (much faster than per-point)
    all_neighbors = tree.query_ball_point(centroids, r_est)

    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []

    for i in range(M):
        idx = all_neighbors[i]

        if len(idx) == 0:
            rows.append(i)
            cols.append(i)
            vals.append(1.0)
            continue

        idx = np.asarray(idx)

        # Sort by distance from centroid i
        diffs = centroids[idx] - centroids[i]
        dists = np.sqrt(np.einsum("ij,ij->i", diffs, diffs))
        order = np.argsort(dists)
        idx_sorted = idx[order]

        # Accumulate area until target
        cum_area = np.cumsum(areas[idx_sorted])
        cutoff = np.searchsorted(cum_area, target_area_m2, side="right")
        cutoff = max(cutoff, 1)
        cutoff = min(cutoff, len(idx_sorted))

        patch_idx = idx_sorted[:cutoff]
        patch_areas = areas[patch_idx]
        weights = patch_areas / patch_areas.sum()

        n = len(patch_idx)
        rows.extend([i] * n)
        cols.extend(patch_idx.tolist())
        vals.extend(weights.tolist())

    return sparse.csr_array(
        (np.array(vals), (np.array(rows), np.array(cols))),
        shape=(M, M),
    )


def averaging_matrix_to_jax(G: sparse.csr_array):
    """Convert a scipy sparse averaging matrix to a dense JAX array.

    Parameters
    ----------
    G : sparse averaging matrix from ``precompute_averaging_matrix``

    Returns
    -------
    jnp.ndarray : dense (M, M) JAX array suitable for ``jnp.dot(G, sab)``
    """
    try:
        import jax.numpy as jnp
    except ImportError as err:
        raise ImportError("JAX required for differentiable averaging") from err
    return jnp.array(G.toarray())
