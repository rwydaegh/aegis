# AEGIS roadmap

*Last updated: 2026-03-21. Living document. Update as decisions change.*

## Where we are

Phases 0-4 of the original implementation plan are done. The dosimetry engine
works: 9 fidelity levels, 200+ tests, Mie-validated physics, Flask+Three.js
viewer, optional DiffeRT ray tracing. Total: ~8,200 lines of Python (NumPy/SciPy).

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

4. **Hydra for configuration and reproducibility.** Every simulation run is
   defined by a YAML config, overridable from CLI, automatically logged.
   This is the foundation for reproducible papers and HPC batch execution.

5. **Server-side compute.** The browser renders. The server computes. No
   WASM, no Pyodide, no browser-side physics.

## Phases

### Phase 1: reproducible research backbone

*Priority: highest. This is what lets us publish papers.*

**1a. Hydra config management**

Replace the current JSON/argparse config system with hydra-zen.

- Define dataclass configs for: simulation parameters (level, frequency,
  tissue, power), scene selection, body model, ray tracer backend, output
  format.
- `python -m aegis.run level=3 body=duke frequency=28e9` runs a simulation.
- `--multirun city=ghent,antwerp body=duke,ella level=2,3,6` runs 18 jobs.
- Hydra auto-logs the resolved config alongside each run.
- The viewer config (viewer/config.py) stays separate for now. Hydra is for
  simulation runs, not the interactive viewer.

Adversarial check: *Is Hydra overkill for a solo researcher?* No. The
alternative is hand-rolled argparse + JSON, which is what we have now, and
it doesn't compose, doesn't log, and doesn't support sweeps. Hydra is
configure-once infrastructure. The learning curve is real but bounded.

**1b. CLI batch runner**

`python -m aegis.run` as a Hydra-driven entry point.

- Loads scene (voxel or Sionna XML)
- Runs ray tracing (DiffeRT or Sionna RT, selected by config)
- Computes dosimetry at specified level
- Saves results: S_ab array, metadata, resolved config YAML
- Output directory: `outputs/{date}/{run_id}/` (Hydra default)

This is the script you run on HPC. No viewer, no web server. Pure batch.

**1c. Sionna RT integration**

Write `src/aegis/integration/sionna.py`, mirroring the DiffeRT integration
pattern.

- Load Sionna scene (XML or programmatic)
- Call Sionna RT path computation
- Convert output to PropagationPaths (k_hat, psi, element_index)
- Handle materials, reflection orders, diffraction paths
- Support both CPU (Embree BVH) and GPU (OptiX) backends

Adversarial check: *Is Sionna RT actually needed before the first paper?*
Depends on the paper. If it's about the differentiable pipeline, DiffeRT
alone is sufficient. If it's about city-scale exposure analysis, Sionna RT
is required (DiffeRT's O(N^K) can't handle large scenes). Verdict: start
the integration early because scene loading and path format conversion are
non-trivial, and you don't want it blocking paper results.

Also: *Sionna RT's API may change.* It went through a major rewrite from
v1 (TensorFlow) to v2 (Mitsuba 3/Dr.Jit). Pin the version and isolate
the integration in one file, same as we did with DiffeRT.

### Phase 2: JAX migration

*Priority: high. This is the unique scientific contribution.*

**2a. Kernel-by-kernel migration**

Migrate incoherent kernels (0-6) first, then coherent (7-8).

- Replace `import numpy as np` with `import jax.numpy as jnp` in each
  kernel file.
- Add `@jax.jit` to the kernel entry point.
- Run existing test suite after each kernel. Golden values must match
  within float64 tolerance.
- Keep a NumPy fallback: if JAX is not installed, the engine dispatches
  to the original NumPy kernels. This preserves `pip install aegis` without
  JAX as a core dependency.

Migration order (by complexity):
1. Level 0 (bound) -- trivial, one scalar reduction
2. Level 2 (geometric) -- the workhorse, matrix multiply
3. Level 1 (aggregate) -- spherical harmonics
4. Level 3 (Fresnel) -- complex Fresnel T(theta)
5. Level 4 (polarisation) -- small extension of level 3
6. Level 5 (curvature) -- adds curvature term
7. Level 6 (diffraction) -- needs jax.scipy.special.erf
8. Level 7 (coherent) -- complex field channel, einsum
9. Level 8 (ECBF) -- needs differentiable eigendecomp + Brent solver

Adversarial check: *Is "mostly mechanical" actually true?* For levels 0-6,
yes. They are pure array operations (dot products, einsum, element-wise
functions). JAX has all of these. For level 8, no. The ECBF solver uses
scipy.optimize.brentq (not in JAX) and the eigendecomposition needs to be
differentiable (jax.numpy.linalg.eigh works but has known numerical edge
cases for degenerate eigenvalues). Level 8 is the hard one. Budget extra
time for it.

Also: *JAX on Windows.* The developer machine runs Windows 11. JAX CPU
works on Windows. JAX GPU requires WSL2 or Linux. For local development
this is fine (CPU is fast enough for testing). For HPC you're on Linux
anyway.

**2b. Differentiable optimization API**

