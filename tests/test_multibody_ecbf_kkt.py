"""Regression test for the KKT complementary-slackness fix in multibody_ecbf.

Bug (fixed 2026-05-13): the convergence check in solve_multibody_ecbf only
verified primal feasibility (rel_viol < tol) but allowed Lagrange multipliers
to remain positive on slack constraints. This locked the solver into a
suboptimal interior point, causing a ~6 % gap between local-Q and global-Q
ECBF results in Paper C.

Fix: added a ``slack_with_lambda`` guard that requires lambda[b] == 0 for any
body b whose constraint is strictly slack before declaring convergence.

Tests:
  - test_kkt_slack_lambda_is_zero: one body binding, one body slack. The slack
    body must have lambda == 0 at the optimum.
  - test_kkt_converges_within_budget: same setup, verifies convergence flag and
    that both bodies satisfy their budgets.
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.coherent.multibody_ecbf import solve_multibody_ecbf


def _rand_complex(rng, *shape):
    return (rng.standard_normal(shape) + 1j * rng.standard_normal(shape)) / np.sqrt(2)


def _rand_psd(rng, M, scale=1.0):
    """Random Hermitian PSD matrix, trace ~ scale * M."""
    A = _rand_complex(rng, M, M)
    Q = A.conj().T @ A
    return scale * Q / np.trace(Q).real * M


def _per_body_abs(W, Q_list):
    return np.array([float(np.real(np.trace(W.conj().T @ Q @ W))) for Q in Q_list])


@pytest.mark.parametrize("seed", [0, 1, 2, 7, 42])
def test_kkt_slack_lambda_is_zero(seed):
    """Lambda on a slack constraint must be zero (complementary slackness).

    Body 0 is close to the antenna: Q0 has large trace, budget L0 is tight.
    Body 1 is far away: Q1 has small trace (1/20 of Q0), budget L1 is huge
    so its constraint is never binding. KKT requires lambda[1] == 0.
    """
    rng = np.random.default_rng(seed)
    M = 8
    K = 2
    H = _rand_complex(rng, K, M)

    # Body 0: close, large absorption matrix
    Q0 = _rand_psd(rng, M, scale=1.0)
    # Body 1: far, small absorption matrix (1/20 scale)
    Q1 = _rand_psd(rng, M, scale=0.05)

    # Unconstrained MRT power on body 0
    W_mrt = H.conj().T @ np.linalg.pinv(H @ H.conj().T)
    P = float(np.real(np.trace(W_mrt.conj().T @ W_mrt)))

    p_mrt = _per_body_abs(W_mrt, [Q0, Q1])

    # L0: tight (80 % of MRT absorption on body 0) - will be binding
    L0 = 0.80 * p_mrt[0]
    # L1: slack (10x of MRT absorption on body 1) - will never be active
    L1 = 10.0 * p_mrt[1]

    _, diag = solve_multibody_ecbf(
        H,
        [Q0, Q1],
        [L0, L1],
        P,
        return_diagnostics=True,
        tol=1e-9,
    )

    # Complementary slackness: slack constraint must have lambda == 0
    assert diag.lambdas[1] < 1e-8, (
        f"KKT slackness violated: lambda[1]={diag.lambdas[1]:.3e} > 0 "
        f"but body 1 constraint is slack (seed={seed})"
    )


@pytest.mark.parametrize("seed", [0, 1, 2, 7, 42])
def test_kkt_converges_within_budget(seed):
    """Solver converges and both budgets are satisfied.

    Same asymmetric setup: body 0 binding, body 1 slack. Verifies:
    - converged flag is True
    - n_outer < 100 (fast convergence)
    - p_abs[0] <= L0 * (1 + tol)
    - p_abs[1] <= L1 * (1 + tol)
    """
    rng = np.random.default_rng(seed)
    M = 8
    K = 2
    H = _rand_complex(rng, K, M)

    Q0 = _rand_psd(rng, M, scale=1.0)
    Q1 = _rand_psd(rng, M, scale=0.05)

    W_mrt = H.conj().T @ np.linalg.pinv(H @ H.conj().T)
    P = float(np.real(np.trace(W_mrt.conj().T @ W_mrt)))
    p_mrt = _per_body_abs(W_mrt, [Q0, Q1])

    L0 = 0.80 * p_mrt[0]
    L1 = 10.0 * p_mrt[1]

    W, diag = solve_multibody_ecbf(
        H,
        [Q0, Q1],
        [L0, L1],
        P,
        return_diagnostics=True,
        tol=1e-9,
    )

    assert diag.converged, f"Solver did not converge (seed={seed}, n_outer={diag.n_outer})"
    assert diag.n_outer < 100, f"Too many outer iterations: {diag.n_outer} (seed={seed})"

    p_abs = _per_body_abs(W, [Q0, Q1])
    tol = 1e-6  # generous relative tolerance for budget check
    assert p_abs[0] <= L0 * (1.0 + tol), (
        f"Budget 0 violated: p={p_abs[0]:.6g} > L={L0:.6g} (seed={seed})"
    )
    assert p_abs[1] <= L1 * (1.0 + tol), (
        f"Budget 1 violated: p={p_abs[1]:.6g} > L={L1:.6g} (seed={seed})"
    )
