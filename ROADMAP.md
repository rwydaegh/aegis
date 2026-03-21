# AEGIS roadmap

*Last updated: 2026-03-21. Living document. Update as decisions change.*

## Where we are

The dosimetry engine is feature-complete: 9 fidelity levels, 240+ tests,
Mie-validated physics, Flask+Three.js viewer, DiffeRT and Sionna RT ray
tracing backends, dataclass configs, CLI batch runner. ~9,000 lines of
Python.

Everything through Phase 2a is done (v0.4.0). All kernels run on JAX.
`jax.grad` flows through the incoherent pipeline (levels 0-6). Phase 2b
(differentiable optimization API) is next.

## Key architectural decisions (settled)

1. **JAX is the compute layer.** Differentiable pipeline from ray tracing
   to absorbed power density. DiffeRT is JAX. Dosimetry kernels are JAX.
   Rust/WASM rejected (kills differentiability).

2. **Ray tracer is pluggable.** PropagationPaths is the adapter interface.
   DiffeRT (JAX, differentiable, small scenes) and Sionna RT (Dr.Jit,
   performant, large scenes). End-to-end gradients are DiffeRT-only.

3. **React frontend** (Phase 3). React Three Fiber + FastAPI replaces
   Flask + single HTML file.

4. **Dataclass configs.** Frozen dataclass hierarchy, YAML serialization,
   CLI overrides. Hydra deferred to Phase 4.

5. **Server-side compute.** Browser renders, server computes.

## Completed phases

- **Phase 1** (reproducible research backbone): dataclass configs, CLI batch
  runner, Sionna RT integration, viewer backend dropdown. Done.
- **Phase 2a** (JAX kernel migration): all 9 levels migrated. v0.4.0. Done.
  See handoff notes below.

## Phase 2a handoff notes (for Phase 2b)

### What was built

- `src/aegis/_array_backend.py` -- shim exporting `xp` (jax.numpy or numpy),
  `jit` (jax.jit or identity), `erf`, `JAX_AVAILABLE`. Enables x64 mode.
- `src/aegis/tissue/fresnel.py` -- full rewrite. Core computation in
  `_fresnel_core()` (pure xp, JIT-safe). Public wrappers add scalar
  convenience but are NOT called from inside JIT boundaries.
- `src/aegis/kernels/_base.py` -- `incidence_geometry()` and
  `fresnel_weights()` use xp. `fresnel_weights` calls `_fresnel_core`
  directly (not `fresnel_transmission`, which has non-JIT-safe branching).
- `src/aegis/coherent/` -- fresnel_operator calls `_fresnel_core`.
  field_channel and body_channel have JAX scatter-add (`jnp.at[].add`)
  with NumPy loop fallback.
- `src/aegis/coherent/ecbf.py` -- stays NumPy (bisection solver).
- `src/aegis/engine.py` -- `_to_numpy()` converts JAX arrays back to NumPy
  at the engine output boundary before `DosimetryResult` construction.
- `tests/test_jax_grad.py` -- 3 gradient smoke tests (skipif no JAX).
- `pyproject.toml` -- `jax` optional dependency group added.

### JIT and differentiability status

**JIT** (`@jit` decorated, compiled to XLA) and **differentiable** (`jax.grad`
works through them) are related but separate concepts. A function can be
differentiable without being `@jit` compiled -- it just runs eagerly instead
of as one fused kernel.

| Level | @jit | Differentiable | Notes |
|-------|------|----------------|-------|
| 0     | Yes  | Yes            | `static_argnums` for shape params |
| 1     | No   | No             | Calls scipy SH (`eval_sh`). Coarse aggregate, low priority. |
| 2     | Yes  | Yes            | The workhorse. Gradient smoke-tested. |
| 3     | Yes  | Yes            | Fresnel. Gradient smoke-tested. |
| 4     | Yes  | Yes            | Same pattern as 3, adds polarisation term. |
| 5     | Yes  | Yes            | Same pattern, adds curvature term. |
| 6     | Yes  | Yes            | Uses `erf` from backend shim. |
| 7     | No   | Partially      | Forward path (G_tilde @ x -> S_ab) is differentiable. Not `@jit` because shape params (M, n_elements) would need `static_argnums` on large orchestrator functions. |
| 8     | No   | Partially      | Same as 7 for forward path. ECBF bisection solver is NOT differentiable (Python while-loop). |

