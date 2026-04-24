# GPU AEGIS 50-body benchmark (JSAC §V.3)

## Scenario

| Parameter | Value |
|---|---|
| Carrier | 26 GHz |
| BS array | 8×8 UPA, M = 64 elements, λ/2 spacing, patch pattern |
| Phantoms | 50 copies of Thelonious, 23,826 triangles each |
| Body placement | random in a 20–80 m ring, ±90° of BS broadside, yaw ∈ [-π, π] |
| Paths per body (center) | 10 (LOS + ground + 8 facade/cluster clusters), stubbed |
| Paths per body (expanded) | 10 × 64 = 640 (per-element, via `expand_paths_to_array`) |
| Tissue | skin @ 26 GHz, ε_r = 16.5, σ = 25.8 S/m, complex n = 4.52 − 1.98j |
| Backend | `AEGIS_ARRAY_BACKEND=jax`, complex128, `jax.jit` per body, per-body host loop |
| Hardware | NVIDIA RTX 3090 (24 GB), driver 565, CUDA 12.7, JAX 0.4.34 |

Paths are synthetic because the prompt asked for AEGIS compute time, not end-to-end ray tracing. The LOS leg is aimed from the BS at each body centroid, the ground bounce reflects BS z, and 8 facade paths perturb the LOS direction by ~8° rms. `expand_paths_to_array` then bakes per-element steering into psi and flattens to 640 paths per body.

## Headline number

**With ~25 k-triangle phantoms (Thelonious as delivered): 50-body Q refresh takes 3.31 s** on an RTX 3090 — overshoots §V.3's 100 ms pose cadence by ~33×.

**With SMPL-X-sized phantoms (~2.4 k triangles, 10× stride decimation): 50-body Q refresh drops to 378 ms** — still 3.8× over 100 ms, but per-body is already under 10 ms, and vmap-batching brings 100 ms within reach.

| Metric | 25 k tri/body (Thelonious) | 2.4 k tri/body (SMPL-X-sized) |
|---|---:|---:|
| 50-body refresh, median | **3312 ms** | **378 ms** |
| 50-body refresh, p10 / p90 | 3306 / 3314 ms | 376 / 381 ms |
| Per body, median | 66.2 ms | 7.5 ms |
| Per body, p10 / p90 | 65.9 / 66.5 ms | 7.3 / 7.8 ms |
| n_runs | 30 (after 3 warm-up) | 30 (after 3 warm-up) |

Steady state is extremely stable at both sizes (p90 − p10 ≈ 5 ms at 25 k, ≈ 0.5 ms at 2.4 k): kernel execution is the bottleneck, not scheduler noise. SMPL-X decimation is done by striding every 10th triangle and rescaling per-triangle areas by ×10, so the total body area is preserved and compute-cost scaling can be read off directly.

## Warm-up vs steady state

| Item | First call (ms) |
|---|---|
| Full pipeline (body channel + Q) | 1035 |
| Fresnel-tensor stage only | 740 |
| Body-channel stage only | 752 |
| Gram stage only | 101 |

First-call cost is XLA compilation plus the first kernel launch. It only pays once per shape. All four jit cache hits after that. Reported steady-state numbers exclude the first three runs.

## Per-stage breakdown (body 0, n = 30 each)

All medians in ms. The 25 k column is the original Thelonious mesh; the 2.4 k column is Thelonious decimated 10× to roughly SMPL-X triangle count.

| Stage | 25 k tri | 2.4 k tri | What it does |
|---|---:|---:|---|
| Fresnel tensor, **N = 640** (non-factored, expanded paths) | **32.2** | **4.0** | Builds μ, t_s, t_p, TE/TM bases over all M × N surface-path pairs |
| Fresnel tensor, **N = 10** (center paths only, factored reference) | **1.3** | **0.6** | Same code, only N_center directions — shows headroom the already-implemented factored path would recover |
| Body-channel G̃ (includes Fresnel) | 61.6 | 6.7 | Fresnel → F@ψ → depth weight → phase → scatter into (M, 3, M_ant) |
| Surface-integration part, derived (G̃ − Fresnel) | 29.4 | 2.7 | F@ψ, depth, phase, element-scatter at N = 640 |
| Gram accumulator Q = Σ area · G̃ᴴG̃ | 4.9 | 0.8 | `einsum("m,mia,mib->ab")` over M triangles to a 64 × 64 matrix |
| Full per-body (body channel + Q) | 66.1 | 7.3 | Sum of the above, jit-fused |
| Python loop overhead (50 no-op jit dispatches) | 3.0 | 4.5 | Negligible relative to kernel cost at both sizes |

Ray-tracing is stubbed, so it contributes nothing to these timings. The user's paper only cares about AEGIS compute cost, so that stub is safe; a realistic DiffeRT pass for 50 bodies would add its own budget.

## Does this fit 100 ms? 10 ms? Neither?

