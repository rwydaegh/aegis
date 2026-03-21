# AEGIS roadmap

*Last updated: 2026-03-21. Living document. Update as decisions change.*

## Where we are

Phases 0-4 of the original implementation plan are done. The dosimetry engine
works: 9 fidelity levels, 240+ tests, Mie-validated physics, Flask+Three.js
viewer, DiffeRT and Sionna RT ray tracing backends, CLI batch runner.
Total: ~9,000 lines of Python (NumPy/SciPy + JAX).

Phase 1 (reproducible research backbone) is complete.
Phase 2a (JAX kernel migration) is complete. Tagged v0.4.0.

The original plan (docs/internal/implementation_plan.md) ends at Phase 6.
This document picks up from here with a revised direction.

## Key architectural decisions (settled)

These were debated in detail (see docs/internal/ideal_architecture.md) and
resolved:

1. **JAX is the compute layer.** The unique research contribution is a
   differentiable pipeline from ray tracing to absorbed power density.
   DiffeRT is JAX. The dosimetry kernels must also be JAX for gradients
   to flow end-to-end. Rust/WASM was considered and rejected because it
   kills differentiability.

2. **Ray tracer is pluggable.** PropagationPaths is the adapter interface.
   DiffeRT (JAX, differentiable, small scenes) and Sionna RT (Dr.Jit/Mitsuba,
   performant, large scenes) are both backends. End-to-end gradients through
   the ray tracer are a DiffeRT-only feature. Sionna RT provides the
   forward path only (no gradients through the channel).

3. **React frontend.** The 98KB single HTML file is replaced with a React +
   React Three Fiber + TypeScript app. FastAPI replaces Flask (async,
   WebSocket, Pydantic validation).

4. **Dataclass configs for reproducibility.** Every simulation run is defined
   by a frozen dataclass config (`SimulationConfig`), serialized to YAML,
   overridable from CLI. Hydra was considered and deferred. The dataclass
   approach gives reproducibility without the dependency. If sweeps or SLURM
   submission become needed, Hydra can slot in later because the dataclasses
   are already the right shape for hydra-zen.

5. **Server-side compute.** The browser renders. The server computes. No
   WASM, no Pyodide, no browser-side physics.

## Phases

### Phase 1: reproducible research backbone (DONE)

*Completed 2026-03-21.*

**1a. Dataclass config system**

Frozen dataclass hierarchy in `src/aegis/config.py`: TissueConfig, BodyConfig,
AntennaConfig, RayTracerConfig, DosimetryConfig, SimulationConfig. YAML
serialization via `to_yaml()` / `from_yaml()`. Validation in `__post_init__`.

**1b. CLI batch runner**

`python -m aegis.run --config runs/my.yaml` (also `aegis-run` console script).

- Loads body mesh, tissue model, propagation paths (synthetic/DiffeRT/Sionna)
- Runs `DosimetryEngine.compute()` at the specified fidelity level
- Saves resolved config, result.npz, and summary.json to timestamped output dir
- CLI overrides: `--level`, `--power-dbm`, `--backend`, `--body`, etc.

**1c. Sionna RT integration**

`src/aegis/integration/sionna.py` converts Sionna RT channel coefficients to
PropagationPaths. Uses a dual-polarized isotropic RX probe to capture the full
E-field polarisation state, then scales to absolute V/m:

```
psi = sqrt(8*pi*Z_0*P_T) / lambda * (a_theta * e_theta + a_phi * e_phi)
```

The (4*pi/lambda) factor corrects for the effective area difference between
Sionna's channel coefficient convention and the monograph's field-at-surface
convention. Verified numerically against the DiffeRT integration for LOS paths.

The viewer has a backend dropdown: scenes can be ray-traced with DiffeRT or
Sionna RT. Sionna requires Linux + GPU (TensorDock cloud machine).

### Phase 2a: JAX kernel migration (DONE)

*Completed 2026-03-21. Tagged v0.4.0.*

All 9 fidelity levels migrated to JAX backend. 236 tests pass. 3 gradient
smoke tests confirm `jax.grad` flows through levels 2 and 3.

**What was built:**

- `src/aegis/_array_backend.py` -- shim exporting `xp` (jax.numpy or numpy),
  `jit` (jax.jit or identity), `erf`, `JAX_AVAILABLE`. Enables x64 mode.
- `src/aegis/tissue/fresnel.py` -- full rewrite. Core computation in
  `_fresnel_core()` (pure xp, JIT-safe). Public wrappers add scalar
  convenience but are NOT called from inside JIT boundaries.
- `src/aegis/kernels/_base.py` -- `incidence_geometry()` and
  `fresnel_weights()` use xp. `fresnel_weights` calls `_fresnel_core`
  directly (not `fresnel_transmission`, which has non-JIT-safe branching).
