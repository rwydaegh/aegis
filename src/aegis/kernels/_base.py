"""Shared geometric and Fresnel building blocks for incoherent kernels.

Levels 2-6 all compute the same incidence geometry and (for 3-6) the same
Fresnel weights. This module extracts that shared pattern so each level
file only contains its unique correction.
"""

from __future__ import annotations

import numpy as np

from aegis.tissue.fresnel import fresnel_transmission


def incidence_geometry(
    normals: np.ndarray,
    k_hat: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
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
    mu = normals @ (-k_hat).T  # (M, N)
    mu_plus = np.maximum(mu, 0.0)  # (M, N)
    return mu, mu_plus


def fresnel_weights(
    mu: np.ndarray,
    n_tilde: complex,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute Fresnel transmission weights at each (triangle, path) pair.

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
    mu_for_fresnel = np.clip(mu, 0.0, 1.0)
    T_s, T_p = fresnel_transmission(mu_for_fresnel, n_tilde)
    T_avg = 0.5 * (T_s + T_p)  # (M, N)
    return T_s, T_p, T_avg
