# AEGIS roadmap

*Last updated: 2026-03-21. Living document. Update as decisions change.*

## Where we are

Phases 0-4 of the original implementation plan are done. The dosimetry engine
works: 9 fidelity levels, 240+ tests, Mie-validated physics, Flask+Three.js
viewer, DiffeRT and Sionna RT ray tracing backends, CLI batch runner.
Total: ~9,000 lines of Python (NumPy/SciPy).

Phase 1 (reproducible research backbone) is complete:

- Dataclass config system (`src/aegis/config.py`) with YAML serialization
- CLI batch runner (`python -m aegis.run --config runs/my.yaml`)
- Sionna RT integration (`src/aegis/integration/sionna.py`)
- Viewer backend dropdown (DiffeRT or Sionna RT per scene)
- Batch runner docs and example configs

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

For levels 0-6, the migration is mechanical (pure array operations). Level 8
is hard: the ECBF solver uses scipy.optimize.brentq (not in JAX) and the
eigendecomposition needs to be differentiable (jax.numpy.linalg.eigh works
but has edge cases for degenerate eigenvalues). Budget extra time for level 8.

JAX CPU works on Windows. JAX GPU requires WSL2 or Linux. For local
development, CPU is fast enough for testing. GPU runs happen on the
TensorDock cloud machine.

**2b. Differentiable optimization API**

Once kernels are JAX, expose optimization as a first-class feature:

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

Open question: DiffeRT's exhaustive path enumeration has discrete topology
changes (paths appear and disappear). Gradients through these discontinuities
may be zero or undefined. Verify with a simple test case before building a
paper around it.

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

- **Rewriting tests.** The 240+ existing tests validate NumPy output. During
  JAX migration, these tests validate that JAX output matches. Do not
  rewrite tests in JAX. Keep them as NumPy-based golden checks.

## Sequencing and dependencies

```
Phase 1  (backbone) ──── DONE ────────────┐
                                          ├── paper-ready
Phase 2a (JAX kernels) ── independent ────┤
Phase 2b (differentiable opt) ── needs 2a ┤
                                          │
Phase 3  (React frontend) ── independent ─┘ (parallel track)

Phase 4  (HPC, wandb, DVC) ── when needed
```

Phases 2a and 3 can proceed in parallel. They touch different parts of the
codebase with no conflicts. Phase 2b needs 2a (JAX kernels). Phase 4 waits
until the need is clear.

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
