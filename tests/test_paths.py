"""Tests for PropagationPaths."""

import numpy as np
import pytest

from aegis.paths import PropagationPaths


def test_from_powers_roundtrip_power():
    rng = np.random.default_rng(0)
    k_hat = rng.standard_normal((5, 3))
    power = rng.uniform(0.1, 2.0, size=5)
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
    np.testing.assert_allclose(paths.power, power, rtol=1e-10, atol=1e-12)


def test_from_powers_single_path_1d_k_hat():
    k_hat = np.array([3.0, 0.0, 4.0])
    power = np.array([0.5])
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)
    assert paths.n_paths == 1
    assert paths.power.shape == (1,)
    np.testing.assert_allclose(paths.power, power, rtol=1e-10, atol=1e-12)
    kh = paths.k_hat[0]
    assert np.linalg.norm(kh) == pytest.approx(1.0, abs=1e-14)


def test_from_powers_zero_power_zero_psi_magnitude():
    paths = PropagationPaths.from_powers(
        k_hat=np.array([[0.0, 0.0, -1.0]]),
        power=np.array([0.0]),
    )
    assert np.all(np.abs(paths.psi) == pytest.approx(0.0, abs=1e-14))


def test_from_powers_normalizes_k_hat():
    raw = np.array([[2.0, 0.0, 0.0], [0.0, 3.0, 4.0]])
    power = np.array([1.0, 1.0])
    paths = PropagationPaths.from_powers(k_hat=raw, power=power)
    norms = np.linalg.norm(paths.k_hat, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-14)
    np.testing.assert_allclose(paths.k_hat[0], [1.0, 0.0, 0.0], atol=1e-14)


# ---------------------------------------------------------------------------
# PropagationPaths.concatenate
# ---------------------------------------------------------------------------


class TestConcatenate:
    def test_two_paths_basic(self):
        p1 = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        p2 = PropagationPaths.from_powers(k_hat=np.array([[1, 0, 0.0]]), power=np.array([2.0]))
        merged = PropagationPaths.concatenate([p1, p2])
        assert merged.n_paths == 2
        np.testing.assert_allclose(merged.power, [1.0, 2.0], rtol=1e-10)

    def test_reindex_elements(self):
        p1 = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0], [0, 1, 0.0]]),
            power=np.array([1.0, 1.0]),
        )
        p2 = PropagationPaths.from_powers(k_hat=np.array([[1, 0, 0.0]]), power=np.array([1.0]))
        merged = PropagationPaths.concatenate([p1, p2], reindex_elements=True)
        # p1 has elements 0,1. p2 element 0 should become 2.
        assert merged.n_elements == 3
        assert merged.element_index[-1] == 2

    def test_no_reindex(self):
        p1 = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        p2 = PropagationPaths.from_powers(k_hat=np.array([[1, 0, 0.0]]), power=np.array([1.0]))
        merged = PropagationPaths.concatenate([p1, p2], reindex_elements=False)
        # Both have element_index=0, so n_elements=1
        assert merged.n_elements == 1

    def test_empty_list(self):
        merged = PropagationPaths.concatenate([])
        assert merged.n_paths == 0

    def test_single_input(self):
        p = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        merged = PropagationPaths.concatenate([p])
        assert merged is p  # returns same object

    def test_preserves_total_power(self):
        rng = np.random.default_rng(42)
        parts = []
        for _ in range(5):
            n = rng.integers(1, 10)
            k = rng.standard_normal((n, 3))
            k /= np.linalg.norm(k, axis=1, keepdims=True)
            pwr = rng.uniform(0.1, 5.0, size=n)
            parts.append(PropagationPaths.from_powers(k_hat=k, power=pwr))
        merged = PropagationPaths.concatenate(parts)
        expected = sum(p.total_power for p in parts)
        assert merged.total_power == pytest.approx(expected, rel=1e-10)

    def test_skips_empty_paths(self):
        empty = PropagationPaths(
            k_hat=np.empty((0, 3)),
            psi=np.empty((0, 3), dtype=complex),
            element_index=np.empty(0, dtype=np.intp),
            delay=np.empty(0),
            is_los=np.empty(0, dtype=bool),
        )
        p = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        merged = PropagationPaths.concatenate([empty, p, empty])
        assert merged is p


# ---------------------------------------------------------------------------
# PropagationPaths.subset
# ---------------------------------------------------------------------------


class TestSubset:
    def test_subset_preserves_power(self):
        rng = np.random.default_rng(99)
        k = rng.standard_normal((10, 3))
        k /= np.linalg.norm(k, axis=1, keepdims=True)
        pwr = rng.uniform(0.5, 2.0, size=10)
        paths = PropagationPaths.from_powers(k_hat=k, power=pwr)
        sub = paths.subset([0, 3, 7])
        np.testing.assert_allclose(sub.power, pwr[[0, 3, 7]], rtol=1e-10)
        assert sub.n_paths == 3

    def test_empty_subset(self):
        paths = PropagationPaths.from_powers(k_hat=np.array([[0, 0, -1.0]]), power=np.array([1.0]))
        sub = paths.subset([])
        assert sub.n_paths == 0
