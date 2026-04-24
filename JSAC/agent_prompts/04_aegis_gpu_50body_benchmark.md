# Agent prompt — GPU AEGIS 50-body per-pose benchmark

*PoC, not a finished experiment. I need one wall-clock number before I can stop hedging in §V.3 of `JSAC/paper.tex`. This is a coding task inside the AEGIS repo.*

## The question

On a GPU, how long does it take AEGIS to recompute the per-body coherent exposure operator $\mathbf{Q}^{(u)}$ for **50 bodies of $\sim$25 k triangles each at one pose**, from ray-tracer path set through $\tilde{\mathbf{G}}$ to $\mathbf{Q}$?

The paper's §V.3 claims this fits inside the 100 ms pose-refresh cadence. My basis is a 3 ms/body measurement on a 4-CPU 8 GB laptop with numba, so 50 bodies should cost ~150 ms on CPU, which is marginal. I need the GPU number to say real-time-in-silico feasibility cleanly.

## What I need back

1. **A single benchmark number**: median and 10th/90th percentile wall-clock time per 50-body refresh on whatever GPU is available, across $\ge 30$ runs after JAX/XLA warm-up. Report the warm-up vs steady-state cost separately.
2. **A per-stage breakdown**: ray tracing / surface integration / Fresnel-tensor construction / Gram accumulation. Where does the time go?
3. **A written paragraph** on whether this fits in 100 ms, 10 ms, or neither. If "neither," which stage is the bottleneck and what would it cost to fix.

## Scenario

- Carrier: 26 GHz.
- BS: $M = 64$ ($8 \times 8$) panel.
- Phantoms: **50 copies of Thelonious** (or Duke/Eartha/Ella mixed — whichever is easiest; the paper only cares about per-body compute time). Positions random across a 20–80 m range ring in front of the BS.
- Paths per body: 5–20 dominant paths from the ray tracer (LOS + ground + facade). Fine to stub the tracer with a synthetic path set if wiring a real tracer is too much friction — this prompt is about AEGIS compute time, not end-to-end.
- One fixed pose per body (use the default standing pose; no SMPL-X needed).
- JAX backend on GPU. If no JAX, NumPy+numba is acceptable as a lower-bound reference.

## Where to start in the repo

- `src/aegis/coherent/exposure_operator.py` → `compute_exposure_operator(G_tilde, areas)` is the $O(M^2)$ Gram accumulator. This is one of the two hot functions.
- `src/aegis/coherent/field_channel.py` → constructs $\tilde{\mathbf{G}}$ over surface points. Other hot function.
- `src/aegis/coherent/fresnel_operator.py` → per-point Fresnel $\mathbf{F}_n(\mathbf{r})$.
- `src/aegis/kernels/level7_coherent.py` → the level-7 kernel orchestration.
- `src/aegis/mimo/compute.py` → there is already a multi-user driver here that assembles $\mathbf{Q}$ for each user; it's not set up for 50 bodies yet but the per-body call is reusable.
- `src/aegis/_array_backend.py` → `AEGIS_ARRAY_BACKEND=jax` enables JAX + GPU. Confirm JAX is actually using the GPU (check `jax.devices()`).
- `pyproject.toml` → `aegis[rt]` extra installs DiffeRT if you want a real ray tracer.
- `docs/internal/features.md` (if it exists) → feature inventory, may list existing benchmark entry points.

Search for existing benchmarks: `grep -rn "benchmark\|timeit\|Q.*50\|50.*bodies" tests/ src/` — there may already be a scaffold.

## What I do NOT want

- A whole pipeline (scheduler, precoder, sum-rate). Just $\mathbf{Q}^{(u)}$ for 50 bodies, one pose each.
- A pose-varying recomputation — if this is fast enough at one pose, the translation-phasor identity (§II.3 of the paper) makes per-slot refresh free, so the pose cadence is the bottleneck.
- Algorithmic changes to AEGIS. If the numbers are bad, flag the stage but do not rewrite it. I will decide whether to refactor.
- Compute time on my laptop — needs GPU. If no GPU is reachable, report back and I'll provision one.

## Constraints

- You will likely hit a "no GPU available" situation. If so, **stop and report that**, do not substitute a CPU benchmark and quietly elide the difference. The whole point of this prompt is the GPU number.
- JAX first-run warm-up at scale can be 10–60 s. That is not the steady-state number. Report both.
- If the coherent exposure operator is not yet batched over bodies, the per-body for-loop overhead should be reported separately from the kernel cost — because a batched implementation is a realistic future optimisation and I want to know whether the un-batched version already fits.

## Output location

- Benchmark script → `JSAC/experiments/gpu_benchmark/bench_50body.py` (create directory).
- Results (raw timings, JSON) → `JSAC/experiments/gpu_benchmark/timings.json`.
- Written takeaway → `JSAC/experiments/gpu_benchmark/README.md`: one paragraph on feasibility, per-stage table, and the raw per-run timings attached.

## Why this matters

The JSAC paper (`JSAC/paper.tex`) currently has `\TODO{...GPU AEGIS 50-body benchmark pending...}` in §V.3. Fixing it either confirms the real-time-in-silico claim (cheap) or forces a rewrite of §V to acknowledge a batched-offline preprocessing mode for $\mathbf{M}^{(u)}(\bm 0, \bm\theta_u)$ with only translation refresh at slot cadence. Both are acceptable paper framings — the experiment tells me which to commit to.
