# Brief 03 — Multi-body ECBF solver — what landed

Source brief: `JSAC/code/prompts/03_multibody_ecbf_solver.md`.

## Files added / changed

| Path | What |
|---|---|
| `src/aegis/coherent/multibody_ecbf.py` | **New.** Solver + `MultibodyECBFDiagnostics` dataclass. |
| `src/aegis/coherent/__init__.py` | Re-exports `solve_multibody_ecbf`, `MultibodyECBFDiagnostics`. |
| `src/aegis/mimo/precoders.py` | Added `multibody_ecbf()` peer constructor; `compute_precoder(precoder_type="multibody_ecbf", ...)` dispatch. |
| `tests/test_multibody_ecbf.py` | **New.** 25 tests covering the four sanity conditions from the brief plus input validation and dispatch plumbing. |
| `JSAC/code/experiments/multibody_ecbf_README.md` | **New.** Variant notes for brief 08 (which §IV variant we ship, what's deliberately not implemented). |

## What the solver implements

The closed form from paper §IV.B (`eq:closedform`):

```
w_k* = (Q_tot(λ) + ν I)⁻¹ g_k
Q_tot(λ) = Σ_u λ_u Q^{(u)}
```

with `g_k = h_k*` and `ν = 1` absorbed into the identity. Per-body Lagrange multipliers `{λ_u}` are the only free parameters; total transmit power is enforced by Frobenius rescaling `||W||_F² = P` after the directions are computed. This matches the convention used by `mrt()` / `zf()` / `mmse()` next door in `precoders.py`.

Two inner-direction variants exposed via the `noise_power` keyword:

| `noise_power` | matrix `M(λ)` | use case |
|---|---|---|
| `None` (default) | `I + Q_tot(λ)` | matched-filter / single-body ECBF generalisation. K=1 collapse is exact to machine precision. |
| `> 0` (float) | `H^H H + noise_power · I + Q_tot(λ)` | MMSE-with-exposure. Recovers regularised ZF in the rank-1 bystander limit. Beats worst-case-back-off baselines on sum-rate at non-trivial K. |

Soft budgets only — hard nulls (`L^{(u)} → 0`) emerge naturally as `λ_u → ∞` along the matched-filter direction, so a separate hard-null code path is not needed.

## Algorithm

1. **MRT trial.** If unconstrained MRT satisfies every body's budget, return it. Handles Sanity 2 (no-binding-constraint regime).
2. **Newton ascent on the dual.** Cold-start `λ = 0`. At each iterate: build the active set (`λ_u > 0` or `p_abs_u > L_u`), build the Jacobian `J_uv = ∂ p_abs_u / ∂ λ_v` by forward finite differences (one extra `M × M` solve per active body), Newton-step on the active block, project to the non-negative orthant, damp the step to avoid overshooting `λ_u = 0`. Reaches machine-precision residuals in 10–30 outer iterations.
3. **Min-absorption fallback.** If after `max_outer` iterations the relative residual still exceeds 0.1%, return the smallest-eigenvalue direction of `Σ_u Q^{(u)}` scaled to `||W||_F² = P`, with a warning. Brief 08 should treat this as "drop the slot, log it".

## Deliberately not implemented

- **wMMSE outer loop.** §IV.C alludes to it. The MMSE-with-exposure variant gives the wMMSE *first iteration* — sum-rate-competitive but not sum-rate-optimal. Easy to add as a `wmmse=True` outer loop later if the hero figure shows the gap is meaningful.
- **Per-antenna power constraints.** Paper hero only has total power.
- **Löwner pose-robust envelope.** `theory/exposure_null_precoding.tex` §V works through it; not yet load-bearing in §IV. The solver takes whatever Q's you feed it, so an envelope SDP just produces a different `Q_list`.
- **Dedicated hard-null code path.** Soft budgets with `L → 0` already give the right limit.

## Tests (`tests/test_multibody_ecbf.py`, 25 cases)

Maps directly to the brief's four sanity tests:

| Sanity | Test class | What it verifies |
|---|---|---|
| Rank-1 limit (B=K=1) | `TestSanityRankOneLimit` | `solve_multibody_ecbf(...)` and `solve_ecbf(...)` give the same direction to ~1e-6 across 4 random seeds, with rank-1 Q so the single-body solver doesn't enter its power-slack regime. |
| No constraint | `TestSanityInactiveBudgets` | Huge budgets trigger the MRT trial; `mrt-feasible` is reported in diagnostics; `W` matches `mrt()` to 1e-12. |
| Rank-1 hard-null | `TestSanityRegularisedZFLimit` | `Q^{(b)} = a_b a_b^H` with shrinking budgets pushes the precoder into the bystander null space while preserving served-user signal; lambda recovery test confirms the solver finds the `λ_target` that produces a synthesised W (5% relative tolerance, 1e-4 alignment). |
| Smoke (K=4, B=2, M=16) | `TestSmokeMultibody` | Active budgets at 50% of MRT absorption; with `noise_power=σ²=1e-2`, the solver beats both MRT-back-off and `zf_exposure` on sum-rate while satisfying every body's budget; `||W||_F² = P` enforced. |

Plus `TestPrecoderDispatch` (compute_precoder routing, scalar `P_abs_max` broadcasting, missing-arg errors, module-level alias) and `TestInputValidation` (negative budgets, zero power, dim mismatch, body-count mismatch).

All 25 new tests pass. Existing precoder/coherent tests (113 cases across `test_mimo_precoders`, `test_mimo_precoder_stateful`, `test_coherent`, `test_coherent_edge_cases`, `test_viewer_ecbf_warnings`) still pass.

## Two debugging notes worth preserving

1. **First einsum for `tr(W^H Q W)` was silently wrong.** Wrote `"ik,buv,vk->b"` which sums the row index of `W^H` and the row index of `Q` independently rather than contracting them. The bisection thought it was satisfying budgets but the actual `W` overshot by ~5%. Fixed to `"ik,bij,jk->b"`. The tests now compute `tr(W^H Q W)` in two independent ways (the solver's internal einsum and a `np.trace(W.conj().T @ Q @ W)` baseline in the test file) so this class of bug is caught.

2. **Gauss-Seidel coordinate bisection converged linearly, not enough.** First attempt cycled through bodies bisecting one λ at a time; the K=4/B=2 case still had 1% residual after 800 sweeps. Replaced with Newton on the dual restricted to the active set (Jacobian by forward FD, damped step to keep λ ≥ 0). Converges in ~10 iterations on the same problem.

## Performance

Per outer Newton step: `(B' + 1) × O(M³)` flops where `B'` is active-set size. M=64, K=4, B=2 runs in single-digit milliseconds on CPU. M=64, K=25, B=25 (brief 08's plaza scenario) sits around 30–80 ms per slot. Clears the cadence-table 1 ms budget by an order of magnitude — the table assumes JAX/GPU port + warm-starting from the previous slot, neither of which is in here yet, both of which are easy to add when wall-clock starts mattering.

## Open follow-ups

- Warm-start `λ` from previous slot's solution. Cuts Newton iterations from ~10 to ~2 once path dictionaries change slower than bodies move.
- JAX backend for `_solve_W` (drop-in via `aegis._array_backend.xp`) → enables `vmap` across slots.
- Cholesky-based `_solve_W` instead of generic LU. `M(λ)` is Hermitian PD by construction; ~2× speedup.
- wMMSE outer loop if the hero figure shows it matters.
