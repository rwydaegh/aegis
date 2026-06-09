"""The tightened query radius in precompute_averaging_matrix must produce a
matrix identical to the legacy single-pass 2.5x ball build.

The optimisation queries a smaller (1.9x) ball and re-queries only the rows that
under-fill the target area at the larger 2.5x radius. Because a row's averaged
value depends only on its nearest neighbours up to the cumulative-area cutoff,
shrinking the ball cannot change a filled row, and the escalation reproduces the
legacy best-effort result for the rest. These tests assert that equivalence on
meshes that exercise every regime: dense (no escalation), sparse (escalation),
and non-contiguous (isolated rows).
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse
from scipy.spatial import cKDTree

from aegis.geometry.averaging import (
    _flatten_neighbor_lists,
    precompute_averaging_matrix,
)


def _legacy_2p5x_build(centroids, areas, target_area_m2=4e-4):
    """The original single-pass build: one 2.5x ball query, best-effort cutoff."""
    centroids = np.ascontiguousarray(centroids, dtype=np.float64)
    areas = np.ascontiguousarray(areas, dtype=np.float64)
    m = len(areas)
    tree = cKDTree(centroids)
    r = np.sqrt(target_area_m2 / np.pi) * 2.5
    neighbors = tree.query_ball_point(centroids, r)
    nb_indices, nb_indptr = _flatten_neighbor_lists(neighbors)
    rows = np.empty(len(nb_indices) + m, dtype=np.int64)
    cols = np.empty(len(nb_indices) + m, dtype=np.int64)
    vals = np.empty(len(nb_indices) + m, dtype=np.float64)
    # The legacy build had no pending concept: it wrote best-effort entries for
    # under-filled rows. We emulate that by handling under-filled rows here so the
    # reference is the true legacy output, not the new escalation path.
    pos = 0
    for i in range(m):
        start, end = nb_indptr[i], nb_indptr[i + 1]
        k = end - start
        if k == 0:
            rows[pos], cols[pos], vals[pos] = i, i, 1.0
            pos += 1
            continue
        idx = nb_indices[start:end]
        diffs = centroids[idx] - centroids[i]
        order = np.argsort(np.einsum("ij,ij->i", diffs, diffs))
        idx_sorted = idx[order]
        cum = np.cumsum(areas[idx_sorted])
        cutoff = min(max(int(np.searchsorted(cum, target_area_m2, side="left")) + 1, 1), len(idx_sorted))
        patch = idx_sorted[:cutoff]
        total = areas[patch].sum()
        w = areas[patch] / total if total > 0 else np.full(cutoff, 1.0 / cutoff)
        rows[pos : pos + cutoff] = i
        cols[pos : pos + cutoff] = patch
        vals[pos : pos + cutoff] = w
        pos += cutoff
    return sparse.csr_array((vals[:pos], (rows[:pos], cols[:pos])), shape=(m, m))


def _max_abs_diff(a: sparse.csr_array, b: sparse.csr_array) -> float:
    d = (a - b).tocoo()
    return float(np.abs(d.data).max()) if d.nnz else 0.0


def _dense_sheet(rng, n=1200):
    """Dense near-planar sheet, small triangles -> patches fill, no escalation."""
    c = rng.uniform(-0.05, 0.05, (n, 3))
    c[:, 2] *= 0.02
    a = np.full(n, 4e-4 / 45)
    return c, a


def _sparse_cloud(rng, n=150):
    """Few large triangles spread out -> 1.9x ball under-fills, escalation fires."""
    c = rng.uniform(-0.2, 0.2, (n, 3))
    a = np.full(n, 4e-4 / 5)
    return c, a


def _isolated_clusters(rng):
    """Two tight clusters far apart plus a lone triangle (non-contiguous surface)."""
    cluster_a = rng.uniform(-0.02, 0.02, (40, 3))
    cluster_b = rng.uniform(-0.02, 0.02, (40, 3)) + np.array([2.0, 0.0, 0.0])
    lone = np.array([[10.0, 10.0, 10.0]])
    c = np.vstack([cluster_a, cluster_b, lone])
    a = np.full(len(c), 4e-4 / 25)
    return c, a


@pytest.mark.parametrize("builder", [_dense_sheet, _sparse_cloud, _isolated_clusters])
def test_matches_legacy_2p5x_build(builder):
    rng = np.random.default_rng(20240609)
    centroids, areas = builder(rng)

    g_new = precompute_averaging_matrix(centroids, areas)
    g_legacy = _legacy_2p5x_build(centroids, areas)

    assert _max_abs_diff(g_new, g_legacy) < 1e-12

    # Row-stochastic and identical action on an arbitrary field.
    rowsums = np.asarray(g_new.sum(axis=1)).ravel()
    np.testing.assert_allclose(rowsums, 1.0, atol=1e-12)
    sab = rng.random(len(areas))
    np.testing.assert_allclose(g_new @ sab, g_legacy @ sab, atol=1e-12)


def test_isolated_triangle_stays_isolated():
    """A triangle with no neighbours within 2.5x keeps a self-weight of 1 (no
    averaging across gaps), even though the fast path defers it as pending."""
    centroids = np.array([[0.0, 0.0, 0.0], [5.0, 0.0, 0.0], [0.0, 5.0, 0.0]])
    areas = np.full(3, 4e-4 / 10)  # each well below target, far apart
    g = precompute_averaging_matrix(centroids, areas)
    np.testing.assert_allclose(g.toarray(), np.eye(3), atol=1e-12)
