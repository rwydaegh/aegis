"""Unit tests for aegis.twin.path_dictionary (paper §V.B calibration LS)."""

from __future__ import annotations

import numpy as np
import pytest

from aegis.twin.path_dictionary import calibrate_amplitudes


def _random_steering(rng: np.random.Generator, m: int, n: int) -> np.ndarray:
    """Random complex 'steering' matrix with unit-norm columns."""
    a = (rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n))) / np.sqrt(2.0)
    a /= np.linalg.norm(a, axis=0, keepdims=True)
    return a


def test_noiseless_recovers_perturbation_exactly() -> None:
    """With no noise and an overdetermined design, beta_hat == gamma to FP error."""
    rng = np.random.default_rng(0)
    m, n = 32, 8
    steering = _random_steering(rng, m, n)
    alpha = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
    gamma = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
    h_clean = (steering * alpha[None, :]) @ gamma

    beta_hat = calibrate_amplitudes(steering, alpha, h_clean)

    np.testing.assert_allclose(beta_hat, gamma, atol=1e-10)


def test_residual_decreases_with_snr() -> None:
    """Mean residual at high SNR is at least 15 dB below the 0 dB baseline."""
    rng = np.random.default_rng(1)
    m, n = 64, 30
    n_trials = 50

    def mean_residual_db(snr_db: float) -> float:
        rs = []
        for _ in range(n_trials):
            steering = _random_steering(rng, m, n)
            alpha = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
            gamma = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
            h_clean = (steering * alpha[None, :]) @ gamma

            sig_pow = float(np.mean(np.abs(h_clean) ** 2))
            noise_pow = sig_pow / (10.0 ** (snr_db / 10.0))
            sigma = np.sqrt(noise_pow / 2.0)
            noise = sigma * (rng.standard_normal(m) + 1j * rng.standard_normal(m))
            beta_hat = calibrate_amplitudes(steering, alpha, h_clean + noise)
            rs.append(np.linalg.norm(beta_hat - gamma) / np.linalg.norm(gamma))
        return 20.0 * np.log10(np.mean(rs))

    res_low = mean_residual_db(0.0)
    res_high = mean_residual_db(30.0)
    assert res_high < res_low - 15.0, (
        f"expected >=15 dB residual drop from 0 to 30 dB SNR; got {res_low:.2f} -> {res_high:.2f} dB"
    )


def test_ridge_shrinks_solution() -> None:
    """Strong Tikhonov regularisation pulls beta toward zero."""
    rng = np.random.default_rng(2)
    m, n = 16, 8
    steering = _random_steering(rng, m, n)
    alpha = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
    gamma = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
    h = (steering * alpha[None, :]) @ gamma

    beta_no_ridge = calibrate_amplitudes(steering, alpha, h, ridge=0.0)
    beta_ridge = calibrate_amplitudes(steering, alpha, h, ridge=1.0e3)

    assert np.linalg.norm(beta_ridge) < 0.5 * np.linalg.norm(beta_no_ridge)


def test_shape_validation() -> None:
    """Bad shapes raise ValueError."""
    rng = np.random.default_rng(3)
    steering = _random_steering(rng, 8, 4)
    alpha = np.ones(4, dtype=complex)
    h = np.zeros(8, dtype=complex)

    with pytest.raises(ValueError, match="alpha_insilico"):
        calibrate_amplitudes(steering, alpha[:3], h)
    with pytest.raises(ValueError, match="h_meas"):
        calibrate_amplitudes(steering, alpha, h[:7])
    with pytest.raises(ValueError, match="steering"):
        calibrate_amplitudes(steering[0], alpha, h)
    with pytest.raises(ValueError, match="ridge"):
        calibrate_amplitudes(steering, alpha, h, ridge=-0.1)
