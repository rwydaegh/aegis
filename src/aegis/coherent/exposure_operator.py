"""Exposure operator Q and its eigendecomposition.

Q = integral_Sigma G_tilde(r)^H @ G_tilde(r) dA  in C^{M_ant x M_ant}

Total absorbed power: P_abs = x^H @ Q @ x
Q is Hermitian positive-semidefinite by construction.

Monograph: def:Q, sec:exposure-operator.
"""

from __future__ import annotations

import numpy as np


def compute_exposure_operator(
    G_tilde: np.ndarray,
    areas: np.ndarray,
) -> np.ndarray:
    """Compute the exposure operator Q from the body-surface channel.

    Q = sum_m G_tilde[m]^H @ G_tilde[m] * area[m]

    Parameters
    ----------
    G_tilde : (M_tri, 3, M_ant)
        Body-surface channel at each triangle centroid.
    areas : (M_tri,)
        Triangle areas [m^2].

    Returns
    -------
    Q : (M_ant, M_ant)
        Hermitian PSD exposure operator.
    """
    M_tri, _, M_ant = G_tilde.shape

    # Q = sum_m area_m * G_tilde_m^H @ G_tilde_m
    # G_tilde_m is (3, M_ant), so G_tilde_m^H @ G_tilde_m is (M_ant, M_ant)
    # Vectorised: einsum over triangles
    # G_tilde^H @ G_tilde per triangle: (M_ant, 3) @ (3, M_ant) = (M_ant, M_ant)
    Q = np.einsum(
        "m,mia,mib->ab",
        areas,
        G_tilde.conj(),
        G_tilde,
    )

    # Enforce exact Hermitian symmetry (numerical cleanup)
    Q = (Q + Q.conj().T) / 2

    return Q


def eigendecompose_Q(
    Q: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Eigendecompose the exposure operator Q.

    Returns eigenvalues in descending order with corresponding eigenvectors.

    Parameters
    ----------
    Q : (M_ant, M_ant)
        Hermitian PSD exposure operator.

    Returns
    -------
    eigenvalues : (M_ant,)
        Eigenvalues in descending order (non-negative).
    eigenvectors : (M_ant, M_ant)
        Columns are eigenvectors, sorted to match eigenvalues.
    """
    eigenvalues, eigenvectors = np.linalg.eigh(Q)

    # Reverse to descending order
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Clamp small negatives from numerical noise
    eigenvalues = np.maximum(eigenvalues, 0.0)

    return eigenvalues, eigenvectors


def compute_rho(
    h: np.ndarray,
    Q: np.ndarray,
    lambda_max: float | None = None,
) -> float:
    """Compute exposure-signal alignment rho.

    rho = h^T @ Q @ h* / (||h||^2 * lambda_max(Q))

    Parameters
    ----------
    h : (M_ant,)
        UE channel vector (complex).
    Q : (M_ant, M_ant)
        Exposure operator.
    lambda_max : float or None
        Largest eigenvalue of Q. Computed if not provided.

    Returns
    -------
    rho : float
        Alignment metric in [0, 1].
    """
    h = np.asarray(h, dtype=complex)
    h_norm_sq = float(np.real(np.vdot(h, h)))

    if h_norm_sq < 1e-30:
        return 0.0

    if lambda_max is None:
        eigenvalues = np.linalg.eigvalsh(Q)
        lambda_max = float(np.max(eigenvalues))

    if lambda_max < 1e-30:
        return 0.0

    # h^T @ Q @ h* = h.conj() @ Q @ h (using vdot convention)
    Qh = Q @ h
    numerator = float(np.real(np.vdot(h, Qh)))

    return numerator / (h_norm_sq * lambda_max)
