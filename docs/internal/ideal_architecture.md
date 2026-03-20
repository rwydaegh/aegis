# AEGIS ideal architecture

*Written 2025-03-20. A self-critical design document for what AEGIS could become
with no constraints on time or resources.*

## What AEGIS does today

AEGIS computes absorbed power density on human bodies from wireless signals.
The pipeline: ray tracer produces propagation paths, dosimetry engine computes
per-triangle absorption, result goes to a 3D viewer or compliance check.

**Current stack:**

| Layer | Technology | Runs on |
|-------|-----------|---------|
| Dosimetry kernels (levels 0-8) | Python, NumPy, SciPy | CPU |
| Wireless ray tracing | DiffeRT (JAX) | CPU, optionally GPU |
| 3D viewer backend | Flask (13 API routes) | CPU |
| 3D viewer frontend | Three.js (single 98KB HTML file) | Browser GPU (WebGL) |
| Tissue physics | NumPy (Cole-Cole, Fresnel) | CPU |
| Compliance | NumPy (ICNIRP 2020 limits) | CPU |

**No C, no Cython, no compiled extensions.** Pure Python backend, vanilla JS frontend.

Core dependencies: numpy, scipy. Everything else is optional.

## What we want

A professional dosimetry tool that is:

1. **Fast** -- real-time interaction with meshes of 100K+ triangles
2. **Accessible** -- runs in a browser, no install
3. **Beautiful** -- modern UI, not a research prototype
4. **Extensible** -- new fidelity levels, new ray tracers, new body models
5. **Correct** -- physics validated against monograph, Mie theory, golden tests

## The ideal architecture

### Separation of concerns

Three distinct products share one physics core:

```
                    ┌──────────────────────────┐
                    │     AEGIS Physics Core    │
                    │  (Rust crate: aegis-core) │
                    │                           │
                    │  Kernels 0-8              │
                    │  Fresnel / Cole-Cole      │
                    │  Mesh processing          │
                    │  Spatial averaging         │
                    │  Compliance (ICNIRP)      │
                    └─────┬──────┬──────┬──────┘
                          │      │      │
               ┌──────────┘      │      └──────────┐
               ▼                 ▼                  ▼
    ┌─────────────────┐  ┌────────────┐  ┌─────────────────┐
    │  Python package  │  │  WASM blob │  │  Native server  │
    │  (PyO3/maturin)  │  │  (wasm-    │  │  (Axum binary)  │
    │                  │  │   pack)    │  │                  │
    │  pip install     │  │  Runs in   │  │  Heavy compute,  │
    │  aegis           │  │  browser   │  │  GPU ray tracing │
    └─────────────────┘  └────────────┘  └─────────────────┘
         Research            Product          Cloud/HPC
```

### Why this split works

- **Research users** keep Python. The PyO3 bindings expose the same API as today.
  Existing tests validate Rust output against NumPy golden values.
- **Product users** get a browser app. The WASM blob runs dosimetry client-side.
  No Python install. Just open a URL.
- **Heavy workloads** (city-scale, MIMO optimization) run on a server with
  GPU access. Same Rust core, native speed, CUDA/Vulkan via wgpu.

### Detailed component breakdown

#### 1. Physics core (Rust)

```
aegis-core/
  src/
    kernels/
      level0_bound.rs      -- O(1) scalar bound
      level2_geometric.rs  -- matrix: mu_plus @ power, O(M*N)
      level3_fresnel.rs    -- + angle-dependent T(theta)
      level6_diffraction.rs-- GELU shadow smoothing
      level7_coherent.rs   -- G_tilde assembly, complex field
      level8_ecbf.rs       -- QCQP solver (Brent bisection)
    tissue/
      cole_cole.rs         -- 4-pole Gabriel model
      fresnel.rs           -- T_s, T_p, amplitude transmission
    geometry/
      mesh.rs              -- STL loading, normals, areas
      averaging.rs         -- cKDTree equivalent (kiddo crate)
    compliance/
      icnirp.rs            -- limit evaluation
    lib.rs                 -- public API
```

