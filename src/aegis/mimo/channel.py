"""Communication channel from antenna array to user equipment.

Computes the (M_ant,) complex channel vector h_k using the multipath
environment and a half-wave dipole UE antenna model.

Design doc: section C1.
"""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0
from aegis.mimo.array import AntennaArray
from aegis.paths import PropagationPaths


def dipole_effective_length(
    k_hat: np.ndarray,
    d_hat: np.ndarray,
    freq_hz: float,
) -> np.ndarray:
    """Effective length vector of a half-wave dipole.

    C_R(k_hat) = (lambda/pi) * cos(pi/2 * cos_theta) / sin_theta * theta_hat

    where theta is the angle between k_hat and the dipole axis d_hat, and
    theta_hat is the unit vector in the E-plane (perpendicular to k_hat,
    in the plane containing k_hat and d_hat).

    Coefficient lambda/pi follows Balanis (4th ed, eq 4-63) for the
    half-wave dipole effective length.

    Parameters
    ----------
    k_hat : (N, 3) unit directions of arrival.
    d_hat : (3,) unit vector along dipole axis.
    freq_hz : frequency [Hz].

    Returns
    -------
    C_R : (N, 3) effective length vectors [m]. Real-valued.
    """
    lam = C_0 / freq_hz

    cos_theta = k_hat @ d_hat
    sin_theta_sq = np.maximum(1.0 - cos_theta**2, 0.0)
    sin_theta = np.sqrt(sin_theta_sq)

    # theta_hat: component of d_hat perpendicular to k_hat, normalized
    d_perp = d_hat[None, :] - cos_theta[:, None] * k_hat
    d_perp_norm = np.linalg.norm(d_perp, axis=1, keepdims=True)

    # At endfire (sin_theta ~ 0), d_perp is zero. Use safe normalization.
    safe_norm = np.where(d_perp_norm > 1e-15, d_perp_norm, 1.0)
    theta_hat = d_perp / safe_norm

    # Scalar pattern: cos(pi/2 * cos_theta) / sin_theta
    numerator = np.cos(np.pi / 2 * cos_theta)
    safe_sin = np.where(sin_theta > 1e-15, sin_theta, 1.0)
    scalar = np.where(sin_theta > 1e-15, numerator / safe_sin, 0.0)

    # Balanis (4th ed): effective length = (lambda/pi) * F(theta)
    C_R = (lam / np.pi) * scalar[:, None] * theta_hat
    return C_R


def compute_channel_vector(
    center_paths: PropagationPaths,
    array: AntennaArray,
    device_position: np.ndarray,
    device_orientation: np.ndarray,
    freq_hz: float,
) -> np.ndarray:
    """Compute the communication channel from the array to a UE.

    h = A^T @ c  where:
    - A[n, j] = exp(+i*k0 * k_hat_n . offset_j)  (steering matrix)
    - c[n] = conj(C_R(k_hat_n)) . psi_n * exp(-i*k0 * k_hat_n . r_UE)

    Parameters
    ----------
    center_paths : PropagationPaths
        N paths from the array center.
    array : AntennaArray
        Antenna array geometry.
    device_position : (3,) UE position in world coordinates [m].
    device_orientation : (3,) unit vector along UE dipole axis.
    freq_hz : frequency [Hz].

    Returns
    -------
    h : (M_ant,) complex channel vector.
    """
    M = array.n_elements
    N = center_paths.n_paths

    if N == 0:
        return np.zeros(M, dtype=complex)

    device_position = np.asarray(device_position, dtype=np.float64)
    device_orientation = np.asarray(device_orientation, dtype=np.float64)
    device_orientation = device_orientation / np.linalg.norm(device_orientation)

    k0 = 2 * np.pi * freq_hz / C_0

    # Steering matrix: (N, M)
    A = array.steering_matrix(center_paths.k_hat, freq_hz)

    # UE phase: exp(-i*k0 * k_hat_n . r_UE)
    ue_phase = np.exp(-1j * k0 * (center_paths.k_hat @ device_position))

    # Dipole effective length -> (N, 3)
    C_R = dipole_effective_length(center_paths.k_hat, device_orientation, freq_hz)

    # Received signal per path: conj(C_R) . psi * phase
    c = np.sum(np.conj(C_R) * center_paths.psi, axis=1) * ue_phase

    # Channel vector: h = A^T @ c
    h = A.T @ c

    return h