**Levels 0-6 are fully differentiable.** `jax.grad` works for any scalar
loss function of their output (tested for 2 and 3, but 4-6 use the exact
same xp operations and `_base.py` helpers).

**Levels 7-8 forward path is differentiable.** The computation
`S_ab = ||G_tilde @ x||^2` uses xp operations (einsum, scatter-add, exp,
sqrt, conj) that are all individually differentiable. So `jax.grad` of S_ab
w.r.t. precoder x works even without `@jit`. What does NOT work is
differentiating through the ECBF solver (level 8) which finds the optimal
x* -- that uses a Python bisection loop.

**Why levels 7-8 are not `@jit`:** The coherent pipeline orchestrator
functions (`compute_body_channel`, `level7_coherent`) take shape parameters
like `n_elements` that are used in `jnp.zeros((M, 3, n_elements))`. These
need to be concrete at JIT trace time, requiring `static_argnums` on
functions with 10+ arguments. The `if JAX_AVAILABLE:` branching in the
accumulate-by-element step is NOT a JIT blocker (it's a Python-level
constant resolved at trace time), but the functions were left un-JIT'd for
simplicity. They can be JIT'd later if performance demands it.

### Two call paths through Fresnel

This is the most important architectural detail:

1. **JIT path** (levels 2-6 kernels): `_base.py::fresnel_weights` calls
   `_fresnel_core` directly. Pure `xp`, no scalar checks, no `np.asarray`.
   Fully JIT-traceable and differentiable.

2. **Non-JIT path** (tests, scalar queries): public functions
   `fresnel_transmission`, `fresnel_reflection`, `fresnel_amplitude` wrap
   `_fresnel_core` with `np.asarray` input, scalar output, ndim branching.
   NOT called from inside JIT boundaries.

If you add a new kernel or optimization path, always use `_fresnel_core`
or `fresnel_weights`, never the public wrappers.

### Gotchas

- JAX defaults to float32. The backend shim sets `jax_enable_x64 = True`
  at import time. Required for physics accuracy. Do not remove.
- `xp.asarray(mu, dtype=complex)` in `_fresnel_core` and `fresnel_weights`
  casts real incidence cosines to complex (Fresnel needs complex arithmetic).
- `xp.full(n_triangles, value)` in level 0 needs `n_triangles` as a
  concrete int. Hence `static_argnums=(0,1,2,4,5)` on the `@jit` decorator.
- Pre-existing test failure: `test_voxel_pipeline::test_parse_reads_unit_from_metadata`
  fails due to test-ordering pollution from `test_viewer_auth.py`. Passes
  in isolation. Not related to JAX migration.

### Test count

236 pass, 1 pre-existing failure, 25 skipped (slow/mesh).

## Phase 2b: differentiable optimization API

*Priority: high. Depends on 2a (done). This is the paper.*

The kernels are JAX. `jax.grad` flows through levels 0-6 (verified for 2, 3).
Now expose optimization as a first-class feature:

```python
def exposure_loss(antenna_pos, scene, body, level):
    paths = differt_trace(scene, antenna_pos)
    result = engine.compute(body, paths, level=level)
    return result.sab.max()

grad_fn = jax.grad(exposure_loss)
```

This works at any fidelity level. Level 2 with jax.grad gives "cheap gradient
of geometric absorption with respect to antenna position." Level 8 with
jax.grad gives "gradient of optimal ECBF exposure with respect to antenna
position." Different costs, different fidelity, same API.

