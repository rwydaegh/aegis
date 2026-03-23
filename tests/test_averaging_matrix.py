"""Tests for precompute_averaging_matrix."""

from __future__ import annotations

import numpy as np
from scipy import sparse

from aegis.geometry.averaging import precompute_averaging_matrix


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