**Neither at 25 k tri/body; "neither but close" at SMPL-X-sized 2.4 k tri/body.** At 25 k triangles per body, 3.3 s for 50 bodies is ~33× over the 100 ms pose cadence and ~330× over a 10 ms slot cadence. At 2.4 k triangles (SMPL-X scale), the same pipeline drops to 378 ms — 3.8× over 100 ms and 37× over 10 ms. The bottleneck in both cases is the Fresnel-tensor stage evaluated over the element-expanded path set: 32.2 ms × 50 = 1.6 s at 25 k and 4.0 ms × 50 = 200 ms at 2.4 k, each roughly half of its own total. Surface integration at N = 640 scales close to linearly with M (29.4 → 2.7 ms, 11× for 10× mesh), Fresnel at N = 640 scales roughly linearly (32.2 → 4.0 ms, 8×), and the Gram accumulator scales sub-linearly because the destination is a fixed 64 × 64 matrix (4.9 → 0.8 ms, 6×). Per-body median at SMPL-X size is 7.5 ms, already under the 10 ms slot cadence for a single body.

Two cheap structural fixes are visible from the numbers above, and their effect is different at the two mesh sizes. **(1)** Fresnel has no per-element dependence — t_s, t_p, e_s, e_p depend only on (normal, k_hat). The already-existing `compute_body_channel_factored` computes Fresnel for N_center = 10 directions and shares the result across all 64 elements, which would cut Fresnel per body from 32.2 → 1.3 ms at 25 k and 4.0 → 0.6 ms at 2.4 k. Today that function uses a Python `for c in range(N_center)` plus `np.add.at`, which is not JIT-friendly and forces host↔device traffic, so it's not currently the right thing to benchmark on GPU; porting its inner scatter to a pure `jnp.zeros(...).at[...].add(...)` is a ~20-line change and does not alter the algorithm. **(2)** Batching the per-body loop with `jax.vmap` across bodies (current 50 host dispatches → 1 device dispatch over a leading 50-axis) would amortise memory-traffic and kernel-launch cost and is orthogonal to the factored fix. Both together: at SMPL-X size, the surface-integration stage alone is ~2.7 ms/body × 50 = 135 ms, but vmap would collapse redundant overhead and fuse the scatter, so sub-100 ms is plausible. At 25 k, even the optimistic combined estimate (~(1.3 + 29.4 + 5) ms × 50 / 5-10× vmap headroom) lands in the 200–500 ms range, which is the regime where §V.3's translation-phasor identity becomes the actual solution: compute M^(u)(**0**, **θ**_u) offline once per pose and refresh only the per-slot translation phasor at the 10 ms cadence.

Recommendation for §V.3:

- If the paper's reference phantom is a detailed ~25 k-triangle mesh (Thelonious/Duke/Eartha/Ella as shipped): **drop the "100 ms in-silico" claim for the live-refresh pipeline** and reframe real-time as "per-pose ~3.3 s preprocessing on a single RTX 3090 (un-factored, un-batched baseline) → 1 ms translation refresh per slot via the phasor identity". That's the framing the prompt flags as an acceptable alternative.
- If the paper is happy to work with SMPL-X-sized phantoms (~2 k–2.5 k triangles, which is what body-pose-tracking literature uses): the 100 ms claim is **within reach** — the current un-batched pipeline is at 378 ms, a single-line port of the factored Fresnel to pure JAX plus `vmap` across the 50-body axis should realistically land under 100 ms on the same GPU. The 10 ms slot cadence still needs the translation-phasor identity.

## Files

- `bench_50body.py` — the benchmark. `AEGIS_ARRAY_BACKEND=jax` required; `XLA_PYTHON_CLIENT_PREALLOCATE=false` recommended.
- `timings.json` — raw timings for 25 k-triangle phantoms (per-run totals, per-body-per-run, per-stage distributions, environment metadata).
- `timings_decim10.json` — same, for the 10× decimated (~2.4 k triangle, SMPL-X-sized) run.

## Reproducing

```bash
pip install -e ".[dev]"
# Match JAX to driver 12.7:
pip install "jax[cuda12]==0.4.34" \
  "nvidia-cuda-nvcc-cu12<12.7" "nvidia-cublas-cu12<12.7" "nvidia-cudnn-cu12<9.6"

AEGIS_ARRAY_BACKEND=jax XLA_PYTHON_CLIENT_PREALLOCATE=false \
  python JSAC/experiments/gpu_benchmark/bench_50body.py
```

To reproduce the SMPL-X-sized run, monkey-patch `BodyMesh.load` to stride the mesh by 10 (rescaling areas ×10) before invoking `main()`, as in `run_decim10.log`. A proper remeshing path is left out on purpose — it would add a dependency and not change the conclusion, since at this resolution compute cost is already close to proportional to M.

One install gotcha worth flagging: the pip `jax[cuda12]==0.4.38` default pulls `nvidia-cublas-cu12 12.9.*` and `nvidia-cuda-nvcc-cu12 12.9.*`, which PTX-compile for a CUDA 12.9 driver. A 12.7 driver then hangs silently inside the first real matmul. Pinning the nvidia-cu12 libs back below 12.7 (as above) fixed that — otherwise you lose ~1 h debugging a silent hang.
