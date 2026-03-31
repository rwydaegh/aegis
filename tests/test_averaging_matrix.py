"""Tests for precompute_averaging_matrix."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from aegis.geometry.averaging import (
    _precompute_numpy,
    precompute_averaging_matrix,
)


def _make_flat_grid(n: int = 10, spacing: float = 0.005):
    """Create a flat triangulated grid of n x n quads (2*n^2 triangles).

    Each quad is split into two triangles. All triangles lie in the z=0
    plane. Returns centroids (M, 3) and areas (M,).
    """
    xs = np.arange(n) * spacing
    ys = np.arange(n) * spacing
    centroids = []
    areas = []
    for i in range(n):
        for j in range(n):
            # Two triangles per grid cell
            x0, y0 = xs[i], ys[j]
            x1, y1 = x0 + spacing, y0
            x2, y2 = x0, y0 + spacing
            x3, y3 = x0 + spacing, y0 + spacing

            # Triangle 1: (x0,y0), (x1,y1), (x2,y2)
            cx1 = (x0 + x1 + x2) / 3
            cy1 = (y0 + y1 + y2) / 3
            centroids.append([cx1, cy1, 0.0])
            areas.append(0.5 * spacing * spacing)

            # Triangle 2: (x1,y1), (x3,y3), (x2,y2)
            cx2 = (x1 + x3 + x2) / 3
            cy2 = (y1 + y3 + y2) / 3
            centroids.append([cx2, cy2, 0.0])
            areas.append(0.5 * spacing * spacing)

    return np.array(centroids), np.array(areas)


class TestPrecomputeAveragingMatrix:
    def test_returns_sparse_csr(self):
        centroids, areas = _make_flat_grid()
        G = precompute_averaging_matrix(centroids, areas)
        assert isinstance(G, sparse.csr_array)

    def test_shape_is_m_by_m(self):
        centroids, areas = _make_flat_grid()
        M = len(areas)
        G = precompute_averaging_matrix(centroids, areas)
        assert G.shape == (M, M)

    def test_row_stochastic(self):
        """Every row sums to 1 (within float tolerance)."""
        centroids, areas = _make_flat_grid()
        G = precompute_averaging_matrix(centroids, areas)
        row_sums = np.array(G.sum(axis=1)).ravel()
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-12)

    def test_all_entries_nonnegative(self):
        centroids, areas = _make_flat_grid()
        G = precompute_averaging_matrix(centroids, areas)
        assert np.all(G.data >= 0)

    def test_uniform_field_unchanged(self):
        """A spatially uniform field should be unchanged by averaging."""
        centroids, areas = _make_flat_grid()
        G = precompute_averaging_matrix(centroids, areas)
        sab = np.ones(len(areas)) * 42.0
        sab_avg = G @ sab
        np.testing.assert_allclose(sab_avg, 42.0, atol=1e-12)

    def test_point_source_smoothed(self):
        """A single hot triangle should be smoothed out by averaging."""
        centroids, areas = _make_flat_grid(n=10, spacing=0.005)
        M = len(areas)
        sab = np.zeros(M)
        sab[M // 2] = 100.0

        G = precompute_averaging_matrix(centroids, areas)
        sab_avg = G @ sab

        # The peak should be reduced
        assert sab_avg.max() < 100.0
        # Energy should spread to neighbors
        assert np.sum(sab_avg > 0) > 1

    def test_smaller_area_fewer_nonzeros(self):
        """A 1 cm^2 averaging area should yield fewer nonzeros than 4 cm^2."""
        centroids, areas = _make_flat_grid(n=15, spacing=0.003)
        G_small = precompute_averaging_matrix(centroids, areas, target_area_m2=1e-4)
        G_large = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        assert G_small.nnz < G_large.nnz

    def test_numpy_path_matches_default(self):
        """The pure-NumPy fallback must produce similar averages to the Numba path.

        Exact matrix equality may differ at patch boundaries due to distance
        tiebreaking, so we verify that the averaged output is close for random
        input vectors and that both matrices are row-stochastic.
        """
        from scipy.spatial import cKDTree

        centroids, areas = _make_flat_grid(n=8, spacing=0.004)
        M = len(areas)
        target = 4e-4
        r_est = np.sqrt(target / np.pi) * 2.5
        tree = cKDTree(centroids)
        all_neighbors = tree.query_ball_point(centroids, r_est)

        G_numpy = _precompute_numpy(centroids, areas, all_neighbors, target, M)
        G_default = precompute_averaging_matrix(centroids, areas, target)

        # Both must be row-stochastic
        np.testing.assert_allclose(
            np.array(G_numpy.sum(axis=1)).ravel(),
            1.0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            np.array(G_default.sum(axis=1)).ravel(),
            1.0,
            atol=1e-12,
        )

        # Both must produce similar averaged output
        rng = np.random.default_rng(42)
        sab = rng.uniform(0, 10, size=M)
        np.testing.assert_allclose(
            G_numpy @ sab,
            G_default @ sab,
            rtol=0.05,
            err_msg="NumPy fallback path diverges from default (Numba) path",
        )


class TestAveragingMatrixProperties:
    """Property tests for the spatial averaging matrix."""

    def test_averaging_reduces_peak(self):
        """Spatial averaging should not increase the peak value for positive sab."""
        rng = np.random.default_rng(42)
        M = 80
        centroids = rng.uniform(0, 0.05, (M, 3))
        areas = np.full(M, 5e-5)

        sab = rng.uniform(0, 10, M)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab_avg = np.asarray(G @ sab).ravel()

        # Peak of averaged <= peak of raw (convexity of weighted average)
        assert np.max(sab_avg) <= np.max(sab) + 1e-10

    def test_total_power_preserved(self):
        """Total absorbed power P_abs = sum(sab * area) should be approximately preserved."""
        rng = np.random.default_rng(42)
        M = 60
        centroids = rng.uniform(0, 0.05, (M, 3))
        areas = rng.uniform(5e-5, 2e-4, M)

        sab = rng.uniform(0, 10, M)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab_avg = np.asarray(G @ sab).ravel()

        p_abs_raw = np.sum(sab * areas)
        p_abs_avg = np.sum(sab_avg * areas)

        assert abs(p_abs_avg - p_abs_raw) / p_abs_raw < 0.10

    def test_single_triangle(self):
        """Single triangle: G should be [1]."""
        centroids = np.array([[0, 0, 0]])
        areas = np.array([1e-4])
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        assert G.toarray().shape == (1, 1)
        assert abs(G.toarray()[0, 0] - 1.0) < 1e-12

    def test_widely_separated_triangles(self):
        """Triangles far apart should only average with themselves."""
        centroids = np.array([[0, 0, 0], [100, 0, 0], [0, 100, 0]], dtype=float)
        areas = np.array([1e-4, 1e-4, 1e-4])
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        # Each row should be a one-hot (self-averaging only)
        G_dense = G.toarray()
        np.testing.assert_allclose(G_dense, np.eye(3), atol=1e-12)
