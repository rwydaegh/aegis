"""Tests for spatial averaging consistency and edge cases.

Verifies that apply_spatial_averaging (direct) and precompute_averaging_matrix
(sparse matrix) produce identical results. Also tests edge cases in averaging.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse

from aegis.geometry.averaging import apply_spatial_averaging, precompute_averaging_matrix


def _make_grid_mesh(nx=10, ny=10, spacing=0.002):
    """Create a regular grid of triangle centroids with known areas."""
    centroids = []
    for i in range(nx):
        for j in range(ny):
            centroids.append([i * spacing, j * spacing, 0.0])
    centroids = np.array(centroids)
    # Each triangle has area = spacing^2 / 2 (half a grid cell)
    areas = np.full(len(centroids), spacing**2 / 2)
    return centroids, areas


class TestAveragingConsistency:
    def test_direct_vs_matrix_agree(self):
        """apply_spatial_averaging and G @ sab should give the same result."""
        centroids, areas = _make_grid_mesh(8, 8)
        rng = np.random.default_rng(42)
        sab = rng.uniform(0, 10, size=len(areas))

        sab_direct = apply_spatial_averaging(sab, centroids, areas, target_area_m2=4e-4)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab_matrix = G @ sab

        np.testing.assert_allclose(sab_direct, sab_matrix, rtol=1e-10)

    def test_both_preserve_constant_field(self):
        """Averaging a constant field should return the same constant."""
        centroids, areas = _make_grid_mesh(6, 6)
        sab = np.full(len(areas), 5.0)

        sab_direct = apply_spatial_averaging(sab, centroids, areas)
        G = precompute_averaging_matrix(centroids, areas)
        sab_matrix = G @ sab

        np.testing.assert_allclose(sab_direct, 5.0, rtol=1e-10)
        np.testing.assert_allclose(sab_matrix, 5.0, rtol=1e-10)

    def test_both_reduce_peak(self):
        """Averaging should reduce or maintain the peak value."""
        centroids, areas = _make_grid_mesh(8, 8)
        sab = np.zeros(len(areas))
        sab[32] = 100.0  # spike at one point

        sab_direct = apply_spatial_averaging(sab, centroids, areas)
        G = precompute_averaging_matrix(centroids, areas)
        sab_matrix = G @ sab

        assert np.max(sab_direct) <= 100.0
        assert np.max(sab_matrix) <= 100.0


class TestMatrixProperties:
    def test_row_stochastic(self):
        """G should be row-stochastic: each row sums to 1."""
        centroids, areas = _make_grid_mesh(6, 6)
        G = precompute_averaging_matrix(centroids, areas)
        row_sums = np.array(G.sum(axis=1)).ravel()
        np.testing.assert_allclose(row_sums, 1.0, rtol=1e-10)

    def test_nonnegative(self):
        """G should have all non-negative entries."""
        centroids, areas = _make_grid_mesh(5, 5)
        G = precompute_averaging_matrix(centroids, areas)
        assert np.all(G.toarray() >= 0)

    def test_sparse_format(self):
        centroids, areas = _make_grid_mesh(5, 5)
        G = precompute_averaging_matrix(centroids, areas)
        assert isinstance(G, sparse.csr_array)
        assert G.shape == (25, 25)

    def test_single_triangle(self):
        """Single triangle: G is 1x1 identity."""
        centroids = np.array([[0.0, 0.0, 0.0]])
        areas = np.array([1e-4])
        G = precompute_averaging_matrix(centroids, areas)
        np.testing.assert_allclose(G.toarray(), [[1.0]])

    def test_different_target_areas(self):
        """Larger target area should include more neighbors."""
        centroids, areas = _make_grid_mesh(10, 10)
        G_small = precompute_averaging_matrix(centroids, areas, target_area_m2=1e-4)
        G_large = precompute_averaging_matrix(centroids, areas, target_area_m2=8e-4)
        # Larger target: more nonzeros per row on average
        nnz_small = G_small.nnz / G_small.shape[0]
        nnz_large = G_large.nnz / G_large.shape[0]
        assert nnz_large >= nnz_small


class TestDirectAveraging:
    def test_single_triangle(self):
        centroids = np.array([[0.0, 0.0, 0.0]])
        areas = np.array([1e-4])
        sab = np.array([7.0])
        result = apply_spatial_averaging(sab, centroids, areas)
        assert result[0] == pytest.approx(7.0)

    def test_preserves_total_power_approx(self):
        """Averaging should approximately preserve area-weighted total power."""
        centroids, areas = _make_grid_mesh(8, 8)
        rng = np.random.default_rng(123)
        sab = rng.uniform(0, 10, size=len(areas))

        total_before = np.sum(sab * areas)
        sab_avg = apply_spatial_averaging(sab, centroids, areas)
        total_after = np.sum(sab_avg * areas)

        # Not exact due to boundary effects, but should be close
        np.testing.assert_allclose(total_after, total_before, rtol=0.15)

    def test_nonnegative_output(self):
        """Averaging non-negative input should give non-negative output."""
        centroids, areas = _make_grid_mesh(6, 6)
        rng = np.random.default_rng(0)
        sab = rng.uniform(0, 5, size=len(areas))
        result = apply_spatial_averaging(sab, centroids, areas)
        assert np.all(result >= 0)
