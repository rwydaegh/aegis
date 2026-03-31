"""Tests for single-pole Debye permittivity model."""

import numpy as np

from aegis.tissue.cole_cole import cole_cole_permittivity, debye_permittivity

EPS_0 = 8.854187817e-12


def test_debye_at_28ghz_christ2025():
    """Christ 2025 Table 6, Layer D dermis mean parameters."""
    eps = debye_permittivity(28e9, eps_inf=7.88, eps_static=47.0, sigma=5.19, tau_s=8.35e-12)
    assert 7.88 < eps.real < 47.0
    assert eps.imag < 0


def test_debye_at_dc_limit():
    """At very low frequency, eps -> eps_static - j*sigma/(omega*eps_0)."""
    eps = debye_permittivity(1.0, eps_inf=5.0, eps_static=50.0, sigma=0.0, tau_s=1e-12)
    assert abs(eps.real - 50.0) < 0.01
    assert abs(eps.imag) < 0.01


def test_debye_at_high_freq_limit():
    """At very high frequency, eps -> eps_inf."""
    eps = debye_permittivity(1e15, eps_inf=5.0, eps_static=50.0, sigma=0.0, tau_s=1e-12)
    assert abs(eps.real - 5.0) < 0.1


def test_debye_matches_cole_cole_alpha_zero():
    """Debye is Cole-Cole with alpha=0, single pole. Results should match."""
    freq = 10e9
    eps_inf = 7.88
    eps_static = 47.0
    sigma = 5.19
    tau_s = 8.35e-12
    eps_debye = debye_permittivity(freq, eps_inf, eps_static, sigma, tau_s)
    cc_params = {
        "ef": eps_inf,
        "del1": eps_static - eps_inf,
        "tau1": tau_s / 1e-12,
        "alf1": 0.0,
        "del2": 0.0,
        "tau2": 0.0,
        "alf2": 0.0,
        "del3": 0.0,
        "tau3": 0.0,
        "alf3": 0.0,
        "del4": 0.0,
        "tau4": 0.0,
        "alf4": 0.0,
        "sig": sigma,
    }
    eps_cc = cole_cole_permittivity(freq, cc_params)
    assert abs(eps_debye - eps_cc) < 1e-6


def test_debye_array_input():
    """Should handle array frequency input."""
    freqs = np.array([1e9, 10e9, 28e9, 60e9, 100e9])
    eps = debye_permittivity(freqs, eps_inf=7.88, eps_static=47.0, sigma=5.19, tau_s=8.35e-12)
    assert eps.shape == (5,)
    assert np.all(np.diff(eps.real) < 0)


def test_debye_conductivity_contribution():
    """Adding conductivity makes imaginary part more negative."""
    f = 28e9
    eps_no_sig = debye_permittivity(f, 4.0, 40.0, sigma=0.0, tau_s=1e-11)
    eps_with_sig = debye_permittivity(f, 4.0, 40.0, sigma=1.0, tau_s=1e-11)
    assert eps_with_sig.imag < eps_no_sig.imag
