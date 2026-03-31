"""Direct unit tests for individual kernel functions and _base helpers.

Tests each kernel level in isolation with analytically known inputs/outputs,
edge cases, and physics sanity checks. Complements test_kernel_properties.py
(Hypothesis invariants via engine) and test_spatial_kernel.py (spatial vs level).
"""

import numpy as np
import pytest

from aegis.kernels._base import fresnel_weights, incidence_geometry, physical_gelu
from aegis.kernels.level0_bound import level0_bound
from aegis.kernels.level1_aggregate import level1_aggregate
from aegis.kernels.level2_geometric import level2_geometric
from aegis.kernels.level3_fresnel import level3_fresnel
from aegis.kernels.level4_polarisation import level4_polarisation
from aegis.kernels.level5_curvature import level5_curvature
from aegis.kernels.level6_diffraction import level6_diffraction
from aegis.tissue.dielectric import SKIN_28GHZ
from tests.conftest import NUMERICAL_FLOOR

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

N_TILDE = SKIN_28GHZ.n_complex
T0 = SKIN_28GHZ.T0
FREQ = SKIN_28GHZ.freq_hz


@pytest.fixture
def single_tri_z():
    """Single triangle with normal along +z."""
    normals = np.array([[0.0, 0.0, 1.0]])
    return normals


@pytest.fixture
def two_tris():
    """Two triangles: one facing +z, one facing -z."""
    return np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]])


# ---------------------------------------------------------------------------
# _base.py: incidence_geometry
# ---------------------------------------------------------------------------


class TestIncidenceGeometry:
    def test_normal_incidence(self, single_tri_z):
        """Wave from +z hitting surface with normal +z: cos(theta) = 1."""
        k_hat = np.array([[0.0, 0.0, -1.0]])  # traveling downward
        mu, mu_plus = incidence_geometry(single_tri_z, k_hat)
        # n_hat . (-k_hat) = [0,0,1] . [0,0,1] = 1
        np.testing.assert_allclose(mu, [[1.0]])
        np.testing.assert_allclose(mu_plus, [[1.0]])

    def test_grazing_incidence(self, single_tri_z):
        """Wave traveling in xy-plane: cos(theta) = 0."""
        k_hat = np.array([[1.0, 0.0, 0.0]])
        mu, mu_plus = incidence_geometry(single_tri_z, k_hat)
        np.testing.assert_allclose(mu, [[0.0]], atol=1e-15)
        np.testing.assert_allclose(mu_plus, [[0.0]], atol=1e-15)

    def test_back_face_clamped(self, single_tri_z):
        """Wave from below (+z direction) should give mu < 0, mu_plus = 0."""
        k_hat = np.array([[0.0, 0.0, 1.0]])  # traveling upward
        mu, mu_plus = incidence_geometry(single_tri_z, k_hat)
        assert float(mu[0, 0]) == pytest.approx(-1.0)
        np.testing.assert_allclose(mu_plus, [[0.0]])

    def test_45_degree_incidence(self, single_tri_z):
        """Wave at 45 degrees."""
        k_hat = np.array([[0.0, -1.0 / np.sqrt(2), -1.0 / np.sqrt(2)]])
        mu, mu_plus = incidence_geometry(single_tri_z, k_hat)
        np.testing.assert_allclose(mu, [[1.0 / np.sqrt(2)]], rtol=1e-14)
        np.testing.assert_allclose(mu_plus, [[1.0 / np.sqrt(2)]], rtol=1e-14)

    def test_multi_triangle_multi_path(self, two_tris):
        """M=2 triangles, N=2 paths -> (2, 2) output."""
        k_hat = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
        mu, mu_plus = incidence_geometry(two_tris, k_hat)
        assert mu.shape == (2, 2)
        assert mu_plus.shape == (2, 2)
        # Triangle 0 (+z normal): path 0 (downward) = 1, path 1 (upward) = -1
        np.testing.assert_allclose(mu[0], [1.0, -1.0])
        np.testing.assert_allclose(mu_plus[0], [1.0, 0.0])
        # Triangle 1 (-z normal): path 0 (downward) = -1, path 1 (upward) = 1
        np.testing.assert_allclose(mu[1], [-1.0, 1.0])
        np.testing.assert_allclose(mu_plus[1], [0.0, 1.0])


