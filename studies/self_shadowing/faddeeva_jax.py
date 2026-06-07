"""Complex error function (Faddeeva w) in JAX, and the exact knife-edge gate.

The exact knife-edge diffraction transition is a Fresnel integral, which is an
error function of a complex argument. JAX ships only a real ``erf``, so to get
the exact transition under the JAX backend we implement the Faddeeva function

    w(z) = exp(-z^2) * erfc(-i z)

via Weideman's rational approximation (W. Weideman, "Computation of the complex
error function", SIAM J. Numer. Anal. 31 (1994) 1497). The coefficients are
computed once in NumPy; the evaluation is pure ``jax.numpy`` (vectorised,
jittable, differentiable). From w we recover the complex ``erf`` and the
Fresnel integrals, hence the exact knife-edge power gate |F(nu)|^2.

Conventions:
  nu > 0 is the deep-shadow side; nu < 0 is lit.
  |F(0)|^2 = 1/4 (the -6 dB geometric shadow boundary).

This module is a verification artefact for the self-shadowing visibility design,
not a production dependency. See studies/self_shadowing/report.
"""

from __future__ import annotations

import numpy as np

import jax

jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp  # noqa: E402


def weideman_coeffs(n_terms: int = 48) -> tuple[float, np.ndarray]:
    """Weideman coefficients (L, a) for the w(z) rational approximation.

    Computed once in NumPy; ``a`` has length ``n_terms`` ordered like
    ``np.polyval`` (highest power first). ``n_terms=48`` gives ~1e-13 accuracy.
    """
    n = int(n_terms)
    m = 2 * n
    m2 = 2 * m
    k = np.arange(-m + 1, m)
    ell = np.sqrt(n / np.sqrt(2.0))
    theta = k * np.pi / m
    t = ell * np.tan(theta / 2.0)
    f = np.exp(-(t**2)) * (ell**2 + t**2)
    f = np.concatenate([[0.0], f])
    a = np.real(np.fft.fft(np.fft.fftshift(f))) / m2
    a = np.flipud(a[1 : n + 1]).copy()
    return float(ell), a


def faddeeva(z, ell: float, a: np.ndarray):
    """Faddeeva w(z) for arbitrary complex z (jax array in, jax array out)."""
    z = jnp.asarray(z, dtype=jnp.complex128)
    a = jnp.asarray(a, dtype=jnp.float64)
    # Evaluate in the upper half-plane, then reflect for Im(z) < 0 via
    # w(-z) = 2 exp(-z^2) - w(z).
    zu = jnp.where(z.imag < 0, -z, z)
    denom = ell - 1j * zu
    big_z = (ell + 1j * zu) / denom
    p = jnp.zeros_like(big_z)
    for c in a:  # n_terms is small; the loop unrolls under jit
        p = p * big_z + c
    w_u = 2.0 * p / denom**2 + (1.0 / jnp.sqrt(jnp.pi)) / denom
    return jnp.where(z.imag < 0, 2.0 * jnp.exp(-z * z) - w_u, w_u)


def erf_complex(z, ell: float, a: np.ndarray):
    """Complex erf(z) = 1 - exp(-z^2) w(i z)."""
    z = jnp.asarray(z, dtype=jnp.complex128)
    return 1.0 - jnp.exp(-z * z) * faddeeva(1j * z, ell, a)


def fresnel_cs(nu, ell: float, a: np.ndarray):
    """Fresnel integrals C(nu), S(nu) via C + iS = (1+i)/2 erf((sqrt(pi)/2)(1-i)nu)."""
    nu = jnp.asarray(nu, dtype=jnp.float64)
    arg = (jnp.sqrt(jnp.pi) / 2.0) * (1.0 - 1j) * nu
    cs = (1.0 + 1j) / 2.0 * erf_complex(arg, ell, a)
    return jnp.real(cs), jnp.imag(cs)


def knife_edge_gate(nu, ell: float, a: np.ndarray):
    """Exact knife-edge power transmission |F(nu)|^2 (nu>0 shadow, nu<0 lit)."""
    c, s = fresnel_cs(nu, ell, a)
    f = (1.0 + 1j) / 2.0 * ((0.5 - c) - 1j * (0.5 - s))
    return jnp.abs(f) ** 2


# Soft-gate surrogates in the dimensionless clearance s = c/sigma (s>0 lit).
def gate_erf(s):
    """Default unsmoothed-power gate 0.5[1+erf(s)] (-3 dB at the boundary)."""
    from jax.scipy.special import erf as jerf

    return 0.5 * (1.0 + jerf(jnp.asarray(s, dtype=jnp.float64)))


def gate_erf_squared(s):
    """Field-squared gate (0.5[1+erf(s)])^2 (-6 dB, knife-edge-consistent)."""
    return gate_erf(s) ** 2
