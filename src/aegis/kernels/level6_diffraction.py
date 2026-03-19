"""Level 6: Diffraction smoothing (ReLU -> GELU).

Replaces the sharp ReLU at the shadow boundary with a physical GELU:
    ReLU_phys(mu) = mu * Phi(mu / sigma_j)

where Phi is the standard normal CDF and
    sigma_j = sqrt(lambda / (2 * pi * R_j))

is set by the local radius of curvature R_j at the shadow boundary.

This smooths the shadow-boundary discontinuity over a Fresnel-zone width.
For compliance, the sharp ReLU (Level 2-5) is sufficient because ICNIRP's
4 cm^2 spatial averaging already regularises the boundary. Level 6 is
relevant for high-resolution local dosimetry or comparison with point
measurements near the terminator line.

Cost: O(M * N), same as Level 3 but with GELU instead of ReLU.
"""

from __future__ import annotations

import numpy as np
from scipy.special import ndtr  # standard normal CDF

from aegis.constants import C_0
from aegis.tissue.fresnel import fresnel_transmission


def _physical_gelu(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """Physical GELU: mu * Phi(mu / sigma).

    Parameters
    ----------
    mu : (M, N) raw cosine values
    sigma : (M,) smoothing width per triangle

    Returns
    -------
    gelu : (M, N)
    """
    # Avoid division by zero for zero-curvature triangles
    sigma_safe = np.where(sigma > 0, sigma, 1e-30)
    z = mu / sigma_safe[:, np.newaxis]
    return mu * ndtr(z)


def level6_diffraction(
    normals: np.ndarray,
    k_hat: np.ndarray,
    power: np.ndarray,
    n_tilde: complex,
    T0: float,
    curvature_H: np.ndarray,
    freq_hz: float,
) -> np.ndarray:
    """Compute per-triangle S_ab with Fresnel + curvature + diffraction.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    n_tilde : complex refractive index
    T0 : normal-incidence transmission
    curvature_H : (M,) twice mean curvature H = 1/R1 + 1/R2 [1/m]
    freq_hz : frequency [Hz]

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    wavelength = C_0 / freq_hz
    k = 2.0 * np.pi / wavelength

    mu = normals @ (-k_hat).T  # (M, N)

    # Local radius of curvature R_j = 2 / H_j (H_j = twice mean curvature)
    # sigma_j = sqrt(lambda / (2 * pi * R_j))
    # For flat regions (H=0), use plain ReLU (sigma -> 0 gives ReLU)
    H_safe = np.maximum(curvature_H, 0.0)
    # R = 2/H, but we need lambda / (2*pi*R) = lambda * H / (4*pi)
    sigma = np.sqrt(np.maximum(wavelength * H_safe / (4.0 * np.pi), 0.0))

    # GELU activation replaces ReLU
    mu_gelu = _physical_gelu(mu, sigma)  # (M, N)

    # Fresnel at each incidence angle
    mu_for_fresnel = np.clip(mu, 0.0, 1.0)
    T_s, T_p = fresnel_transmission(mu_for_fresnel, n_tilde)
    T_avg = 0.5 * (T_s + T_p)  # (M, N)

    # Base Fresnel term with GELU
    sab_base = (T_avg * mu_gelu) @ power  # (M,)

    # Curvature correction with GELU^2
    gelu_sq = mu_gelu**2
    sab_curvature = T0 * ((H_safe / k)[:, np.newaxis] * gelu_sq) @ power

    return sab_base + sab_curvature