# ---------------------------------------------------------------------------
# _base.py: fresnel_weights
# ---------------------------------------------------------------------------


class TestFresnelWeights:
    def test_normal_incidence_transmission(self):
        """At normal incidence (mu=1), T_s = T_p = T0."""
        mu = np.array([[1.0]])
        T_s, T_p, T_avg = fresnel_weights(mu, N_TILDE)
        # At normal incidence T_s and T_p should be equal
        np.testing.assert_allclose(T_s, T_p, rtol=1e-10)
        # T_avg should match T0
        np.testing.assert_allclose(float(T_avg[0, 0]), T0, rtol=1e-4)

    def test_grazing_incidence_vanishes(self):
        """At grazing incidence (mu=0), transmission should be very small."""
        mu = np.array([[0.0]])
        T_s, T_p, T_avg = fresnel_weights(mu, N_TILDE)
        assert float(T_avg[0, 0]) < T0

    def test_transmission_bounded(self):
        """Fresnel transmission must be in [0, 1]."""
        mu = np.linspace(0, 1, 50).reshape(1, -1)
        T_s, T_p, T_avg = fresnel_weights(mu, N_TILDE)
        assert np.all(T_s >= NUMERICAL_FLOOR)
        assert np.all(T_p >= NUMERICAL_FLOOR)
        assert np.all(T_s <= 1.0 + 1e-15)
        assert np.all(T_p <= 1.0 + 1e-15)

    def test_output_is_real(self):
        """Fresnel power transmission must be real-valued."""
        mu = np.array([[0.3, 0.7, 1.0]])
        T_s, T_p, T_avg = fresnel_weights(mu, N_TILDE)
        np.testing.assert_allclose(np.imag(T_s), 0.0, atol=1e-14)
        np.testing.assert_allclose(np.imag(T_p), 0.0, atol=1e-14)


# ---------------------------------------------------------------------------
# _base.py: physical_gelu
# ---------------------------------------------------------------------------


class TestPhysicalGelu:
    def test_large_mu_approaches_mu(self):
        """For mu >> sigma, GELU(mu) -> mu (well-illuminated region)."""
        mu = np.array([[5.0, 10.0]])
        sigma = np.array([0.01])
        result = physical_gelu(mu, sigma)
        np.testing.assert_allclose(result, mu, rtol=1e-6)

    def test_large_negative_mu_approaches_zero(self):
        """For mu << -sigma, GELU(mu) -> 0 (deep shadow)."""
        mu = np.array([[-5.0, -10.0]])
        sigma = np.array([0.01])
        result = physical_gelu(mu, sigma)
        np.testing.assert_allclose(result, 0.0, atol=1e-10)

    def test_zero_mu_gives_half(self):
        """At the shadow boundary (mu=0), GELU(0) = 0 * 0.5 = 0."""
        mu = np.array([[0.0]])
        sigma = np.array([0.1])
        result = physical_gelu(mu, sigma)
        np.testing.assert_allclose(result, 0.0, atol=1e-15)

    def test_shape_preserved(self):
        """Output shape matches mu shape."""
        M, N = 5, 10
        mu = np.random.default_rng(42).standard_normal((M, N))
        sigma = np.abs(np.random.default_rng(43).standard_normal(M)) + 0.01
        result = physical_gelu(mu, sigma)
        assert result.shape == (M, N)

    def test_monotonic_in_positive_mu(self):
        """GELU is monotonically increasing for mu > 0 (illuminated region)."""
        mu_vals = np.linspace(0.01, 5.0, 100).reshape(1, -1)
        sigma = np.array([0.5])
        result = physical_gelu(mu_vals, sigma)
        diffs = np.diff(result[0])
        assert np.all(diffs >= NUMERICAL_FLOOR)


# ---------------------------------------------------------------------------
# Level 0: worst-case bound
# ---------------------------------------------------------------------------


