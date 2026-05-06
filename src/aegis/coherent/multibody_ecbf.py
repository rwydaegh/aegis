"""Multi-body exposure-constrained beamforming (ECBF) precoder.

Solves the per-body PSD-budget QCQP from paper sec:precoder eq:P-MB:

    max_{W}   sum_k log2(1 + SINR_k(W))
    s.t.      sum_k w_k^H Q^{(u)} w_k <= L^{(u)}   for u = 1 .. B
              ||W||_F^2 <= P

with closed form (eq:closedform):

    w_k* = (Q_tot(lambda) + nu I)^{-1} g_k

Two inner-direction variants are exposed via ``noise_power``:

    noise_power = None   ->  g_k = h_k^*, M = I + Q_tot
                             (matched-filter; collapses to the single-body
                             ECBF in coherent/ecbf.py for K = 1)
    noise_power > 0      ->  g_k = h_k^*, M = H^H H + noise_power * I + Q_tot
                             (MMSE-with-exposure; recovers regularised ZF in
                             the rank-1 bystander limit and dominates the
                             worst-case back-off baselines on sum-rate).

The total power is enforced by re-scaling ||W||_F^2 = P after the
directions are computed; this matches mrt() / zf() / mmse() in
aegis.mimo.precoders.

Algorithm: cold-start lambda = 0, then Newton ascent on the dual function
restricted to the currently active set of bodies. The Jacobian
J_uv = d p_abs_u / d lambda_v is built by forward finite differences and
the Newton step is damped to keep lambda >= 0. Convergence is super-
linear once the active set stabilises, which beats vanilla
Gauss-Seidel coordinate bisection by roughly two orders of magnitude on
the number of inversions required to reach machine precision.

Sanity limits exercised in tests/test_multibody_ecbf.py:
    B = 1, K = 1                 -> single-body ECBF (rank-1 degenerate).
    All budgets large            -> MRT (caught by the trial step).
    Q^{(u)} = a_u a_u^H, L -> 0  -> regularised ZF on bystanders (Prop. 1).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np

from aegis._array_backend import xp
from aegis.defaults import NUMERICAL_FLOOR


@dataclass
class MultibodyECBFDiagnostics:
    """Solver diagnostics for the multi-body ECBF call.

    Attributes
    ----------
    lambdas : (B,) ndarray
        Final per-body Lagrange multipliers. Active bodies have lambda_u > 0.
    p_abs : (B,) ndarray
        Per-body absorbed power at the returned precoder, in W.
    L : (B,) ndarray
        Per-body budgets (echoed back for caller convenience).
    method : str
        One of {"mrt-feasible", "multibody-ecbf", "min-absorption"}.
    converged : bool
        True if Newton ascent on the dual reached its tolerance.
    n_outer : int
        Number of outer Newton steps used.
    n_active : int
        Number of bodies with binding budget at the optimum.
    residual : float
        Maximum relative budget violation, max_u (p_abs_u - L_u)_+ / L_u.
    """

    lambdas: np.ndarray
    p_abs: np.ndarray
    L: np.ndarray
    method: str
    converged: bool = True
    n_outer: int = 0
    n_active: int = 0
    residual: float = 0.0
    extra: dict = field(default_factory=dict)


def solve_multibody_ecbf(
    H: np.ndarray,
    Q_list: list[np.ndarray] | tuple[np.ndarray, ...] | np.ndarray,
    L_list: list[float] | tuple[float, ...] | np.ndarray,
    P: float,
    *,
    noise_power: float | None = None,
    max_outer: int = 30,
    tol: float = 1e-9,
    return_diagnostics: bool = False,
    lambda_init: np.ndarray | None = None,
) -> np.ndarray | tuple[np.ndarray, MultibodyECBFDiagnostics]:
    """Solve the multi-body ECBF QCQP.

    Parameters
    ----------
    H : (K, M) complex
        Per-user channel matrix, one row per served user.
    Q_list : sequence of (M, M) Hermitian PSD matrices
        Per-body exposure operators, one per body in U cup B (paper sec:precoder).
        Length B = K + B_bystanders is allowed and typical.
    L_list : sequence of B positive floats
        Per-body absorbed-power budgets in W.
    P : float
        Total transmit power budget in W.
    noise_power : float, optional
        When provided, the inner solver builds the regularised matrix
        M(lambda) = H^H H + noise_power * I + Q_tot(lambda), giving the
        MMSE-with-exposure direction w_k* = M^{-1} h_k^*. This is what
        recovers regularised ZF in the rank-1 limit and dominates the
        worst-case-back-off baselines on sum-rate. The default
        ``noise_power=None`` disables the H^H H term, leaving the
        matched-filter form M = I + Q_tot used by the single-body ECBF in
        coherent/ecbf.py - which is what makes the K=1 limit collapse to
        the single-body solver to machine precision.
    max_outer : int, default 30
        Maximum Newton-ascent iterations over the body multipliers.
    tol : float, default 1e-9
        Stopping tolerance on the relative budget residual and on
        the multiplier change between iterations.
    return_diagnostics : bool, default False
        If True, return (W, diagnostics). Otherwise return W only.
    lambda_init : (B,) ndarray, optional
        Warm-start for the per-body Lagrange multipliers. Default is
        cold-start lambda = 0. When the geometry is changing slowly across
        repeated calls (e.g. a slot loop where bodies move ~1 m/s), passing
        the previous call's diagnostics.lambdas typically cuts the Newton
        iteration count by 2-4x and lowers the min-absorption fallback
        rate, because the active-constraint set rarely changes between
        adjacent slots. Negative entries are clipped to 0; mismatched
        length raises ValueError.

    Returns
    -------
    W : (M, K) complex ndarray
        Multi-user precoder with ||W||_F^2 = P (or smaller if the solver
        falls back to a min-absorption direction).
    diagnostics : MultibodyECBFDiagnostics, optional
        Returned only when return_diagnostics is True.
    """
    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H.reshape(1, -1)
    if H.ndim != 2:
        raise ValueError(f"H must be 2D (K, M), got shape {H.shape}")
    K, M = H.shape

    if P <= 0:
        raise ValueError(f"Transmit power P must be positive, got {P}")
    if noise_power is not None and noise_power <= 0:
        raise ValueError(f"noise_power must be positive when provided, got {noise_power}")

    Q_arr = _stack_Q(Q_list, M)
    B = Q_arr.shape[0]

    # Optional H^H H regularisation. Built once and passed through to the
    # inner solver so we do not pay the (M, K) -> (M, M) outer product per
    # Newton iteration.
    if noise_power is None:
        base_mat = None
        I_scale = 1.0
    else:
        base_mat = H.conj().T @ H
        I_scale = float(noise_power)

    L_arr = np.asarray(L_list, dtype=float)
    if L_arr.ndim != 1 or L_arr.shape[0] != B:
        raise ValueError(
            f"L_list must be a 1D sequence with one entry per body, got shape {L_arr.shape} for B={B} bodies"
        )
    if np.any(L_arr <= 0):
        raise ValueError("All per-body budgets L^{(u)} must be positive")

    # MRT trial: cheapest possible precoder.
    W_mrt = _mrt(H, P)
    p_abs_mrt = _per_body_abs(W_mrt, Q_arr)
    if np.all(p_abs_mrt <= L_arr * (1.0 + tol)):
        diag = MultibodyECBFDiagnostics(
            lambdas=np.zeros(B),
            p_abs=p_abs_mrt,
            L=L_arr,
            method="mrt-feasible",
            converged=True,
            n_outer=0,
            n_active=0,
            residual=float(np.max(np.maximum(0.0, p_abs_mrt - L_arr) / L_arr, initial=0.0)),
        )
        return (xp.asarray(W_mrt), diag) if return_diagnostics else xp.asarray(W_mrt)

    # Newton ascent on the dual. The KKT system on active bodies is
    #     p_abs_u(lambda) - L_u = 0   for active u (lambda_u > 0)
    #     p_abs_u(lambda) - L_u <= 0  for inactive u (lambda_u = 0).
    # The Jacobian J_uv = d p_abs_u / d lambda_v is computed by forward
    # finite differences on _solve_W, which costs B' inversions per step
    # (B' = number of currently active bodies) plus one fresh evaluation.
    H_conj = H.conj().T
    if lambda_init is None:
        lambdas = np.zeros(B)
    else:
        lambdas = np.asarray(lambda_init, dtype=float).copy()
        if lambdas.shape != (B,):
            raise ValueError(f"lambda_init must have shape ({B},) to match the body count, got {lambdas.shape}")
        np.maximum(lambdas, 0.0, out=lambdas)
    converged = False
    n_outer = 0
    fd_step = 1e-5

    for outer_iter in range(max_outer):
        n_outer = outer_iter + 1
        W = _solve_W(lambdas, Q_arr, H_conj, P, base_mat=base_mat, I_scale=I_scale)
        p_abs = _per_body_abs(W, Q_arr)
        gap = p_abs - L_arr
        rel_viol = np.max(np.maximum(0.0, gap) / L_arr, initial=0.0)
        if rel_viol < tol:
            converged = True
            break

        # Active set: anything currently violating, plus any body that
        # already carries a positive multiplier (so we can release it).
        active = (gap > 0) | (lambdas > 0)
        idx = np.where(active)[0]
        if idx.size == 0:
            converged = True
            break

        # Build Jacobian via forward differences on active bodies.
        h = fd_step * np.maximum(np.abs(lambdas[idx]), 1.0)
        n_active = idx.size
        J = np.zeros((n_active, n_active))
        for v in range(n_active):
            lam_p = lambdas.copy()
            lam_p[idx[v]] = lambdas[idx[v]] + h[v]
            W_p = _solve_W(lam_p, Q_arr, H_conj, P, base_mat=base_mat, I_scale=I_scale)
            p_p = _per_body_abs(W_p, Q_arr)
            J[:, v] = (p_p[idx] - p_abs[idx]) / h[v]
        gap_active = gap[idx]

        # Newton step on -J (dual is concave in lambda, so -J is PSD-ish
        # near the optimum). Solve (-J) delta = gap_active, then project.
        try:
            delta = np.linalg.solve(-J + 1e-12 * np.eye(n_active), gap_active)
        except np.linalg.LinAlgError:
            delta = gap_active.copy()  # crude fallback

        # Damped step: keep the iterate inside the feasible cone.
        max_decrease = lambdas[idx]  # how far we can decrease without going negative
        step_scale = 1.0
        too_negative = (delta < -max_decrease) & (max_decrease > 0)
        if np.any(too_negative):
            ratios = -max_decrease[too_negative] / delta[too_negative]
            step_scale = float(min(1.0, ratios.min() * 0.99))
        new_lambdas = lambdas.copy()
        new_lambdas[idx] = np.maximum(0.0, lambdas[idx] + step_scale * delta)
        # Convergence on multipliers as a secondary safeguard.
        denom = np.maximum(np.abs(lambdas), 1.0)
        rel_change = float(np.max(np.abs(new_lambdas - lambdas) / denom, initial=0.0))
        lambdas = new_lambdas
        if rel_change < tol and rel_viol < 10 * tol:
            converged = True
            break

    # Build final precoder from converged multipliers.
    W = _solve_W(lambdas, Q_arr, H_conj, P, base_mat=base_mat, I_scale=I_scale)
    p_abs = _per_body_abs(W, Q_arr)
    viol = np.maximum(0.0, p_abs - L_arr)
    residual = float(np.max(viol / L_arr, initial=0.0))

    if residual > 1e-3:
        warnings.warn(
            f"Multi-body ECBF: residual relative budget violation {residual:.3g} "
            f"exceeds 1e-3 after {n_outer} outer sweeps. Returning the smallest-"
            "joint-eigenvalue direction as a min-absorption fallback.",
            stacklevel=2,
        )
        W = _min_absorption_fallback(Q_arr, P, K)
        p_abs = _per_body_abs(W, Q_arr)
        diag = MultibodyECBFDiagnostics(
            lambdas=lambdas,
            p_abs=p_abs,
            L=L_arr,
            method="min-absorption",
            converged=False,
            n_outer=n_outer,
            n_active=int(np.count_nonzero(lambdas > 0)),
            residual=float(np.max(np.maximum(0.0, p_abs - L_arr) / L_arr, initial=0.0)),
        )
        return (xp.asarray(W), diag) if return_diagnostics else xp.asarray(W)

    diag = MultibodyECBFDiagnostics(
        lambdas=lambdas,
        p_abs=p_abs,
        L=L_arr,
        method="multibody-ecbf",
        converged=converged,
        n_outer=n_outer,
        n_active=int(np.count_nonzero(lambdas > 0)),
        residual=residual,
    )
    return (xp.asarray(W), diag) if return_diagnostics else xp.asarray(W)


def _stack_Q(Q_list, M: int) -> np.ndarray:
    """Stack per-body operators into a (B, M, M) complex array.

    Validates Hermitian shape; PSD-ness is taken on faith because Q is
    constructed from Q = Jt M J in production code and is PSD by construction.
    """
    if isinstance(Q_list, np.ndarray) and Q_list.ndim == 3:
        Q_arr = np.ascontiguousarray(Q_list, dtype=complex)
    else:
        Q_arr = np.stack([np.asarray(Q, dtype=complex) for Q in Q_list], axis=0)
    if Q_arr.ndim != 3 or Q_arr.shape[1] != M or Q_arr.shape[2] != M:
        raise ValueError(f"Each Q^{{(u)}} must be ({M}, {M}); got stacked shape {Q_arr.shape}")
    return Q_arr


def _mrt(H: np.ndarray, P: float) -> np.ndarray:
    """MRT precoder, copy of aegis.mimo.precoders.mrt to avoid circular import."""
    K = H.shape[0]
    W_conj = H.conj().T
    norms = np.linalg.norm(W_conj, axis=0, keepdims=True)
    norms = np.maximum(norms, NUMERICAL_FLOOR)
    return np.sqrt(P / K) * W_conj / norms


def _per_body_abs(W: np.ndarray, Q_arr: np.ndarray) -> np.ndarray:
    """sum_k w_k^H Q^{(u)} w_k = trace(W^H Q W) for each body u.

    Vectorised across bodies. Returns a real (B,) array of absorbed powers.
    """
    # einsum: W*_{i,k} Q_{b,i,j} W_{j,k} -> b. The i-index pairs row of W^H
    # (= conj of W column entry) with the row of Q, the j-index pairs Q's
    # column with W. Anything else silently sums incorrectly.
    return np.real(np.einsum("ik,bij,jk->b", W.conj(), Q_arr, W, optimize=True))


def _solve_W(
    lambdas: np.ndarray,
    Q_arr: np.ndarray,
    H_conj: np.ndarray,
    P: float,
    *,
    base_mat: np.ndarray | None = None,
    I_scale: float = 1.0,
) -> np.ndarray:
    """Compute the closed-form precoder matrix at the given multipliers.

    W_raw[:, k] = (base_mat + I_scale * I + sum_u lambda_u Q_u)^{-1} h_k^*
    W = sqrt(P) * W_raw / ||W_raw||_F

    base_mat is None for the single-body-equivalent matched-filter form
    (M = I + Q_tot), or H^H H for the MMSE-with-exposure form.
    """
    M = Q_arr.shape[1]
    M_lam = I_scale * np.eye(M, dtype=complex) if base_mat is None else base_mat + I_scale * np.eye(M, dtype=complex)
    if lambdas.size > 0:
        # Vectorised accumulation.
        active = lambdas > 0
        if np.any(active):
            M_lam = M_lam + np.einsum("u,uij->ij", lambdas[active], Q_arr[active])
    # M_lam is Hermitian PSD + I, hence Hermitian positive definite.
    try:
        W_raw = np.linalg.solve(M_lam, H_conj)
    except np.linalg.LinAlgError:
        # Extremely defensive: fall back to pseudo-inverse.
        W_raw = np.linalg.pinv(M_lam) @ H_conj
    frob = float(np.linalg.norm(W_raw, "fro"))
    if frob < NUMERICAL_FLOOR:
        K = H_conj.shape[1]
        return np.zeros((M, K), dtype=complex)
    return np.sqrt(P) * W_raw / frob


def _min_absorption_fallback(Q_arr: np.ndarray, P: float, K: int) -> np.ndarray:
    """Build a precoder along the smallest-eigenvalue direction of Q_sum.

    Used when the body-aware Newton ascent fails to bring all budgets
    within tolerance. The direction minimises sum_u tr(Q^{(u)} W W^H) at
    fixed Frobenius energy, which is the right notion of "back off"
    when the feasible set is empty.
    """
    Q_sum = np.einsum("uij->ij", Q_arr)
    _, V = np.linalg.eigh(Q_sum)
    direction = V[:, 0]  # smallest-eigenvalue eigenvector
    # Distribute power equally across K streams along the same direction.
    # This is a degenerate fallback: every column is identical, so the
    # resulting MIMO sum-rate is poor, but the absorbed power is minimised.
    W = np.tile(direction[:, None], (1, K)) * np.sqrt(P / K)
    return W