Once kernels are JAX, expose optimization as a first-class feature:

```python
def exposure_loss(antenna_pos, scene, body, level):
    paths = differt_trace(scene, antenna_pos)
    result = engine.compute(body, paths, level=level)
    return result.sab.max()

grad_fn = jax.grad(exposure_loss)
```

This works at any fidelity level, not just level 8. Level 2 with jax.grad
gives you "cheap gradient of geometric absorption with respect to antenna
position." Level 8 with jax.grad gives you "gradient of optimal ECBF
exposure with respect to antenna position." Different costs, different
fidelity, same API.

Adversarial check: *Can you actually differentiate through DiffeRT's
compute_paths?* In principle yes (it's JAX). In practice, DiffeRT's
exhaustive path enumeration has discrete topology changes (paths appear
and disappear as geometry changes). Gradients through these discontinuities
may be zero or undefined. This is a known challenge in differentiable
rendering. DiffeRT may handle it (it's designed for this), but verify
with a simple test case before building a paper around it.

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

*Priority: medium. Independent of Phases 1-2. Can be done in parallel.*

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

Adversarial check: *Is React Three Fiber actually necessary?* R3F is a
thin wrapper over Three.js. For our use case (one body mesh, a few ray
paths, one antenna), raw Three.js would work fine. R3F's value is in
state management (React reconciler batches updates) and the ecosystem
(drei helpers for camera controls, instanced rendering, etc.). For a
growing, component-based UI, R3F pays off. For a static visualization,
it's overhead. Given we want controls, dashboards, and interactivity,
R3F is justified.

Also: *Two build systems (Python + Node).* This is annoying but standard.
The React app builds to static files (one command: `npm run build`). The
Python package includes these files. CI builds both. It's manageable.

### Phase 4: scale and infrastructure

*Priority: lower. Add when the need arises, not before.*

**4a. HPC/SLURM execution**

- Hydra's submitit launcher plugin for SLURM job submission
- `python -m aegis.run --multirun city=ghent,antwerp hydra/launcher=submitit_slurm`
- JAX's `jax.distributed.initialize()` for multi-GPU (auto-reads SLURM env)
- Environment management: pixi or conda-lock for reproducible CUDA/JAX

**4b. Experiment tracking (wandb)**

Add when running enough experiments that filesystem-based tracking becomes
unmanageable. Two-line integration:

```python
wandb.init(project="aegis", config=resolved_hydra_config)
wandb.log({"sab_max": result.sab.max(), "p_abs": result.p_abs})
```

Do not add preemptively. Hydra's auto-logged configs are sufficient for
the first papers.

**4c. Data versioning (DVC)**

Add when phantom meshes or scene data outgrow git. Currently the data/
directory is manageable. DVC becomes valuable when you have dozens of
city scenes and multiple phantom versions.

**4d. City-scale campaigns**

The long-term vision: ray tracing over many cities, statistical analysis
of exposure patterns, MIMO with moving bodies.

- Sionna RT for large scenes (O(log N) BVH, diffraction, scattering)
- Batch Hydra configs per city/scenario
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

- **Rewriting tests.** The 200+ existing tests validate NumPy output. During
  JAX migration, these tests validate that JAX output matches. Do not
  rewrite tests in JAX. Keep them as NumPy-based golden checks.

## Sequencing and dependencies

```
Phase 1a (Hydra) ─────────────────────────┐
Phase 1b (CLI runner) ──── needs 1a ──────┤
Phase 1c (Sionna RT) ──── independent ────┤
                                          ├── paper-ready
Phase 2a (JAX kernels) ── independent ────┤
Phase 2b (differentiable opt) ── needs 2a ┤
                                          │
Phase 3  (React frontend) ── independent ─┘ (parallel track)

Phase 4  (HPC, wandb, DVC) ── when needed
```

Phases 1a/1b, 1c, 2a, and 3 can all proceed in parallel. They touch
different parts of the codebase with no conflicts. Phase 2b needs 2a
(JAX kernels). Phase 1b needs 1a (Hydra config). Phase 4 waits until
the need is clear.

## Open questions

1. **What is the first paper about?** The sequencing depends on this.
   If it's "differentiable dosimetry pipeline," JAX migration (Phase 2)
   is critical path. If it's "multi-level exposure analysis across cities,"
   Sionna RT (Phase 1c) is critical path.

2. **How important is antenna placement optimization vs. beamforming
   optimization?** Antenna placement needs differentiable ray tracing
   (DiffeRT only, small scenes). Beamforming needs differentiable
   dosimetry but not differentiable ray tracing (works with Sionna RT
   too). The answer affects how much we invest in DiffeRT vs. Sionna.

3. **Exposure-aware optimization at intermediate levels.** You noted that
   optimization is not just a level-8 thing. What does optimization at
   level 2 or 3 look like concretely? Minimizing peak S_ab over antenna
   position? Optimizing a precoder with a simplified absorption model?
   This shapes the JAX migration priority order.

4. **HPC access.** Do you have access to a GPU cluster now? If yes,
   Phase 4a moves up. If no, it stays deferred.
