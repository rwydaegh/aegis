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

from aegis._array_backend import xp
from aegis.defaults import NUMERICAL_FLOOR


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
        Optimal precoding vector with ||x*||^2 <= P. The power constraint
        is active (||x*||^2 = P) at the QCQP optimum unless the parametric
        family cannot reach P_abs_max with full power, in which case the
        QCQP optimum lies in the power-slack regime with ||x*||^2 < P.
    """
    if P <= 0:
        raise ValueError(f"Transmit power P must be positive, got {P}")
    if P_abs_max <= 0:
        raise ValueError(f"P_abs_max must be positive, got {P_abs_max}")

    h = np.asarray(h, dtype=complex)
    Q = np.asarray(Q)

    if h.ndim != 1:
        raise ValueError(f"Channel vector h must be 1D, got shape {h.shape}")
    if Q.ndim != 2 or Q.shape[0] != Q.shape[1]:
        raise ValueError(f"Exposure operator Q must be square, got shape {Q.shape}")
    if h.shape[0] != Q.shape[0]:
        raise ValueError(f"Dimension mismatch: h has {h.shape[0]} elements, Q is {Q.shape[0]}x{Q.shape[1]}")

    # First check if unconstrained MRT satisfies the exposure constraint
    x_mrt = _mrt_precoder(h, P)
    p_abs_mrt = float(np.real(x_mrt.conj() @ Q @ x_mrt))

    if p_abs_mrt <= P_abs_max + tol:
        return xp.asarray(x_mrt)

    # Eigendecompose Q for efficient solver
    eigenvalues, V = np.linalg.eigh(Q)
    eigenvalues = np.maximum(eigenvalues, 0.0)

    # Numerical rank tolerance for separating null-space eigenvalues from
    # genuine nonzero ones. NUMERICAL_FLOOR (1e-30) is a safe-division guard,
    # not a rank threshold. Use numpy.matrix_rank's convention, relative to
    # the largest eigenvalue, so the classification is invariant to
    # platform-dependent eigh roundoff (see Windows-3.12 flake: zero
    # eigenvalues recovered as ~1e-15).
    rank_tol = max(Q.shape) * np.finfo(eigenvalues.dtype).eps * float(eigenvalues.max(initial=0.0))

    # Transform h into Q eigenbasis: h_tilde = V^H @ h*
    h_conj = h.conj()
    h_tilde = V.conj().T @ h_conj

    # x(lambda) = sqrt(P) * (lambda*Q + I)^{-1} h* / ||...||
    # In eigenbasis: x_tilde_k = h_tilde_k / (lambda * eigenvalues_k + 1)
    # P_abs = P * sum(eigenvalues_k * |x_tilde_k|^2) / ||x_tilde||^2

    def p_abs_at_lambda(lam):
        """Compute P_abs for given lambda (power constraint always active)."""
        weights = 1.0 / (lam * eigenvalues + 1.0)
        x_tilde = h_tilde * weights
        norm_sq = float(np.real(np.vdot(x_tilde, x_tilde)))
        if norm_sq < NUMERICAL_FLOOR:
            return 0.0
        p_abs = P * float(np.real(np.sum(eigenvalues * np.abs(x_tilde) ** 2))) / norm_sq
        return p_abs

    # Compute the true asymptotic minimum P_abs as lambda -> infinity.
    # When h has a component in the null space of Q, the null-space directions
    # dominate (their weights stay 1) and p_abs -> 0. Otherwise, the limit is
    # a weighted average: P * sum(a_k^2/mu_k) / sum(a_k^2/mu_k^2) where
    # a_k = |h_tilde_k| and mu_k are the nonzero eigenvalues.
    a_sq = np.abs(h_tilde) ** 2
    nonzero_mask = eigenvalues > rank_tol
    null_energy = float(np.sum(a_sq[~nonzero_mask]))
    energy_tol = np.finfo(a_sq.dtype).eps * float(a_sq.sum(initial=0.0))

    if null_energy > energy_tol:
        # h has a null-space component: as lambda -> inf, x concentrates
        # there and p_abs -> 0.
        p_abs_inf = 0.0
    elif np.any(nonzero_mask):
        mu_nz = eigenvalues[nonzero_mask]
        a_sq_nz = a_sq[nonzero_mask]
        denom = float(np.sum(a_sq_nz / mu_nz**2))
        p_abs_inf = P * float(np.sum(a_sq_nz / mu_nz)) / denom if denom > NUMERICAL_FLOOR else 0.0
    else:
        p_abs_inf = 0.0

    # Power-slack regime: when Q is invertible and h is not aligned with
    # the smallest eigenvalue directions, the parametric family
    # x(lambda) = sqrt(P)*(lambda*Q+I)^{-1}h*/||...|| (which forces
    # ||x||^2 = P) may never reach P_abs_max. The true QCQP optimum then
    # has ||x||^2 < P with x proportional to Q^{-1} h*. This must be
    # checked before the infeasibility branch below, since when Q is
    # invertible p_abs_inf == p_abs_asymp and the QCQP is always feasible
    # via the slack solution.
    if eigenvalues[0] > rank_tol:
        h_abs_sq = np.abs(h_tilde) ** 2
        inv_eigvals = 1.0 / eigenvalues
        # h*^H Q^{-1} h* and h*^H Q^{-2} h*
        qinv_form = float(np.sum(h_abs_sq * inv_eigvals))
        qinv2_form = float(np.sum(h_abs_sq * inv_eigvals**2))
        if qinv2_form > NUMERICAL_FLOOR:
            p_abs_asymp = P * qinv_form / qinv2_form
            if p_abs_asymp > P_abs_max:
                # Power constraint is slack at optimality.
                # x = alpha * Q^{-1} h*, scaled so x^H Q x = P_abs_max.
                alpha = np.sqrt(P_abs_max / qinv_form)
                x_tilde_slack = alpha * h_tilde * inv_eigvals
                x_slack = V @ x_tilde_slack
                return xp.asarray(x_slack)

    if p_abs_inf > P_abs_max:
        # Infeasible: return smallest-eigenvalue direction
        warnings.warn(
            "ECBF constraint infeasible: minimum achievable P_abs "
            f"({p_abs_inf:.4g} W) exceeds P_abs_max ({P_abs_max:.4g} W); "
            "returning minimum-absorption precoder",
            stacklevel=2,
        )
        return xp.asarray(np.sqrt(P) * V[:, 0])

    # Bisect on lambda to find P_abs = P_abs_max
    lam_low = 0.0
    lam_high = 1.0
    while p_abs_at_lambda(lam_high) > P_abs_max:
        lam_high *= 10.0
        if lam_high > 1e20:
            warnings.warn(
                "ECBF lambda bracket expansion exceeded 1e20 without "
                "satisfying absorption constraint; returning minimum-absorption direction",
                stacklevel=2,
            )
            return xp.asarray(np.sqrt(P) * V[:, 0])

    lam_star = _bisect(
        lambda lam: p_abs_at_lambda(lam) - P_abs_max,
        lam_low,
        lam_high,
        tol=tol,
    )

    if lam_star is None:
        # Fallback: return minimum-absorption direction
        warnings.warn(
            "ECBF bisection solver failed; falling back to minimum-absorption direction",
            stacklevel=2,
        )
        return xp.asarray(np.sqrt(P) * V[:, 0])

    # Reconstruct optimal precoder
    weights = 1.0 / (lam_star * eigenvalues + 1.0)
    x_tilde = h_tilde * weights
    x_conj = V @ x_tilde
    norm = np.sqrt(float(np.real(np.vdot(x_conj, x_conj))))
    if norm < NUMERICAL_FLOOR:
        return xp.asarray(np.sqrt(P) * V[:, 0])

    x_star = np.sqrt(P) * x_conj / norm
    return xp.asarray(x_star)


def solve_ecbf_sweep(
    h: np.ndarray,
    Q: np.ndarray,
    p_abs_max_list,
    P: float,
    tol: float = 1e-10,
) -> list:
    """Solve the ECBF QCQP for many absorbed-power budgets sharing one ``(h, Q)``.

    Equivalent to ``[solve_ecbf(h, Q, b, P) for b in p_abs_max_list]``, but the
    budget-independent work (the MRT reference and the eigendecomposition of ``Q``)
    is done once and reused across every budget, so a budget sweep costs a single
    ``eigh`` instead of one per point. The exposure operator and the channel are
    fixed along an absorbed-power sweep, so only the scalar budget changes between
    points. Returns a list of precoders aligned with ``p_abs_max_list``.
    """
    if P <= 0:
        raise ValueError(f"Transmit power P must be positive, got {P}")

    h = np.asarray(h, dtype=complex)
    Q = np.asarray(Q)
    if h.ndim != 1:
        raise ValueError(f"Channel vector h must be 1D, got shape {h.shape}")
    if Q.ndim != 2 or Q.shape[0] != Q.shape[1]:
        raise ValueError(f"Exposure operator Q must be square, got shape {Q.shape}")
    if h.shape[0] != Q.shape[0]:
        raise ValueError(f"Dimension mismatch: h has {h.shape[0]} elements, Q is {Q.shape[0]}x{Q.shape[1]}")

    # Budget-independent factorisation, computed once for the whole sweep.
    x_mrt = _mrt_precoder(h, P)
    p_abs_mrt = float(np.real(x_mrt.conj() @ Q @ x_mrt))

    eigenvalues, V = np.linalg.eigh(Q)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    rank_tol = max(Q.shape) * np.finfo(eigenvalues.dtype).eps * float(eigenvalues.max(initial=0.0))

    h_conj = h.conj()
    h_tilde = V.conj().T @ h_conj
    a_sq = np.abs(h_tilde) ** 2
    nonzero_mask = eigenvalues > rank_tol
    null_energy = float(np.sum(a_sq[~nonzero_mask]))
    energy_tol = np.finfo(a_sq.dtype).eps * float(a_sq.sum(initial=0.0))

    if null_energy > energy_tol:
        p_abs_inf = 0.0
    elif np.any(nonzero_mask):
        mu_nz = eigenvalues[nonzero_mask]
        a_sq_nz = a_sq[nonzero_mask]
        denom = float(np.sum(a_sq_nz / mu_nz**2))
        p_abs_inf = P * float(np.sum(a_sq_nz / mu_nz)) / denom if denom > NUMERICAL_FLOOR else 0.0
    else:
        p_abs_inf = 0.0

    invertible = eigenvalues[0] > rank_tol
    if invertible:
        inv_eigvals = 1.0 / eigenvalues
        qinv_form = float(np.sum(a_sq * inv_eigvals))
        qinv2_form = float(np.sum(a_sq * inv_eigvals**2))

    def p_abs_at_lambda(lam):
        weights = 1.0 / (lam * eigenvalues + 1.0)
        x_tilde = h_tilde * weights
        norm_sq = float(np.real(np.vdot(x_tilde, x_tilde)))
        if norm_sq < NUMERICAL_FLOOR:
            return 0.0
        return P * float(np.real(np.sum(eigenvalues * np.abs(x_tilde) ** 2))) / norm_sq

    def solve_for_budget(p_abs_max):
        # Mirrors the tail of solve_ecbf, but on the shared factorisation above.
        if p_abs_max <= 0:
            raise ValueError(f"P_abs_max must be positive, got {p_abs_max}")
        if p_abs_mrt <= p_abs_max + tol:
            return xp.asarray(x_mrt)
        if invertible and qinv2_form > NUMERICAL_FLOOR:
            p_abs_asymp = P * qinv_form / qinv2_form
            if p_abs_asymp > p_abs_max:
                alpha = np.sqrt(p_abs_max / qinv_form)
                return xp.asarray(V @ (alpha * h_tilde * inv_eigvals))
        if p_abs_inf > p_abs_max:
            warnings.warn(
                "ECBF constraint infeasible: minimum achievable P_abs "
                f"({p_abs_inf:.4g} W) exceeds P_abs_max ({p_abs_max:.4g} W); "
                "returning minimum-absorption precoder",
                stacklevel=2,
            )
            return xp.asarray(np.sqrt(P) * V[:, 0])
        lam_high = 1.0
        while p_abs_at_lambda(lam_high) > p_abs_max:
            lam_high *= 10.0
            if lam_high > 1e20:
                warnings.warn(
                    "ECBF lambda bracket expansion exceeded 1e20 without "
                    "satisfying absorption constraint; returning minimum-absorption direction",
                    stacklevel=2,
                )
                return xp.asarray(np.sqrt(P) * V[:, 0])
        lam_star = _bisect(lambda lam: p_abs_at_lambda(lam) - p_abs_max, 0.0, lam_high, tol=tol)
        if lam_star is None:
            warnings.warn(
                "ECBF bisection solver failed; falling back to minimum-absorption direction",
                stacklevel=2,
            )
            return xp.asarray(np.sqrt(P) * V[:, 0])
        x_conj = V @ (h_tilde / (lam_star * eigenvalues + 1.0))
        norm = np.sqrt(float(np.real(np.vdot(x_conj, x_conj))))
        if norm < NUMERICAL_FLOOR:
            return xp.asarray(np.sqrt(P) * V[:, 0])
        return xp.asarray(np.sqrt(P) * x_conj / norm)

    return [solve_for_budget(float(b)) for b in p_abs_max_list]


def _bisect(f, a, b, tol=1e-10, maxiter=200):
    """Simple bisection root finder. Returns None on failure."""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return None
    for _ in range(maxiter):
        mid = 0.5 * (a + b)
        scale = max(abs(a), abs(b), 1.0)
        if (b - a) / scale < tol:
            return mid
        fm = f(mid)
        if fa * fm <= 0:
            b = mid
        else:
            a = mid
            fa = fm
    return 0.5 * (a + b)


def _mrt_precoder(h, P):
    """Maximum ratio transmission precoder: x = sqrt(P) * h* / ||h||."""
    h_conj = h.conj()
    norm = np.sqrt(float(np.real(np.vdot(h_conj, h_conj))))
    if norm < NUMERICAL_FLOOR:
        x = np.zeros(h.shape, dtype=h.dtype)
        x[0] = np.sqrt(P)
        return x
    return np.sqrt(P) * h_conj / norm
