# 03 — Multi-body ECBF solver

**Goal.** Implement the joint multi-body exposure-constrained beamforming precoder from paper §IV — the sum-rate-maximising solver subject to a per-body absorbed-power budget on every body in the cell.

This is **the algorithmic contribution of the JSAC paper**. Without it, §IV is unsupported and §VII has nothing to evaluate.

## Blockers

None on the code side. The single-body ECBF solver (`src/aegis/coherent/ecbf.py`) is the rank-one degenerate case and gives you both an oracle to test against and a starting point for the bisection structure. The theory is fully worked out in:

- `JSAC/planning/paper_v2.tex` §IV — the closed-form derivation, eq. closedform: `w_k* = (Q_tot + νI)⁻¹ g_k`
- `theory/exposure_null_precoding.tex` — the multi-body QCQP framing, hard-null vs soft-null variants, Lagrangian
- `theory/system_formalism.tex` — the path-amplitude factorisation framing if you want a different lens
- `theory/monograph_v2.tex` Part III — the foundational ECBF chapter

## Why this matters

The single-body solver answers "given one body's Q, max signal-to-channel for one user under that body's exposure budget." The paper's claim is bigger: the BS serves K users (each with their own channel `h_k`) while constraining absorbed power on every one of B bodies in the cell (each with their own Q_u and budget L_u). Hard-nulling is wasteful at high `K + B`; the paper proposes a budgeted formulation with KKT bisection on per-body Lagrangians.

ZF is the rank-1 limit of the proposed solver (Proposition 1 in the paper). MRT is what you get when no exposure constraint is active. Both should fall out as sanity checks.

## What's already in place

- `src/aegis/coherent/ecbf.py` (232 LOC) — fully working single-body ECBF QCQP. Does bisection on `λ` over `x(λ) = (λQ + I)⁻¹ h*`, handles power-slack regime when full power overshoots `P_abs_max`, falls back gracefully on infeasibility, manages eigh roundoff. This is the right reference implementation to match in the rank-1 limit.
- `src/aegis/coherent/exposure_operator.py` — builds Q, eigendecomposes, returns `ρ` (channel-Q alignment).
- `src/aegis/mimo/precoders.py` — has `mrt`, `zf`, `mmse`, `zf_exposure`. The new solver should land here as a peer constructor on `Precoder` (or wherever feels right; `Precoder` is in `src/aegis/precoder.py`).
- `src/aegis/mimo/compute.py` — the orchestration layer that builds user channels and assembles per-body Q for multi-user multi-body scenes. This is what will *call* the new solver from brief 08.

## Open questions for the dev

- **Soft-budget vs hard-null vs both.** The paper argues soft-budgets win on DoF economy at high `K + B`. `theory/exposure_null_precoding.tex` works through both. Implement what the paper actually evaluates; if the paper is ambiguous, ship both as named variants and let the experiments pick.
- **KKT bisection scheme.** The paper sketches `(Q_tot + νI)⁻¹ g_k` with `ν` selected by binding-set search. The single-body solver bisects on one Lagrangian; multi-body needs a vector of them, with combinatorial active-set search or projected-gradient or interior-point — your call. Whatever's robust under the test cases below.
- **wMMSE vs direct.** Paper §IV.C alludes to wMMSE for sum-rate maximisation under linear precoding. Worth checking whether wMMSE outer-loop + closed-form-given-active-set inner-loop is the cleanest factoring.
- **Warm-starting.** From MRT? From ZF? From the previous slot's solution? Decide once you see the convergence behaviour.
- **Infeasibility handling.** If even the worst-case-power-back-off precoder violates a budget, what should the solver return? The single-body solver returns the smallest-eigenvector fallback with a warning. Multi-body needs an analogous policy — probably reject the slot, log it, let the caller decide.
- **API shape.** Probably mirrors the single-body call: `multibody_ecbf(channels, Q_list, budget_list, P_total) -> (X, diagnostics)` where `X` is `M_ant × K`. But the `diagnostics` payload (Lagrangians, active set, iteration count, residuals) is rich enough to want a dataclass.

## What "done" looks like

- A working solver, probably at `src/aegis/coherent/multibody_ecbf.py`, callable from `src/aegis/mimo/precoders.py` or `src/aegis/precoder.py` as a new `Precoder` constructor.
- Unit tests that include:
  - **Sanity 1 (rank-1 limit)**: with `B=1`, agrees with the existing single-body ECBF to machine precision.
  - **Sanity 2 (no constraint)**: with budgets large enough to be inactive, agrees with MRT.
  - **Sanity 3 (rank-1 hard-null limit)**: in the regime where the paper says ZF is the limit, agrees with regularised ZF.
  - **Smoke test**: a small (K=4 users, B=2 bodies, M_ant=16) scenario where active budgets force a non-trivial precoder, and the solution beats both MRT and ZF in achieved sum-rate while respecting all budgets.
- A short README in `JSAC/code/experiments/` (or alongside the solver) documenting which paper variant it implements (soft-budget? hard-null? wMMSE outer?), so brief 08 doesn't have to reverse-engineer.

## What this is NOT

- A general convex solver for arbitrary QCQPs. This is the specific multi-body sum-rate / per-body PSD-budget problem from §IV.
- A wrapper around CVXPY. The paper's whole pitch is closed-form-up-to-bisection; bringing in a heavy convex solver defeats the cadence claim. Pure NumPy / JAX.
- A replacement for the single-body solver. Both exist; the rank-1 limit just confirms they agree.
- A scheduler. Solving one slot per call is fine; brief 08 owns the time loop.
