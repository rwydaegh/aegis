# 05 — Theorem 2 tightness figure

**Goal.** One figure showing how loose the rank-1 Cauchy bound is in practice, ready to drop into paper §II.

## Blockers

None. Single-body, no ECBF, no multi-body solver. Pure post-hoc analysis on the existing coherent stack.

## Why this matters

Paper Theorem 2 (`paper_v2.tex` §II, eq. cauchy-bound-op) gives the pose-agnostic operator bound:

`xᴴ Q x ≤ T₀ · (A_ab/4) · D_max · |aᴴ x|²`

where `a` is the LOS steering vector. This is the **safety net for tier-C and tier-D bystanders** — the bodies the BS doesn't have pose telemetry on. The paper invokes it as the worst-case backstop and uses it conceptually throughout §IV/§VII to argue that the closed-loop precoder remains compliant even under unknown pose.

But the paper never shows how *tight* the bound is. If the rank-1 ceiling overshoots actual `xᴴ Q x` by 6 dB on average, every tier-C bystander costs the precoder ~6 dB of capacity — that's a real and acknowledgeable tax. If it's tight to 0.5 dB, the safety net is essentially free. Reviewers will ask. The number matters for the chronic-dose narrative too (§VII.E).

## What's already in place

- `src/aegis/coherent/exposure_operator.py` — builds Q for a body given paths.
- `src/aegis/geometry/directivity.py` — gives `D(k̂)`. `D_max` is its sup over directions.
- The 4 IT'IS STL phantoms are loadable; Thelonious is the canonical paper subject (matches `fig:rank-cdf` and the GPU benchmark).
- Paper Appendix C has the proof sketch — useful for understanding what tightness regime to expect.
- The composability analysis (`theory/composability_analysis.md` §5) flags a factor-of-4 bug in the L0/L1 area-of-absorption formula. Worth checking whether this affects `A_ab/4` here; if so, brief the paper authors before plotting.

## Open questions for the dev

- **Which precoder ensemble for `x`**. The bound holds for *all* `x`. A meaningful tightness figure samples `x` from the distributions actually used in practice:
  - Random isotropic Gaussian unit vectors (the fully-uninformed baseline).
  - MRT toward a random user direction (the "all power, one beam" stress test).
  - ECBF outputs from `coherent/ecbf.py` solved against the same Q with realistic budgets (the regime that actually matters for the paper).
  - ZF outputs in a multi-user toy scene.
  - All of the above as separate CDFs on one plot is probably the cleanest.
- **Which body / scene**. Thelonious only? Add Duke / Eartha / Ella to show demographic spread? The four IT'IS phantoms are the natural set; SMPL-X variations are a stretch goal.
- **Which channel**. The paper's plaza-specular geometry vs. 3GPP UMa-LOS (matching `fig:rank-cdf`) vs. an idealised single-LOS — pick at least the plaza-specular and 3GPP cases since they're the paper's reference scenes.
- **What's the metric**. CDF of `LHS / RHS` ratio in dB. Mean, p10, p90, max. Possibly broken down by `ρ` (channel-Q alignment) since the bound is tightest when the LOS direction dominates and loosest when Q has rich angular spread.
- **Whether the figure goes in the body of §II or an appendix**. Up to you — the dev is closest to whether the figure is a one-liner or a full subsection.

## What "done" looks like

- A figure (`tightness.pdf` or similar) showing the bound's tightness as a CDF or scatter, with at least a few precoder ensembles distinguished. Caption-ready.
- The script that produces it lives in `JSAC/code/experiments/cauchy_tightness/` next to the existing experiments. Includes README + run instructions.
- Numerical summary in the README: median ratio in dB, p90, max; per phantom and per channel.
- A one-paragraph commentary on what the numbers imply for the tier-C/D capacity tax. This goes in the experiment README, not the paper directly — paper rewrite is a separate pass.

## What this is NOT

- A theorem-proving exercise. The bound is in the paper; this brief verifies its empirical tightness.
- A figure for §III's rank-CDF. That's a different figure, already done (`JSAC/code/experiments/rank_check/`).
- A multi-body study. Single-body is the right framing — Theorem 2 is per-body.
- A new theory contribution. If you find the bound is unexpectedly tight or loose in some regime, write that up in the README, but don't try to re-derive Theorem 2.
