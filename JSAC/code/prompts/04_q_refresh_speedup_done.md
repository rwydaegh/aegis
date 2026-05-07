# 04 — Q-refresh speedup, done

Companion to `prompts/04_q_refresh_speedup.md`. What was built, why it lands where it does, and what still needs the RTX 3090 to close out.

## What landed

### `src/aegis/coherent/_fast.py` (lever a: factored Fresnel + vmap)

Pure-JAX path that supersedes `compute_body_channel_factored` (which used a Python `for c in range(N_center)` plus `np.add.at` and so couldn't JIT cleanly) and `compute_body_channel` on element-expanded paths (which redoes Fresnel `M_ant`× more times than necessary).

Two structural moves:

1. **Fresnel factored over directions, not paths.** `compute_fresnel_operator(normals, k_hat, n_tilde)` only sees `N_center` unique directions. The per-element steering — `exp(+i k0 k_hat[c] · offset[j])` — is folded into the *final* contraction.
2. **Closed-form einsum, no scatter.** With (1), `G_tilde(r)` reduces to
   ```
   G_tilde[m, i, j] = einsum('mc,mci,cj->mij', scalar, F_psi_center, phase_advance)
   ```
   No `np.add.at`, no host-side loop, no `(M_tri, 3, M_ant)` zero-init scatter destination. Pure functional.

`compute_q_batch_vmap` then lifts to a `jax.vmap` over the leading body axis, collapsing the 50 host dispatches in `bench_50body.py` into a single device dispatch.

Output is bit-equivalent (up to fp64 round-off) to `compute_body_channel` evaluated on `expand_paths_to_array(center_paths, array, freq_hz)`. See test below.

### `src/aegis/coherent/translation.py` (lever b: translation phasor)

Implements paper §III.C eq:Mphase: `M(t) = Φ(t)^H M(0) Φ(t)` with `Φ(t) = diag(φ[c])`, `φ[c] = exp(-i k0 k_hat[c]·Δt)`.

Three entry points:

- `compute_static_path_gram(...)` — builds `M_static[c, d, a, b]`, the area-weighted, Fresnel-and-depth-baked Gram in `(N_c, N_c, M_ant, M_ant)` shape. Called once per (body geometry, pose) at pose cadence.
- `translation_phasor(center_k_hat, delta_t, freq_hz)` — `(N_c,)` complex exponentials. Cheap.
- `q_translate(M_static, phi)` and `q_translate_batch(M_static_b, phi_b)` — slot-cadence refresh:
  ```
  Q(Δt) = einsum('c,d,cdab->ab', conj(φ), φ, M_static)
  ```
  One small einsum per body, no Fresnel, no surface integration.

`M_static` size at the benchmark scenario (`N_c=10`, `M_ant=64`, complex128): 6.6 MB per body, 330 MB for 50 bodies. Fits one workstation GPU comfortably; can drop to complex64 for half that if needed.

Caller owns the cache lifetime — translation.py exposes the kernels but does not policy how long `M_static` stays on device. That belongs to whatever scheduler the plaza_run pulls together (brief 08).

Exported via `aegis.coherent` public namespace alongside the existing coherent kernels.

### Tests

`tests/test_coherent_fast.py`, five equivalence checks:

| Test | What it pins |
|---|---|
| `test_factored_jax_matches_compute_body_channel` | Factored-JAX ≡ `compute_body_channel` on `expand_paths_to_array` output |
| `test_vmap_q_matches_per_body` | `compute_q_batch_vmap` ≡ per-body `compute_q_for_body` for every body in the batch |
| `test_translation_phasor_matches_recompute` | `q_translate(M_static, φ(Δt))` ≡ rebuilding Q at translated centroids |
| `test_translation_zero_recovers_static` | Δt = 0 reproduces Q at the cache pose |
| `test_translation_batch_matches_per_body` | Batched translation refresh ≡ single-body refresh per element |

Module-level skip if `AEGIS_ARRAY_BACKEND` isn't `jax` (the kernels share `xp` with `compute_fresnel_operator`, which won't trace under the numpy backend).