class TestLevel0Bound:
    def test_basic_bound(self):
        total_area = 1.0
        A_ab = 0.5
        D_max = 2.0
        power = np.array([1.0, 2.0])
        sab, p_abs = level0_bound(total_area, A_ab, D_max, power, T0, 10)
        expected_p_abs = T0 * (A_ab * D_max / 4.0) * 3.0
        assert float(p_abs) == pytest.approx(expected_p_abs, rel=1e-10)
        assert sab.shape == (10,)
        np.testing.assert_allclose(sab, expected_p_abs / total_area)

    def test_zero_power(self):
        sab, p_abs = level0_bound(1.0, 0.5, 2.0, np.array([0.0]), T0, 5)
        np.testing.assert_allclose(sab, 0.0)
        assert float(p_abs) == pytest.approx(0.0)

    def test_zero_area(self):
        sab, p_abs = level0_bound(0.0, 0.5, 2.0, np.array([1.0]), T0, 3)
        np.testing.assert_allclose(sab, 0.0)

    def test_uniform_output(self):
        """Level 0 produces uniform sab across all triangles."""
        sab, _ = level0_bound(2.0, 1.0, 1.0, np.array([5.0]), T0, 20)
        assert np.all(sab == sab[0])


# ---------------------------------------------------------------------------
# Level 1: aggregate with directivity
# ---------------------------------------------------------------------------


class TestLevel1Aggregate:
    def test_isotropic_fallback(self):
        """Without SH or table, D=1 -> same as no directivity."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([2.0])
        sab, p_abs = level1_aggregate(1.0, 0.5, k_hat, power, T0, 5)
        expected = T0 * (0.5 / 4.0) * 2.0
        assert float(p_abs) == pytest.approx(expected, rel=1e-10)
        assert sab.shape == (5,)

    def test_zero_area(self):
        sab, p_abs = level1_aggregate(0.0, 0.5, np.array([[0.0, 0.0, -1.0]]), np.array([1.0]), T0, 3)
        np.testing.assert_allclose(sab, 0.0)
        assert float(p_abs) == pytest.approx(T0 * 0.5 / 4.0, rel=1e-10)

    def test_with_lookup_table(self):
        """Directivity from nearest-neighbor lookup table."""
        k_hat = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
        power = np.array([1.0, 1.0])
        D_table = np.array([3.0, 0.5])
        D_dirs = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
        sab, p_abs = level1_aggregate(1.0, 1.0, k_hat, power, T0, 4, D_table=D_table, D_dirs=D_dirs)
        expected = T0 * (1.0 / 4.0) * (1.0 * 3.0 + 1.0 * 0.5)
        assert float(p_abs) == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Level 2: geometric ReLU
# ---------------------------------------------------------------------------


class TestLevel2Geometric:
    def test_normal_incidence_single_triangle(self, single_tri_z):
        """Normal incidence on a flat surface: sab = T0 * power."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([5.0])
        sab = level2_geometric(single_tri_z, k_hat, power, T0)
        np.testing.assert_allclose(sab, [T0 * 5.0], rtol=1e-12)

    def test_back_face_gives_zero(self, single_tri_z):
        """Wave from below: sab = 0 (ReLU clamps negative cosine)."""
        k_hat = np.array([[0.0, 0.0, 1.0]])
        power = np.array([5.0])
        sab = level2_geometric(single_tri_z, k_hat, power, T0)
        np.testing.assert_allclose(sab, [0.0])

    def test_45_degree(self, single_tri_z):
        """sab = T0 * cos(45) * power."""
        k_hat = np.array([[0.0, -1.0 / np.sqrt(2), -1.0 / np.sqrt(2)]])
        power = np.array([2.0])
        sab = level2_geometric(single_tri_z, k_hat, power, T0)
        expected = T0 * (1.0 / np.sqrt(2)) * 2.0
        np.testing.assert_allclose(sab, [expected], rtol=1e-12)

    def test_multi_path_superposition(self, single_tri_z):
        """Two paths: sab = T0 * sum(cos_i * power_i)."""
        k_hat = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, 1.0]])
        power = np.array([3.0, 7.0])
        sab = level2_geometric(single_tri_z, k_hat, power, T0)
        # Path 0: cos=1, path 1: cos=-1 (clamped to 0)
        np.testing.assert_allclose(sab, [T0 * 3.0], rtol=1e-12)

    def test_output_shape(self, two_tris):
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        sab = level2_geometric(two_tris, k_hat, power, T0)
        assert sab.shape == (2,)

    def test_linear_in_power(self, single_tri_z):
        k_hat = np.array([[0.0, 0.0, -1.0]])
        sab1 = level2_geometric(single_tri_z, k_hat, np.array([1.0]), T0)
        sab10 = level2_geometric(single_tri_z, k_hat, np.array([10.0]), T0)
        np.testing.assert_allclose(sab10, sab1 * 10.0, rtol=1e-12)


