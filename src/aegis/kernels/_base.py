"""Shared geometric and Fresnel building blocks for incoherent kernels."""

from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import erf, xp
from aegis.defaults import NUMERICAL_FLOOR


def incidence_geometry(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """Compute cosine of incidence and its ReLU.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions

    Returns
    -------
    mu : (M, N) raw cosine of local incidence angle
    mu_plus : (M, N) ReLU(mu), zero for back-facing paths
    """
    mu = normals @ (-k_hat).T
    mu_plus = xp.maximum(mu, 0.0)
    return mu, mu_plus


def fresnel_weights(
    mu: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
) -> tuple[NDArray[np.floating], NDArray[np.floating], NDArray[np.floating]]:
    """Compute Fresnel transmission weights at each (triangle, path) pair.

    Inlined (rather than calling ``_fresnel_core``) to avoid allocating the
    amplitude transmission coefficients ``t_s``/``t_p``, which the spatial
    kernel never consumes. For (M, N) = (164k, 240) this saves ~1.3 GB of
    transient complex128 allocation per call.

    Parameters
    ----------
    mu : (M, N) raw cosine of local incidence angle
    n_tilde : complex refractive index of the tissue

    Returns
    -------
    T_s : (M, N) TE power transmission
    T_p : (M, N) TM power transmission
    T_avg : (M, N) unpolarised average (T_s + T_p) / 2
    """
    mu_for_fresnel = xp.clip(mu, 0.0, 1.0)
    # Cast to complex once (Fresnel needs complex arithmetic).
    mu_complex = xp.asarray(mu_for_fresnel, dtype=complex)

    n2 = n_tilde**2
    xi = xp.sqrt(n2 - 1 + mu_complex**2)
    xi = xp.where(xp.real(xi) < 0, -xi, xi)

    r_s = (mu_complex - xi) / (mu_complex + xi)
    r_p = (n2 * mu_complex - xi) / (n2 * mu_complex + xi)

    T_s = xp.real(1 - xp.abs(r_s) ** 2)
    T_p = xp.real(1 - xp.abs(r_p) ** 2)

    mu_real = xp.real(mu_complex)
    T_s = xp.where(mu_real < 1e-10, 0.0, T_s)
    T_p = xp.where(mu_real < 1e-10, 0.0, T_p)

    T_avg = 0.5 * (T_s + T_p)
    return T_s, T_p, T_avg


def te_tm_power_weights(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    psi: NDArray[np.complexfloating],
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """TE/TM power fractions of each path's polarisation at each triangle.

    For incident field direction ``E_hat = psi / |psi|`` and the local TE/TM
    basis ``(e_s, e_p)`` at each (triangle, path) pair, returns

        w_s = |e_s . E_hat|^2,   w_p = |e_p . E_hat|^2

    renormalised so ``w_s + w_p = 1`` (exact for a transverse plane wave). The
    polarisation-aware transmission is then ``T_eff = w_s*T_s + w_p*T_p``,
    identical to the ``T_avg + (q/2) DeltaT`` form with ``q = w_p - w_s``.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    psi : (N, 3) complex polarisation-amplitude vectors

    Returns
    -------
    w_s, w_p : (M, N) TE and TM power fractions
    """
    # Reused here for the incoherent path; te_tm_basis is pure geometry.
    from aegis.coherent.fresnel_operator import te_tm_basis

    e_s, e_p = te_tm_basis(k_hat, normals)  # (M, N, 3), real

    psi = xp.asarray(psi)
    p_norm = xp.sqrt(xp.sum(xp.abs(psi) ** 2, axis=1))  # (N,)
    p_norm_safe = xp.where(p_norm > 0, p_norm, 1.0)
    e_hat = psi / p_norm_safe[:, None]  # (N, 3) complex unit
    re = xp.real(e_hat)
    im = xp.imag(e_hat)

    # |e_s . E_hat|^2 = (e_s . Re)^2 + (e_s . Im)^2, keeping e_s real.
    ws = xp.einsum("mnj,nj->mn", e_s, re) ** 2 + xp.einsum("mnj,nj->mn", e_s, im) ** 2
    wp = xp.einsum("mnj,nj->mn", e_p, re) ** 2 + xp.einsum("mnj,nj->mn", e_p, im) ** 2

    norm = ws + wp
    norm_safe = xp.where(norm > 0, norm, 1.0)
    return ws / norm_safe, wp / norm_safe


def physical_gelu(
    mu: NDArray[np.floating],
    sigma: NDArray[np.floating],
) -> NDArray[np.floating]:
    """Physical GELU: mu * (1/2)[1 + erf(mu / sigma)].

    Replaces ReLU at the shadow boundary with a diffraction-smoothed
    transition (monograph eq. 2.44). Width sigma = sqrt(lambda*H/(4*pi)).
    """
    sigma_safe = xp.where(sigma > 0, sigma, NUMERICAL_FLOOR)
    z = mu / sigma_safe[:, None]
    # erf is an Any-typed scipy/jax shim; the product is a float ndarray.
    return cast(NDArray[np.floating], mu * 0.5 * (1.0 + erf(z)))
