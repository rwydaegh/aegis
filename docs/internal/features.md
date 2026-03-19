# AEGIS feature inventory

Complete list of intended features, grouped by subsystem. Status reflects current implementation state as of 2026-03-19.

## Core dosimetry engine

### Fidelity levels 0-8

Nine kernel levels that trade accuracy for speed. Each level adds one physics correction on top of the previous.

| Level | Name | What it computes | Status |
|-------|------|-----------------|--------|
| 0 | Bound | O(1) worst-case upper bound on total absorbed power. No per-triangle map. | Done |
| 1 | Aggregate | Spherical-harmonic compressed directivity. Exact total power via D(k) SH coefficients. O(N) per path. | Done |
| 2 | Geometric ReLU | Per-triangle absorption map: `Sab = Sinc * T0 * ReLU(n_hat . (-k_hat))`. The core equation. O(MN). | Done |
| 3 | Fresnel | Level 2 + angle-dependent Fresnel transmission `T_avg(theta)` replacing constant T0. | Done |
| 4 | Polarisation | Level 3 + TE/TM decomposition via Stokes excess factor `q * DeltaT/2`. | Done |
| 5 | Curvature | Level 4 + local mean curvature correction `H/k * ReLU^2`. | Done |
| 6 | Diffraction | Level 5 + shadow boundary smoothing (ReLU replaced by GELU). | Done |
| 7 | Coherent MIMO | Full field channel `Sab = ||G_tilde(r) * x||^2`. Requires complex path amplitudes and precoder vector. | Done |
| 8 | ECBF | Level 7 + exposure-constrained beamforming. QCQP solver finds precoder that maximizes signal subject to absorption limit. | Done |

### Dispatch and result

- `DosimetryEngine.compute(body, paths, level, precoder, body_mass)` dispatches to the correct kernel and returns a uniform `DosimetryResult`. Done.
- `DosimetryResult` contains: per-triangle `Sab`, spatially averaged `Sab`, total `P_abs`, whole-body `SAR_wb`, peak `Sab`, compliance booleans, and (for levels 7-8) exposure operator Q, alignment rho, Q eigenvalues. Done.

### Precoder

- `Precoder` dataclass with factory methods `mrt(h)` (max-ratio transmission) and `ecbf(h, Q, P_abs_max, P)` (exposure-constrained). Done.

---

## Tissue physics

### Dielectric model

- `TissueModel` frozen dataclass storing `eps_r`, `sigma`, `freq`. Done.
- Predefined constants: `SKIN_28GHZ`, `SKIN_60GHZ`, `MUSCLE_28GHZ`, `FAT_28GHZ`. Done.
- Methods: complex refractive index, normal-incidence Fresnel T0. Done.

### Cole-Cole dispersion

- 4-pole Cole-Cole model for complex permittivity `eps(f)` across 100 MHz to 100 GHz. Done.
- Computes `eps_r(f)`, `sigma(f)`, `n_tilde(f)` from Cole-Cole parameters. Done.

### IT'IS tissue database

- Interface to the IT'IS Foundation v5.0 database (100+ tissue types). Done.
- Lookup by tissue name and frequency. Returns Cole-Cole parameters. Done.

### Fresnel transmission

- Normal-incidence power transmission T0. Done.
- Angle-dependent TE and TM transmission: `Ts(theta)`, `Tp(theta)`. Done.
- Average transmission `T_avg(theta)` and excess `DeltaT(theta)` for polarisation correction. Done.
- Flux-averaged transmission `T_bar(f)` for sub-6 GHz exact total-power results. Done.

---

## Geometry

### Body mesh

- `BodyMesh` class: loads STL files, computes triangle normals, areas, centroids, total surface area. Done.
- Vertex and face data accessible as NumPy arrays. Done.

### Ambient occlusion

- Exposure fraction `eta(r)` per triangle (how much of the hemisphere above each triangle is unobstructed). Done.
- Used for self-shadowing correction and the generalized Cauchy formula. Done.

### Directivity

- Absorption directivity `D(k) = 4 * A_perp(k) / A_ab`. Done.
- Antenna directivity patterns (isotropic, dipole, patch). Done.

### Projected area

- `A_perp(k)`: projected area of the body along direction k. Done.
- Used by Level 1 for exact total power without per-triangle map. Done.

### Spatial averaging

- ICNIRP-compliant 4 cm^2 spatial averaging kernel. Done.
- Smooths per-triangle Sab map to get regulatory-relevant peak values. Done.

### Cauchy formula

- Generalized Cauchy: `<P_abs> = Sinc * T0 * A_ab / 4` (direction-averaged absorbed power). Done.
- Accounts for non-convexity via absorption area `A_ab = integral(eta * dA)`. Done.

---

## Coherent MIMO (levels 7-8)

### Body channel matrix

- `H_b`: maps antenna element weights to body surface fields. Done.
- Each column is one path's contribution across all M triangles. Done.

### Field channel

- `S_field`: complex 3xM field channel per surface point. Done.
- Incorporates path amplitude vectors `psi_n` (V/m per sqrt(W)). Done.