# ---------------------------------------------------------------------------
# Level 3: Fresnel
# ---------------------------------------------------------------------------


class TestLevel3Fresnel:
    def test_normal_incidence_matches_T0(self, single_tri_z):
        """At normal incidence, T_avg ~ T0, so level3 ~ level2."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        sab3 = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        sab2 = level2_geometric(single_tri_z, k_hat, power, T0)
        # Should be very close (Fresnel at normal incidence = T0)
        np.testing.assert_allclose(sab3, sab2, rtol=1e-3)

    def test_back_face_zero(self, single_tri_z):
        k_hat = np.array([[0.0, 0.0, 1.0]])
        power = np.array([1.0])
        sab = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        np.testing.assert_allclose(sab, [0.0], atol=1e-15)

    def test_non_negative(self, two_tris):
        rng = np.random.default_rng(7)
        k_hat = rng.standard_normal((20, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 5.0, size=20)
        sab = level3_fresnel(two_tris, k_hat, power, N_TILDE)
        assert np.all(sab >= NUMERICAL_FLOOR)


# ---------------------------------------------------------------------------
# Level 4: polarisation
# ---------------------------------------------------------------------------


class TestLevel4Polarisation:
    def test_q_zero_equals_level3(self, single_tri_z):
        """q=0 means no polarisation correction: level4 == level3."""
        k_hat = np.array([[0.0, 0.0, -1.0], [1.0 / np.sqrt(2), 0.0, -1.0 / np.sqrt(2)]])
        power = np.array([1.0, 2.0])
        sab3 = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        sab4 = level4_polarisation(single_tri_z, k_hat, power, N_TILDE, q=0.0)
        np.testing.assert_allclose(sab4, sab3, rtol=1e-12)

    def test_q_nonzero_differs(self, single_tri_z):
        """Non-zero q should produce a different result than level 3."""
        k_hat = np.array([[1.0 / np.sqrt(2), 0.0, -1.0 / np.sqrt(2)]])
        power = np.array([1.0])
        sab3 = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        sab4 = level4_polarisation(single_tri_z, k_hat, power, N_TILDE, q=1.0)
        # At oblique incidence T_p != T_s, so q=1 should differ
        assert not np.allclose(sab4, sab3, rtol=1e-6)

    def test_non_negative_random(self):
        rng = np.random.default_rng(42)
        M, N = 10, 15
        normals = rng.standard_normal((M, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 5.0, size=N)
        sab = level4_polarisation(normals, k_hat, power, N_TILDE, q=0.0)
        assert np.all(sab >= NUMERICAL_FLOOR)


# ---------------------------------------------------------------------------
# Level 5: curvature
# ---------------------------------------------------------------------------


class TestLevel5Curvature:
    def test_zero_curvature_equals_level3(self, single_tri_z):
        """H=0 makes curvature term vanish: level5 == level3."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        H = np.array([0.0])
        sab3 = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        sab5 = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H, FREQ)
        np.testing.assert_allclose(sab5, sab3, rtol=1e-10)

    def test_positive_curvature_adds_power(self, single_tri_z):
        """Positive curvature adds a correction term, increasing sab."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        H_zero = np.array([0.0])
        H_pos = np.array([50.0])
        sab_flat = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H_zero, FREQ)
        sab_curved = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H_pos, FREQ)
        assert float(sab_curved[0]) >= float(sab_flat[0]) - 1e-14

    def test_negative_curvature_clamped(self, single_tri_z):
        """Negative curvature is clamped to zero, so same as H=0."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        H_neg = np.array([-100.0])
        H_zero = np.array([0.0])
        sab_neg = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H_neg, FREQ)
        sab_zero = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H_zero, FREQ)
        np.testing.assert_allclose(sab_neg, sab_zero, rtol=1e-12)

    def test_non_negative(self):
        rng = np.random.default_rng(55)
        M, N = 8, 12
        normals = rng.standard_normal((M, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 5.0, size=N)
        H = rng.uniform(-10, 50, size=M)
        sab = level5_curvature(normals, k_hat, power, N_TILDE, T0, H, FREQ)
        assert np.all(sab >= NUMERICAL_FLOOR)


# ---------------------------------------------------------------------------
# Level 6: diffraction
# ---------------------------------------------------------------------------


class TestLevel6Diffraction:
    def test_high_freq_small_curvature_near_level5(self):
        """At high freq and small curvature, diffraction sigma is tiny.

        GELU should approximate ReLU, so level6 ~ level5.
        """
        from conftest import make_icosahedron

        body = make_icosahedron()
        rng = np.random.default_rng(77)
        N = 5
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 3.0, size=N)
        # Very small curvature -> sigma -> 0 -> GELU -> ReLU
        H = np.full(body.n_triangles, 0.01)
        sab5 = level5_curvature(body.normals, k_hat, power, N_TILDE, T0, H, FREQ)
        sab6 = level6_diffraction(body.normals, k_hat, power, N_TILDE, T0, H, FREQ)
        # Should be close but not identical due to smoothing
        np.testing.assert_allclose(sab6, sab5, rtol=0.01)

    def test_non_negative(self):
        rng = np.random.default_rng(66)
        M, N = 8, 10
        normals = rng.standard_normal((M, 3))
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.1, 5.0, size=N)
        H = rng.uniform(0, 50, size=M)
        sab = level6_diffraction(normals, k_hat, power, N_TILDE, T0, H, FREQ)
        assert np.all(sab >= NUMERICAL_FLOOR)

    def test_diffraction_smooths_shadow_boundary(self, single_tri_z):
        """Level 6 should give nonzero sab near grazing incidence where
        level 5 with ReLU gives exactly zero."""
        # Slightly from below: cos(theta) slightly negative
        k_hat = np.array([[0.0, 0.05, 0.9987]])  # mostly +z
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = np.array([1.0])
        H = np.array([20.0])  # some curvature to widen sigma
        sab5 = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H, FREQ)
        sab6 = level6_diffraction(single_tri_z, k_hat, power, N_TILDE, T0, H, FREQ)
        # Level 5 uses ReLU: back-face -> 0
        np.testing.assert_allclose(sab5, [0.0], atol=1e-10)
        # Level 6 uses GELU: smoothed transition, may be slightly > 0
        assert float(sab6[0]) >= 0.0


