"""Tests for differentiable optimization helpers."""

import numpy as np
import pytest


def test_peak_exposure():
    from aegis.optim import peak_exposure

    sab = np.array([1.0, 3.0, 2.0])
    assert float(peak_exposure(sab)) == pytest.approx(3.0)


def test_total_absorbed_power():
    from aegis.optim import total_absorbed_power

    sab = np.array([10.0, 20.0])
    areas = np.array([0.01, 0.02])
    expected = 10.0 * 0.01 + 20.0 * 0.02
    assert float(total_absorbed_power(sab, areas)) == pytest.approx(expected)


def test_soft_peak_approaches_max():
    from aegis.optim import soft_peak_exposure

    sab = np.array([1.0, 5.0, 3.0])
    result = float(soft_peak_exposure(sab, temperature=100.0))
    assert result == pytest.approx(5.0, abs=0.1)


def test_soft_peak_always_ge_max():
    from aegis.optim import soft_peak_exposure

    sab = np.array([2.0, 7.0, 4.0])
    # log-sum-exp is always >= max
    assert float(soft_peak_exposure(sab)) >= float(np.max(sab)) - 1e-10


def test_coherent_sab_shape():
    from aegis.optim import coherent_sab

    M, M_ant = 4, 2
    G_tilde = np.zeros((M, 3, M_ant), dtype=complex)
    x = np.ones(M_ant, dtype=complex)
    sab = coherent_sab(G_tilde, x)
    assert sab.shape == (M,)


def test_coherent_sab_known_value():
    from aegis.optim import coherent_sab

    # Single triangle, single element, z-component = 1
    G_tilde = np.zeros((1, 3, 1), dtype=complex)
    G_tilde[0, 2, 0] = 1.0 + 0j
    x = np.array([2.0 + 0j])
    sab = coherent_sab(G_tilde, x)
    # ||G @ x||^2 = |1 * 2|^2 = 4
    assert float(sab[0]) == pytest.approx(4.0)


def test_coherent_sab_non_negative():
    from aegis.optim import coherent_sab

    rng = np.random.default_rng(42)
    G_tilde = rng.standard_normal((5, 3, 3)) + 1j * rng.standard_normal((5, 3, 3))
    x = rng.standard_normal(3) + 1j * rng.standard_normal(3)
    sab = coherent_sab(G_tilde, x)
    assert np.all(np.asarray(sab) >= 0)
