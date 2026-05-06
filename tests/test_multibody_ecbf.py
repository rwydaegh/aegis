"""Tests for the multi-body exposure-constrained beamforming solver.

Covers the four sanity tests requested by the JSAC brief:

    Sanity 1 - rank-1 limit (B=K=1) agrees with single-body ECBF.
    Sanity 2 - inactive budgets reproduce MRT.
    Sanity 3 - rank-1 hard-null limit agrees with regularised ZF.
    Smoke    - K=4, B=2, M=16 active-budget scenario beats worst-case
               back-off and ZF-with-exposure on sum-rate.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.testing import assert_allclose

from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.multibody_ecbf import (
    MultibodyECBFDiagnostics,
    solve_multibody_ecbf,
)
from aegis.mimo.precoders import (
    compute_precoder,
    mrt,
    multibody_ecbf,
    zf_exposure,
)


def _rand_complex(rng, *shape):
    return (rng.standard_normal(shape) + 1j * rng.standard_normal(shape)) / np.sqrt(2)


def _rand_psd(rng, M, scale=1.0):
    """Random Hermitian PSD matrix with trace ~ scale * M."""
    A = _rand_complex(rng, M, M)
    Q = A.conj().T @ A
    return scale * Q / np.trace(Q).real * M


def _per_body_abs(W, Q_list):
    return np.array([float(np.real(np.trace(W.conj().T @ Q @ W))) for Q in Q_list])


def _frob_sq(W):
    return float(np.real(np.trace(W.conj().T @ W)))


def _sum_rate(W, H, sigma2):
    HW = H @ W  # (K, K)
    sigp = np.abs(np.diag(HW)) ** 2
    total = np.sum(np.abs(HW) ** 2, axis=1)
    interf = total - sigp
    sinr = sigp / (interf + sigma2)
    return float(np.sum(np.log2(1.0 + sinr)))


def _direction_align(a, b):
    """|<a, b>| / (||a|| ||b||) - 1, modulo global phase."""
    num = abs(np.vdot(a, b))
    den = np.linalg.norm(a) * np.linalg.norm(b)
    if den < 1e-30:
        return 0.0
    return float(num / den)


# ---------------------------------------------------------------------------
# Sanity 1 - B=1 K=1 agrees with single-body ECBF.
# ---------------------------------------------------------------------------


class TestSanityRankOneLimit:
    @pytest.mark.parametrize("seed", [11, 22, 33, 44])
    def test_agrees_with_single_body_ecbf(self, seed):
        rng = np.random.default_rng(seed)
        M = 8
        h = _rand_complex(rng, M)
        # Rank-1 (or near rank-1) Q so the single-body solver does not
        # enter its power-slack regime; both implementations then
        # parametrise the same family x(lambda) = (lambda Q + I)^{-1} h*.
        a = _rand_complex(rng, M)
        Q = np.outer(a, a.conj())
        # Force MRT to overshoot so the constraint is active.
        x_mrt = np.sqrt(1.0) * h.conj() / np.linalg.norm(h)
        p_abs_mrt = float(np.real(np.vdot(x_mrt, Q @ x_mrt)))
        L = 0.25 * p_abs_mrt
        P = 1.0

        x_single = np.asarray(solve_ecbf(h, Q, P_abs_max=L, P=P))
        W_multi = solve_multibody_ecbf(h.reshape(1, -1), [Q], [L], P=P)
        x_multi = np.asarray(W_multi)[:, 0]

        # Match in direction up to global phase, and in power.
        assert_allclose(
            np.abs(np.vdot(x_single, x_multi)), np.linalg.norm(x_single) * np.linalg.norm(x_multi), rtol=1e-6, atol=1e-8
        )
        assert_allclose(_frob_sq(W_multi), float(np.real(np.vdot(x_single, x_single))), rtol=1e-6, atol=1e-8)

    def test_diagnostics_reports_active_budget(self):
        rng = np.random.default_rng(7)
        M = 6
        h = _rand_complex(rng, M)
        a = _rand_complex(rng, M)
        Q = np.outer(a, a.conj())
        x_mrt = h.conj() / np.linalg.norm(h)
        L = 0.1 * float(np.real(np.vdot(x_mrt, Q @ x_mrt)))

        W, diag = solve_multibody_ecbf(h.reshape(1, -1), [Q], [L], P=1.0, return_diagnostics=True)
        assert isinstance(diag, MultibodyECBFDiagnostics)
        assert diag.method == "multibody-ecbf"
        assert diag.n_active == 1
        assert diag.lambdas[0] > 0
        # Body absorbed power should sit at the budget.
        assert_allclose(diag.p_abs[0], L, rtol=1e-6, atol=1e-8)


# ---------------------------------------------------------------------------
# Sanity 2 - inactive budgets reproduce MRT.
# ---------------------------------------------------------------------------


class TestSanityInactiveBudgets:
    @pytest.mark.parametrize(("K", "M"), [(1, 8), (3, 16), (4, 32)])
    def test_huge_budgets_match_mrt(self, K, M):
        rng = np.random.default_rng(100 + K)
        H = _rand_complex(rng, K, M)
        Q_list = [_rand_psd(rng, M, scale=1.0) for _ in range(3)]
        # Budgets several orders of magnitude above MRT absorption.
        W_mrt = mrt(H, P=1.0)
        p_abs_mrt = _per_body_abs(W_mrt, Q_list)
        L = (p_abs_mrt + 1.0) * 1e6

        W, diag = solve_multibody_ecbf(H, Q_list, list(L), P=1.0, return_diagnostics=True)
        assert diag.method == "mrt-feasible"
        assert diag.n_active == 0
        assert_allclose(np.asarray(W), W_mrt, atol=1e-12)


# ---------------------------------------------------------------------------
# Sanity 3 - rank-1 limit, regularised ZF.
# ---------------------------------------------------------------------------


class TestSanityRegularisedZFLimit:
    """The paper's Proposition 1: rank-1 body operators recover regularised ZF.

    With Q^{(j)} = h_j h_j^H and sufficiently small budgets, the closed-form
    solution w_k = (sum_j lambda_j h_j h_j^H + I)^{-1} h_k* coincides
    column-wise with the regularised ZF precoder W_rzf = H^H (HH^H + alpha I)^{-1}
    (after Frobenius re-normalisation), with alpha = 1 / lambda when the
    multipliers are equal.
    """

    def _setup(self, seed, K, M, lam_target):
        rng = np.random.default_rng(seed)
        H = _rand_complex(rng, K, M)
        Q_list = [np.outer(H[k].conj(), H[k]) for k in range(K)]
        # Build the precoder we expect for lam_target on every body.
        M_lam = lam_target * sum(Q_list) + np.eye(M, dtype=complex)
        W_raw = np.linalg.solve(M_lam, H.conj().T)
        frob = float(np.linalg.norm(W_raw, "fro"))
        W_target = np.sqrt(1.0) * W_raw / frob
        # The per-body budget consistent with this lambda_target.
        L = _per_body_abs(W_target, Q_list)
        return H, Q_list, L, W_target

    @pytest.mark.parametrize(
        ("seed", "K", "M", "lam_target"),
        [(101, 2, 8, 5.0), (102, 3, 16, 50.0), (103, 4, 16, 200.0)],
    )
    def test_solver_recovers_target_lambda(self, seed, K, M, lam_target):
        H, Q_list, L, W_target = self._setup(seed, K, M, lam_target)

        W, diag = solve_multibody_ecbf(H, Q_list, L, P=1.0, return_diagnostics=True, max_outer=80)
        assert diag.method == "multibody-ecbf"
        # All bodies should be active (binding) and their lambdas close to
        # the symmetric target. The Newton ascent breaks perfect symmetry
        # below machine precision, so allow a small relative tolerance.
        assert np.all(diag.lambdas > 0)
        for lam in diag.lambdas:
            assert_allclose(lam, lam_target, rtol=0.05)
        # Direction match column-by-column (up to global phase).
        for k in range(K):
            assert _direction_align(np.asarray(W)[:, k], W_target[:, k]) > 1.0 - 1e-4

    def test_bystander_nulls_emerge_as_budgets_shrink(self):
        """Proposition 1: rank-1 bystander operators with vanishing budgets
        force the precoder into the null space of the bystander steering
        vectors, while the served users' signals stay finite.
        """
        rng = np.random.default_rng(203)
        K, B, M = 2, 2, 16
        H = _rand_complex(rng, K, M)
        # Bystanders are distinct from users.
        A = _rand_complex(rng, B, M)
        Q_list = [np.outer(A[b].conj(), A[b]) for b in range(B)]

        W_loose = np.asarray(solve_multibody_ecbf(H, Q_list, [10.0] * B, P=1.0))
        W_tight = np.asarray(solve_multibody_ecbf(H, Q_list, [1e-3] * B, P=1.0))

        # Bystander absorption shrinks proportional to budget.
        p_abs_loose = _per_body_abs(W_loose, Q_list)
        p_abs_tight = _per_body_abs(W_tight, Q_list)
        for b in range(B):
            assert p_abs_tight[b] <= 1e-3 * (1.0 + 1e-6)
            assert p_abs_tight[b] < p_abs_loose[b]

        # Served-user signal does not collapse to zero (bystanders are not
        # aligned with users), so |h_k^H w_k|^2 stays a finite fraction of
        # power. This is what distinguishes ZF-against-bystanders from the
        # degenerate "null everything" case.
        sig_tight = np.abs(np.diag(H @ W_tight)) ** 2
        assert np.all(sig_tight > 1e-3 * (np.linalg.norm(H, axis=1) ** 2).min())


# ---------------------------------------------------------------------------
# Smoke - K=4, B=2 active scenario.
# ---------------------------------------------------------------------------


class TestSmokeMultibody:
    def _build(self, seed=2024):
        rng = np.random.default_rng(seed)
        K, B, M = 4, 2, 16
        H = _rand_complex(rng, K, M)
        Q_list = [_rand_psd(rng, M, scale=1.0) for _ in range(B)]
        # Budgets force a non-trivial precoder but stay above the
        # joint-spectrum infeasibility floor: 50% of MRT absorption.
        W_mrt = mrt(H, P=1.0)
        p_abs_mrt = _per_body_abs(W_mrt, Q_list)
        L = list(0.5 * p_abs_mrt)
        return H, Q_list, L

    def test_satisfies_all_budgets(self):
        H, Q_list, L = self._build(seed=2024)
        W, diag = solve_multibody_ecbf(H, Q_list, L, P=1.0, return_diagnostics=True)
        p_abs = _per_body_abs(np.asarray(W), Q_list)
        # Hard satisfaction (numerical wiggle room).
        for u, (p, lim) in enumerate(zip(p_abs, L, strict=True)):
            assert p <= lim * (1.0 + 1e-6), f"body {u}: p_abs={p} > L={lim}"
        assert diag.method == "multibody-ecbf"
        assert diag.residual < 1e-6

    def test_total_power(self):
        H, Q_list, L = self._build(seed=2024)
        # Frobenius normalisation is enforced even when the budget is
        # infeasible at the higher P (the min-absorption fallback also
        # returns ||W||_F^2 = P), so the warning is expected.
        with pytest.warns(UserWarning, match="Multi-body ECBF: residual"):
            W = np.asarray(solve_multibody_ecbf(H, Q_list, L, P=2.5))
        assert_allclose(_frob_sq(W), 2.5, rtol=1e-8, atol=1e-10)

    def test_beats_mrt_backoff(self):
        """Compare achievable sum-rate vs. MRT scaled to satisfy budgets.

        Uses the MMSE-with-exposure inner (noise_power set), which is
        what gives the multi-body solver its sum-rate advantage over the
        worst-case-back-off baseline.
        """
        H, Q_list, L = self._build(seed=2024)
        sigma2 = 1e-2
        P = 1.0

        W_mb = np.asarray(solve_multibody_ecbf(H, Q_list, L, P=P, noise_power=sigma2))
        W_mrt = mrt(H, P=P)

        # Worst-case back-off baseline: scale MRT down until every body's
        # absorbed power is within budget.
        p_abs_mrt = _per_body_abs(W_mrt, Q_list)
        scale_sq = min(L[u] / p_abs_mrt[u] for u in range(len(Q_list)))
        scale_sq = min(scale_sq, 1.0)
        W_mrt_backoff = W_mrt * np.sqrt(scale_sq)

        sr_mb = _sum_rate(W_mb, H, sigma2)
        sr_backoff = _sum_rate(W_mrt_backoff, H, sigma2)

        assert sr_mb > sr_backoff, f"multi-body sum-rate {sr_mb:.3f} not above MRT-backoff {sr_backoff:.3f}"

    def test_beats_zf_exposure(self):
        H, Q_list, L = self._build(seed=2024)
        # zf_exposure uses a single P_abs_max budget; pick the tightest body.
        P_abs_max = float(min(L))
        sigma2 = 1e-2
        P = 1.0

        W_mb = np.asarray(solve_multibody_ecbf(H, Q_list, L, P=P, noise_power=sigma2))
        W_zfe = zf_exposure(H, Q_list, P_abs_max=P_abs_max, P=P)

        sr_mb = _sum_rate(W_mb, H, sigma2)
        sr_zfe = _sum_rate(W_zfe, H, sigma2)

        # Multi-body beats the conservative zf_exposure on sum-rate.
        assert sr_mb > sr_zfe


# ---------------------------------------------------------------------------
# API plumbing.
# ---------------------------------------------------------------------------


class TestPrecoderDispatch:
    def test_compute_precoder_dispatches(self):
        rng = np.random.default_rng(909)
        K, M = 2, 8
        H = _rand_complex(rng, K, M)
        Q_list = [_rand_psd(rng, M) for _ in range(2)]
        W_ref = solve_multibody_ecbf(H, Q_list, [1.0, 1.0], P=1.0)
        W_dispatch = compute_precoder(
            H,
            precoder_type="multibody_ecbf",
            P=1.0,
            Q_list=Q_list,
            L_list=[1.0, 1.0],
        )
        assert_allclose(np.asarray(W_dispatch), np.asarray(W_ref), atol=1e-12)

    def test_compute_precoder_accepts_scalar_pabsmax(self):
        rng = np.random.default_rng(910)
        K, M = 2, 8
        H = _rand_complex(rng, K, M)
        Q_list = [_rand_psd(rng, M) for _ in range(3)]
        # P_abs_max broadcasts to one budget per body.
        W = compute_precoder(
            H,
            precoder_type="multibody_ecbf",
            P=1.0,
            Q_list=Q_list,
            P_abs_max=2.0,
        )
        p_abs = _per_body_abs(np.asarray(W), Q_list)
        assert np.all(p_abs <= 2.0 * (1.0 + 1e-8))

    def test_compute_precoder_missing_qlist_raises(self):
        H = np.eye(2, dtype=complex)
        with pytest.raises(ValueError, match="multibody_ecbf requires Q_list"):
            compute_precoder(H, precoder_type="multibody_ecbf")

    def test_compute_precoder_missing_budgets_raises(self):
        rng = np.random.default_rng(911)
        H = _rand_complex(rng, 2, 4)
        Q_list = [_rand_psd(rng, 4)]
        with pytest.raises(ValueError, match="L_list .* or P_abs_max"):
            compute_precoder(H, precoder_type="multibody_ecbf", Q_list=Q_list)

    def test_module_level_alias(self):
        rng = np.random.default_rng(912)
        H = _rand_complex(rng, 2, 8)
        Q_list = [_rand_psd(rng, 8), _rand_psd(rng, 8)]
        L = [0.5, 0.5]
        W = multibody_ecbf(H, Q_list, L, P=1.0)
        assert W.shape == (8, 2)


class TestWarmStart:
    """Warm-starting lambda from a previous call cuts iteration count."""

    def _build_active(self, seed=2026):
        rng = np.random.default_rng(seed)
        K, B, M = 4, 3, 16
        H = _rand_complex(rng, K, M)
        Q_list = [_rand_psd(rng, M, scale=1.0) for _ in range(B)]
        # Tight enough to give an active set, loose enough to stay feasible.
        W_mrt = mrt(H, P=1.0)
        p_abs_mrt = _per_body_abs(W_mrt, Q_list)
        L = list(0.6 * p_abs_mrt)
        return H, Q_list, L

    def test_warmstart_matches_cold(self):
        """Warm-start from the cold-solve lambdas reproduces the same W to
        machine precision and converges in ~one outer iteration."""
        H, Q_list, L = self._build_active()
        W_cold, diag_cold = solve_multibody_ecbf(H, Q_list, L, P=1.0, return_diagnostics=True)
        W_warm, diag_warm = solve_multibody_ecbf(
            H,
            Q_list,
            L,
            P=1.0,
            return_diagnostics=True,
            lambda_init=diag_cold.lambdas,
        )
        assert_allclose(np.asarray(W_warm), np.asarray(W_cold), atol=1e-9)
        assert diag_warm.n_outer < diag_cold.n_outer
        assert diag_warm.n_outer <= 2

    def test_warmstart_clips_negative(self):
        """Negative entries in lambda_init are clipped to 0 silently."""
        H, Q_list, L = self._build_active()
        bad_init = np.array([-0.5, 0.0, 1.0])
        W, diag = solve_multibody_ecbf(
            H,
            Q_list,
            L,
            P=1.0,
            return_diagnostics=True,
            lambda_init=bad_init,
        )
        # Solver still converges and respects budgets.
        p_abs = _per_body_abs(np.asarray(W), Q_list)
        for u, (p, lim) in enumerate(zip(p_abs, L, strict=True)):
            assert p <= lim * (1.0 + 1e-6), f"body {u}: p_abs={p} > L={lim}"

    def test_warmstart_shape_mismatch_raises(self):
        H, Q_list, L = self._build_active()
        with pytest.raises(ValueError, match="lambda_init must have shape"):
            solve_multibody_ecbf(H, Q_list, L, P=1.0, lambda_init=np.zeros(7))


# ---------------------------------------------------------------------------
# Input validation.
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_negative_budget_raises(self):
        rng = np.random.default_rng(913)
        H = _rand_complex(rng, 1, 4)
        Q = _rand_psd(rng, 4)
        with pytest.raises(ValueError, match="budget"):
            solve_multibody_ecbf(H, [Q], [-0.1], P=1.0)

    def test_zero_power_raises(self):
        rng = np.random.default_rng(914)
        H = _rand_complex(rng, 1, 4)
        Q = _rand_psd(rng, 4)
        with pytest.raises(ValueError, match="power"):
            solve_multibody_ecbf(H, [Q], [1.0], P=0.0)

    def test_dim_mismatch_raises(self):
        rng = np.random.default_rng(915)
        H = _rand_complex(rng, 1, 4)
        Q = _rand_psd(rng, 5)  # wrong dim
        with pytest.raises(ValueError, match="must be"):
            solve_multibody_ecbf(H, [Q], [1.0], P=1.0)

    def test_budget_count_mismatch_raises(self):
        rng = np.random.default_rng(916)
        H = _rand_complex(rng, 1, 4)
        Q = _rand_psd(rng, 4)
        with pytest.raises(ValueError, match="one entry per body"):
            solve_multibody_ecbf(H, [Q], [1.0, 2.0], P=1.0)