**Remaining work for full differentiability:**

1. **Beamforming optimization (levels 7-8):** gradient of S_ab w.r.t.
   precoder x. The forward path (G_tilde @ x -> S_ab) is already xp-native
   and differentiable. But the engine wraps output in `_to_numpy()`. For
   optimization, call the kernel directly (bypass the engine), or add a
   `jax_mode=True` flag that skips NumPy conversion.

2. **ECBF differentiability (level 8):** The bisection solver in `ecbf.py`
   is not differentiable. Two options:
   - `jax.custom_vjp`: define the backward pass analytically using implicit
     function theorem (the QCQP KKT conditions give dx*/dlambda).
   - `jax.lax.while_loop`: rewrite bisection as a JAX-traceable loop.
   The first option is cleaner and numerically stable.

3. **DiffeRT end-to-end:** DiffeRT is JAX, so `jax.grad` should flow
   from dosimetry back through the ray tracer to antenna position.
   Open question: DiffeRT's exhaustive path enumeration has discrete
   topology changes (paths appear/disappear). Gradients through these
   discontinuities may be zero or undefined. Verify with a simple test
   case before building a paper around it.

**Spatial averaging boundary**

The ICNIRP 4 cm^2 spatial averaging uses scipy.spatial.cKDTree. Not
JAX-traceable and does not need to be. Spatial averaging is post-processing
for compliance reporting, not for the loss function. Keep it in NumPy,
outside the jax.grad boundary.

## Phase 3: React frontend

*Priority: medium. Independent of Phase 2. Can be done in parallel.*

**3a. React + React Three Fiber + Vite scaffold**

New `aegis-web/` directory. Components: scene view (R3F), control panel,
compliance dashboard, optimization view (later).

**3b. FastAPI replaces Flask**

Async, WebSocket for live dosimetry, Pydantic validation, auto OpenAPI docs.

**3c. Bundle into pip install**

Pre-built frontend assets served by FastAPI. Same UX as today.

## Phase 4: scale and infrastructure

*Priority: lower. Add when the need arises, not before.*

- **HPC/SLURM:** Hydra for sweep configs, `jax.distributed` for multi-GPU
- **wandb:** when filesystem tracking becomes unmanageable
- **DVC:** when mesh/scene data outgrows git
- **City-scale campaigns:** Sionna RT for large scenes, vmap over body
  positions, pmap across GPUs

## What we are NOT doing

- **Rust/WASM.** Kills differentiability.
- **WebGPU compute shaders.** Server-side JAX is fast enough.
- **Custom CUDA kernels.** JAX XLA handles GPU optimization.
- **wandb/DVC/Hydra now.** Add when the need is real.
- **Rewriting tests.** Tests stay NumPy-based golden checks. JAX-specific
  tests (gradients) are in `tests/test_jax_grad.py`, skip when no JAX.

## Sequencing

```
Phase 1  (backbone) ──── DONE ────────────┐
                                          │
Phase 2a (JAX kernels) ── DONE (v0.4.0) ──┤
                                          ├── paper-ready
Phase 2b (differentiable opt) ── NEXT ────┤
                                          │
Phase 3  (React frontend) ── independent ─┘ (parallel track)

Phase 4  (HPC, wandb, DVC) ── when needed
```

## Open questions

1. **What is the first paper about?** If "differentiable dosimetry pipeline,"
   Phase 2b is critical path. If "multi-level exposure analysis across
   cities," Sionna RT is already available.

2. **Antenna placement vs. beamforming optimization?** Antenna placement
   needs differentiable ray tracing (DiffeRT only, small scenes). Beamforming
   needs differentiable dosimetry only (works with Sionna RT too).

3. **Exposure-aware optimization at intermediate levels.** What does
   optimization at level 2 or 3 look like concretely? Minimizing peak
   S_ab over antenna position? Optimizing a precoder with a simplified
   absorption model?
