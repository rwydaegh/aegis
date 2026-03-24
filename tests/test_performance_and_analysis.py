"""Tests for performance optimizations and path analysis module.

Covers:
- Vectorized STL I/O round-trip
- Vectorized body channel accumulation
- Path contribution analysis
- Path importance scoring
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
from conftest import make_flat_mesh, make_icosahedron, make_single_triangle

from aegis.analysis import exposure_heatmap, path_contributions, path_importance
from aegis.coherent.body_channel import _accumulate_by_element_numpy
from aegis.geometry.mesh import BodyMesh, load_stl_binary
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# STL round-trip tests
# ---------------------------------------------------------------------------


class TestSTLRoundTrip:
    """Verify vectorized STL load/save produces identical meshes."""

    def test_round_trip_icosahedron(self):
        mesh = make_icosahedron()
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp = Path(f.name)
        try:
            mesh.save_binary_stl(tmp)
            verts, normals, centroids = load_stl_binary(tmp)
            loaded = BodyMesh(
                vertices=verts,
                normals=normals,
                centroids=centroids,
                areas=0.5 * np.linalg.norm(np.cross(verts[:, 1] - verts[:, 0], verts[:, 2] - verts[:, 0]), axis=1),
            )
            np.testing.assert_allclose(loaded.centroids, mesh.centroids, atol=1e-5)
            assert loaded.n_triangles == mesh.n_triangles
        finally:
            tmp.unlink(missing_ok=True)

    def test_round_trip_flat_mesh(self):
        mesh = make_flat_mesh(50)
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp = Path(f.name)
        try:
            mesh.save_binary_stl(tmp)
            verts, normals, centroids = load_stl_binary(tmp)
            # Normals should be approximately [0, 0, 1] for flat mesh
            np.testing.assert_allclose(normals[:, 2], 1.0, atol=1e-5)
            assert verts.shape == (50, 3, 3)
        finally:
            tmp.unlink(missing_ok=True)

    def test_round_trip_single_triangle(self):
        mesh = make_single_triangle()
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp = Path(f.name)
        try:
            mesh.save_binary_stl(tmp)
            verts, normals, centroids = load_stl_binary(tmp)
            assert verts.shape == (1, 3, 3)
            np.testing.assert_allclose(normals[0], [0, 0, 1], atol=1e-5)
        finally:
            tmp.unlink(missing_ok=True)

    def test_round_trip_preserves_areas(self):
        mesh = make_icosahedron()
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp = Path(f.name)
        try:
            mesh.save_binary_stl(tmp)
            loaded = BodyMesh.load(tmp)
            # float32 round-trip loses some precision
            np.testing.assert_allclose(loaded.areas, mesh.areas, rtol=1e-4)
        finally:
            tmp.unlink(missing_ok=True)

    def test_truncated_file_raises(self):
        """Loading a truncated STL should raise ValueError."""
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            tmp = Path(f.name)
            # Write header + triangle count of 10, but no triangle data
            f.write(b"\x00" * 80)
            import struct

            f.write(struct.pack("<I", 10))
            f.write(b"\x00" * 20)  # only 20 bytes, need 500

        try:
            with pytest.raises(ValueError, match="truncated"):
                load_stl_binary(tmp)
        finally:
            tmp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Body channel accumulation tests
# ---------------------------------------------------------------------------


class TestAccumulateByElement:
    """Test the vectorized np.add.at accumulation."""

    def test_single_element(self):
        M, N = 10, 5
        rng = np.random.default_rng(42)
        weighted = rng.standard_normal((M, N, 3)) + 1j * rng.standard_normal((M, N, 3))
        element_index = np.zeros(N, dtype=int)
        result = _accumulate_by_element_numpy(weighted, element_index, M, 1)
        assert result.shape == (M, 3, 1)
        expected = np.sum(weighted, axis=1, keepdims=True).transpose(0, 2, 1)
        np.testing.assert_allclose(result, expected, atol=1e-12)

    def test_two_elements(self):
        M, N = 5, 6
        rng = np.random.default_rng(123)
        weighted = rng.standard_normal((M, N, 3)) + 1j * rng.standard_normal((M, N, 3))
        element_index = np.array([0, 0, 1, 1, 0, 1])
        result = _accumulate_by_element_numpy(weighted, element_index, M, 2)
        assert result.shape == (M, 3, 2)
        # Element 0: indices 0, 1, 4
        expected_0 = np.sum(weighted[:, [0, 1, 4], :], axis=1)
        np.testing.assert_allclose(result[:, :, 0], expected_0, atol=1e-12)
        # Element 1: indices 2, 3, 5
        expected_1 = np.sum(weighted[:, [2, 3, 5], :], axis=1)
        np.testing.assert_allclose(result[:, :, 1], expected_1, atol=1e-12)

    def test_many_elements(self):
        M, N = 8, 20
        n_elements = 4
        rng = np.random.default_rng(7)
        weighted = rng.standard_normal((M, N, 3)) + 1j * rng.standard_normal((M, N, 3))
        element_index = rng.integers(0, n_elements, size=N)
        result = _accumulate_by_element_numpy(weighted, element_index, M, n_elements)
        # Verify against naive loop
        expected = np.zeros((M, 3, n_elements), dtype=complex)
        for j in range(n_elements):
            mask = element_index == j
            if np.any(mask):
                expected[:, :, j] = np.sum(weighted[:, mask, :], axis=1)
        np.testing.assert_allclose(result, expected, atol=1e-12)

    def test_empty_element(self):
        """Element with no paths should produce zero column."""
        M, N = 4, 3
        rng = np.random.default_rng(99)
        weighted = rng.standard_normal((M, N, 3)) + 1j * rng.standard_normal((M, N, 3))
        element_index = np.array([0, 0, 2])  # element 1 has no paths
        result = _accumulate_by_element_numpy(weighted, element_index, M, 3)
        np.testing.assert_array_equal(result[:, :, 1], 0.0)


# ---------------------------------------------------------------------------
# Path contribution analysis tests
# ---------------------------------------------------------------------------


class TestPathContributions:
    def test_single_path(self):
        mesh = make_flat_mesh(20)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([10.0]),
        )
        result = path_contributions(mesh, paths, SKIN_28GHZ)
        assert result["path_indices"].shape == (1,)
        assert result["fractions"][0] == pytest.approx(1.0)
        assert result["sab_total"] > 0

    def test_dominant_path(self):
        """One strong path should dominate contributions."""
        mesh = make_flat_mesh(20)
        k_hat = np.array([[0, 0, -1.0], [0, 0, -1.0]])
        power = np.array([100.0, 0.01])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        result = path_contributions(mesh, paths, SKIN_28GHZ)
        # First path should be dominant (fraction > 0.99)
        assert result["fractions"][0] > 0.99

    def test_specific_triangle(self):
        mesh = make_flat_mesh(20)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([5.0]),
        )
        result = path_contributions(mesh, paths, SKIN_28GHZ, triangle_index=3)
        assert result["triangle_index"] == 3

    def test_top_k(self):
        mesh = make_flat_mesh(20)
        rng = np.random.default_rng(42)
        N = 50
        k_hat = np.zeros((N, 3))
        k_hat[:, 2] = -1.0
        power = rng.uniform(0.1, 10.0, size=N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        result = path_contributions(mesh, paths, SKIN_28GHZ, top_k=5)
        assert len(result["path_indices"]) == 5
        assert len(result["contributions"]) == 5
        # Contributions should be in descending order
        assert np.all(np.diff(result["contributions"]) <= 0)

    def test_contributions_sum_to_sab(self):
        """All contributions should sum to total S_ab at target triangle."""
        mesh = make_flat_mesh(30)
        rng = np.random.default_rng(7)
        N = 10
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 5.0, size=N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        result = path_contributions(mesh, paths, SKIN_28GHZ)
        assert np.sum(result["contributions"]) == pytest.approx(result["sab_total"], rel=1e-10)

    def test_cumulative_reaches_one(self):
        mesh = make_flat_mesh(20)
        k_hat = np.array([[0, 0, -1.0], [1, 0, 0.0]])
        power = np.array([5.0, 3.0])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        result = path_contributions(mesh, paths, SKIN_28GHZ)
        assert result["cumulative"][-1] == pytest.approx(1.0, abs=1e-10)

    def test_back_facing_paths_contribute_zero(self):
        """A path going away from the surface should contribute zero."""
        mesh = make_flat_mesh(20)
        # Path going upward (+z) on a +z normal mesh = back-facing
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, 1.0]]),
            power=np.array([10.0]),
        )
        result = path_contributions(mesh, paths, SKIN_28GHZ)
        assert result["sab_total"] == pytest.approx(0.0, abs=1e-15)


class TestExposureHeatmap:
    def test_shape(self):
        mesh = make_flat_mesh(15)
        N = 8
        k_hat = np.zeros((N, 3))
        k_hat[:, 2] = -1.0
        power = np.ones(N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        C = exposure_heatmap(mesh, paths, SKIN_28GHZ)
        assert C.shape == (15, N)

    def test_nonnegative(self):
        mesh = make_icosahedron()
        rng = np.random.default_rng(42)
        N = 20
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 5.0, size=N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        C = exposure_heatmap(mesh, paths, SKIN_28GHZ)
        assert np.all(C >= 0)

    def test_row_sums_match_sab(self):
        """Row sums of contribution matrix should equal S_ab from level 3 kernel."""
        from aegis.engine import DosimetryEngine

        mesh = make_flat_mesh(30)
        rng = np.random.default_rng(7)
        N = 10
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 2.0, size=N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        C = exposure_heatmap(mesh, paths, SKIN_28GHZ)
        sab_from_C = np.sum(C, axis=1)

        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=3)
        np.testing.assert_allclose(sab_from_C, result.sab, rtol=1e-10)


class TestPathImportance:
    def test_shape(self):
        mesh = make_flat_mesh(20)
        N = 5
        k_hat = np.zeros((N, 3))
        k_hat[:, 2] = -1.0
        power = np.ones(N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        imp = path_importance(mesh, paths, SKIN_28GHZ)
        assert imp.shape == (N,)

    def test_sums_to_p_abs(self):
        """Path importance should sum to total absorbed power (level 3)."""
        from aegis.engine import DosimetryEngine

        mesh = make_flat_mesh(30)
        rng = np.random.default_rng(42)
        N = 10
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 3.0, size=N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

        imp = path_importance(mesh, paths, SKIN_28GHZ)
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=3)
        np.testing.assert_allclose(np.sum(imp), result.p_abs, rtol=1e-10)

    def test_nonnegative(self):
        mesh = make_icosahedron()
        rng = np.random.default_rng(99)
        N = 15
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.0, 5.0, size=N)
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        imp = path_importance(mesh, paths, SKIN_28GHZ)
        assert np.all(imp >= 0)

    def test_zero_power_path_has_zero_importance(self):
        mesh = make_flat_mesh(10)
        k_hat = np.array([[0, 0, -1.0], [0, 0, -1.0]])
        power = np.array([5.0, 0.0])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
        imp = path_importance(mesh, paths, SKIN_28GHZ)
        assert imp[1] == pytest.approx(0.0, abs=1e-15)
