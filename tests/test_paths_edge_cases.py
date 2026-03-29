"""Edge case tests for PropagationPaths.

Covers validation errors, boundary inputs, factory methods, serialization,
and property correctness that are not already in test_paths.py.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from aegis.constants import Z_0
from aegis.paths import PropagationPaths

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paths(n: int = 3, seed: int = 0) -> PropagationPaths:
    """Return a small valid PropagationPaths with n paths."""
    rng = np.random.default_rng(seed)
    k = rng.standard_normal((n, 3))
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    power = rng.uniform(0.5, 2.0, size=n)
    return PropagationPaths.from_powers(k_hat=k, power=power)


# ---------------------------------------------------------------------------
# 1. PropagationPaths direct construction validation
# ---------------------------------------------------------------------------


class TestValidation:
    """__post_init__ raises ValueError on bad inputs."""

    def _valid_kwargs(self, n: int = 2) -> dict:
        k = np.eye(3, dtype=np.float64)[:n]
        psi = np.ones((n, 3), dtype=complex)
        return dict(
            k_hat=k,
            psi=psi,
            element_index=np.arange(n, dtype=np.intp),
            delay=np.zeros(n, dtype=np.float64),
            is_los=np.ones(n, dtype=bool),
        )

    def test_k_hat_wrong_shape_raises(self):
        kw = self._valid_kwargs(2)
        kw["k_hat"] = np.ones((2, 4), dtype=np.float64)  # wrong last dim
        with pytest.raises(ValueError, match="k_hat must be"):
            PropagationPaths(**kw)

    def test_k_hat_1d_raises(self):
        kw = self._valid_kwargs(2)
        kw["k_hat"] = np.ones(3, dtype=np.float64)  # (3,) not (N, 3)
        with pytest.raises((ValueError, IndexError)):
            PropagationPaths(**kw)

    def test_psi_wrong_shape_raises(self):
        kw = self._valid_kwargs(2)
        kw["psi"] = np.ones((2, 2), dtype=complex)  # wrong last dim
        with pytest.raises(ValueError, match="psi must be"):
            PropagationPaths(**kw)

    def test_element_index_negative_raises(self):
        kw = self._valid_kwargs(2)
        kw["element_index"] = np.array([-1, 0], dtype=np.intp)
        with pytest.raises(ValueError, match="element_index must be non-negative"):
            PropagationPaths(**kw)

    def test_mismatched_psi_length_raises(self):
        kw = self._valid_kwargs(2)
        kw["psi"] = np.ones((3, 3), dtype=complex)  # N=3 but k_hat N=2
        with pytest.raises(ValueError, match="psi must be"):
            PropagationPaths(**kw)

    def test_mismatched_element_index_length_raises(self):
        kw = self._valid_kwargs(2)
        kw["element_index"] = np.arange(5, dtype=np.intp)  # length 5 vs N=2
        with pytest.raises(ValueError, match="element_index must be"):
            PropagationPaths(**kw)

    def test_mismatched_delay_length_raises(self):
        kw = self._valid_kwargs(2)
        kw["delay"] = np.zeros(4, dtype=np.float64)
        with pytest.raises(ValueError, match="delay must be"):
            PropagationPaths(**kw)

    def test_mismatched_is_los_length_raises(self):
        kw = self._valid_kwargs(2)
        kw["is_los"] = np.ones(4, dtype=bool)
        with pytest.raises(ValueError, match="is_los must be"):
            PropagationPaths(**kw)

    def test_element_index_zero_paths_allows_empty(self):
        # element_index = empty array, n=0 — no negative check should fire
        paths = PropagationPaths(
            k_hat=np.empty((0, 3), dtype=np.float64),
            psi=np.empty((0, 3), dtype=complex),
            element_index=np.empty(0, dtype=np.intp),
            delay=np.empty(0, dtype=np.float64),
            is_los=np.empty(0, dtype=bool),
        )
        assert paths.n_paths == 0


# ---------------------------------------------------------------------------
# 2. from_powers edge cases
# ---------------------------------------------------------------------------


class TestFromPowers:
    def test_1d_k_hat_expanded_to_2d(self):
        k = np.array([0.0, 0.0, -1.0])  # shape (3,)
        paths = PropagationPaths.from_powers(k_hat=k, power=np.array([1.0]))
        assert paths.k_hat.shape == (1, 3)
        assert paths.n_paths == 1

    def test_scalar_power_expanded(self):
        k = np.array([[0.0, 0.0, -1.0]])
        # 0-d array
        power = np.float64(1.5)
        paths = PropagationPaths.from_powers(k_hat=k, power=power)
        assert paths.n_paths == 1
        assert paths.power.shape == (1,)

    def test_zero_power_produces_zero_psi_magnitude(self):
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[1.0, 0.0, 0.0]]),
            power=np.array([0.0]),
        )
        assert np.all(np.abs(paths.psi) == pytest.approx(0.0, abs=1e-15))

    def test_nan_power_raises(self):
        with pytest.raises(ValueError, match="finite"):
            PropagationPaths.from_powers(
                k_hat=np.array([[0.0, 0.0, -1.0]]),
                power=np.array([float("nan")]),
            )

    def test_inf_power_raises(self):
        with pytest.raises(ValueError, match="finite"):
            PropagationPaths.from_powers(
                k_hat=np.array([[0.0, 0.0, -1.0]]),
                power=np.array([float("inf")]),
            )

    def test_nan_in_k_hat_raises(self):
        with pytest.raises(ValueError, match="finite"):
            PropagationPaths.from_powers(
                k_hat=np.array([[float("nan"), 0.0, -1.0]]),
                power=np.array([1.0]),
            )

    def test_inf_in_k_hat_raises(self):
        with pytest.raises(ValueError, match="finite"):
            PropagationPaths.from_powers(
                k_hat=np.array([[float("inf"), 0.0, 0.0]]),
                power=np.array([1.0]),
            )

    def test_zero_norm_k_hat_raises(self):
        with pytest.raises(ValueError, match="positive norm"):
            PropagationPaths.from_powers(
                k_hat=np.array([[0.0, 0.0, 0.0]]),
                power=np.array([1.0]),
            )

    def test_power_shape_mismatch_raises(self):
        k = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])  # N=2
        power = np.array([1.0, 2.0, 3.0])  # N=3
        with pytest.raises(ValueError, match="power shape"):
            PropagationPaths.from_powers(k_hat=k, power=power)

    def test_negative_power_clamped_to_zero(self):
        """np.maximum(power, 0) in amplitude calc means negative -> zero psi."""
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 1.0, 0.0]]),
            power=np.array([-5.0]),
        )
        # amplitude = sqrt(2*Z_0 * max(-5, 0)) = sqrt(0) = 0
        assert np.all(np.abs(paths.psi) == pytest.approx(0.0, abs=1e-15))
        assert paths.power[0] == pytest.approx(0.0, abs=1e-15)

    def test_psi_orthogonal_to_k_hat(self):
        """psi should be perpendicular to k_hat (transverse EM wave)."""
        rng = np.random.default_rng(7)
        k_raw = rng.standard_normal((10, 3))
        k_raw /= np.linalg.norm(k_raw, axis=1, keepdims=True)
        power = rng.uniform(0.1, 2.0, size=10)
        paths = PropagationPaths.from_powers(k_hat=k_raw, power=power)
        dots = np.einsum("ij,ij->i", paths.k_hat, paths.psi.real)
        np.testing.assert_allclose(dots, 0.0, atol=1e-13)

    def test_power_roundtrip(self):
        """|psi|^2 / (2*Z_0) should reproduce input power."""
        rng = np.random.default_rng(11)
        k = rng.standard_normal((8, 3))
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        power = rng.uniform(0.01, 5.0, size=8)
        paths = PropagationPaths.from_powers(k_hat=k, power=power)
        np.testing.assert_allclose(paths.power, power, rtol=1e-12, atol=1e-14)


# ---------------------------------------------------------------------------
# 3. from_spherical
# ---------------------------------------------------------------------------


class TestFromSpherical:
    def test_theta0_phi0_gives_plus_z(self):
        paths = PropagationPaths.from_spherical(
            theta=np.array([0.0]),
            phi=np.array([0.0]),
            power=np.array([1.0]),
        )
        np.testing.assert_allclose(paths.k_hat[0], [0.0, 0.0, 1.0], atol=1e-14)

    def test_theta_pi_phi0_gives_minus_z(self):
        paths = PropagationPaths.from_spherical(
            theta=np.array([math.pi]),
            phi=np.array([0.0]),
            power=np.array([1.0]),
        )
        np.testing.assert_allclose(paths.k_hat[0], [0.0, 0.0, -1.0], atol=1e-14)

    def test_theta_halfpi_phi0_gives_plus_x(self):
        paths = PropagationPaths.from_spherical(
            theta=np.array([math.pi / 2]),
            phi=np.array([0.0]),
            power=np.array([1.0]),
        )
        np.testing.assert_allclose(paths.k_hat[0], [1.0, 0.0, 0.0], atol=1e-14)

    def test_theta_halfpi_phi_halfpi_gives_plus_y(self):
        paths = PropagationPaths.from_spherical(
            theta=np.array([math.pi / 2]),
            phi=np.array([math.pi / 2]),
            power=np.array([1.0]),
        )
        np.testing.assert_allclose(paths.k_hat[0], [0.0, 1.0, 0.0], atol=1e-14)

    def test_scalar_theta_phi_inputs(self):
        """0-d arrays (scalars) should work and produce n_paths=1."""
        paths = PropagationPaths.from_spherical(
            theta=np.float64(0.0),
            phi=np.float64(0.0),
            power=np.array([1.0]),
        )
        assert paths.n_paths == 1
        np.testing.assert_allclose(paths.k_hat[0], [0.0, 0.0, 1.0], atol=1e-14)

    def test_k_hat_are_unit_vectors(self):
        rng = np.random.default_rng(3)
        N = 20
        theta = rng.uniform(0, math.pi, N)
        phi = rng.uniform(0, 2 * math.pi, N)
        power = np.ones(N)
        paths = PropagationPaths.from_spherical(theta=theta, phi=phi, power=power)
        norms = np.linalg.norm(paths.k_hat, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-14)


# ---------------------------------------------------------------------------
# 4. uniform_sphere
# ---------------------------------------------------------------------------


class TestUniformSphere:
    def test_n_paths_1_works(self):
        paths = PropagationPaths.uniform_sphere(n_paths=1, total_power=2.0)
        assert paths.n_paths == 1
        assert paths.total_power == pytest.approx(2.0, rel=1e-12)

    def test_total_power_distributed_equally(self):
        total = 3.0
        n = 50
        paths = PropagationPaths.uniform_sphere(n_paths=n, total_power=total, seed=0)
        per_path = total / n
        np.testing.assert_allclose(paths.power, per_path, rtol=1e-12)

    def test_seed_reproducible(self):
        a = PropagationPaths.uniform_sphere(n_paths=20, seed=42)
        b = PropagationPaths.uniform_sphere(n_paths=20, seed=42)
        np.testing.assert_array_equal(a.k_hat, b.k_hat)
        np.testing.assert_array_equal(a.psi, b.psi)

    def test_different_seeds_differ(self):
        a = PropagationPaths.uniform_sphere(n_paths=20, seed=1)
        b = PropagationPaths.uniform_sphere(n_paths=20, seed=2)
        assert not np.allclose(a.k_hat, b.k_hat)

    def test_all_k_hat_unit_vectors(self):
        paths = PropagationPaths.uniform_sphere(n_paths=100, seed=0)
        norms = np.linalg.norm(paths.k_hat, axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-13)


# ---------------------------------------------------------------------------
# 5. concatenate edge cases
# ---------------------------------------------------------------------------


class TestConcatenateEdgeCases:
    def _empty(self) -> PropagationPaths:
        return PropagationPaths(
            k_hat=np.empty((0, 3), dtype=np.float64),
            psi=np.empty((0, 3), dtype=complex),
            element_index=np.empty(0, dtype=np.intp),
            delay=np.empty(0, dtype=np.float64),
            is_los=np.empty(0, dtype=bool),
        )

    def test_empty_list_returns_empty(self):
        result = PropagationPaths.concatenate([])
        assert result.n_paths == 0
        assert result.k_hat.shape == (0, 3)
        assert result.psi.shape == (0, 3)

    def test_single_element_returns_same_object(self):
        p = _make_paths(3)
        result = PropagationPaths.concatenate([p])
        assert result is p

    def test_reindex_elements_true_shifts_indices(self):
        # p1 has paths 0..1 (element indices 0,1)
        # p2 has path 0 (element index 0)
        # After reindex: p2's element index should become 2
        p1 = PropagationPaths.from_powers(
            k_hat=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
            power=np.array([1.0, 1.0]),
        )
        p2 = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, 1.0]]),
            power=np.array([1.0]),
        )
        merged = PropagationPaths.concatenate([p1, p2], reindex_elements=True)
        assert merged.n_paths == 3
        np.testing.assert_array_equal(merged.element_index, [0, 1, 2])

    def test_reindex_elements_false_preserves_indices(self):
        p1 = PropagationPaths.from_powers(
            k_hat=np.array([[1.0, 0.0, 0.0]]),
            power=np.array([1.0]),
        )
        p2 = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 1.0, 0.0]]),
            power=np.array([1.0]),
        )
        # Both have element_index=[0]; after concat without reindex both are 0
        merged = PropagationPaths.concatenate([p1, p2], reindex_elements=False)
        np.testing.assert_array_equal(merged.element_index, [0, 0])

    def test_empty_paths_in_list_are_filtered(self):
        empty = self._empty()
        p = _make_paths(2)
        # list with empties on both sides
        result = PropagationPaths.concatenate([empty, p, empty])
        # Only one non-empty item -> returns the same object
        assert result is p

    def test_all_empty_list_returns_empty(self):
        empty1 = self._empty()
        empty2 = self._empty()
        result = PropagationPaths.concatenate([empty1, empty2])
        assert result.n_paths == 0

    def test_concatenate_preserves_is_los_flags(self):
        """is_los flags should be concatenated faithfully."""
        k1 = np.array([[0.0, 0.0, -1.0]])
        k2 = np.array([[0.0, 0.0, 1.0]])
        # Build manually to set is_los explicitly
        p1 = PropagationPaths(
            k_hat=k1,
            psi=np.zeros((1, 3), dtype=complex),
            element_index=np.array([0], dtype=np.intp),
            delay=np.zeros(1),
            is_los=np.array([True]),
        )
        p2 = PropagationPaths(
            k_hat=k2,
            psi=np.zeros((1, 3), dtype=complex),
            element_index=np.array([0], dtype=np.intp),
            delay=np.zeros(1),
            is_los=np.array([False]),
        )
        merged = PropagationPaths.concatenate([p1, p2], reindex_elements=False)
        np.testing.assert_array_equal(merged.is_los, [True, False])


# ---------------------------------------------------------------------------
# 6. Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_to_dict_from_dict_roundtrip(self):
        original = _make_paths(5)
        d = original.to_dict()
        restored = PropagationPaths.from_dict(d)

        np.testing.assert_allclose(restored.k_hat, original.k_hat, rtol=1e-15)
        np.testing.assert_allclose(restored.psi.real, original.psi.real, rtol=1e-15)
        np.testing.assert_allclose(restored.psi.imag, original.psi.imag, rtol=1e-15)
        np.testing.assert_array_equal(restored.element_index, original.element_index)
        np.testing.assert_allclose(restored.delay, original.delay)
        np.testing.assert_array_equal(restored.is_los, original.is_los)
        assert restored.n_paths == original.n_paths

    def test_to_dict_stores_psi_as_real_imag(self):
        paths = _make_paths(2)
        d = paths.to_dict()
        assert isinstance(d["psi"], dict)
        assert "real" in d["psi"]
        assert "imag" in d["psi"]

    def test_from_dict_plain_list_psi(self):
        """from_dict handles psi stored as a plain nested list (not real/imag dict)."""
        paths = _make_paths(3)
        d = paths.to_dict()
        # Replace the dict-form psi with a plain nested list of complex numbers
        # (represented as Python complex via real+imag)
        psi_array = paths.psi
        d["psi"] = psi_array.tolist()  # list of [complex, complex, complex] rows
        restored = PropagationPaths.from_dict(d)
        np.testing.assert_allclose(restored.psi, paths.psi, rtol=1e-14)

    def test_roundtrip_empty_paths(self):
        empty = PropagationPaths(
            k_hat=np.empty((0, 3), dtype=np.float64),
            psi=np.empty((0, 3), dtype=complex),
            element_index=np.empty(0, dtype=np.intp),
            delay=np.empty(0, dtype=np.float64),
            is_los=np.empty(0, dtype=bool),
        )
        d = empty.to_dict()
        restored = PropagationPaths.from_dict(d)
        assert restored.n_paths == 0
        assert restored.k_hat.shape == (0, 3)

    def test_roundtrip_preserves_power(self):
        original = _make_paths(10)
        restored = PropagationPaths.from_dict(original.to_dict())
        np.testing.assert_allclose(restored.power, original.power, rtol=1e-14)


# ---------------------------------------------------------------------------
# 7. Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_n_elements_zero_paths_returns_zero(self):
        paths = PropagationPaths(
            k_hat=np.empty((0, 3), dtype=np.float64),
            psi=np.empty((0, 3), dtype=complex),
            element_index=np.empty(0, dtype=np.intp),
            delay=np.empty(0, dtype=np.float64),
            is_los=np.empty(0, dtype=bool),
        )
        assert paths.n_elements == 0

    def test_total_power_matches_sum(self):
        rng = np.random.default_rng(5)
        k = rng.standard_normal((7, 3))
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        power = rng.uniform(0.2, 3.0, size=7)
        paths = PropagationPaths.from_powers(k_hat=k, power=power)
        assert paths.total_power == pytest.approx(float(np.sum(power)), rel=1e-12)

    def test_los_paths_filtering(self):
        # Two LOS, one NLOS
        k = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        psi = np.zeros((3, 3), dtype=complex)
        paths = PropagationPaths(
            k_hat=k,
            psi=psi,
            element_index=np.array([0, 1, 2], dtype=np.intp),
            delay=np.zeros(3),
            is_los=np.array([True, False, True]),
        )
        los = paths.los_paths
        nlos = paths.nlos_paths
        assert los.n_paths == 2
        assert nlos.n_paths == 1
        # LOS paths should have is_los all True
        assert np.all(los.is_los)
        assert not np.any(nlos.is_los)

    def test_nlos_paths_filtering_all_los(self):
        """When all paths are LOS, nlos_paths should be empty."""
        paths = _make_paths(4)  # from_powers sets all is_los=True
        assert paths.nlos_paths.n_paths == 0

    def test_los_paths_filtering_none_los(self):
        """When no paths are LOS, los_paths should be empty."""
        k = np.array([[0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
        psi = np.zeros((2, 3), dtype=complex)
        paths = PropagationPaths(
            k_hat=k,
            psi=psi,
            element_index=np.array([0, 1], dtype=np.intp),
            delay=np.zeros(2),
            is_los=np.array([False, False]),
        )
        assert paths.los_paths.n_paths == 0
        assert paths.nlos_paths.n_paths == 2

    def test_len_returns_n_paths(self):
        for n in (0, 1, 5, 20):
            if n == 0:
                paths = PropagationPaths(
                    k_hat=np.empty((0, 3), dtype=np.float64),
                    psi=np.empty((0, 3), dtype=complex),
                    element_index=np.empty(0, dtype=np.intp),
                    delay=np.empty(0, dtype=np.float64),
                    is_los=np.empty(0, dtype=bool),
                )
            else:
                paths = _make_paths(n)
            assert len(paths) == n
            assert len(paths) == paths.n_paths

    def test_subset_with_empty_indices(self):
        paths = _make_paths(5)
        sub = paths.subset([])
        assert sub.n_paths == 0
        assert sub.k_hat.shape == (0, 3)
        assert sub.psi.shape == (0, 3)

    def test_subset_single_index(self):
        paths = _make_paths(5)
        sub = paths.subset([2])
        assert sub.n_paths == 1
        np.testing.assert_array_equal(sub.k_hat, paths.k_hat[[2]])

    def test_n_elements_single_element(self):
        paths = _make_paths(1)
        # from_powers assigns element_index = [0]
        assert paths.n_elements == 1

    def test_n_elements_counts_unique_max(self):
        """n_elements = max(element_index) + 1, not len(unique)."""
        k = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        psi = np.zeros((2, 3), dtype=complex)
        paths = PropagationPaths(
            k_hat=k,
            psi=psi,
            element_index=np.array([0, 5], dtype=np.intp),  # gap in indices
            delay=np.zeros(2),
            is_los=np.ones(2, dtype=bool),
        )
        # max(0, 5) + 1 = 6
        assert paths.n_elements == 6

    def test_power_uses_correct_z0_factor(self):
        """power = |psi|^2 / (2 * Z_0) -- verify the denominator."""
        psi_mag = 3.0  # V/m
        k = np.array([[0.0, 0.0, -1.0]])
        psi = np.zeros((1, 3), dtype=complex)
        psi[0, 0] = psi_mag  # only x-component
        paths = PropagationPaths(
            k_hat=k,
            psi=psi,
            element_index=np.array([0], dtype=np.intp),
            delay=np.zeros(1),
            is_los=np.ones(1, dtype=bool),
        )
        expected = psi_mag**2 / (2 * Z_0)
        assert paths.power[0] == pytest.approx(expected, rel=1e-14)
