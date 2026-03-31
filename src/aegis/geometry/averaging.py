"""ICNIRP 4 cm^2 spatial averaging for absorbed power density.

Extracted from scripts/sab_demo.py.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse

# ---------------------------------------------------------------------------
# Numba-accelerated inner loop (optional, falls back to pure NumPy)
# ---------------------------------------------------------------------------

try:
    import numba as nb

    @nb.njit(cache=True)
    def _build_coo_numba(
        centroids,
        areas,
        nb_indices,
        nb_indptr,
        target_area,
        rows,
        cols,
        vals,
    ):
        """Build COO entries for the averaging matrix (Numba-accelerated).

        Parameters
        ----------
        centroids : (M, 3) float64
        areas : (M,) float64
        nb_indices, nb_indptr : CSR-format neighbor lists from ball query
        target_area : float64
        rows, cols : (nnz_max,) int64 pre-allocated output
        vals : (nnz_max,) float64 pre-allocated output

        Returns
        -------
        pos : int, number of nonzero entries written
        """
        M = len(areas)
        pos = 0
        for i in range(M):
            start = nb_indptr[i]
            end = nb_indptr[i + 1]
            k = end - start
            if k == 0:
                rows[pos] = i
                cols[pos] = i
                vals[pos] = 1.0
                pos += 1
                continue

            # Compute squared distances inline (no allocation)
            dists = np.empty(k, dtype=np.float64)
            for j in range(k):
                nj = nb_indices[start + j]
                dx = centroids[nj, 0] - centroids[i, 0]
                dy = centroids[nj, 1] - centroids[i, 1]
                dz = centroids[nj, 2] - centroids[i, 2]
                dists[j] = dx * dx + dy * dy + dz * dz

            # Argsort (Numba supports np.argsort)
            order = np.argsort(dists)

            # Accumulate area until target
            cum_area = 0.0
            cutoff = k
            for j in range(k):
                oj = order[j]
                cum_area += areas[nb_indices[start + oj]]
                if cum_area >= target_area:
                    cutoff = j + 1
                    break

            if cutoff < 1:
                cutoff = 1

            # Compute weights (area-weighted, normalized)
            total = 0.0
            for j in range(cutoff):
                oj = order[j]
                total += areas[nb_indices[start + oj]]

            for j in range(cutoff):
                oj = order[j]
                nj = nb_indices[start + oj]
                w = areas[nj] / total if total > 0 else 1.0 / cutoff
                rows[pos] = i
                cols[pos] = nj
                vals[pos] = w
                pos += 1

        return pos

    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False


def _flatten_neighbor_lists(all_neighbors):
    """Convert list-of-lists to CSR-format (indices, indptr) arrays."""
    lengths = np.array([len(nb) for nb in all_neighbors], dtype=np.int64)
    indptr = np.empty(len(all_neighbors) + 1, dtype=np.int64)
    indptr[0] = 0
    np.cumsum(lengths, out=indptr[1:])
    # Concatenate all neighbor lists into a single flat array
    if indptr[-1] == 0:
        return np.empty(0, dtype=np.int64), indptr
    indices = np.concatenate([np.asarray(nb, dtype=np.int64) for nb in all_neighbors])
    return indices, indptr


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
    G = precompute_averaging_matrix(centroids, areas, target_area_m2)
    return G @ sab


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

    Uses Numba JIT compilation when available for ~15-30x speedup over
    the pure-Python loop. Falls back to NumPy otherwise.

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

    if _HAS_NUMBA:
        return _precompute_numba(centroids, areas, all_neighbors, target_area_m2, M)

    return _precompute_numpy(centroids, areas, all_neighbors, target_area_m2, M)


def _precompute_numba(centroids, areas, all_neighbors, target_area_m2, M):
    """Numba-accelerated path: ~15-30x faster than pure Python."""
    nb_indices, nb_indptr = _flatten_neighbor_lists(all_neighbors)

    # Upper bound on nnz: each row writes at most k_i entries (cutoff <= k_i),
    # plus one self-entry for rows with no neighbors.
    nnz_est = len(nb_indices) + M
    rows = np.empty(nnz_est, dtype=np.int64)
    cols = np.empty(nnz_est, dtype=np.int64)
    vals = np.empty(nnz_est, dtype=np.float64)

    centroids_c = np.ascontiguousarray(centroids, dtype=np.float64)
    areas_c = np.ascontiguousarray(areas, dtype=np.float64)

    nnz = _build_coo_numba(
        centroids_c,
        areas_c,
        nb_indices,
        nb_indptr,
        target_area_m2,
        rows,
        cols,
        vals,
    )

    return sparse.csr_array(
        (vals[:nnz], (rows[:nnz], cols[:nnz])),
        shape=(M, M),
    )


def _precompute_numpy(centroids, areas, all_neighbors, target_area_m2, M):
    """Pure-NumPy fallback (original algorithm)."""
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

        # Sort by squared distance (sqrt unnecessary for ordering)
        diffs = centroids[idx] - centroids[i]
        dist_sq = np.einsum("ij,ij->i", diffs, diffs)
        order = np.argsort(dist_sq)
        idx_sorted = idx[order]

        # Accumulate area until target
        cum_area = np.cumsum(areas[idx_sorted])
        cutoff = np.searchsorted(cum_area, target_area_m2, side="left") + 1
        cutoff = max(cutoff, 1)
        cutoff = min(cutoff, len(idx_sorted))

        patch_idx = idx_sorted[:cutoff]
        patch_areas = areas[patch_idx]
        total = patch_areas.sum()
        weights = np.full(len(patch_idx), 1.0 / len(patch_idx)) if total <= 0 else patch_areas / total

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