- Levels 0, 2, 3, 4, 5, 6 have `@jit`. Level 1 stays non-JIT (scipy SH).
- `src/aegis/coherent/` -- fresnel_operator calls `_fresnel_core`.
  field_channel and body_channel have JAX scatter-add (`jnp.at[].add`)
  with NumPy loop fallback, selected by `JAX_AVAILABLE` flag.
- `src/aegis/coherent/ecbf.py` -- stays NumPy. Bisection solver is
  inherently non-JIT-traceable. Returns `xp.asarray()` at the boundary.
- `src/aegis/engine.py` -- `_to_numpy()` converts JAX arrays back to NumPy
  at the engine output boundary before `DosimetryResult` construction.
- `tests/test_jax_grad.py` -- 3 gradient smoke tests (skipif no JAX).
- `pyproject.toml` -- `jax` optional dependency group added.

**Architecture: two call paths through Fresnel**

This is the most important thing to understand for Phase 2b:

1. **JIT path** (levels 2-6 kernels): `_base.py::fresnel_weights` calls
   `_fresnel_core` directly. Pure `xp`, no scalar checks, no `np.asarray`.
   This path is fully JIT-traceable and differentiable.

2. **Non-JIT path** (engine config, tests, scalar queries): public functions
   `fresnel_transmission`, `fresnel_reflection`, `fresnel_amplitude` wrap
   `_fresnel_core` with `np.asarray` input, scalar output, ndim branching.
   These are NOT called from inside JIT boundaries.

If you add a new kernel or optimization path, always use `_fresnel_core`
or `fresnel_weights`, never the public wrappers.

**What is NOT fully JIT'd (and why)**

- Level 1: calls `scipy` spherical harmonics (`eval_sh`). Not JIT-traceable.
  Low priority -- level 1 is a coarse aggregate, rarely used in optimization.
- Levels 7-8: the coherent pipeline has `if JAX_AVAILABLE:` branching in
  `field_channel.py` and `body_channel.py` to select between JAX scatter-add
  and NumPy loop. The functions themselves are not `@jit` decorated. The
  individual operations (einsum, phase computation) use `xp` and are
  JIT-compatible, but the accumulate-by-element step uses different code
  paths. To make this fully JIT'd, you would need to remove the branching
  and always use JAX scatter-add (dropping the NumPy fallback).
- ECBF solver (`ecbf.py`): bisection with Python while-loop. Not
  JIT-traceable. To make this differentiable, you would need to replace
  the bisection with a fixed-point iteration (e.g., `jax.lax.while_loop`)
  or use implicit differentiation (`jax.custom_vjp`). This is the hardest
  remaining task for full differentiability through level 8.
- `exposure_operator.py::compute_rho` and `eigendecompose_Q`: use `xp`
  throughout (einsum, eigh, argsort). These are JIT-compatible but not
  `@jit` decorated because they are called from level7/level8 which have
  non-JIT code paths. If you isolate them, they can be JIT'd.

**Gotchas for future work**

- JAX defaults to float32. The backend shim sets `jax_enable_x64 = True`
  at import time. This is required for physics accuracy. Do not remove it.
- `xp.asarray(mu, dtype=complex)` is used in `_fresnel_core` and
  `fresnel_weights` to cast real incidence cosines to complex (Fresnel
  needs complex arithmetic). If you see unexpected dtypes, check this cast.
- `xp.full(n_triangles, value)` in level 0 needs `n_triangles` as a
  concrete int (not a traced value). Hence `static_argnums=(0,1,2,4,5)`
  on the `@jit` decorator. If you change the signature, update static_argnums.
- The pre-existing `test_voxel_pipeline::test_parse_reads_unit_from_metadata`
  test fails due to test-ordering pollution from `test_viewer_auth.py`
  contaminating global config state. It passes in isolation. Not related
  to JAX migration. Fix by adding proper test isolation (fixture teardown).

**Test count:** 236 pass, 1 pre-existing failure, 25 skipped (slow/mesh).

### Phase 2b: differentiable optimization API

*Priority: high. Depends on 2a (done). This is the paper.*

**2b. Differentiable optimization API**

The kernels are JAX. `jax.grad` flows through levels 2 and 3 (verified by
smoke tests). Now expose optimization as a first-class feature:

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
   precoder x. The forward path (G_tilde @ x -> S_ab) is already xp-native.
   But the engine wraps it in `_to_numpy()` and the coherent pipeline has
   `JAX_AVAILABLE` branching. For optimization, call the kernel directly
   (bypass the engine), or add a `jax_mode=True` flag that skips conversion.

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

**2c. Spatial averaging boundary**

The ICNIRP 4 cm^2 spatial averaging uses scipy.spatial.cKDTree. This is
not JAX-traceable and does not need to be.

- Spatial averaging is a post-processing step applied to the final S_ab.
- You optimize the raw S_ab (or its max, or a percentile). The averaged
  S_ab is for compliance reporting, not for the loss function.