### Exposure operator Q

- `Q = integral(G_tilde^H * G_tilde * dA)`: M x M Hermitian PSD matrix. Done.
- Eigendecomposition reveals "exposure modes" (worst-case precoders). Done.
- Quadratic form `x^H Q x` gives total absorbed power for any precoder x. Done.

### Fresnel operator

- Applies angle-dependent Fresnel transmission in the coherent regime. Done.
- Modifies field channel columns by `sqrt(T_s)` and `sqrt(T_p)` per polarization component. Done.

### ECBF solver

- Exposure-constrained beamforming: maximizes `|h^H x|^2` subject to `x^H Q x <= P_abs_max`. Done.
- Closed-form QCQP solution via KKT conditions: `x* = sqrt(P) * (lambda*Q + nu*I)^-1 * h* / norm(...)`. Done.
- Returns optimal precoder, achieved capacity, and exposure margin. Done.

---

## Compliance

### ICNIRP 2020 limits

- Spatial peak Sab threshold: 10 W/m^2 (averaged over 4 cm^2). Done.
- Whole-body SAR threshold: 0.08 W/kg (general public). Done.
- `DosimetryResult` includes boolean compliance flags. Done.

---

## Propagation paths

### PropagationPaths dataclass

- Canonical form: each path has complex 3D amplitude vector `psi_n` (V/m/sqrt(W)), direction `k_hat`, element index, optional delay and LOS flag. Done.
- Constructors: `from_powers()` (incoherent, scalar power per path), `from_sionna()` (full coherent data from ray tracer). Done.
- Derived: incoherent power `S_i = |psi_i|^2 * Z0 / (4*pi)`. Done.

---

## Ray tracer integration

### DiffeRT adapter

- `differt.py`: bridges DiffeRT ray tracer output to `PropagationPaths`. Done.
- Supports Sionna XML scene files (indoor/outdoor). Done.
- Configurable max reflection order (0, 1, 2). Done.

---

## Visualization (offline)

### Heatmap

- Plotly `Mesh3d` interactive 3D heatmap of Sab on body surface. Done.
- Matplotlib static heatmap for publications. Done.
- Inferno colormap, auto-scaled to data range. Done.

### Dashboard

- Multi-panel summary: P_abs bar, Sab histogram, SAR gauge, compliance indicator. Done.

### Level comparison

- Side-by-side heatmaps comparing two or more fidelity levels on the same body/paths. Done.
- Shows absolute and relative differences. Done.

---

## Interactive 3D viewer (frontend)

### Server (Flask REST API)

12 endpoints serving the single-page Three.js application.

| Endpoint | Purpose | Status |
|----------|---------|--------|
| `GET /` | Serve index.html | Done |
| `GET /api/config` | Scene config: bodies, tissues, levels, voxel metadata, DiffeRT availability | Done |
| `GET /api/body` | Binary body mesh (float32 positions + normals) | Done |
| `GET /api/voxels` | Binary voxel data (positions, colors, material indices) | Done |
| `POST /api/compute` | Dosimetry computation, returns binary Sab + stats header | Done |
| `GET /api/scenes` | List available Sionna XML scenes | Done |
| `POST /api/scene/load` | Load Sionna scene geometry (binary triangles) | Done |
| `POST /api/compute/rt` | Ray-traced dosimetry via DiffeRT on Sionna scene | Done |
| `POST /api/compute/voxel-rt` | Ray tracing through voxel environment | Done |
| `GET /api/location/load` | EventSource: fetch location voxels (streaming progress) | Done |
| `POST /api/location/cancel` | Cancel in-progress location loading | Done |

### 3D rendering

- Body mesh with per-vertex Sab heatmap color (Inferno colormap). Done.
- Voxel environment as `InstancedMesh` (handles 500K+ voxels at 60fps). Done.
- Sionna scene geometry (transparent/semi-transparent triangles). Done.
- Ground plane with grid and shadow receiving. Done.
- Antenna position marker (vertical colored line). Done.
- Distance line and label (dashed white line, midpoint sprite showing meters). Done.
- Ray path visualization (colored lines by reflection order). Done.
- ACES filmic tone mapping, hemisphere light + directional light. Done.

### Interactive controls

- WASD keys: translate body in XZ plane (with gravity, friction, max speed). Done.
- Q/E keys: rotate body around Y axis. Done.
- Space: jump (with gravity physics). Done.
- Shift: sprint multiplier. Done.
- Arrow keys: nudge antenna position (0.5m steps). Done.
- Mouse left-click: place antenna via raycaster. Done (has BUG-1: conflicts with orbit drag).
- Mouse drag: orbit camera (OrbitControls). Done.
- Scroll: zoom. Done.
- Right-click drag: pan camera. Done.

### Dosimetry controls (side panel)

- Level selector dropdown (levels 0-6 in UI, 7-8 backend only). Done.
- Power input (dBm). Done.
- Path count selector (1, 5, 10, 20 synthetic multipath). Done.
- Tissue preset (hardcoded to skin 28 GHz, no UI selector yet). Partial.

