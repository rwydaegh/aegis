"""Level 7: coherent MIMO absorption map.

S_ab(r) = ||G_tilde(r) @ x||^2

Computes per-triangle absorbed power density from the body-surface channel
G_tilde(r) and a precoding vector x. Uses Approximations 1 and 2 from the
monograph (combined error < 5% for skin at 28 GHz).

Monograph: thm:coherent-law (Theorem 4.1).
"""

from __future__ import annotations

import numpy as np

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import (
    compute_exposure_operator,
    compute_rho,
    eigendecompose_Q,
)


def level7_coherent(
    normals: np.ndarray,
    centroids: np.ndarray,
    areas: np.ndarray,
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    x: np.ndarray,
    n_tilde: complex,
    sigma: float,
    freq_hz: float,
    n_elements: int,
    h: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, float | None]:
    """Compute coherent absorbed power density map.

    Parameters
    ----------
    normals : (M, 3)
    centroids : (M, 3)
    areas : (M,)
    k_hat : (N, 3)
    psi : (N, 3)
    element_index : (N,)
    x : (M_ant,) precoding vector
    n_tilde : complex refractive index
    sigma : tissue conductivity [S/m]
    freq_hz : frequency [Hz]
    n_elements : int
    h : (M_ant,) UE channel vector (optional, for rho computation)

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    Q : (M_ant, M_ant) exposure operator
    eigenvalues : (M_ant,) or None, eigenvalues of Q
    rho : float or None, exposure-signal alignment
    """
    G_tilde = compute_body_channel(
        normals,
        centroids,
        k_hat,
        psi,
        element_index,
        n_tilde,
        sigma,
        freq_hz,
        n_elements,
    )

    # S_ab(r) = ||G_tilde(r) @ x||^2
    # G_tilde: (M, 3, M_ant), x: (M_ant,)
    field = np.einsum("mia,a->mi", G_tilde, x)  # (M, 3)
    sab = np.real(np.sum(field.conj() * field, axis=1))  # (M,)
    sab = np.maximum(sab, 0.0)

    # Exposure operator Q
    Q = compute_exposure_operator(G_tilde, areas)
    eigenvalues, _ = eigendecompose_Q(Q)

    # Exposure-signal alignment rho
    rho = None
    if h is not None:
        rho = compute_rho(h, Q, lambda_max=float(eigenvalues[0]))

    return sab, Q, eigenvalues, rho
