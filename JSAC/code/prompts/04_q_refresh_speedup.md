# 04 — Q-refresh speedup (factored Fresnel + translation phasor)

**Goal.** Get 50-body Q construction under 100 ms on a workstation GPU. Currently 378 ms at decim10 (≈2.4 k tri / body), 3.3 s at full Thelonious mesh.

## Blockers

None. This is pure optimisation work on the existing coherent stack.

## Why this matters

Paper §VI claims "in-silico real-time on a workstation GPU" — 100 ms refresh for 50 bodies, matching the dictionary refresh cadence. The current benchmark (`JSAC/code/experiments/gpu_benchmark/`) reports 378 ms at decim10, with the paper saying "with a 20-line factored-Fresnel + vmap port, fits 100 ms." That port is asserted, not measured. Reviewers will ask.

There are two known levers and the paper invokes both. They're independent: doing one doesn't preclude the other. They might be done by the same dev in one sweep or by two devs in parallel.

## What's already in place

- `JSAC/code/experiments/gpu_benchmark/` — the existing 50-body benchmark with `timings.json` and `timings_decim10.json`. Pull these as the baseline you're trying to beat.
- `src/aegis/coherent/body_channel.py` — builds `G̃(r) ∈ ℂ^{N_tri × 3 × M_ant}` using Approximation 2 (depth coupling = 1). This is where most of the per-body work happens and where factored-Fresnel would land.
- `src/aegis/coherent/exposure_operator.py` — builds Q from G̃. This is where eigendecomposition costs sit (O(M_ant³) per body).
- `src/aegis/coherent/fresnel_operator.py` — the per-path Fresnel projector. Currently applied per-path; "factored" presumably means decomposing the projector into reusable pieces that don't have to be rebuilt as bodies translate.
- `src/aegis/_array_backend.py` — JAX/NumPy switching. The benchmark already uses JAX. `vmap` across bodies should be straightforward; the question is what bookkeeping lets it actually batch cleanly.
- The translation phasor identity (`M(t) = Φ(t)ᴴ M(0) Φ(t)`) is in `theory/exposure_null_precoding.tex` §11 (item 5) and `theory/system_formalism.tex`. It's stated, not yet implemented.

## The two levers

**(a) Factored Fresnel + vmap.** The Fresnel apply per path currently does O(N_paths × N_tri × M_ant) work per body, with a fresh tensor build per call. Factoring means pulling out per-path quantities that depend only on `(k̂, ψ_pol)` — independent of body translation — and reusing them across bodies. Combined with `jax.vmap` over the body axis, you should be able to amortise.

**(b) Translation phasor.** When a body moves by `Δt`, the full path-correlation Gram `M` doesn't need to be recomputed. The identity `M(t) = Φ(t)ᴴ M(0) Φ(t)` says it's just a sandwich with a diagonal phase matrix `Φ(t) = diag(exp(-i k k̂_n · Δt))`. So per-slot Q refresh under a 1 ms cadence becomes one phase multiply, not a re-eval of `J^T M J`. Static dictionary terms cache once per body geometry; only the moving body costs anything per slot.

These are conceptually orthogonal — (a) speeds up cold construction, (b) makes warm refresh near-free. The paper needs both for the cadence story to hold honestly.

## Open questions for the dev

- **Which lever pulls more first.** If 50-body cold construction at 100 ms is achievable from (a) alone, (b) becomes a "nice to have" for the cadence claim. If (a) tops out at 200 ms but (b) shaves 95% off warm refresh, you need both. Measure before deciding scope.
- **Public API vs private optimisation.** Translation phasor wants a `Q.translate(Δt)` or similar method on whatever Q lives on. Factored Fresnel is more of a transparent speedup — same call, faster internals. Expose only what brief 08 will plausibly call.
- **Full mesh vs decimated.** The paper reports both numbers (decim10 + native Thelonious). 50-body native is 3.3 s currently — order-of-magnitude harder to bring under 100 ms. Decide whether (a) hit decim10 < 100 ms is enough or (b) we need to push native too. The paper's cadence table is at SMPL-X mesh resolution, so decim10 is probably the right target.
- **Memory budget.** `G̃` for 50 bodies × 25k tri × 3 × 64 antennas × complex64 is ~24 GB. Decim10 brings it under 3 GB. Translation phasor caching needs the *static* `M(0)` per body, which is dictionary-paths-squared in size. Watch the working set.
- **Where this code lives.** ROADMAP suggested `coherent/_fast.py` and `coherent/translation.py`. Push back if a different shape feels right.

## What "done" looks like

- A measured 50-body Q-refresh time **under 100 ms** at the same mesh resolution as the existing benchmark, on the same GPU class. Reproducible via a script that lives next to (or extends) `JSAC/code/experiments/gpu_benchmark/`.
- The benchmark output (`timings.json` updated or a `timings_after_speedup.json` written alongside) so future readers can see before/after.
- Existing tests still pass — coherent levels 7/8 must agree with their pre-speedup outputs to whatever tolerance the existing tests use. The Mie regression test and the multi-user golden are the canaries.
- A note in the experiment README explaining what was changed and which lever produced what fraction of the speedup.

## What this is NOT

- A rewrite of the coherent stack. The math is fine; it's the data flow that's slow.
- A switch to a different array backend. JAX is already in use; if NumPy needs deprecating, that's a separate decision.
- A multi-GPU sharding effort. Single workstation GPU is the target.
- A claim of theoretical novelty. Both levers are mentioned in the paper; this brief just makes them real.
