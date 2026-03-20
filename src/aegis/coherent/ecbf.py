"""Exposure-constrained beamforming (ECBF) QCQP solver.

Solves:
    max_x  |h^T x|^2
    s.t.   x^H Q x <= P_abs_max
           ||x||^2 <= P

Optimal solution:
    x* = sqrt(P) * (lambda*Q + nu*I)^{-1} h* / ||(lambda*Q + nu*I)^{-1} h*||

where lambda, nu >= 0 are Lagrange multipliers found by bisection
on the complementary slackness conditions.

Monograph: sec:ecbf, eq:QCQP, eq:optimal-x.
"""

from __future__ import annotations

import warnings

import numpy as np
from scipy.optimize import brentq


def solve_ecbf(
    h: np.ndarray,
    Q: np.ndarray,
    P_abs_max: float,
    P: float,
    tol: float = 1e-10,
) -> np.ndarray:
    """Solve the ECBF QCQP for the optimal precoding vector.

    Parameters
    ----------
    h : (M_ant,)
        UE channel vector (complex).
    Q : (M_ant, M_ant)
        Exposure operator (Hermitian PSD).
    P_abs_max : float
        Maximum allowed absorbed power [W].
    P : float
        Total transmit power budget [W].
    tol : float
        Solver tolerance.

    Returns
    -------
    x_star : (M_ant,)
        Optimal precoding vector with ||x*||^2 = P.
    """
    h = np.asarray(h, dtype=complex)

    # First check if unconstrained MRT satisfies the exposure constraint
    x_mrt = _mrt_precoder(h, P)
    p_abs_mrt = float(np.real(x_mrt.conj() @ Q @ x_mrt))

    if p_abs_mrt <= P_abs_max + tol:
        return x_mrt

    # Eigendecompose Q for efficient solver
    eigenvalues, V = np.linalg.eigh(Q)
    eigenvalues = np.maximum(eigenvalues, 0.0)

    # Transform h into Q eigenbasis: h_tilde = V^H @ h*
    h_conj = h.conj()
    h_tilde = V.conj().T @ h_conj

    # x(lambda) = sqrt(P) * (lambda*Q + I)^{-1} h* / ||...||
    # In eigenbasis: x_tilde_k = h_tilde_k / (lambda * eigenvalues_k + 1)
    # P_abs = P * sum(eigenvalues_k * |x_tilde_k|^2) / ||x_tilde||^2

    def p_abs_at_lambda(lam: float) -> float:
        """Compute P_abs for given lambda (power constraint always active)."""
        weights = 1.0 / (lam * eigenvalues + 1.0)
        x_tilde = h_tilde * weights
        norm_sq = float(np.real(np.vdot(x_tilde, x_tilde)))
        if norm_sq < 1e-30:
            return 0.0
        p_abs = P * float(np.real(np.sum(eigenvalues * np.abs(x_tilde) ** 2))) / norm_sq
        return p_abs

    # Check if constraint is feasible. As lambda -> inf, x concentrates
    # in the smallest eigenvalue direction, giving P_abs -> P * lambda_min.
    # If P * lambda_min > P_abs_max, constraint is infeasible. Return the
    # minimum-absorption precoder (smallest eigenvector direction).
    p_abs_min = P * float(eigenvalues[0])  # eigenvalues from eigh are ascending
    if p_abs_min > P_abs_max:
        # Infeasible: return smallest-eigenvalue direction
        x_min = np.sqrt(P) * V[:, 0]
        return x_min

    # Bisect on lambda to find P_abs = P_abs_max
    lam_low = 0.0
    lam_high = 1.0
    while p_abs_at_lambda(lam_high) > P_abs_max:
        lam_high *= 10.0
        if lam_high > 1e20:
            break

    try:
        lam_star = brentq(
            lambda lam: p_abs_at_lambda(lam) - P_abs_max,
            lam_low,
            lam_high,
            xtol=tol,
            rtol=tol,
        )
    except ValueError:
        # Fallback: return minimum-absorption direction
        warnings.warn(
            "ECBF brentq solver failed; falling back to minimum-absorption direction",
            stacklevel=2,
        )
        x_min = np.sqrt(P) * V[:, 0]
        return x_min

    # Reconstruct optimal precoder
    weights = 1.0 / (lam_star * eigenvalues + 1.0)
    x_tilde = h_tilde * weights
    x_conj = V @ x_tilde
    norm = np.sqrt(float(np.real(np.vdot(x_conj, x_conj))))
    if norm < 1e-30:
        return x_mrt

    x_star = np.sqrt(P) * x_conj / norm
    return x_star


def _mrt_precoder(h: np.ndarray, P: float) -> np.ndarray:
    """Maximum ratio transmission precoder: x = sqrt(P) * h* / ||h||."""
    h_conj = h.conj()
    norm = np.sqrt(float(np.real(np.vdot(h_conj, h_conj))))
    if norm < 1e-30:
        x = np.zeros_like(h)
        x[0] = np.sqrt(P)
        return x
    return np.sqrt(P) * h_conj / norm
