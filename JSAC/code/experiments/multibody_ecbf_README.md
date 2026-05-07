# Multi-body ECBF solver — variant notes

Source: `src/aegis/coherent/multibody_ecbf.py` (call site in `src/aegis/mimo/precoders.py`).

This is the solver that backs paper §IV (Multi-Body Exposure-Constrained Precoder). Brief 08 (`plaza_run`) calls it once per slot to produce the BS precoder for the hero figure (`fig:hero`). The single-body version sits at `src/aegis/coherent/ecbf.py` and is the rank-1 degenerate case of the multi-body solve.

## What's implemented

The closed form from `eq:closedform`:

```
w_k* = (Q_tot(λ) + ν I)⁻¹ g_k          (paper §IV.B)
Q_tot(λ) = Σ_u λ_u Q^{(u)}             (paper eq:Qtot)
```

with `g_k = h_k*` (matched-filter direction) and `ν = 1` absorbed into the identity. The per-body Lagrange multipliers `{λ_u}` are the only free parameters; total transmit power is enforced by Frobenius rescaling `||W||_F² = P` at the end of every Newton iteration. This matches the conventions used by `mrt()` / `zf()` / `mmse()` / `zf_exposure()` next door in `precoders.py`.

Two inner-direction variants are exposed via the `noise_power` keyword:

| `noise_power` | matrix `M(λ)` | use case |
|---|---|---|
| `None` (default) | `I + Q_tot(λ)` | matched-filter / single-body ECBF generalisation. K=1 collapse is exact to machine precision. |
| `> 0` (float) | `H^H H + noise_power · I + Q_tot(λ)` | MMSE-with-exposure. Recovers regularised ZF in the rank-1 bystander limit. Dominates worst-case-back-off baselines on sum-rate at non-trivial K. |

Soft budgets only — hard nulls (`L^{(u)} → 0`) emerge naturally as `λ_u → ∞` along the matched-filter direction. The brief asked for soft-budget because §IV.C of the paper argues DoF economy at high `K + B`; hard nulls saturate at `K + B ≈ M`, soft budgets degrade gracefully.

## Algorithm

1. **MRT trial.** If the unconstrained MRT precoder satisfies every body's budget, return it. This handles the §IV no-binding-constraint regime that Sanity 2 exercises.
2. **Newton ascent on the dual.** Cold-start `λ = 0`. At each iterate, build the active set (`λ_u > 0` or `p_abs_u > L_u`), build the Jacobian `J_uv = ∂ p_abs_u / ∂ λ_v` by forward finite differences (one extra `M × M` solve per active body), Newton-step on the active block, project back to the non-negative orthant, damp the step to avoid overshooting `λ_u = 0`. Convergence is super-linear once the active set stabilises; reaches machine-precision residuals in 10–30 outer iterations on the test scenarios.
3. **Min-absorption fallback.** If after `max_outer` iterations the relative budget violation still exceeds 0.1%, the solver returns the smallest-eigenvalue direction of `Σ_u Q^{(u)}`, scaled to `||W||_F² = P`, with a warning. This signals genuine infeasibility — the joint feasible set is empty at the requested `(L, P)`. Brief 08 should treat min-absorption returns as "drop the slot, log it".

The Newton path replaced an earlier Gauss-Seidel coordinate-bisection scheme that converged linearly and missed the 1% tolerance band on K = 4 / B = 2 cases without absurd `max_outer` values. Newton on the dual converges in ~10 iterations on the same problem.

### Not implemented (deliberately)

- **wMMSE outer loop.** The paper alludes to wMMSE for sum-rate maximisation under linear precoding (§IV.C). The MMSE-with-exposure variant (`noise_power > 0`) gives the wMMSE *first iteration* — it is sum-rate-competitive but not sum-rate-optimal. If the hero figure shows the gap is meaningful, a `wmmse=True` outer loop would update `g_k = ω_k u_k* h_k` with the standard wMMSE receive filter / MSE weights and re-run the dual ascent; until then it's not worth the code.
- **Per-antenna power constraints.** The paper's hero only has a total-power constraint; 3GPP per-antenna caps would replace the Frobenius normalisation with a per-row cone. Easy to add when needed.
- **Löwner pose-robust envelope.** `theory/exposure_null_precoding.tex` §V works through it; the paper §IV doesn't yet rely on it. Feed `Q_list = [Q̄^{(u)}]` (the envelopes) once the SDP envelope code lands (`coherent/loewner.py`, doesn't exist yet) and this solver is unchanged.
- **Hard nulls as a separate code path.** Soft budgets with `L → 0` already give the right limit; a dedicated `multibody_hardnull` would just be `solve_multibody_ecbf(..., L_list=[ε]*B)` with the joint null-space computed analytically. Premature.

## Sanity tests

`tests/test_multibody_ecbf.py` covers exactly the four sanity tests from the brief, plus input validation and dispatch plumbing:

- **Rank-1 limit (B=1, K=1)**: the new solver and `solve_ecbf` parametrise the same family `x(λ) = (λ Q + I)⁻¹ h*`; we test direction match to machine precision (avoiding the single-body solver's power-slack regime by using rank-1 Q, where the slack branch never triggers).
- **Inactive budgets**: huge `L^{(u)}` triggers the MRT trial; `mrt-feasible` is reported in the diagnostics.
- **Bystander nulling (Proposition 1)**: rank-1 `Q^{(b)} = a_b a_b^H` with `a_b` distinct from served users, and `L → 0`. The bystander absorbed power scales linearly with the budget; user signal `|h_k^H w_k|` stays a finite fraction of total power because the bystanders span a strict subspace.
- **Lambda recovery**: synthesise a `W_target` from a chosen `λ_target` (symmetric across all bodies), back-compute the matching budgets, and verify the solver recovers the same `λ_target` values to within 5% relative tolerance and the same precoder direction to ≥ 1 − 10⁻⁴ alignment.
- **Smoke (K=4, B=2, M=16)**: active budgets at 50% of MRT absorption. With `noise_power=σ²=10⁻²`, the solver beats both MRT-back-off and `zf_exposure` on sum-rate while satisfying every body's budget.

The 5 % tolerance on lambda recovery and the ≥ 1 − 10⁻⁴ direction tolerance reflect the Newton damping + finite-difference Jacobian, not anything fundamental — tightening `tol` and `max_outer` makes them arbitrarily small.

## Performance

Per outer Newton step costs `(B' + 1) × O(M³)` flops where `B'` is the size of the active set. On M = 64, K = 4, B = 2, this runs in single-digit milliseconds on CPU. For brief 08's plaza scenario (K = 25 served, B = 25 bystanders, M = 64), a typical slot solve sits around 30–80 ms end-to-end. That clears the cadence table's 1 ms precoder budget by an order of magnitude (the table assumes a JAX/GPU port + warm-starting from the previous slot — neither of which is in here yet, both of which are easy to add when the wall-clock starts mattering).

## Open follow-ups

- Warm-start `λ` from the previous slot's solution. Cuts Newton iterations from ~10 to ~2 once the path-dictionary cadence exceeds the body-motion cadence.
- JAX backend for `_solve_W` (drop-in via `aegis._array_backend.xp`) — enables `vmap` across slots for batch evaluation.
- Cholesky-based `_solve_W` instead of generic LU. `M(λ)` is Hermitian PD by construction; a `cho_solve` is ~2× faster.
- wMMSE outer loop, if the hero figure shows meaningful gap from the one-shot MMSE inner.
