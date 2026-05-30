"""WMMSE-driven multi-body exposure-constrained beamforming.

Outer block-coordinate descent on (u_k, v_k, W); inner dual-Newton
ascent on the per-body Lagrange multipliers reusing the kernels of
``aegis.coherent.multibody_ecbf``.

For a base-station serving ``K`` users with channels ``h_1, ..., h_K``
(convention: received baseband ``y_k = h_k^T x``), the multi-user
sum-rate maximisation under per-body absorbed-power caps

    max_{W}    sum_k log2(1 + SINR_k(W))
    s.t.       sum_k w_k^H Q^{(u)} w_k <= L^{(u)}    u in U cup B
               ||W||_F^2 <= P_tx

admits, via the WMMSE surrogate of Christensen 2008 / Shi 2011 and the
KKT stationarity for the per-body exposure caps, the closed-form inner
update

    (H_intf + Q_tot(lambda) + nu I) w_k = u_k v_k h_k^*,

with

    v_k    = (h_k^T w_k) / (sum_j |h_k^T w_j|^2 + sigma_n^2)   MMSE filter
    u_k    = 1 / (1 - v_k* h_k^T w_k)                          rate weight
    H_intf = sum_l u_l |v_l|^2 h_l^* h_l^T = H^H D H,
             D = diag(u_1 |v_1|^2, ..., u_K |v_K|^2)
    Q_tot  = sum_u lambda_u Q^{(u)}.

Comparing to ``multibody_ecbf.solve_multibody_ecbf(noise_power=sigma_n^2)``,
which clamps (u_k, v_k) at (1, 1) and gives the unweighted MMSE-with-
exposure precoder, the WMMSE outer iteration restores the proper rate
weights and recovers the sum-rate optimum in the regime where per-user
SINR varies across the population. The inner dual ascent on the per-body
multipliers ``lambda`` is structurally identical to the unweighted form;
the difference lives entirely in how ``base_mat`` and the per-stream
drive are assembled at each WMMSE step.

Limits exercised in tests:
    K = 1                         -> single-user reduction (u_k v_k = 1 by construction)
    All budgets large             -> WMMSE-MMSE without exposure
    Q^{(u)} = a_u a_u^H, L -> 0   -> rank-1 ZF on bystanders (Prop. 1).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np

from aegis._array_backend import xp
from aegis.coherent.multibody_ecbf import (
    MultibodyECBFDiagnostics,
    _decompose_lowrank,
    _min_absorption_fallback,
    _mrt,
    _per_body_abs,
    _per_body_abs_lowrank,
    _solve_W_factored,
    _stack_Q,
)


@dataclass
class MultibodyECBFWMMSEDiagnostics(MultibodyECBFDiagnostics):
    """Adds WMMSE outer-loop diagnostics to the standard ECBF record."""

    n_wmmse: int = 0
    sumrate_history_bps_hz: list[float] = field(default_factory=list)
    final_uv: tuple[np.ndarray, np.ndarray] | None = None


def solve_multibody_ecbf_wmmse(
    H: np.ndarray,
    Q_list,
    L_list,
    P: float,
    *,
    noise_power: float = 1e-2,
    max_outer_wmmse: int = 12,
    tol_wmmse: float = 1e-4,
    max_outer_dual: int = 8,
    tol_dual: float = 1e-7,
    return_diagnostics: bool = False,
    lambda_init: np.ndarray | None = None,
    lowrank_rank: int | None = None,
    uv_init: tuple[np.ndarray, np.ndarray] | None = None,
):
    """Solve the multi-body WMMSE-ECBF QCQP.

    Parameters mirror :func:`multibody_ecbf.solve_multibody_ecbf` except for
    the WMMSE-specific knobs:

    Parameters
    ----------
    H : (K, M) complex
        Per-user channel matrix, ``y_k = h_k^T x`` convention.
    Q_list : sequence of (M, M) Hermitian PSD
        Per-body exposure operators.
    L_list : sequence of (B,) positive
        Per-body absorbed-power caps in W. ``B = K + n_bystanders`` is allowed.
    P : float
        Total transmit-power budget in W.
    noise_power : float
        Receive noise power ``sigma_n^2``. Strictly positive — the
        unweighted ``noise_power=None`` path of the MMSE solver is not
        meaningful for WMMSE (``v_k`` undefined at zero noise).
    max_outer_wmmse : int
        Cap on the outer (u, v, W) block-coordinate iterations. Typical
        binding-regime convergence sits at 4-8 iterations; the bound on
        sum-rate gain after the 6th is small.
    tol_wmmse : float
        Stop the outer loop when relative sum-rate change drops below
        this fraction.
    max_outer_dual : int
        Inner dual-Newton iteration cap (passed through to the per-WMMSE
        ECBF solve).
    tol_dual : float
        Inner relative-budget tolerance.
    return_diagnostics : bool
        If True, return ``(W, MultibodyECBFWMMSEDiagnostics)``.
    lambda_init, lowrank_rank :
        Same semantics as the unweighted solver. Warm-starting ``lambda``
        across slots typically halves the inner Newton iteration count.
    uv_init : optional ``(u_init, v_init)``
        Warm-start for the rate weights and MMSE filters. When the
        previous slot's solution is fed in, the WMMSE outer typically
        converges in 2-3 iterations rather than 6-8.

    Returns
    -------
    W : (M, K) complex
    diagnostics : MultibodyECBFWMMSEDiagnostics, optional
    """
    if noise_power is None or noise_power <= 0:
        raise ValueError(f"WMMSE requires a positive noise_power (sigma_n^2); got {noise_power}")

    H = np.asarray(H, dtype=complex)
    if H.ndim == 1:
        H = H.reshape(1, -1)
    K, M = H.shape
    if P <= 0:
        raise ValueError(f"Transmit power P must be positive, got {P}")

    Q_arr = _stack_Q(Q_list, M)
    B = Q_arr.shape[0]

    L_arr = np.asarray(L_list, dtype=float)
    if L_arr.shape != (B,):
        raise ValueError(f"L_list shape {L_arr.shape} != (B={B},)")
    if np.any(L_arr <= 0):
        raise ValueError("All per-body budgets must be positive")

    if lowrank_rank is not None and (lowrank_rank <= 0 or lowrank_rank > M):
        raise ValueError(f"lowrank_rank must be in [1, {M}], got {lowrank_rank}")

    H_row = H  # (K, M), rows = h_k^T
    H_conj = H.conj().T  # (M, K), columns = h_k^* (the matched-filter drive)

    # MRT trial (cheap optimum if it satisfies every budget).
    W_mrt = _mrt(H, P)
    p_abs_mrt = _per_body_abs(W_mrt, Q_arr)
    if np.all(p_abs_mrt <= L_arr * (1.0 + tol_dual)):
        sr0 = _shannon_sumrate_bps_hz(H_row, W_mrt, noise_power)
        diag = MultibodyECBFWMMSEDiagnostics(
            lambdas=np.zeros(B),
            p_abs=p_abs_mrt,
            L=L_arr,
            method="mrt-feasible",
            converged=True,
            n_outer=0,
            n_active=0,
            residual=float(np.max(np.maximum(0.0, p_abs_mrt - L_arr) / L_arr, initial=0.0)),
            n_wmmse=0,
            sumrate_history_bps_hz=[sr0],
        )
        return (xp.asarray(W_mrt), diag) if return_diagnostics else xp.asarray(W_mrt)

    # Lowrank decomposition.
    U_arr = D_arr = None
    if lowrank_rank is not None:
        U_arr, D_arr = _decompose_lowrank(Q_arr, lowrank_rank)
    use_lowrank = U_arr is not None

    # Warm-start: cold-starting (u, v) from MRT explodes the rate weights for
    # weak users (small h_k^T w_k_MRT but tiny self-power, so v_k is large
    # and u_k|v_k|^2 grows). The classical Christensen-Shi cure is to run one
    # unweighted MMSE-with-exposure pass first to reach a feasible W, then
    # init (u, v) from that W. We mirror this when uv_init is not provided.
    from aegis.coherent.multibody_ecbf import solve_multibody_ecbf as _solve_mmse_ecbf

    if uv_init is not None:
        u_vec = np.asarray(uv_init[0], dtype=complex).copy()
        v_vec = np.asarray(uv_init[1], dtype=complex).copy()
        if u_vec.shape != (K,) or v_vec.shape != (K,):
            raise ValueError(f"uv_init shapes must be ({K},), got u={u_vec.shape}, v={v_vec.shape}")
        W = W_mrt.copy()
    else:
        # One MMSE-with-exposure pass reaches a feasible (or near-feasible) W,
        # giving sane (u_k, v_k) values for the WMMSE outer loop.
        W_seed, _ = _solve_mmse_ecbf(
            H,
            list(Q_arr),
            L_arr,
            P,
            noise_power=float(noise_power),
            max_outer=max(8, max_outer_dual),
            tol=max(1e-3, tol_dual),
            lambda_init=lambda_init.copy() if lambda_init is not None else None,
            lowrank_rank=lowrank_rank,
            return_diagnostics=True,
        )
        W = np.asarray(W_seed, dtype=complex)
        u_vec, v_vec = _update_uv(H_row, W, noise_power)

    if lambda_init is None:
        lambdas = np.zeros(B)
    else:
        lambdas = np.asarray(lambda_init, dtype=float).copy()
        if lambdas.shape != (B,):
            raise ValueError(f"lambda_init shape {lambdas.shape} != (B={B},)")
        np.maximum(lambdas, 0.0, out=lambdas)

    sumrate_hist: list[float] = []
    converged_outer = False

    n_wmmse = 0
    fallback_triggered = False
    W_best = W.copy()
    sr_best = _shannon_sumrate_bps_hz(H_row, W, noise_power)
    p_abs_best = _per_body_abs_lowrank(W, U_arr, D_arr) if use_lowrank else _per_body_abs(W, Q_arr)
    feasible_best = bool(np.all(p_abs_best <= L_arr * (1.0 + 1e-3)))
    for wmmse_iter in range(max_outer_wmmse):
        n_wmmse = wmmse_iter + 1
        # Build base_mat = H^H diag(u_l |v_l|^2) H and drive G[:,k] = u_k v_k h_k^*.
        # The KKT inner system is
        #     (H^H D H + Q_tot(lambda) + nu I) w_k = u_k v_k h_k^*,
        # with nu the power dual. We enforce ||W||_F^2 = P via 1D bisection
        # on nu inside each fixed-lambda inner solve, then update lambda via
        # the standard dual-Newton ascent. Without bisection, the
        # Frobenius-rescaling shortcut used by the unweighted MMSE solver is
        # numerically unstable here: the rate-weighted Gram H^H D H can be
        # 100x larger than the noise regulariser, sending the unconstrained
        # inverse into the noise subspace.
        weights_uv2 = np.real(u_vec) * (np.abs(v_vec) ** 2)
        weights_uv2 = np.maximum(weights_uv2, 0.0)
        base_mat = (H_row.conj().T * weights_uv2[None, :]) @ H_row  # (M, M)
        drive = H_conj * (u_vec * v_vec)[None, :]  # (M, K)
        nu_floor = max(float(noise_power) * 1e-3, 1e-12)
        nu_ceil = max(float(noise_power) * 1e6, float(np.linalg.norm(base_mat)) + 1.0)

        W, lambdas, p_abs, dual_diag = _wmmse_dual_newton(
            Q_arr=Q_arr,
            base_mat=base_mat,
            drive=drive,
            P=P,
            L_arr=L_arr,
            lambdas=lambdas,
            U_arr=U_arr,
            D_arr=D_arr,
            use_lowrank=use_lowrank,
            max_outer=max_outer_dual,
            tol=tol_dual,
            nu_floor=nu_floor,
            nu_ceil=nu_ceil,
        )

        if dual_diag["fallback"]:
            fallback_triggered = True
            break

        # Sum-rate (with proper nu bisection, ||W||_F^2 = P).
        sr = _shannon_sumrate_bps_hz(H_row, W, noise_power)
        sumrate_hist.append(sr)

        # Track the best feasible iterate. WMMSE is monotone in the surrogate
        # objective but not necessarily in the Shannon sum-rate when the
        # exposure caps cut into the iteration trajectory; keeping the best
        # feasible W defends against pathological iterates.
        feas_now = bool(np.all(p_abs <= L_arr * (1.0 + 1e-3)))
        if feas_now and (not feasible_best or sr > sr_best):
            W_best = W.copy()
            sr_best = sr
            p_abs_best = p_abs.copy()
            feasible_best = True

        # Update (u, v) from new W.
        u_vec_new, v_vec_new = _update_uv(H_row, W, noise_power)

        # Outer convergence check on sum-rate.
        if wmmse_iter >= 1:
            sr_prev = sumrate_hist[-2]
            denom = max(abs(sr_prev), 1e-9)
            rel_delta = abs(sr - sr_prev) / denom
            if rel_delta < tol_wmmse:
                converged_outer = True
                u_vec, v_vec = u_vec_new, v_vec_new
                break

        u_vec, v_vec = u_vec_new, v_vec_new

    # Use the best feasible W if we found one strictly better than the latest.
    if feasible_best and (not fallback_triggered) and sr_best > sr - 1e-9:
        W = W_best
        p_abs = p_abs_best

    # Final state. ALWAYS run primal projection against the full-rank Q
    # so the returned W is feasible by construction, regardless of dual
    # convergence status. Mirrors the multibody_ecbf path.
    p_abs_full = _per_body_abs(W, Q_arr)
    SAFETY = 0.97
    margin = (SAFETY * L_arr) / np.maximum(p_abs_full, 1e-30)
    scale = float(np.sqrt(max(0.0, min(1.0, margin.min()))))

    if fallback_triggered or scale < 1e-3:
        W_fb = _min_absorption_fallback(Q_arr, P, K)
        p_abs_fb = _per_body_abs(W_fb, Q_arr)
        residual = float(np.max(np.maximum(0.0, p_abs_fb - L_arr) / L_arr, initial=0.0))
        warnings.warn(
            f"WMMSE-ECBF: dual blow-up after {n_wmmse} WMMSE iters "
            f"(scale={scale:.3e}); falling back to min-absorption.",
            stacklevel=2,
        )
        diag = MultibodyECBFWMMSEDiagnostics(
            lambdas=lambdas,
            p_abs=p_abs_fb,
            L=L_arr,
            method="min-absorption",
            converged=False,
            n_outer=max_outer_dual,
            n_active=int(np.count_nonzero(lambdas > 0)),
            residual=residual,
            n_wmmse=n_wmmse,
            sumrate_history_bps_hz=sumrate_hist + [_shannon_sumrate_bps_hz(H_row, W_fb, noise_power)],
            final_uv=(u_vec, v_vec),
        )
        return (xp.asarray(W_fb), diag) if return_diagnostics else xp.asarray(W_fb)

    method_final = "multibody-ecbf-wmmse"
    if scale < 1.0 - 1e-9:
        W = W * scale
        p_abs_full = _per_body_abs(W, Q_arr)
        method_final = "multibody-ecbf-wmmse-projected"

    residual = float(np.max(np.maximum(0.0, p_abs_full - L_arr) / L_arr, initial=0.0))
    p_abs = p_abs_full
    diag = MultibodyECBFWMMSEDiagnostics(
        lambdas=lambdas,
        p_abs=p_abs,
        L=L_arr,
        method=method_final,
        converged=converged_outer or (method_final.endswith("projected")),
        n_outer=max_outer_dual,
        n_active=int(np.count_nonzero(lambdas > 0)),
        residual=residual,
        n_wmmse=n_wmmse,
        sumrate_history_bps_hz=sumrate_hist,
        final_uv=(u_vec, v_vec),
    )
    return (xp.asarray(W), diag) if return_diagnostics else xp.asarray(W)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _update_uv(H_row: np.ndarray, W: np.ndarray, sigma2: float) -> tuple[np.ndarray, np.ndarray]:
    """One WMMSE block update of MMSE filters ``v_k`` and rate weights ``u_k``.

    With ``y_k = h_k^T (sum_j w_j s_j) + n_k`` and unit symbol variance,

        v_k = (h_k^T w_k) / (sum_j |h_k^T w_j|^2 + sigma2)
        u_k = 1 / (1 - v_k* h_k^T w_k) = 1 / MSE_k.
    """
    Y = H_row @ W  # (K, K), Y[k, j] = h_k^T w_j
    diag_Y = np.diag(Y).copy()  # (K,) complex
    R = np.sum(np.abs(Y) ** 2, axis=1) + sigma2  # (K,) total received pow + noise
    v = diag_Y / R  # (K,) complex MMSE filter
    mse = np.real(1.0 - np.conj(v) * diag_Y)  # (K,) real positive
    mse = np.maximum(mse, 1e-12)
    u = 1.0 / mse  # (K,) real
    return u.astype(complex), v


def _shannon_sumrate_bps_hz(H_row: np.ndarray, W: np.ndarray, sigma2: float) -> float:
    """Per-stream Shannon SE summed across streams. Treats other streams as Gaussian interference."""
    Y = H_row @ W
    abs2 = np.abs(Y) ** 2
    useful = np.diag(abs2)
    interf = np.sum(abs2, axis=1) - useful + sigma2
    sinr = useful / np.maximum(interf, 1e-30)
    return float(np.sum(np.log2(1.0 + sinr)))


def _solve_W_nu(
    nu: float,
    *,
    base_mat: np.ndarray,
    drive: np.ndarray,
    Q_arr: np.ndarray,
    lambdas: np.ndarray,
    U_arr: np.ndarray | None,
    D_arr: np.ndarray | None,
) -> np.ndarray:
    """Solve (H^H D H + Q_tot(lambda) + nu I) W = drive for fixed nu, no rescale."""
    M = base_mat.shape[0]
    M_lam = base_mat + nu * np.eye(M, dtype=complex)
    if lambdas.size > 0 and np.any(lambdas > 0):
        active = lambdas > 0
        if U_arr is not None:
            idx = np.where(active)[0]
            weights = np.sqrt(lambdas[idx, None] * D_arr[idx])
            V_blocks = U_arr[idx] * weights[:, None, :]
            V = V_blocks.transpose(1, 0, 2).reshape(M, -1)
            M_lam = M_lam + V @ V.conj().T
        else:
            M_lam = M_lam + np.einsum("u,uij->ij", lambdas[active], Q_arr[active])
    try:
        W = np.linalg.solve(M_lam, drive)
    except np.linalg.LinAlgError:
        W = np.linalg.pinv(M_lam) @ drive
    return W


def _bisect_nu_for_power(
    *,
    P: float,
    base_mat: np.ndarray,
    drive: np.ndarray,
    Q_arr: np.ndarray,
    lambdas: np.ndarray,
    U_arr: np.ndarray | None,
    D_arr: np.ndarray | None,
    nu_floor: float,
    nu_ceil: float,
    tol_rel: float = 1e-3,
    max_iter: int = 32,
) -> tuple[np.ndarray, float]:
    """1D bisection on nu so that ||W(nu)||_F^2 = P.

    The map nu -> ||W(nu)||_F^2 is strictly decreasing on (0, ∞), so
    bisection converges to the unique nu that satisfies the power
    constraint. Floor and ceiling are sized in the caller from the
    matrix scale.
    """
    lo, hi = nu_floor, nu_ceil
    # Expand ceiling if needed (W norm at hi still > P).
    for _ in range(8):
        W_hi = _solve_W_nu(hi, base_mat=base_mat, drive=drive, Q_arr=Q_arr, lambdas=lambdas, U_arr=U_arr, D_arr=D_arr)
        if float(np.linalg.norm(W_hi) ** 2) <= P * (1.0 + tol_rel):
            break
        hi *= 4.0
    # Expand floor downward only if at lo we're already below P (means nu
    # is too high; we'd never reach P). Mostly the lo is fine.
    W_lo = _solve_W_nu(lo, base_mat=base_mat, drive=drive, Q_arr=Q_arr, lambdas=lambdas, U_arr=U_arr, D_arr=D_arr)
    if float(np.linalg.norm(W_lo) ** 2) <= P:
        # Even at lo, we're within budget: return lo (most aggressive precoder).
        return W_lo, lo

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        W = _solve_W_nu(mid, base_mat=base_mat, drive=drive, Q_arr=Q_arr, lambdas=lambdas, U_arr=U_arr, D_arr=D_arr)
        norm2 = float(np.linalg.norm(W) ** 2)
        if abs(norm2 - P) / P < tol_rel:
            return W, mid
        if norm2 > P:
            lo = mid
        else:
            hi = mid
    return W, mid


def _wmmse_dual_newton(
    *,
    Q_arr: np.ndarray,
    base_mat: np.ndarray,
    drive: np.ndarray,
    P: float,
    L_arr: np.ndarray,
    lambdas: np.ndarray,
    U_arr: np.ndarray | None,
    D_arr: np.ndarray | None,
    use_lowrank: bool,
    max_outer: int,
    tol: float,
    nu_floor: float,
    nu_ceil: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Dual-Newton ascent on per-body lambda with nu-bisection for power.

    At each Newton step we (i) bisect nu to satisfy ||W||_F^2 = P at the
    current lambda, (ii) measure body-budget gaps at the resulting W,
    (iii) compute a finite-difference Jacobian and Newton step on lambda
    over the active set, projected back to the non-negative orthant.
    """
    fd_step = 1e-5
    info = {"fallback": False, "n_outer": 0, "converged": False}

    for outer_iter in range(max_outer):
        info["n_outer"] = outer_iter + 1
        W, _nu = _bisect_nu_for_power(
            P=P,
            base_mat=base_mat,
            drive=drive,
            Q_arr=Q_arr,
            lambdas=lambdas,
            U_arr=U_arr,
            D_arr=D_arr,
            nu_floor=nu_floor,
            nu_ceil=nu_ceil,
        )
        p_abs = _per_body_abs_lowrank(W, U_arr, D_arr) if use_lowrank else _per_body_abs(W, Q_arr)
        gap = p_abs - L_arr
        rel_viol = np.max(np.maximum(0.0, gap) / L_arr, initial=0.0)
        if rel_viol < tol:
            info["converged"] = True
            return W, lambdas, p_abs, info

        active = (gap > 0) | (lambdas > 0)
        idx = np.where(active)[0]
        if idx.size == 0:
            info["converged"] = True
            return W, lambdas, p_abs, info

        h_step = fd_step * np.maximum(np.abs(lambdas[idx]), 1.0)
        n_active = idx.size
        J = np.zeros((n_active, n_active))
        for v in range(n_active):
            lam_p = lambdas.copy()
            lam_p[idx[v]] = lambdas[idx[v]] + h_step[v]
            W_p, _ = _bisect_nu_for_power(
                P=P,
                base_mat=base_mat,
                drive=drive,
                Q_arr=Q_arr,
                lambdas=lam_p,
                U_arr=U_arr,
                D_arr=D_arr,
                nu_floor=nu_floor,
                nu_ceil=nu_ceil,
            )
            p_p = _per_body_abs_lowrank(W_p, U_arr, D_arr) if use_lowrank else _per_body_abs(W_p, Q_arr)
            J[:, v] = (p_p[idx] - p_abs[idx]) / h_step[v]
        gap_active = gap[idx]
        try:
            delta = np.linalg.solve(-J + 1e-12 * np.eye(n_active), gap_active)
        except np.linalg.LinAlgError:
            delta = gap_active.copy()

        max_decrease = lambdas[idx]
        step_scale = 1.0
        too_negative = (delta < -max_decrease) & (max_decrease > 0)
        if np.any(too_negative):
            ratios = -max_decrease[too_negative] / delta[too_negative]
            step_scale = float(min(1.0, ratios.min() * 0.99))
        new_lambdas = lambdas.copy()
        new_lambdas[idx] = np.maximum(0.0, lambdas[idx] + step_scale * delta)
        denom = np.maximum(np.abs(lambdas), 1.0)
        rel_change = float(np.max(np.abs(new_lambdas - lambdas) / denom, initial=0.0))
        lambdas = new_lambdas
        if rel_change < tol and rel_viol < 10 * tol:
            info["converged"] = True
            return W, lambdas, p_abs, info

    # Out of inner iters: build final W and check residual.
    W, _ = _bisect_nu_for_power(
        P=P,
        base_mat=base_mat,
        drive=drive,
        Q_arr=Q_arr,
        lambdas=lambdas,
        U_arr=U_arr,
        D_arr=D_arr,
        nu_floor=nu_floor,
        nu_ceil=nu_ceil,
    )
    p_abs = _per_body_abs_lowrank(W, U_arr, D_arr) if use_lowrank else _per_body_abs(W, Q_arr)
    residual = float(np.max(np.maximum(0.0, p_abs - L_arr) / L_arr, initial=0.0))
    if residual > 1e-3:
        info["fallback"] = True
    return W, lambdas, p_abs, info