### Benchmark + README

`JSAC/code/experiments/gpu_benchmark/bench_50body_fast.py` mirrors `bench_50body.py`'s scenario (50 Thelonious copies on a 20–80 m ring, 8×8 patch UPA at 26 GHz, decim-10 by default via `AEGIS_BENCH_DECIM`) but routes through `compute_q_batch_vmap` and the `M_static` + `q_translate_batch` warm path. Outputs land in `timings_after_speedup.json` next to the existing baselines.

The README in `gpu_benchmark/` got an "After-speedup variant (prompt 04)" section explaining what each lever does, what file it lives in, and how to invoke the new bench.

## How to validate on the workstation

```bash
AEGIS_ARRAY_BACKEND=jax python -m pytest tests/test_coherent_fast.py -v
AEGIS_ARRAY_BACKEND=jax XLA_PYTHON_CLIENT_PREALLOCATE=false \
  python JSAC/code/experiments/gpu_benchmark/bench_50body_fast.py
```

Set `AEGIS_BENCH_DECIM=1` to push at the full 25 k-tri Thelonious mesh; the default 10× stride matches `timings_decim10.json`.

## What I deliberately did not do

- **No public `Q.translate(Δt)` method.** The brief left this open ("expose only what brief 08 will plausibly call"). Until plaza_run is wired up I left the API as functional (pass `M_static` and `φ` explicitly) so the caller decides where to store the cache. Wrapping in a class is a one-screen change once 08 has shape requirements.
- **No deletion of `compute_body_channel_factored`.** Kept for backward compatibility with existing tests (`tests/test_coherent.py::TestFactoredBodyChannel`); `_fast.py` is the new, JIT-clean path that other code should use going forward. The old function still works, it's just not the thing to JIT.
- **No NumPy-backend fallback for the new kernels.** They depend on `jax.vmap`. Tests skip cleanly when the backend is numpy. The benchmark's whole reason to exist is GPU throughput; making it run efficiently on numpy would be misleading.
- **No multi-GPU, no quantisation, no memory-map of `M_static`.** Out of scope; the brief is single-workstation-GPU, fp64.

## What still needs Robin's GPU

The CPU smoke run on a small synthetic batch (B=5 bodies, M=200 triangles, M_ant=16) confirms the structural shape — single hot vmap dispatch ≈ 2 ms, translation refresh ≈ 0.7 ms — but the paper number lives at B=50, M≈2.4 k (decim-10) or 25 k (full Thelonious), M_ant=64. That has to be measured on the same RTX 3090 as `timings.json` / `timings_decim10.json` for the comparison to be honest.

The `bench_50body_fast.py` summary block prints `Fits 100 ms pose cadence (cold)? YES/NO` and `Fits 10 ms slot cadence (warm)? YES/NO` so the answer is unambiguous. The JSON has p10/p50/p90 + the `M_static` build cost + first-call compile time. If the 100 ms claim still doesn't land at decim-10 after the speedup, the warm-path numbers (which should be a few ms) carry the cadence story regardless.

## Test sweep

`python -m pytest tests/ -m "not slow" --ignore=tests/test_multibody_ecbf.py` → 3092 passed, 26 skipped, no regressions outside another agent's in-progress prompt 03 work (`multibody_ecbf.py`, `sensing/`).

## Files touched

- `src/aegis/coherent/_fast.py` (new)
- `src/aegis/coherent/translation.py` (new)
- `src/aegis/coherent/__init__.py` (added translation re-exports alongside the parallel agent's multibody_ecbf re-exports)
- `tests/test_coherent_fast.py` (new)
- `JSAC/code/experiments/gpu_benchmark/bench_50body_fast.py` (new)
- `JSAC/code/experiments/gpu_benchmark/README.md` (added after-speedup section)
