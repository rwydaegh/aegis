"""Shared geometric and Fresnel building blocks for incoherent kernels."""

from __future__ import annotations

from aegis._array_backend import xp
from aegis.tissue.fresnel import _fresnel_core


def incidence_geometry(normals, k_hat):
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


def fresnel_weights(mu, n_tilde):
    """Compute Fresnel transmission weights at each (triangle, path) pair.

    Calls _fresnel_core directly (not fresnel_transmission) to stay JIT-safe.

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
    # Cast to complex for _fresnel_core (Fresnel needs complex arithmetic)
    mu_complex = xp.asarray(mu_for_fresnel, dtype=complex)
    _, _, T_s, T_p, _, _ = _fresnel_core(mu_complex, n_tilde)
    T_avg = 0.5 * (T_s + T_p)
    return T_s, T_p, T_avg