- Keep spatial averaging in NumPy. Put it outside the jax.grad boundary.

If a future paper needs gradients through spatial averaging, implement a
fixed-radius neighbor sum in pure JAX (differentiable but approximate).
Do not do this preemptively.

### Phase 3: React frontend

*Priority: medium. Independent of Phase 2. Can be done in parallel.*

**3a. React + React Three Fiber + Vite scaffold**

New `aegis-web/` directory. Components:

- Scene view (R3F): body mesh with S_ab vertex colors, ray paths, draggable
  antenna, environment geometry
- Control panel: level selector, tissue, power, frequency
- Compliance dashboard: ICNIRP pass/fail, margin, spatial stats
- Optimization view (later): gradient descent visualization

Tech: React, TypeScript, React Three Fiber, Vite, Zustand (state), shadcn/ui
(components).

**3b. FastAPI replaces Flask**

- Async request handling
- WebSocket endpoint for live dosimetry (drag antenna, see S_ab update)
- Pydantic models for request/response validation
- Automatic OpenAPI documentation
- Serves built React assets as static files

**3c. Bundle into pip install**

`pip install aegis` includes the pre-built frontend assets. `python -m
aegis.viewer` launches the FastAPI server and opens the browser. Same
user experience as today, but with a real frontend.

R3F is justified over raw Three.js because the UI has growing complexity
(controls, dashboards, interactivity). Two build systems (Python + Node)
is annoying but standard.

### Phase 4: scale and infrastructure

*Priority: lower. Add when the need arises, not before.*

**4a. HPC/SLURM execution**

- Hydra (added at this point, not before) for sweep configs and SLURM submission
- `python -m aegis.run --multirun city=ghent,antwerp hydra/launcher=submitit_slurm`
- JAX's `jax.distributed.initialize()` for multi-GPU (auto-reads SLURM env)
- Environment management: pixi or conda-lock for reproducible CUDA/JAX

**4b. Experiment tracking (wandb)**

Add when running enough experiments that filesystem-based tracking becomes
unmanageable. Two-line integration:

```python
wandb.init(project="aegis", config=cfg.to_dict())
wandb.log({"sab_max": result.sab.max(), "p_abs": result.p_abs})
```

Do not add preemptively. The batch runner's auto-saved configs are sufficient
for the first papers.

**4c. Data versioning (DVC)**

Add when phantom meshes or scene data outgrow git. Currently the data/
directory is manageable. DVC becomes valuable when you have dozens of
city scenes and multiple phantom versions.

**4d. City-scale campaigns**

The long-term vision: ray tracing over many cities, statistical analysis
of exposure patterns, MIMO with moving bodies.

- Sionna RT for large scenes (O(log N) BVH, diffraction, scattering)
- Batch configs per city/scenario
- vmap over body positions for time-varying exposure
- pmap across GPUs for parallel scenarios
- Statistical post-processing: distributions, symmetry analysis

## What we are NOT doing

- **Rust/WASM.** Kills differentiability. The compute stays in JAX/Python.
  If we ever need a zero-install browser demo, revisit, but it's not on
  the roadmap.

- **WebGPU compute shaders.** Server-side JAX is fast enough. No need to
  run physics in the browser.

- **Custom CUDA kernels.** JAX's XLA compiler handles GPU optimization.
  Writing custom CUDA is premature.

- **wandb/DVC/pixi now.** Add when the need is real, not as preventive
  infrastructure.

- **Hydra now.** Deferred to Phase 4. Dataclass configs + argparse + YAML
  are sufficient for reproducibility. Hydra adds value only when sweeps
  or SLURM submission are needed.

- **Rewriting tests.** The 240+ existing tests validate NumPy output. The
  JAX migration preserved all golden values. Tests stay NumPy-based.
  JAX-specific tests (gradient smoke tests) are in `tests/test_jax_grad.py`
  and skip when JAX is not installed.

## Sequencing and dependencies

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

Phase 2b is unblocked. Phase 3 can proceed in parallel (different files).
Phase 4 waits until the need is clear.

## Open questions

1. **What is the first paper about?** The sequencing depends on this.
   If it's "differentiable dosimetry pipeline," JAX migration (Phase 2)
   is critical path. If it's "multi-level exposure analysis across cities,"
   Sionna RT is already available.

2. **How important is antenna placement optimization vs. beamforming
   optimization?** Antenna placement needs differentiable ray tracing
   (DiffeRT only, small scenes). Beamforming needs differentiable
   dosimetry but not differentiable ray tracing (works with Sionna RT
   too). The answer affects how much we invest in DiffeRT vs. Sionna.

3. **Exposure-aware optimization at intermediate levels.** What does
   optimization at level 2 or 3 look like concretely? Minimizing peak
   S_ab over antenna position? Optimizing a precoder with a simplified
   absorption model? This shapes the JAX migration priority order.
