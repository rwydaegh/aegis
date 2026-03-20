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
