"""Edge case tests for geometry and kernel modules.

Covers:
- fibonacci_sphere / compute_projected_area (projected_area.py)
- BodyMesh (mesh.py)
- incidence_geometry / fresnel_weights / physical_gelu (_base.py)
- level0_bound, level1_aggregate, level5_curvature, level6_diffraction
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.geometry.mesh import BodyMesh
from aegis.geometry.projected_area import (
    _fibonacci_sphere_cache,
    compute_projected_area,
    fibonacci_sphere,
)
from aegis.kernels._base import fresnel_weights, incidence_geometry, physical_gelu
from aegis.kernels.level0_bound import level0_bound
from aegis.kernels.level1_aggregate import level1_aggregate
from aegis.kernels.level5_curvature import level5_curvature
from aegis.kernels.level6_diffraction import level6_diffraction
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unit(v):
    """Normalise a vector to unit length."""
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


# Refractive index from the standard SKIN_28GHZ preset
N_TILDE = SKIN_28GHZ.n_complex
T0_SKIN = SKIN_28GHZ.T0


# ===========================================================================
# fibonacci_sphere
# ===========================================================================


class TestFibonacciSphere:
    def test_n1_single_vector(self):
        pts = fibonacci_sphere(1)
        assert pts.shape == (1, 3)

    def test_n1_is_unit(self):
        pts = fibonacci_sphere(1)
        norm = np.linalg.norm(pts[0])
        assert abs(norm - 1.0) < 1e-12

    def test_negative_n_raises(self):
        with pytest.raises(ValueError, match="n must be positive"):
            fibonacci_sphere(-1)

    def test_zero_n_raises(self):
        with pytest.raises(ValueError, match="n must be positive"):
            fibonacci_sphere(0)

    def test_all_unit_length(self):
        pts = fibonacci_sphere(100)
        norms = np.linalg.norm(pts, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_cache_same_object(self):
        # Prime the cache for n=77 (unlikely to be used elsewhere)
        _fibonacci_sphere_cache.pop(77, None)
        first = fibonacci_sphere(77)
        second = fibonacci_sphere(77)
        assert first is second, "cache must return the identical array object"

    def test_output_read_only(self):
        pts = fibonacci_sphere(10)
        assert not pts.flags.writeable

    def test_shape_n_by_3(self):
        for n in (1, 10, 50, 200):
            pts = fibonacci_sphere(n)
            assert pts.shape == (n, 3), f"shape mismatch for n={n}"


# ===========================================================================
# compute_projected_area
# ===========================================================================


class TestComputeProjectedArea:
    """Tests for compute_projected_area(normals, areas, k_hat, chunk_dirs)."""

    @pytest.fixture(autouse=True)
    def _flat_setup(self):
        """A single flat triangle with normal +z and area 1."""
        self.normals = np.array([[0.0, 0.0, 1.0]])
        self.areas = np.array([1.0])

    def test_single_direction_scalar_like(self):
        k_hat = np.array([[0.0, 0.0, -1.0]])  # from above -> normal incidence
        A = compute_projected_area(self.normals, self.areas, k_hat)
        assert A.shape == (1,)
        assert float(A[0]) > 0.0

    def test_normal_incidence_value(self):
        # k_hat pointing down, normal pointing up: dot(n, -k) = 1 -> A = 1
        k_hat = np.array([[0.0, 0.0, -1.0]])
        A = compute_projected_area(self.normals, self.areas, k_hat)
        np.testing.assert_allclose(float(A[0]), 1.0, atol=1e-14)

    def test_back_facing_direction_gives_zero(self):
        # k_hat pointing up: the normal is also up, so dot(n, -k) = -1 -> clamp to 0
        k_hat = np.array([[0.0, 0.0, 1.0]])
        A = compute_projected_area(self.normals, self.areas, k_hat)
        assert float(A[0]) == 0.0

    def test_grazing_incidence(self):
        # k_hat in-plane -> dot = 0 -> A = 0
        k_hat = np.array([[1.0, 0.0, 0.0]])
        A = compute_projected_area(self.normals, self.areas, k_hat)
        np.testing.assert_allclose(float(A[0]), 0.0, atol=1e-14)

    def test_chunk_dirs_1(self):
        k_hat = fibonacci_sphere(30)
        A_default = compute_projected_area(self.normals, self.areas, k_hat)
        A_chunk1 = compute_projected_area(self.normals, self.areas, k_hat, chunk_dirs=1)
        np.testing.assert_allclose(A_chunk1, A_default, atol=1e-14)

    def test_chunk_dirs_10(self):
        k_hat = fibonacci_sphere(30)
        A_default = compute_projected_area(self.normals, self.areas, k_hat)
        A_chunk10 = compute_projected_area(self.normals, self.areas, k_hat, chunk_dirs=10)
        np.testing.assert_allclose(A_chunk10, A_default, atol=1e-14)

    def test_chunk_dirs_1000(self):
        k_hat = fibonacci_sphere(30)
        A_default = compute_projected_area(self.normals, self.areas, k_hat)
        A_chunk1000 = compute_projected_area(self.normals, self.areas, k_hat, chunk_dirs=1000)
        np.testing.assert_allclose(A_chunk1000, A_default, atol=1e-14)

    def test_multi_triangle_mesh(self, flat_mesh):
        k_hat = np.array([[0.0, 0.0, -1.0]])
        A = compute_projected_area(flat_mesh.normals, flat_mesh.areas, k_hat)
        assert A.shape == (1,)
        # For a flat mesh all pointing +z, sum of areas gives A
        np.testing.assert_allclose(float(A[0]), flat_mesh.total_area, atol=1e-12)


# ===========================================================================
# BodyMesh
# ===========================================================================


class TestBodyMesh:
    def test_sphere_creates_valid_mesh(self):
        m = BodyMesh.sphere(radius=1.0, n_subdivisions=1)
        assert m.n_triangles > 0
        assert m.normals.shape == (m.n_triangles, 3)
        assert m.vertices.shape == (m.n_triangles, 3, 3)
        assert m.areas.shape == (m.n_triangles,)

    def test_sphere_outward_normals(self):
        # For a sphere at origin, every normal dot centroid should be positive
        m = BodyMesh.sphere(radius=1.0, n_subdivisions=1)
        dots = np.einsum("ij,ij->i", m.normals, m.centroids)
        assert np.all(dots > 0), "all sphere normals must point outward"

    def test_sphere_normals_unit_length(self):
        m = BodyMesh.sphere(radius=1.0, n_subdivisions=1)
        norms = np.linalg.norm(m.normals, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_total_area_positive(self, flat_mesh):
        assert flat_mesh.total_area > 0.0

    def test_total_area_sphere_approx_4pi(self):
        m = BodyMesh.sphere(radius=1.0, n_subdivisions=4)
        expected = 4 * np.pi
        # At subdivision 4 the mesh is dense enough for 1% accuracy
        assert abs(m.total_area - expected) / expected < 0.01

    def test_n_triangles_matches_vertices_shape(self, flat_mesh):
        assert flat_mesh.n_triangles == flat_mesh.vertices.shape[0]

    def test_n_triangles_matches_normals_shape(self, ico_mesh):
        assert ico_mesh.n_triangles == ico_mesh.normals.shape[0]

    def test_sphere_radius_scales_area(self):
        r = 2.5
        m = BodyMesh.sphere(radius=r, n_subdivisions=3)
        expected = 4 * np.pi * r**2
        assert abs(m.total_area - expected) / expected < 0.02

    def test_from_arrays_roundtrip(self):
        m = BodyMesh.sphere(radius=1.0, n_subdivisions=1)
        m2 = BodyMesh.from_arrays(m.vertices, m.normals)
        np.testing.assert_allclose(m2.areas, m.areas, atol=1e-12)


# ===========================================================================
# incidence_geometry
# ===========================================================================


class TestIncidenceGeometry:
    def test_normal_incidence_mu_one(self):
        """k_hat antiparallel to normal -> mu = 1."""
        normals = np.array([[0.0, 0.0, 1.0]])
        k_hat = np.array([[0.0, 0.0, -1.0]])  # pointing into surface
        mu, mu_plus = incidence_geometry(normals, k_hat)
        np.testing.assert_allclose(float(mu[0, 0]), 1.0, atol=1e-14)
        np.testing.assert_allclose(float(mu_plus[0, 0]), 1.0, atol=1e-14)

    def test_grazing_incidence_mu_near_zero(self):
        """k_hat perpendicular to normal -> mu = 0."""
        normals = np.array([[0.0, 0.0, 1.0]])
        k_hat = np.array([[1.0, 0.0, 0.0]])
        mu, mu_plus = incidence_geometry(normals, k_hat)
        np.testing.assert_allclose(float(mu[0, 0]), 0.0, atol=1e-14)
        np.testing.assert_allclose(float(mu_plus[0, 0]), 0.0, atol=1e-14)

    def test_back_facing_mu_negative_mu_plus_zero(self):
        """k_hat parallel to normal -> mu < 0, mu_plus = 0."""
        normals = np.array([[0.0, 0.0, 1.0]])
        k_hat = np.array([[0.0, 0.0, 1.0]])  # travelling away from surface
        mu, mu_plus = incidence_geometry(normals, k_hat)
        assert float(mu[0, 0]) < 0.0
        assert float(mu_plus[0, 0]) == 0.0

    def test_shape_M_N(self):
        """Result shape is (M, N) for M normals and N paths."""
        M, N = 7, 5
        rng = np.random.default_rng(0)
        normals = rng.standard_normal((M, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        mu, mu_plus = incidence_geometry(normals, k_hat)
        assert np.asarray(mu).shape == (M, N)
        assert np.asarray(mu_plus).shape == (M, N)

    def test_mu_plus_non_negative(self):
        rng = np.random.default_rng(1)
        normals = rng.standard_normal((20, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((15, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        _, mu_plus = incidence_geometry(normals, k_hat)
        assert float(np.asarray(mu_plus).min()) >= 0.0


# ===========================================================================
# fresnel_weights
# ===========================================================================


class TestFresnelWeights:
    def test_grazing_T_near_zero(self):
        """mu=0 -> T_s = T_p = 0."""
        mu = np.zeros((1, 1))
        T_s, T_p, T_avg = fresnel_weights(mu, N_TILDE)
        assert float(np.asarray(T_s)[0, 0]) == pytest.approx(0.0, abs=1e-10)
        assert float(np.asarray(T_p)[0, 0]) == pytest.approx(0.0, abs=1e-10)

    def test_normal_incidence_T_values_skin28ghz(self):
        """mu=1 (normal incidence) should give T_avg close to T0."""
        mu = np.ones((1, 1))
        T_s, T_p, T_avg = fresnel_weights(mu, N_TILDE)
        T_avg_val = float(np.asarray(T_avg)[0, 0])
        # At normal incidence TE=TM, so T_avg == T0
        np.testing.assert_allclose(T_avg_val, T0_SKIN, rtol=1e-6)

    def test_T_s_T_p_non_negative(self):
        mu = np.linspace(0.0, 1.0, 20).reshape(20, 1)
        T_s, T_p, _ = fresnel_weights(mu, N_TILDE)
        assert float(np.asarray(T_s).min()) >= 0.0
        assert float(np.asarray(T_p).min()) >= 0.0

    def test_T_avg_equals_mean_of_T_s_T_p(self):
        rng = np.random.default_rng(2)
        mu = np.abs(rng.standard_normal((10, 8)))
        mu = np.clip(mu, 0, 1)
        T_s, T_p, T_avg = fresnel_weights(mu, N_TILDE)
        T_s = np.asarray(T_s)
        T_p = np.asarray(T_p)
        T_avg = np.asarray(T_avg)
        np.testing.assert_allclose(T_avg, 0.5 * (T_s + T_p), atol=1e-12)

    def test_T_avg_at_normal_incidence_bounded(self):
        """T_avg at normal incidence must be in (0, 1)."""
        mu = np.ones((1, 1))
        _, _, T_avg = fresnel_weights(mu, N_TILDE)
        val = float(np.asarray(T_avg)[0, 0])
        assert 0.0 < val < 1.0


# ===========================================================================
# physical_gelu
# ===========================================================================


class TestPhysicalGelu:
    def _call(self, mu_arr, sigma_arr):
        """Convenience: call physical_gelu and return a plain numpy array."""
        result = physical_gelu(np.asarray(mu_arr), np.asarray(sigma_arr))
        return np.asarray(result)

    def test_large_positive_mu_approaches_identity(self):
        """For mu >> sigma the GELU -> mu (identity branch)."""
        mu = np.array([[100.0]])
        sigma = np.array([0.01])
        out = self._call(mu, sigma)
        np.testing.assert_allclose(float(out[0, 0]), 100.0, rtol=1e-4)

    def test_large_negative_mu_approaches_zero(self):
        """For mu << -sigma the GELU -> 0 (ReLU shadow branch)."""
        mu = np.array([[-100.0]])
        sigma = np.array([0.01])
        out = self._call(mu, sigma)
        assert abs(float(out[0, 0])) < 1e-6

    def test_mu_zero_value_near_zero(self):
        """At the shadow boundary (mu=0) the GELU is near 0."""
        mu = np.array([[0.0]])
        sigma = np.array([0.1])
        out = self._call(mu, sigma)
        # GELU(0) = 0 * 0.5*(1+erf(0)) = 0
        np.testing.assert_allclose(float(out[0, 0]), 0.0, atol=1e-14)

    def test_positive_mu_always_non_negative(self):
        """For mu >= 0 the GELU is always >= 0 (erf >= 0 and mu >= 0)."""
        rng = np.random.default_rng(3)
        mu = rng.uniform(0.0, 5.0, (20, 10))
        sigma = rng.uniform(0.01, 2.0, 20)
        out = self._call(mu, sigma)
        assert float(out.min()) >= 0.0

    def test_large_negative_mu_near_zero(self):
        """For mu << -sigma the GELU approaches 0 (erf -> -1, product -> 0).

        The function is NOT strictly non-negative: it dips slightly negative
        near the shadow boundary.  Kernels clamp the final result themselves
        via xp.maximum(..., 0).  This test verifies that the deep-shadow value
        |GELU(mu)| is negligibly small (< 1e-4 * |mu|).
        """
        mu = np.array([[-50.0]])
        sigma = np.array([0.01])
        out = self._call(mu, sigma)
        assert abs(float(out[0, 0])) < 1e-4 * abs(float(mu[0, 0]))

    def test_shape_preserved(self):
        mu = np.ones((5, 3))
        sigma = np.ones(5) * 0.1
        out = self._call(mu, sigma)
        assert out.shape == (5, 3)


# ===========================================================================
# level0_bound
# ===========================================================================


class TestLevel0Bound:
    def _call(self, **kw):
        defaults = dict(
            total_area=1.0,
            A_ab=0.25,
            D_max=1.0,
            power=np.array([1.0]),
            T0=T0_SKIN,
            n_triangles=4,
        )
        defaults.update(kw)
        return level0_bound(**defaults)

    def test_uniform_sab_across_triangles(self):
        sab, _ = self._call(n_triangles=10)
        sab = np.asarray(sab)
        assert sab.shape == (10,)
        np.testing.assert_allclose(sab, sab[0], rtol=1e-12)

    def test_known_value(self):
        """p_abs = T0 * A_ab * D_max / 4 * S_total."""
        total_area = 2.0
        A_ab = 0.5
        D_max = 1.0
        power = np.array([3.0])
        T0 = 0.5
        sab, p_abs = self._call(
            total_area=total_area,
            A_ab=A_ab,
            D_max=D_max,
            power=power,
            T0=T0,
            n_triangles=1,
        )
        expected_p_abs = T0 * (A_ab * D_max / 4.0) * 3.0
        np.testing.assert_allclose(float(np.asarray(p_abs)), expected_p_abs, rtol=1e-12)
        expected_sab = expected_p_abs / total_area
        np.testing.assert_allclose(float(np.asarray(sab)[0]), expected_sab, rtol=1e-12)

    def test_zero_total_area_safe(self):
        sab, _ = self._call(total_area=0.0)
        assert float(np.asarray(sab)[0]) == 0.0

    def test_sab_non_negative(self):
        sab, _ = self._call(power=np.array([1.0, 2.0, 0.5]))
        assert float(np.asarray(sab).min()) >= 0.0


# ===========================================================================
# level1_aggregate
# ===========================================================================


class TestLevel1Aggregate:
    def _base_args(self, N=3):
        rng = np.random.default_rng(5)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = np.ones(N)
        return dict(
            total_area=1.0,
            A_ab=0.25,
            k_hat=k_hat,
            power=power,
            T0=T0_SKIN,
            n_triangles=4,
        )

    def test_no_directivity_uniform_sab(self):
        """Without sh_coeffs or D_table all weights are 1 -> same as level 0 style."""
        args = self._base_args(N=5)
        sab, _ = level1_aggregate(**args)
        sab = np.asarray(sab)
        np.testing.assert_allclose(sab, sab[0], rtol=1e-12)

    def test_no_directivity_matches_level0_formula(self):
        """Without directivity: p_abs = T0 * (A_ab/4) * sum(power)."""
        args = self._base_args(N=4)
        _, p_abs = level1_aggregate(**args)
        expected = args["T0"] * (args["A_ab"] / 4.0) * float(np.sum(args["power"]))
        np.testing.assert_allclose(float(np.asarray(p_abs)), expected, rtol=1e-12)

    def test_D_table_nearest_neighbour(self):
        """D_table lookup with simple 2-direction table."""
        N = 6
        rng = np.random.default_rng(6)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = np.ones(N)

        # Two directivity poles: one forward (+z) and one backward (-z)
        D_dirs = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])
        D_table = np.array([2.0, 0.5])

        sab, p_abs = level1_aggregate(
            total_area=1.0,
            A_ab=0.25,
            k_hat=k_hat,
            power=power,
            T0=T0_SKIN,
            n_triangles=4,
            D_table=D_table,
            D_dirs=D_dirs,
        )
        # p_abs should differ from the uniform case because D != 1
        sab_uni, p_abs_uni = level1_aggregate(
            total_area=1.0,
            A_ab=0.25,
            k_hat=k_hat,
            power=power,
            T0=T0_SKIN,
            n_triangles=4,
        )
        # D_table with values != 1 produces a different result
        assert float(np.asarray(p_abs)) != pytest.approx(float(np.asarray(p_abs_uni)))

    def test_sab_non_negative(self):
        args = self._base_args()
        sab, _ = level1_aggregate(**args)
        assert float(np.asarray(sab).min()) >= 0.0


# ===========================================================================
# level5_curvature
# ===========================================================================


class TestLevel5Curvature:
    def _make_inputs(self, M=8, N=5):
        rng = np.random.default_rng(7)
        normals = rng.standard_normal((M, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 2.0, N)
        curvature_H = rng.uniform(0.0, 5.0, M)
        return normals, k_hat, power, curvature_H

    def test_zero_curvature_matches_level3(self):
        """H=0 everywhere -> curvature term vanishes -> matches level3_fresnel."""
        from aegis.kernels.level3_fresnel import level3_fresnel

        M, N = 6, 4
        normals, k_hat, power, _ = self._make_inputs(M=M, N=N)
        curvature_zero = np.zeros(M)
        freq = 28e9

        sab5 = np.asarray(level5_curvature(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_zero, freq))
        sab3 = np.asarray(level3_fresnel(normals, k_hat, power, N_TILDE))

        np.testing.assert_allclose(sab5, sab3, rtol=1e-10)

    def test_result_non_negative(self):
        normals, k_hat, power, curvature_H = self._make_inputs()
        sab = np.asarray(level5_curvature(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_H, 28e9))
        assert float(sab.min()) >= 0.0

    def test_negative_curvature_clamped_non_negative(self):
        """Negative curvature values must not produce negative sab."""
        M, N = 5, 3
        normals, k_hat, power, _ = self._make_inputs(M=M, N=N)
        curvature_neg = -np.ones(M) * 10.0
        sab = np.asarray(level5_curvature(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_neg, 28e9))
        assert float(sab.min()) >= 0.0

    def test_very_low_frequency_no_div_by_zero(self):
        """Very low frequency exercises the k floor (1e-6)."""
        M, N = 4, 3
        normals, k_hat, power, curvature_H = self._make_inputs(M=M, N=N)
        freq_low = 1e-3  # near-DC
        sab = np.asarray(level5_curvature(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_H, freq_low))
        assert np.all(np.isfinite(sab))
        assert float(sab.min()) >= 0.0

    def test_shape(self):
        M, N = 9, 6
        normals, k_hat, power, curvature_H = self._make_inputs(M=M, N=N)
        sab = np.asarray(level5_curvature(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_H, 28e9))
        assert sab.shape == (M,)


# ===========================================================================
# level6_diffraction
# ===========================================================================


class TestLevel6Diffraction:
    def _make_inputs(self, M=8, N=5):
        rng = np.random.default_rng(8)
        normals = rng.standard_normal((M, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 2.0, N)
        curvature_H = rng.uniform(0.0, 5.0, M)
        return normals, k_hat, power, curvature_H

    def test_result_non_negative(self):
        normals, k_hat, power, curvature_H = self._make_inputs()
        sab = np.asarray(level6_diffraction(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_H, 28e9))
        assert float(sab.min()) >= 0.0

    def test_zero_curvature_sigma_floor(self):
        """H=0 -> sigma hits the floor (1e-20) -> no division by zero."""
        M, N = 5, 3
        normals, k_hat, power, _ = self._make_inputs(M=M, N=N)
        curvature_zero = np.zeros(M)
        sab = np.asarray(level6_diffraction(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_zero, 28e9))
        assert np.all(np.isfinite(sab))
        assert float(sab.min()) >= 0.0

    def test_very_low_frequency_no_div_by_zero(self):
        M, N = 4, 3
        normals, k_hat, power, curvature_H = self._make_inputs(M=M, N=N)
        sab = np.asarray(level6_diffraction(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_H, 1e-3))
        assert np.all(np.isfinite(sab))
        assert float(sab.min()) >= 0.0

    def test_shape(self):
        M, N = 7, 4
        normals, k_hat, power, curvature_H = self._make_inputs(M=M, N=N)
        sab = np.asarray(level6_diffraction(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_H, 28e9))
        assert sab.shape == (M,)

    def test_large_positive_mu_finite(self):
        """All well-illuminated triangles: result should be finite and positive."""
        M, N = 3, 2
        # Normal pointing exactly at each source
        normals = np.tile([0.0, 0.0, 1.0], (M, 1))
        k_hat = np.tile([0.0, 0.0, -1.0], (N, 1))
        power = np.array([1.0, 1.0])
        curvature_H = np.ones(M) * 0.1
        sab = np.asarray(level6_diffraction(normals, k_hat, power, N_TILDE, T0_SKIN, curvature_H, 28e9))
        assert np.all(np.isfinite(sab))
        assert float(sab.min()) > 0.0
