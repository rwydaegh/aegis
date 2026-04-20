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