**Key design decisions:**

The incoherent kernels (0-6) are matrix multiplications on dense (M, N) arrays.
Rust's `ndarray` crate handles this. No custom SIMD needed -- BLAS backends
(OpenBLAS, MKL) do the heavy lifting, same as NumPy.

The ECBF solver (level 8) uses Brent's method bisection on a scalar function.
Rust has no scipy.optimize, but Brent's method is ~50 lines to implement.
The eigendecomposition of Q uses `ndarray-linalg` (wraps LAPACK). This is
the one place where we depend on a Fortran library -- same as NumPy does.

**What about gradients?** The ECBF solver needs no autodiff -- it's a
root-finding problem with analytical derivatives. For future gradient-based
optimization (antenna placement, beamforming design), we have two options:

- Keep a JAX/Python path specifically for optimization research
- Use Rust autodiff crates (enzyme-ad, when mature)

This is the one area where "Rust everywhere" does not clearly win.
Gradient-based wireless optimization is JAX's strength.

#### 2. Python bindings (PyO3)

```python
# User-facing API stays identical
from aegis import DosimetryEngine, BodyMesh, PropagationPaths

engine = DosimetryEngine(tissue=SKIN_28GHZ)
result = engine.compute(body, paths, level=3)
print(result.sab)  # numpy array, backed by Rust computation
```

PyO3/maturin compiles the Rust core into a `.pyd` (Windows) or `.so` (Linux)
that imports like a normal Python module. NumPy arrays cross the boundary
with zero copy via the buffer protocol.

**Migration path:** Write Rust kernel, expose via PyO3, run existing Python
test suite. If tests pass, the Rust version is correct. Swap the import.
One kernel at a time. No big bang rewrite.

#### 3. WASM target (browser compute)

The same `aegis-core` crate compiles to WebAssembly via `wasm-pack`.
Browser-side JavaScript calls into WASM for dosimetry:

```javascript
import init, { compute_dosimetry } from './aegis_core_bg.wasm';

await init();
const sab = compute_dosimetry(meshBuffer, pathsBuffer, level, tissueParams);
// sab is a Float32Array, render it on the mesh
```

**What runs in the browser vs. server:**

| Task | Where | Why |
|------|-------|-----|
| Dosimetry compute (levels 0-6) | Browser (WASM) | Fast enough, ~5-50ms |
| Coherent compute (levels 7-8) | Browser (WASM) | Eigendecomp is small (M_ant < 64) |
| Mesh rendering | Browser (WebGPU/WebGL) | Obviously |
| Wireless ray tracing | **Server** (DiffeRT/JAX) | Needs full scene graph, GPU |
| City-scale batch compute | **Server** (native Rust + GPU) | Too heavy for browser |

**Wait -- can we ray trace in the browser?**

Not the wireless propagation kind. DiffeRT is a differentiable ray tracer
built on JAX. It handles multi-bounce reflections, diffraction, scattering
in complex environments. There is no WASM equivalent and writing one would
be a multi-year research project.

What we CAN do in the browser:
- Render 3D scenes (Three.js / WebGPU) -- this is graphics ray tracing
- Run dosimetry on pre-computed paths (WASM) -- this is our core math
- Visualize results interactively -- colormaps, slicing, comparison

The ray tracing stays server-side. This is fine. The typical workflow is:
server computes paths once, browser interactively explores dosimetry results
at different fidelity levels, antenna positions, and tissue parameters.

#### 4. Frontend (React + React Three Fiber)