def _dual_newton_ecbf(
    *,
    Q_arr: np.ndarray,
    base_mat: np.ndarray,
    drive: np.ndarray,
    P: float,
    L_arr: np.ndarray,
    lambdas: np.ndarray,
    I_scale: float,
    U_arr: np.ndarray | None,
    D_arr: np.ndarray | None,
    use_lowrank: bool,
    max_outer: int,
    tol: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Inner dual-Newton ascent on per-body Lagrange multipliers.

    Same scaffold as ``multibody_ecbf.solve_multibody_ecbf`` (Newton on the
    dual residual ``F_u(lambda) = p_abs_u - L_u`` with active-set tracking
    and damped non-negative projection), but parametrised by an arbitrary
    ``base_mat`` and per-stream ``drive`` so the WMMSE outer can supply
    its own H_intf and ``g_k = u_k v_k h_k^*``.

    Returns ``(W, lambdas, p_abs, info)`` with ``info["fallback"]`` set
    when the residual still exceeds 1e-3 after ``max_outer`` steps.
    """
    fd_step = 1e-5
    Q_arr.shape[0]
    info = {"fallback": False, "n_outer": 0, "converged": False}

    for outer_iter in range(max_outer):
        info["n_outer"] = outer_iter + 1
        W, _ = _solve_W_factored(
            lambdas,
            Q_arr,
            drive,
            P,
            base_mat=base_mat,
            I_scale=I_scale,  # base_mat already includes H^H D H + sigma I via callers if desired
            U_arr=U_arr,
            D_arr=D_arr,
        )
        p_abs = _per_body_abs_lowrank(W, U_arr, D_arr) if use_lowrank else _per_body_abs(W, Q_arr)
        gap = p_abs - L_arr
        rel_viol = np.max(np.maximum(0.0, gap) / L_arr, initial=0.0)
        if rel_viol < tol:
            info["converged"] = True
            return W, lambdas, p_abs, info

        active = (gap > 0) | (lambdas > 0)
        idx = np.where(active)[0]
        if idx.size == 0:
            info["converged"] = True
            return W, lambdas, p_abs, info

        h_step = fd_step * np.maximum(np.abs(lambdas[idx]), 1.0)
        n_active = idx.size
        J = np.zeros((n_active, n_active))
        for v in range(n_active):
            lam_p = lambdas.copy()
            lam_p[idx[v]] = lambdas[idx[v]] + h_step[v]
            W_p, _ = _solve_W_factored(
                lam_p,
                Q_arr,
                drive,
                P,
                base_mat=base_mat,
                I_scale=0.0,
                U_arr=U_arr,
                D_arr=D_arr,
            )
            p_p = _per_body_abs_lowrank(W_p, U_arr, D_arr) if use_lowrank else _per_body_abs(W_p, Q_arr)
            J[:, v] = (p_p[idx] - p_abs[idx]) / h_step[v]
        gap_active = gap[idx]
        try:
            delta = np.linalg.solve(-J + 1e-12 * np.eye(n_active), gap_active)
        except np.linalg.LinAlgError:
            delta = gap_active.copy()

        max_decrease = lambdas[idx]
        step_scale = 1.0
        too_negative = (delta < -max_decrease) & (max_decrease > 0)
        if np.any(too_negative):
            ratios = -max_decrease[too_negative] / delta[too_negative]
            step_scale = float(min(1.0, ratios.min() * 0.99))
        new_lambdas = lambdas.copy()
        new_lambdas[idx] = np.maximum(0.0, lambdas[idx] + step_scale * delta)
        denom = np.maximum(np.abs(lambdas), 1.0)
        rel_change = float(np.max(np.abs(new_lambdas - lambdas) / denom, initial=0.0))
        lambdas = new_lambdas
        if rel_change < tol and rel_viol < 10 * tol:
            info["converged"] = True
            return W, lambdas, p_abs, info

    # Out of inner iters: build final W and check residual.
    W, _ = _solve_W_factored(
        lambdas,
        Q_arr,
        drive,
        P,
        base_mat=base_mat,
        I_scale=0.0,
        U_arr=U_arr,
        D_arr=D_arr,
    )
    p_abs = _per_body_abs_lowrank(W, U_arr, D_arr) if use_lowrank else _per_body_abs(W, Q_arr)
    residual = float(np.max(np.maximum(0.0, p_abs - L_arr) / L_arr, initial=0.0))
    if residual > 1e-3:
        info["fallback"] = True
    return W, lambdas, p_abs, info
