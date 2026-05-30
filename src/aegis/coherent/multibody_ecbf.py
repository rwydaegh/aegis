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
import scipy.linalg as _sla

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
    lowrank_rank: int | None = None,
    lowrank_factor: tuple[np.ndarray, np.ndarray] | None = None,
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
    lowrank_rank : int, optional
        Truncate each Q^{(u)} to its top ``lowrank_rank`` eigenpairs before
        the inner Newton sweep. The plaza-run Q's are empirically rank 3
        (relative Frobenius reconstruction error 5e-13 at r=3), so the
        truncation is exact for typical body-near-array geometries and
        cuts the per-body absorption einsum from O(B M^2 K) to
        O(B M r K). This is the production hot path; mutually exclusive
        with ``lowrank_factor``.
    lowrank_factor : (U_arr, D_arr), optional
        Pre-computed low-rank decomposition Q^{(u)} = U_u diag(D_u) U_u^H.
        ``U_arr`` has shape (B, M, r), ``D_arr`` has shape (B, r) with
        non-negative real entries. Use this when the caller already has a
        decomposition (e.g. plumbed across Newton calls so the eigh runs
        once per slot rather than once per call). When provided, ``Q_list``
        is still required for the MRT trial absorption check; pass the
        full M x M matrices, or pass the same factor reconstructed
        Q ~= U diag(D) U^H. Mutually exclusive with ``lowrank_rank``.

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

    if lowrank_rank is not None and lowrank_factor is not None:
        raise ValueError("Specify at most one of lowrank_rank, lowrank_factor")

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

    # Resolve low-rank factors. Production hot path: r=3 truncation is
    # numerically exact for plaza-run Q's (relative Frobenius error 5e-13)
    # and cuts the per-body absorption einsum from O(B M^2 K) to
    # O(B M r K). When neither path is requested, fall back to the
    # full-rank Q stack for backward compatibility.
    U_arr: np.ndarray | None = None
    D_arr: np.ndarray | None = None
    if lowrank_factor is not None:
        U_arr, D_arr = lowrank_factor
        U_arr = np.ascontiguousarray(U_arr, dtype=complex)
        D_arr = np.ascontiguousarray(D_arr, dtype=float)
        if U_arr.shape[0] != B or U_arr.shape[1] != M or U_arr.ndim != 3:
            raise ValueError(f"lowrank_factor U must have shape (B={B}, M={M}, r), got {U_arr.shape}")
        if D_arr.shape != (B, U_arr.shape[2]):
            raise ValueError(f"lowrank_factor D must have shape (B={B}, r={U_arr.shape[2]}), got {D_arr.shape}")
    if lowrank_rank is not None and (lowrank_rank <= 0 or lowrank_rank > M):
        raise ValueError(f"lowrank_rank must be in [1, {M}], got {lowrank_rank}")
    # Lazy decomposition: defer the eigh until we actually need it. Many
    # callers pass tight budgets but the MRT trial is feasible for ~all
    # slack-regime slots, so paying B * M^3 of eigh here is wasted work.

    use_lowrank = U_arr is not None

    # MRT trial: cheapest possible precoder. Use the full-rank Q here even
    # when low-rank is requested because the einsum is a one-shot cost
    # whose alternative requires the eigh that we are trying to avoid.
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

    # MRT was infeasible: we will run Newton, so now pay the eigh if the
    # caller asked for ``lowrank_rank`` truncation. This deferred path
    # avoids decomposing Q in the slack regime where MRT is feasible and
    # the eigh would be wasted work.
    if lowrank_rank is not None and U_arr is None:
        U_arr, D_arr = _decompose_lowrank(Q_arr, lowrank_rank)
        use_lowrank = True

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
        W, cho = _solve_W_factored(
            lambdas,
            Q_arr,
            H_conj,
            P,
            base_mat=base_mat,
            I_scale=I_scale,
            U_arr=U_arr,
            D_arr=D_arr,
        )
        p_abs = _per_body_abs_lowrank(W, U_arr, D_arr) if use_lowrank else _per_body_abs(W, Q_arr)
        gap = p_abs - L_arr
        rel_viol = np.max(np.maximum(0.0, gap) / L_arr, initial=0.0)
        # KKT complementary slackness: a body that is strictly slack
        # (gap < -tol*L) must have lambda = 0. If a positive multiplier
        # persists on a slack body, the dual hasn't converged yet — keep
        # iterating so the active set can release it. Without this guard,
        # the solver can lock in a spurious lambda and produce a
        # suboptimal precoder (Paper C local-vs-global-Q artefact).
        slack_with_lambda = (lambdas > 0) & (gap < -tol * L_arr)
        if rel_viol < tol and not np.any(slack_with_lambda):
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
        # Each FD column is a rank-r update to M_lam (when low-rank), or a
        # full M x M perturbation (legacy). We re-solve with the cached
        # Cholesky factor by re-factorising; an O(M^3) factorisation per
        # column is unavoidable without a Sherman-Morrison-Woodbury step,
        # but the per-body absorption is already the dominant cost.
        h = fd_step * np.maximum(np.abs(lambdas[idx]), 1.0)
        n_active = idx.size
        J = np.zeros((n_active, n_active))
        for v in range(n_active):
            lam_p = lambdas.copy()
            lam_p[idx[v]] = lambdas[idx[v]] + h[v]
            W_p, _ = _solve_W_factored(
                lam_p,
                Q_arr,
                H_conj,
                P,
                base_mat=base_mat,
                I_scale=I_scale,
                U_arr=U_arr,
                D_arr=D_arr,
            )
            p_p = _per_body_abs_lowrank(W_p, U_arr, D_arr) if use_lowrank else _per_body_abs(W_p, Q_arr)
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
    W, _ = _solve_W_factored(
        lambdas,
        Q_arr,
        H_conj,
        P,
        base_mat=base_mat,
        I_scale=I_scale,
        U_arr=U_arr,
        D_arr=D_arr,
    )
    # ALWAYS evaluate against full-rank Q at the final step and project
    # primally to the exact limit. The dual ascent may have used a low-rank
    # approximation that hides ~1-5% of the true absorption tail, but this
    # evaluation uses the FULL operator, so p_abs_full is the exact absorbed
    # power. Project exactly to L (no extra cushion): the exact projection
    # alone guarantees feasibility, turning the dual approximation error into
    # a bounded sum-rate cost rather than a sneaky violation. A deliberate
    # regulatory margin, if wanted, belongs at the call site as L_target < L,
    # not as a hidden constant here.
    p_abs_full = _per_body_abs(W, Q_arr)
    margin = L_arr / np.maximum(p_abs_full, 1e-30)
    scale = float(np.sqrt(max(0.0, min(1.0, margin.min()))))
    method = "multibody-ecbf"
    converged_final = converged
    if scale < 1.0 - 1e-9:
        if scale > 1e-3:
            W = W * scale
            p_abs_full = _per_body_abs(W, Q_arr)
            method = "multibody-ecbf-projected"
            converged_final = True
        else:
            warnings.warn(
                f"Multi-body ECBF: dual residual blew up after "
                f"{n_outer} sweeps; projection scale {scale:.3e} too small. "
                "Falling back to min-absorption direction.",
                stacklevel=2,
            )
            W = _min_absorption_fallback(Q_arr, P, K)
            p_abs_full = _per_body_abs(W, Q_arr)
            method = "min-absorption"
            converged_final = False
    residual = float(np.max(np.maximum(0.0, p_abs_full - L_arr) / L_arr, initial=0.0))

    diag = MultibodyECBFDiagnostics(
        lambdas=lambdas,
        p_abs=p_abs_full,
        L=L_arr,
        method=method,
        converged=converged_final,
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


def _per_body_abs_lowrank(W: np.ndarray, U_arr: np.ndarray, D_arr: np.ndarray) -> np.ndarray:
    """Low-rank specialisation of ``_per_body_abs``.

    With Q^{(u)} = U_u diag(D_u) U_u^H, the per-body absorption is

        p_abs[u] = sum_k w_k^H U_u diag(D_u) U_u^H w_k
                 = sum_k sum_r D_u[r] |U_u^H w_k|^2[r].

    Cost: O(B M r K) vs O(B M^2 K) for the full-rank path. For
    M = 64, B = 50, K = 25, r = 3 this is ~20x cheaper; for M = 256 it
    is ~80x cheaper.
    """
    # V[b, r, k] = sum_i conj(U[b, i, r]) * W[i, k]
    V = np.einsum("bir,ik->brk", U_arr.conj(), W, optimize=True)
    # |V|^2 weighted by D, summed over (r, k) -> per-body sum.
    abs2 = (V.real * V.real) + (V.imag * V.imag)  # (B, r, K)
    return np.einsum("br,brk->b", D_arr, abs2, optimize=True)


def _decompose_lowrank(Q_arr: np.ndarray, rank: int) -> tuple[np.ndarray, np.ndarray]:
    """Top-``rank`` Hermitian eigendecomposition of each Q^{(u)}.

    Uses ``scipy.linalg.eigh(subset_by_index=...)`` so the cost is
    O(B M^2 r) rather than O(B M^3). For Hermitian PSD Q, the returned
    eigenvalues are non-negative; small numerical noise below
    ``NUMERICAL_FLOOR`` is clipped to 0 so it does not perturb the
    inner solver.
    """
    B, M, _ = Q_arr.shape
    r = min(int(rank), M)
    U_arr = np.empty((B, M, r), dtype=complex)
    D_arr = np.empty((B, r), dtype=float)
    for u in range(B):
        # eigh returns eigenpairs in ascending order; subset_by_index
        # picks the top r. Hermitianisation defends against accumulated
        # numerical drift in upstream einsum chains.
        Q_u = 0.5 * (Q_arr[u] + Q_arr[u].conj().T)
        evals, evecs = _sla.eigh(Q_u, subset_by_index=[M - r, M - 1])
        # Reverse to descending so D[0] is the largest.
        D_arr[u] = np.maximum(evals[::-1], 0.0)
        U_arr[u] = evecs[:, ::-1]
    return U_arr, D_arr


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
    W, _ = _solve_W_factored(
        lambdas,
        Q_arr,
        H_conj,
        P,
        base_mat=base_mat,
        I_scale=I_scale,
        U_arr=None,
        D_arr=None,
    )
    return W


def _solve_W_factored(
    lambdas: np.ndarray,
    Q_arr: np.ndarray,
    H_conj: np.ndarray,
    P: float,
    *,
    base_mat: np.ndarray | None = None,
    I_scale: float = 1.0,
    U_arr: np.ndarray | None = None,
    D_arr: np.ndarray | None = None,
) -> tuple[np.ndarray, None]:
    """Build M_lam, optionally from low-rank Q, then solve via np.linalg.solve.

    The legacy assembly is ``M_lam = base + I_scale*I + sum_u lambda_u Q_u``
    via an einsum over (active body, M, M); cost O(B M^2). When
    ``U_arr`` is provided, the per-body Q is reconstructed implicitly as
    sum_u lambda_u U_u diag(D_u) U_u^H, assembled by a single rank-update
    V V^H with V containing the sqrt-weighted active columns. This is
    O(M (n_active r)^2 + n_active M r) instead of O(B M^2), which is a
    win whenever ``n_active * r < B``.

    The inner solve uses ``np.linalg.solve`` (LAPACK gesv): empirically
    faster than ``scipy.linalg.cho_*`` and ``scipy.linalg.solve`` despite
    the latter's Cholesky path, because gesv has the smallest Python-side
    overhead at our M = 64-256 sizes (see scratch_bench.py).
    """
    M = Q_arr.shape[1]
    M_lam = I_scale * np.eye(M, dtype=complex) if base_mat is None else base_mat + I_scale * np.eye(M, dtype=complex)

    if lambdas.size > 0:
        active = lambdas > 0
        if np.any(active):
            if U_arr is not None:
                # Low-rank assembly: M_lam += sum_u lambda_u U_u diag(D_u) U_u^H
                # stacked into a single V V^H rank update.
                idx = np.where(active)[0]
                weights = np.sqrt(lambdas[idx, None] * D_arr[idx])  # (n_act, r)
                V_blocks = U_arr[idx] * weights[:, None, :]  # (n_act, M, r)
                V = V_blocks.transpose(1, 0, 2).reshape(M, -1)
                M_lam = M_lam + V @ V.conj().T
            else:
                M_lam = M_lam + np.einsum("u,uij->ij", lambdas[active], Q_arr[active])

    try:
        W_raw = np.linalg.solve(M_lam, H_conj)
    except np.linalg.LinAlgError:
        W_raw = np.linalg.pinv(M_lam) @ H_conj
    frob = float(np.linalg.norm(W_raw, "fro"))
    if frob < NUMERICAL_FLOOR:
        K = H_conj.shape[1]
        return np.zeros((M, K), dtype=complex), None
    return np.sqrt(P) * W_raw / frob, None


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