```
aegis-web/
  src/
    components/
      SceneView.tsx        -- R3F canvas, body mesh, rays, antenna
      ControlPanel.tsx     -- level selector, tissue, power sliders
      ComplianceBadge.tsx  -- ICNIRP pass/fail indicator
      Dashboard.tsx        -- S_ab histogram, spatial stats
      ColorBar.tsx         -- continuous colormap legend
    hooks/
      useDosimetry.ts      -- WASM compute wrapper
      useBodyMesh.ts       -- binary mesh loader
      usePaths.ts          -- path data from server
    store/
      index.ts             -- Zustand state (antenna pos, level, tissue)
    wasm/
      aegis_core_bg.wasm   -- compiled Rust physics
    App.tsx
    main.tsx
  vite.config.ts
  package.json
```

**Tech choices:**

| Choice | Why | Alternative considered |
|--------|-----|-----------------------|
| React | Component model, ecosystem, hiring pool | Svelte (smaller but less ecosystem) |
| React Three Fiber | Declarative Three.js, React integration | Raw Three.js (current, works but messy) |
| TypeScript | Type safety for complex 3D state | JavaScript (current, error-prone) |
| Vite | Fast builds, WASM support, HMR | Webpack (slower, more config) |
| Zustand | Minimal state management, no boilerplate | Redux (overkill), Context (too basic) |
| shadcn/ui | Beautiful, accessible components | MUI (heavy), custom (slow to build) |

