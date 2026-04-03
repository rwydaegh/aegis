"""Exposure operator Q and its eigendecomposition.

Q = integral_Sigma G_tilde(r)^H @ G_tilde(r) dA  in C^{M_ant x M_ant}

Total absorbed power: P_abs = x^H @ Q @ x
Q is Hermitian positive-semidefinite by construction.

Monograph: def:Q, sec:exposure-operator.
"""

from __future__ import annotations

from aegis._array_backend import xp
from aegis.defaults import NUMERICAL_FLOOR


def compute_exposure_operator(
    G_tilde,
    areas,
):
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
    # Q = sum_m area_m * G_tilde_m^H @ G_tilde_m
    # G_tilde_m is (3, M_ant), so G_tilde_m^H @ G_tilde_m is (M_ant, M_ant)
    # Vectorised: einsum over triangles
    Q = xp.einsum(
        "m,mia,mib->ab",
        areas,
        xp.conj(G_tilde),
        G_tilde,
    )

    # Enforce exact Hermitian symmetry (numerical cleanup)
    Q = (Q + xp.conj(Q).T) / 2

    return Q


def eigendecompose_Q(
    Q,
):
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
    eigenvalues, eigenvectors = xp.linalg.eigh(Q)

    # Reverse to descending order (flip instead of argsort[::-1] for JAX traceability)
    eigenvalues = xp.flip(eigenvalues)
    eigenvectors = xp.flip(eigenvectors, axis=1)

    # Clamp small negatives from numerical noise
    eigenvalues = xp.maximum(eigenvalues, 0.0)

    return eigenvalues, eigenvectors


def compute_rho(
    h,
    Q,
    lambda_max=None,
):
    """Compute exposure-signal alignment rho.

    rho = h^H @ Q @ h / (||h||^2 * lambda_max(Q))

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
    h = xp.asarray(h, dtype=complex)
    h_norm_sq = float(xp.real(xp.vdot(h, h)))

    if h_norm_sq < NUMERICAL_FLOOR:
        return 0.0

    if lambda_max is None:
        eigenvalues = xp.linalg.eigvalsh(Q)
        lambda_max = float(xp.max(eigenvalues))

    if lambda_max < NUMERICAL_FLOOR:
        return 0.0

    # h^H @ Q @ h (Hermitian quadratic form, Q is Hermitian PSD)
    Qh = Q @ h
    numerator = float(xp.real(xp.vdot(h, Qh)))

    return float(xp.clip(numerator / (h_norm_sq * lambda_max), 0.0, 1.0))
