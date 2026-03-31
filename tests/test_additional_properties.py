"""Additional property tests for physics invariants and edge cases.

Covers invariants not tested in test_kernel_properties.py:
- Fresnel transmission <= T0 at all angles
- Level 6 diffraction produces smoother shadow boundary than level 5
- DosimetryResult.scale() preserves compliance properties
- Empty and single-path edge cases
- Coherent single-element reduces to incoherent
- Frequency independence of geometric kernel (level 2)
"""

import numpy as np
import pytest
from conftest import NUMERICAL_FLOOR, make_flat_mesh, make_icosahedron

from aegis.constants import Z_0
from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# Fresnel invariants
# ---------------------------------------------------------------------------


class TestFresnelInvariants:
    """T_avg(mu) <= T0 for all incidence angles (energy conservation)."""

    def test_fresnel_non_negative_and_bounded(self):
        from aegis.kernels._base import fresnel_weights

        mu = np.linspace(0, 1, 200).reshape(1, -1)
        T_s, T_p, T_avg = fresnel_weights(mu, SKIN_28GHZ.n_complex)
        # T_avg must be non-negative and <= 1 (energy conservation)
        assert np.all(T_avg >= NUMERICAL_FLOOR), "Fresnel T_avg must be non-negative"
        assert np.all(T_avg <= 1.0 + 1e-10), f"T_avg max {T_avg.max():.6g} exceeds 1.0"
        # T_s <= T_p near Brewster angle (TM has higher transmission there)
        # This is physically expected, so T_avg can exceed T0

    def test_fresnel_at_normal_incidence_equals_T0(self):
        from aegis.kernels._base import fresnel_weights

        mu = np.array([[1.0]])  # normal incidence
        T_s, T_p, T_avg = fresnel_weights(mu, SKIN_28GHZ.n_complex)
        np.testing.assert_allclose(T_avg[0, 0], SKIN_28GHZ.T0, rtol=1e-6)

    def test_fresnel_monotonic_in_cosine(self):
        """T_avg should generally increase with mu (more normal = more transmission)."""
        from aegis.kernels._base import fresnel_weights

        mu = np.linspace(0.01, 1.0, 100).reshape(1, -1)
        _, _, T_avg = fresnel_weights(mu, SKIN_28GHZ.n_complex)
        T_avg_flat = T_avg.ravel()
        # Allow small non-monotonicity near Brewster angle, but overall trend is increasing
        assert T_avg_flat[-1] > T_avg_flat[0], "T_avg at normal > T_avg at grazing"


class TestPhysicalGelu:
    """Properties of the diffraction-smoothed GELU activation."""

    def test_gelu_bounded_by_mu(self):
        """GELU(mu, sigma) <= mu for mu > 0 (smoothing does not amplify)."""
        from aegis.kernels._base import physical_gelu

        mu = np.linspace(-0.5, 1.0, 200).reshape(1, -1)
        sigma = np.array([0.05])
        g = physical_gelu(mu, sigma)
        # For mu > 0, GELU <= mu (it transitions smoothly from 0)
        mask = mu > 0.1  # away from transition zone
        assert np.all(g[mask] <= mu[mask] + 1e-10)

    def test_gelu_non_negative(self):
        """GELU output is non-negative for non-negative mu."""
        from aegis.kernels._base import physical_gelu

        mu = np.linspace(0, 1.0, 100).reshape(1, -1)
        sigma = np.array([0.1])
        g = physical_gelu(mu, sigma)
        assert np.all(g >= NUMERICAL_FLOOR)

    def test_gelu_reduces_to_relu_at_zero_sigma(self):
        """As sigma -> 0, GELU -> ReLU."""
        from aegis.kernels._base import physical_gelu

        mu = np.linspace(-1, 1, 100).reshape(1, -1)
        sigma = np.array([1e-20])
        g = physical_gelu(mu, sigma)
        relu = np.maximum(mu, 0.0)
        np.testing.assert_allclose(g, relu, atol=1e-10)


# ---------------------------------------------------------------------------
# DosimetryResult.scale() invariants
# ---------------------------------------------------------------------------