**Deployment:** Vite builds static assets. The Python package bundles them
(or they're served from a CDN). `pip install aegis` still works -- Flask
serves the built frontend. For standalone deployment, the frontend is a
static site that talks to an API server.

#### 5. Ray tracing (DiffeRT, unchanged)

DiffeRT stays. It is the right tool for wireless propagation:

- Differentiable (JAX) -- enables gradient-based antenna optimization
- Handles multi-bounce, diffraction, scattering
- GPU-accelerated via JAX/CUDA
- Actively maintained, Sionna-compatible scene format

The integration layer (`src/aegis/integration/differt.py`) becomes a server
endpoint. Browser requests ray tracing, server runs DiffeRT, returns
PropagationPaths as binary.

For users without DiffeRT, AEGIS still works -- they provide paths from
any ray tracer (external CSV, MATLAB export, etc.) via `PropagationPaths.from_powers()`.

## Self-critique: what could go wrong

### "Is Rust/WASM actually faster for this workload?"

The dosimetry kernels are matrix multiplications. NumPy already calls
optimized BLAS (OpenBLAS/MKL) for these. Rust's `ndarray` calls the
**same BLAS**. For the core `mu_plus @ power` operation, Rust may not be
meaningfully faster than NumPy.

Where Rust wins: the non-BLAS code. Mesh loading, spatial averaging
(tree traversal), Fresnel evaluation (element-wise complex math), the
ECBF bisection loop. These involve branching, scalar ops, and memory
access patterns that Python is bad at. Estimated 10-50x speedup on
these paths.

For WASM specifically: WASM does NOT have BLAS. Matrix multiplications
in WASM use pure Rust loops, which are ~2-5x slower than optimized BLAS.
For M=50K, N=100, this might take 50ms instead of 10ms. Still interactive,
but not free. If this becomes a bottleneck, WebGPU compute shaders can
handle the matrix ops.

**Verdict:** Rust/WASM is worth it for the non-BLAS code and for the
deployment story (no Python install), not for raw matrix multiply speed.

### "Is the React rewrite worth the complexity?"

The current 98KB HTML file works. It's ugly to maintain but functional.
A React rewrite means:

- node_modules, package.json, build step
- Two language ecosystems to manage (Python + JS/TS)
- Build artifacts that must be bundled into the Python package
- More moving parts that can break

For a research tool used by 1-3 people: probably not worth it.
For a product shown to telecom engineers and regulators: necessary.

**Verdict:** Only do this if AEGIS is becoming a product. If it stays
a research tool, invest in the physics, not the UI.

### "What about JAX? Are we abandoning it?"

No. The architecture has two JAX touchpoints:

1. **DiffeRT** uses JAX for differentiable ray tracing. This stays.
2. **Gradient-based optimization** (antenna placement, beamforming) is
   best done in JAX. The exposure operator Q and its eigendecomposition
   need gradients that flow through the physics.

The Rust core handles forward evaluation (compute S_ab given paths).
JAX handles inverse problems (optimize antenna position to minimize S_ab).
These are complementary, not competing.

**Verdict:** Keep a JAX research path alongside the Rust production path.
Do not try to do autodiff in Rust. It's not ready.

### "Can we really share one Rust crate across three targets?"

Yes, with caveats:

- **PyO3 target:** Needs Python-specific wrapper functions with GIL handling.
  These live in a separate `aegis-py` crate that depends on `aegis-core`.
- **WASM target:** Needs `#[wasm_bindgen]` annotations. Some APIs differ
  (no filesystem access, no threads initially). Separate `aegis-wasm` crate.
- **Native target:** The server binary. Separate `aegis-server` crate.

The physics lives in `aegis-core` with no platform-specific code. The
platform crates are thin wrappers. This is a standard Rust workspace pattern.

```
aegis-rs/
  Cargo.toml          -- workspace
  aegis-core/         -- physics, pure Rust, no platform deps
  aegis-py/           -- PyO3 bindings
  aegis-wasm/         -- wasm-bindgen bindings
  aegis-server/       -- Axum HTTP server
```

**Verdict:** This works. It's how projects like Typst, Zed, and Dioxus
are structured. The main risk is feature flags and conditional compilation
getting messy, but for a math library this is manageable.

### "Is WebGPU ready?"

As of early 2025: Chrome and Edge ship WebGPU by default. Firefox has it
behind a flag (enabled in Nightly). Safari has partial support.

For a professional tool, you'd want a WebGL fallback. Three.js and
React Three Fiber support both backends, so this is handled at the
renderer level, not in application code.

For WebGPU compute shaders (running dosimetry on the GPU in the browser):
this is more experimental. The API is stable but tooling is young.
Unless the WASM path proves too slow, skip WebGPU compute and just use
WASM for math.

**Verdict:** Use WebGPU for rendering (via Three.js). Use WASM for
compute. Only reach for WebGPU compute shaders if WASM matrix multiply
becomes a bottleneck.

### "What's the migration path? How do we not break everything?"

Phased, one piece at a time, never breaking the Python package:

**Phase 1 -- React frontend (weeks, no Rust yet)**
- New `aegis-web/` directory with Vite + React + R3F
- Flask serves the built static assets (replaces index.html)
- Python backend unchanged
- Ship: `pip install aegis` still works, viewer is now React

**Phase 2 -- Rust core with Python bindings (months)**
- New `aegis-rs/` workspace alongside `src/aegis/`
- One kernel at a time: write in Rust, expose via PyO3
- Python test suite validates Rust output matches NumPy
- Gradually replace Python kernels with Rust imports
- Ship: `pip install aegis` installs the Rust extension (maturin)

**Phase 3 -- WASM target (months)**
- Compile `aegis-core` to WASM via `wasm-pack`
- React frontend loads WASM, runs dosimetry client-side
- Server only needed for ray tracing and heavy compute
- Ship: standalone web app, optionally backed by API server

**Phase 4 -- Server binary (if needed)**
- Axum server for cloud/HPC deployments
- GPU ray tracing via wgpu or CUDA bindings
- Batch processing API for city-scale compliance checks
- Ship: Docker container, cloud deployment

Each phase is independently valuable. You can stop after any phase and
have a working, improved product.

## Summary

The ideal AEGIS architecture:

- **Physics core in Rust** -- one crate, three targets (Python, WASM, native)
- **DiffeRT stays** for wireless ray tracing (JAX, GPU)
- **React + R3F frontend** -- modern, component-based, TypeScript
- **WASM for browser compute** -- no install, interactive dosimetry
- **JAX kept for optimization** -- gradients through the physics
- **Phased migration** -- never break the Python package

The biggest risk is overengineering before the physics is stable. The
biggest reward is a zero-install professional dosimetry tool that runs
in any browser.
