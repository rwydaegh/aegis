"""Body absorption directivity D(k_hat) and spherical harmonic compression.

Extracted from scripts/compute_body_directivity.py.
"""

from __future__ import annotations

import numpy as np
from scipy.special import sph_harm


def spherical_angles_from_k_hat(k_hat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert unit vectors to (theta, phi).

    theta: polar angle in [0, pi], measured from +z.
    phi: azimuth in [-pi, pi], measured from +x toward +y.
    """
    k_hat = np.asarray(k_hat, dtype=float)
    if k_hat.ndim != 2 or k_hat.shape[1] != 3:
        raise ValueError(f"Expected k_hat shape (N,3), got {k_hat.shape}")

    norms = np.linalg.norm(k_hat, axis=1)
    if not np.all(norms > 0):
        raise ValueError("k_hat contains zero-length vectors")

    k = k_hat / norms[:, None]
    z = np.clip(k[:, 2], -1.0, 1.0)
    theta = np.arccos(z)
    phi = np.arctan2(k[:, 1], k[:, 0])
    return theta, phi


def compute_directivity(A_perp: np.ndarray) -> np.ndarray:
    """Compute directivity D = A_perp / mean(A_perp).

    D has mean 1 by construction.
    """
    A_perp = np.asarray(A_perp, dtype=np.float64)
    mean = float(np.mean(A_perp))
    if mean <= 0:
        raise ValueError(f"mean(A_perp) must be > 0, got {mean}")
    return A_perp / mean


def fit_sh(
    D: np.ndarray,
    theta: np.ndarray,
    phi: np.ndarray,
    L: int,
) -> np.ndarray:
    """Fit complex SH coefficients via least squares.

    Parameters
    ----------
    D : (N,) directivity samples
    theta, phi : (N,) spherical angles
    L : maximum SH degree

    Returns
    -------
    c : ((L+1)^2,) complex coefficients
    """
    if L < 0:
        raise ValueError("L must be >= 0")

    D = np.asarray(D, dtype=float)
    theta = np.asarray(theta, dtype=float)
    phi_02pi = np.mod(np.asarray(phi, dtype=float), 2 * np.pi)

    cols = []
    for ell in range(L + 1):
        for m in range(-ell, ell + 1):
            cols.append(sph_harm(m, ell, phi_02pi, theta))

    Y = np.stack(cols, axis=1)
    c, *_ = np.linalg.lstsq(Y, D.astype(complex), rcond=None)
    return c


def eval_sh(
    c: np.ndarray,
    theta: np.ndarray,
    phi: np.ndarray,
    L: int,
) -> np.ndarray:
    """Evaluate SH expansion at given angles.

    Returns real-valued reconstruction.
    """
    phi_02pi = np.mod(np.asarray(phi, dtype=float), 2 * np.pi)
    theta = np.asarray(theta, dtype=float)

    cols = []
    idx = 0
    for ell in range(L + 1):
        for m in range(-ell, ell + 1):
            cols.append(sph_harm(m, ell, phi_02pi, theta) * c[idx])
            idx += 1
    return np.real(np.sum(np.stack(cols, axis=1), axis=1))


def sh_reconstruction_error(
    D: np.ndarray,
    theta: np.ndarray,
    phi: np.ndarray,
    L: int,
) -> dict:
    """Fit SH at degree L and return error metrics.

    Returns dict with keys: L, n_coeff, rms, max_abs, p99_abs, coefficients.
    """
    c = fit_sh(D, theta, phi, L)
    D_hat = eval_sh(c, theta, phi, L)
    err = D_hat - D
    abs_err = np.abs(err)
    return {
        "L": L,
        "n_coeff": (L + 1) ** 2,
        "rms": float(np.sqrt(np.mean(err**2))),
        "max_abs": float(np.max(abs_err)),
        "p99_abs": float(np.percentile(abs_err, 99.0)),
        "coefficients": c,
    }