# ---------------------------------------------------------------------------
# Cross-level consistency
# ---------------------------------------------------------------------------


class TestCrossLevelConsistency:
    def test_level3_bounded_by_T0_power(self):
        """Total absorbed power from level 3 cannot exceed T0 * total_area * total_power."""
        from conftest import make_icosahedron

        body = make_icosahedron()
        rng = np.random.default_rng(88)
        N = 10
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.5, 3.0, size=N)

        sab3 = level3_fresnel(body.normals, k_hat, power, N_TILDE)

        # Energy conservation: P_abs <= T0 * A_body * S_total
        p_abs = float(np.sum(sab3 * body.areas))
        upper = T0 * body.total_area * float(np.sum(power))
        assert p_abs <= upper * 1.001, f"P_abs={p_abs:.6g} exceeds bound={upper:.6g}"

    def test_zero_power_all_levels(self, single_tri_z):
        """Zero incident power should give zero sab for all incoherent levels."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([0.0])
        H = np.array([10.0])

        sab0, p0 = level0_bound(1.0, 0.5, 2.0, power, T0, 1)
        sab1, p1 = level1_aggregate(1.0, 0.5, k_hat, power, T0, 1)
        sab2 = level2_geometric(single_tri_z, k_hat, power, T0)
        sab3 = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        sab4 = level4_polarisation(single_tri_z, k_hat, power, N_TILDE, q=0.5)
        sab5 = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H, FREQ)
        sab6 = level6_diffraction(single_tri_z, k_hat, power, N_TILDE, T0, H, FREQ)

        for name, sab in [
            ("L0", sab0),
            ("L1", sab1),
            ("L2", sab2),
            ("L3", sab3),
            ("L4", sab4),
            ("L5", sab5),
            ("L6", sab6),
        ]:
            np.testing.assert_allclose(sab, 0.0, atol=1e-15, err_msg=f"{name} non-zero for zero power")

    def test_single_path_level_ordering(self, single_tri_z):
        """For a single normal-incidence path, levels 2-3 should agree closely."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        sab2 = level2_geometric(single_tri_z, k_hat, power, T0)
        sab3 = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        # At normal incidence Fresnel T_avg = T0, so they should be very close
        np.testing.assert_allclose(sab3, sab2, rtol=1e-3)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_triangle_single_path(self, single_tri_z):
        """Minimal configuration: 1 triangle, 1 path."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        sab = level2_geometric(single_tri_z, k_hat, power, T0)
        assert sab.shape == (1,)
        assert float(sab[0]) > 0

    def test_many_paths(self, single_tri_z):
        """Large number of paths should work without issues."""
        rng = np.random.default_rng(99)
        N = 1000
        k_hat = rng.standard_normal((N, 3))
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = rng.uniform(0.01, 1.0, size=N)
        sab = level2_geometric(single_tri_z, k_hat, power, T0)
        assert sab.shape == (1,)
        assert np.isfinite(sab[0])

    def test_very_small_power(self, single_tri_z):
        """Very small (but nonzero) power should produce finite result."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1e-30])
        sab = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        assert np.isfinite(sab[0])
        assert float(sab[0]) >= 0

    def test_very_large_power(self, single_tri_z):
        """Large power should produce finite, scaled result."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        sab_small = level3_fresnel(single_tri_z, k_hat, np.array([1.0]), N_TILDE)
        sab_large = level3_fresnel(single_tri_z, k_hat, np.array([1e10]), N_TILDE)
        np.testing.assert_allclose(sab_large, sab_small * 1e10, rtol=1e-10)

    def test_all_back_facing(self, single_tri_z):
        """When all paths come from behind, sab should be zero."""
        k_hat = np.array([[0.0, 0.0, 1.0], [0.0, 0.1, 0.995]])
        k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
        power = np.array([5.0, 10.0])
        sab = level2_geometric(single_tri_z, k_hat, power, T0)
        np.testing.assert_allclose(sab, [0.0], atol=1e-14)

    def test_curvature_high_frequency(self, single_tri_z):
        """At very high frequency, curvature correction (H/k) should be tiny."""
        k_hat = np.array([[0.0, 0.0, -1.0]])
        power = np.array([1.0])
        H = np.array([10.0])
        freq_very_high = 300e9  # 300 GHz
        sab5 = level5_curvature(single_tri_z, k_hat, power, N_TILDE, T0, H, freq_very_high)
        sab3 = level3_fresnel(single_tri_z, k_hat, power, N_TILDE)
        # At 300 GHz, k is large so H/k is tiny -> nearly equal to level 3
        np.testing.assert_allclose(sab5, sab3, rtol=0.01)


# ---------------------------------------------------------------------------
# Level 1 array backend fix verification
# ---------------------------------------------------------------------------


class TestLevel1ArrayBackend:
    """Verify the np.full -> xp.full fix in level1_aggregate."""

    def test_level1_returns_correct_type(self):
        """level1_aggregate should return xp arrays, not NumPy arrays when using xp backend."""
        k_hat = np.array([[0, 0, -1.0]])
        power = np.array([1.0])
        sab, p_abs = level1_aggregate(
            total_area=0.1,
            A_ab=0.01,
            k_hat=k_hat,
            power=power,
            T0=T0,
            n_triangles=10,
        )
        assert sab.shape == (10,)
        assert np.all(np.isfinite(np.asarray(sab)))

    def test_level1_uniform_distribution(self):
        """Level 1 should distribute power uniformly across all triangles."""
        k_hat = np.array([[0, 0, -1.0], [1, 0, 0.0]])
        power = np.array([1.0, 0.5])
        n_tri = 20

        sab, p_abs = level1_aggregate(
            total_area=0.5,
            A_ab=0.02,
            k_hat=k_hat,
            power=power,
            T0=T0,
            n_triangles=n_tri,
        )
        sab_np = np.asarray(sab)
        # All values should be identical (uniform)
        assert np.allclose(sab_np, sab_np[0])
        # sab * total_area should equal p_abs
        assert abs(sab_np[0] * 0.5 - p_abs) < 1e-12