### Dashboard panel

- P_abs (total absorbed power, mW). Done.
- Peak Sab (W/m^2). Done.
- S_inc (incident power density). Done.
- Distance to body (meters). Done.
- Illuminated triangle count / total. Done.
- ICNIRP compliance status (PASS green / FAIL red, threshold 10 W/m^2). Done.

### Heatmap legend

- Vertical gradient bar (Inferno colormap) on right side of viewport. Done.
- Shows min/mid/max Sab values in W/m^2. Done.
- Updates on every recompute. Done.

### Camera presets

- Front, Side, Top view buttons. Done.
- Focus body (zoom to frame). Done.
- Reset camera (default framing). Done.

### Layer controls

- Toggle buttons per voxel material (concrete, asphalt, vegetation, water, brick, glass). Done.
- Toggle body mesh visibility. Done.
- Buttons show voxel counts. Done.
- Color mode: material classification vs photogrammetry original. Done.

### Ray tracing controls

- Enable/disable checkbox. Done.
- RT source dropdown: Voxel environment or Sionna scenes. Done.
- Max reflection order selector (0, 1, 2). Done.
- RT status display (path count, source type, computation time). Done.

### Location loader

- Text input for location string (geocoded via Google Maps API). Done.
- Radius slider (meters). Done.
- Force re-download checkbox. Done.
- EventSource streaming for real-time progress logs. Done.
- Cancel button for in-progress downloads. Done.
- Automatic body placement on loaded location. Done.
- Requires GOOGLE_API_KEY environment variable. Done.

### Wireframe mode

- Toggle button to render all geometry as wireframe. Done.

### Live recompute

- Debounced 200ms recompute on body movement (WASD). Done.
- Debounced recompute on antenna nudge (arrow keys). Done.
- Computing overlay with spinner during fetch. Done.
- Does not block camera interaction (pointer-events: none). Done.

---

## Known bugs (as of 2026-03-17)

| ID | Severity | Description |
|----|----------|-------------|
| BUG-1 | High | Click-to-place antenna fires on orbit drag (every mouseup triggers raycaster). Needs mouse-delta threshold. |
| BUG-2 | High | Sionna scene geometry overlaps voxel environment (should hide voxels when Sionna is active). |
| BUG-3 | High | Floating voxels, body at arbitrary elevation. Spatial coherence between voxel coordinates and body placement is poor. |
| BUG-4 | Medium | RT ray paths converge on wrong point (offset from body centroid, likely coordinate system mismatch). |
| BUG-5 | Low | Stale RT status text after disabling ray tracing. |
| BUG-6 | Low | Stale ray path lines remain visible after disabling RT. |
| BUG-7 | Trivial | Missing favicon (404 on /favicon.ico). |

---

## Not yet implemented (from design docs)

These features appear in the monograph, project proposal, or implementation plan but are not yet built.

### Physics

- Levels 7-8 in the viewer UI (backend works, no frontend controls for precoder input)
- Tissue selector in the viewer (switch between skin/muscle/fat, or pick frequency)
- SAR visualization in the viewer (backend computes it, no heatmap mode for SAR)
- Spatial averaging visualization (show 4 cm^2 averaged Sab as separate map)
- Polarisation-aware Stokes vector dosimetry visualization
- Sub-6 GHz mode with flux-averaged T_bar(f)

### Body and animation

- SMPL/SMPL-X parametric body model integration (currently only static STL meshes)
- Skeleton armature and pose control (24-joint SMPL)
- Walk cycle animation with per-frame dosimetry recompute
- BVH/FBX motion capture import
- Linear blend skinning deformation
- Lazy AO recompute on pose change (every N frames or on pose threshold)
- Multiple body models (currently only Thelonious)

### Visualization

- Absorption directivity Mollweide projection (sphere plot of D(k))
- Q eigenspectrum bar chart (exposure modes)
- Rho alignment gauge (0 to 1)
- Split-screen comparison in viewer (Level 2 vs Level 7, MRT vs ECBF)
- Blender export with per-vertex Sab as vertex color attribute
- GLTF export with embedded heatmap
- Publication-quality Cycles renders

### Optimization tools

- Antenna placement optimizer (gradient-based, minimize worst-case Sab over user positions)
- Beam pattern designer with sliding power constraint (Pareto front: capacity vs exposure)
- RIS phase optimizer (differentiable through surface reflections)
- Population Monte Carlo sampler (random poses x positions x angles, produces exposure CDFs)
- End-to-end differentiable pipeline (scene to ray tracer to dosimetry to loss, gradient tape)

### Performance

- JAX GPU acceleration for all kernels (NumPy-only currently, clean migration path exists)
- JIT compilation of inner loops
- GPU-accelerated ambient occlusion (BVH or OptiX ray casting)
- Real-time RT rendering (currently static ray paths only)

### Platform

- Web demo deployment
- CI/CD pipeline (GitHub Actions)
- Branch protection and review gates