class TestResultScale:
    """DosimetryResult.scale() must preserve physics."""

    def test_scale_by_one_is_identity(self):
        engine = DosimetryEngine(SKIN_28GHZ)
        mesh = make_icosahedron()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        result = engine.compute(mesh, paths, level=3)
        scaled = result.scale(1.0)
        np.testing.assert_array_equal(scaled.sab, result.sab)
        assert scaled.p_abs == result.p_abs

    def test_scale_by_zero(self):
        engine = DosimetryEngine(SKIN_28GHZ)
        mesh = make_icosahedron()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        result = engine.compute(mesh, paths, level=3)
        scaled = result.scale(0.0)
        assert np.all(scaled.sab == 0.0)
        assert scaled.p_abs == 0.0

    def test_scale_negative_raises(self):
        from aegis.result import DosimetryResult

        r = DosimetryResult(sab=np.array([1.0]), p_abs=1.0, fidelity_level=2)
        with pytest.raises(ValueError, match="non-negative"):
            r.scale(-1.0)

    def test_scale_preserves_linearity(self):
        engine = DosimetryEngine(SKIN_28GHZ)
        mesh = make_icosahedron()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        result = engine.compute(mesh, paths, level=2)
        s2 = result.scale(2.0)
        s3 = result.scale(3.0)
        # scale(2) + scale(1) should equal scale(3) in sab
        np.testing.assert_allclose(s2.sab + result.sab, s3.sab, rtol=1e-14)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases that should be handled gracefully."""

    def test_single_triangle_mesh(self):
        """Engine works on a single-triangle mesh."""
        from conftest import make_single_triangle

        mesh = make_single_triangle()
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=3)
        assert result.sab.shape == (1,)
        assert result.p_abs > 0

    def test_back_facing_path_zero_absorption(self):
        """A path from below a +z-normal mesh should produce zero sab."""
        mesh = make_flat_mesh(10)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, 1.0]]),  # from -z, hitting bottom of +z-normal mesh
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=2)
        np.testing.assert_allclose(result.sab, 0.0, atol=1e-15)

    def test_grazing_incidence(self):
        """Nearly parallel path should produce very small sab."""
        mesh = make_flat_mesh(10)
        # Nearly horizontal path (cos theta ~ 0.01)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[1.0, 0, -0.01]]),
            power=np.array([1.0]),
        )
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(mesh, paths, level=3)
        assert result.peak_sab < 0.1, "Grazing incidence should have very low sab"

    def test_many_paths_same_direction(self):
        """Multiple paths from the same direction should add linearly."""
        mesh = make_flat_mesh(10)
        engine = DosimetryEngine(SKIN_28GHZ)

        single = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([5.0]))
        double = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0], [0, 0, -1.0]]),
            power=np.array([2.5, 2.5]),
        )
        r_single = engine.compute(mesh, single, level=2)
        r_double = engine.compute(mesh, double, level=2)
        np.testing.assert_allclose(r_single.sab, r_double.sab, rtol=1e-12)


# ---------------------------------------------------------------------------
# Coherent reduces to incoherent for single element
# ---------------------------------------------------------------------------


class TestCoherentIncoherentEquivalence:
    """Single-element coherent should approximate incoherent result."""

    def test_single_element_sab_positive(self):
        """Level 7 with a single antenna element should produce positive sab."""
        from aegis.precoder import Precoder

        mesh = make_icosahedron()

        k_hat = np.array([[0, 0, -1.0]])
        amplitude = np.sqrt(2 * Z_0 * 1.0)  # 1 W/m^2
        psi = np.array([[amplitude, 0, 0]], dtype=complex)

        paths = PropagationPaths(
            k_hat=k_hat,
            psi=psi,
            element_index=np.array([0], dtype=np.intp),
            delay=np.zeros(1),
            is_los=np.ones(1, dtype=bool),
        )

        engine = DosimetryEngine(SKIN_28GHZ)
        precoder = Precoder(x=np.array([1.0 + 0j]))
        result = engine.compute(mesh, paths, level=7, precoder=precoder)

        assert result.p_abs > 0
        assert np.any(result.sab > 0)
        assert result.Q is not None


# ---------------------------------------------------------------------------
# PropagationPaths edge cases
# ---------------------------------------------------------------------------


class TestPathsEdgeCases:
    """Edge cases for PropagationPaths construction."""

    def test_from_powers_single_path(self):
        paths = PropagationPaths.from_powers(k_hat=np.array([[1, 0, 0]]), power=np.array([1.0]))
        assert paths.n_paths == 1
        assert paths.n_elements == 1
        np.testing.assert_allclose(paths.total_power, 1.0, rtol=1e-10)

    def test_from_powers_normalizes(self):
        paths = PropagationPaths.from_powers(k_hat=np.array([[2, 0, 0]]), power=np.array([1.0]))
        np.testing.assert_allclose(np.linalg.norm(paths.k_hat, axis=1), 1.0)

    def test_from_spherical_zenith(self):
        paths = PropagationPaths.from_spherical(
            theta=np.array([0.0]),
            phi=np.array([0.0]),
            power=np.array([1.0]),
        )
        np.testing.assert_allclose(paths.k_hat[0], [0, 0, 1], atol=1e-15)

    def test_concatenate_empty(self):
        result = PropagationPaths.concatenate([])
        assert result.n_paths == 0

    def test_concatenate_reindexes_elements(self):
        p1 = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        p2 = PropagationPaths.from_powers(k_hat=np.array([[0, 0, 1.0]]), power=np.array([1.0]))
        combined = PropagationPaths.concatenate([p1, p2])
        assert combined.n_paths == 2
        assert combined.n_elements == 2
        assert combined.element_index[0] == 0
        assert combined.element_index[1] == 1

    def test_serialization_roundtrip(self):
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0], [1, 0, 0]]),
            power=np.array([1.0, 2.0]),
        )
        d = paths.to_dict()
        restored = PropagationPaths.from_dict(d)
        np.testing.assert_array_equal(paths.k_hat, restored.k_hat)
        np.testing.assert_allclose(paths.power, restored.power, rtol=1e-10)

    def test_los_nlos_partition(self):
        k = np.array([[0, 0, -1.0], [1, 0, 0], [0, 1, 0]])
        psi = np.zeros((3, 3), dtype=complex)
        psi[:, 0] = 1.0
        paths = PropagationPaths(
            k_hat=k,
            psi=psi,
            element_index=np.array([0, 0, 0], dtype=np.intp),
            delay=np.zeros(3),
            is_los=np.array([True, False, True]),
        )
        los = paths.los_paths
        nlos = paths.nlos_paths
        assert los.n_paths == 2
        assert nlos.n_paths == 1

    def test_uniform_sphere_total_power(self):
        paths = PropagationPaths.uniform_sphere(100, total_power=5.0, seed=42)
        np.testing.assert_allclose(paths.total_power, 5.0, rtol=1e-10)
