# AEGIS — Implementation Plan

## 0. The Central Design Decision: What Comes First?

### The tension

| Start with... | Pros | Cons |
|---------------|------|------|
| **Incoherent** (Levels 0–4) | Simple, testable against monograph tables, fast to build | Risk: abstractions designed for powers/scalars don't extend to coherent amplitudes/vectors |
| **Coherent** (Levels 7–8) | Abstractions are general from day one | Hard to validate (no ground truth yet), slower to get first demo |

### The resolution

**Start with the *data model* of coherent, but *implement* incoherent first.**

This means:
- Every `Path` stores the full complex polarisation-amplitude vector `ψ_n ∈ ℂ³`, not just power `Sᵢ`. The incoherent kernel uses `|ψ_n|²` to get power; the coherent kernel uses `ψ_n` directly.
- The `BodyMesh` stores everything both modes need (normals, areas, curvature, η). Coherent additionally computes TE/TM bases and Fresnel *amplitudes*, but these are derived quantities, not stored state.
- The `DosimetryResult` is the same regardless of fidelity: per-triangle `Sab`, total `Pabs`, `SARwb`.

**WHY THIS WORKS:** The monograph's own structure proves it. The coherent absorption law (Theorem 4.1) reduces to the incoherent formula (Corollary 4.2) when cross-terms vanish. Same data, same result type, different kernel.

---

## 1. Data Model (Build First, Never Refactor)

These are the core types. They are designed once, used everywhere.

### 1.1 `TissueModel`

**What it is:** The complex refractive index ñ(f) and everything derived from it.

**What it stores:**
```
TissueModel:
    name: str                        # "skin", "muscle", "fat", ...
    cole_cole_params: ColeColeParams  # 4-pole Cole-Cole model parameters
```

**What it computes (all vectorised over frequency and/or angle):**
```
Methods:
    eps_r(f) → complex              # Complex relative permittivity ε̃_r(f)
    n_tilde(f) → complex            # Complex refractive index ñ = √ε̃_r
    n_abs(f) → float                # |ñ|
    T0(f) → float                   # Normal-incidence power absorption: 4n/((1+n)²+κ²)
    Tbar(f) → float                 # Flux-weighted averaged transmission: 2∫₀¹ Tavg(μ)μ dμ
    
    # --- Per-angle quantities (vectorised over θ or μ) ---
    xi(mu, f) → complex             # ξ = √(ñ² - 1 + μ²), Re(ξ)>0
    rs(mu, f) → complex             # TE reflection amplitude
    rp(mu, f) → complex             # TM reflection amplitude
    ts(mu, f) → complex             # TE transmission amplitude: 2μ/(μ+ξ)
    tp(mu, f) → complex             # TM transmission amplitude: 2ñμ/(ñ²μ+ξ)
    Ts(mu, f) → float               # TE power absorption: 1-|rs|²
    Tp(mu, f) → float               # TM power absorption: 1-|rp|²
    Tavg(mu, f) → float             # Unpolarised average: (Ts+Tp)/2
    DeltaT(mu, f) → float           # Polarisation splitting: Tp-Ts
    
    # --- Depth quantities (needed for coherent) ---
    alpha(mu, f) → float            # Amplitude decay rate into tissue
    beta(mu, f) → float             # Phase rate into tissue
    sigma_tissue(f) → float         # Conductivity at frequency f
```

**Why no refactoring:** Both incoherent and coherent need `T0` and `Tbar`. Coherent additionally needs `ts`, `tp`, `alpha`, `beta` — but these are just more methods on the same class.

**Test:** Reproduce Table 1 (Fresnel coefficients for skin at 28 GHz), Table 7 (skin data across frequencies), Table 9 (T̄ vs frequency).

### 1.2 `BodyMesh`

**What it is:** A triangle mesh of a human body with all derived geometric quantities.

**What it stores (immutable per pose):**
```
BodyMesh:
    vertices: float[V, 3]           # Vertex positions (metres)
    triangles: int[M, 3]            # Triangle vertex indices
    
    # --- Derived (recomputed per pose) ---
    normals: float[M, 3]            # Unit outward normals, per triangle
    areas: float[M]                 # Triangle areas (m²)
    centroids: float[M, 3]         # Triangle centroids
    total_area: float               # Σ areas
    curvature: float[M]             # 2× mean curvature H = 1/R₁ + 1/R₂ (optional)
```

**What it computes:**
```
Methods:
    recompute_from_vertices()       # Update normals, areas, centroids from vertices
    
    # --- Static geometry (computed once, cached) ---
    compute_ambient_occlusion(n_dirs) → float[M]       # Exposure fraction η(r)
    compute_projected_area_table(dirs) → float[n_dirs]  # A⊥(k̂) per direction
    compute_absorption_area() → float                   # Aab = Σ aᵢηᵢ
    compute_directivity_sh(L_max) → float[(L+1)²]      # SH coefficients of D(k̂)
    
    # --- ICNIRP spatial averaging ---
    build_averaging_matrix(radius_m) → sparse[M, M]    # G matrix for 4cm² averaging
```

**Why no refactoring:** The mesh is the same for incoherent and coherent. The coherent path needs TE/TM basis vectors, but those depend on the *path direction* too, so they are computed in the dosimetry kernel, not stored on the mesh.

**Test:** Reproduce Thelonious statistics: 23,826 triangles, ~7,870 cm² surface area, η mean 0.80, A_ab.

### 1.3 `PropagationPaths`

**This is the critical abstraction.** It must serve both incoherent and coherent without change.

**What it is:** A batch of N propagation paths arriving at the body, output by a ray tracer.

```
PropagationPaths:
    # --- Always present ---
    k_hat: float[N, 3]              # Direction of arrival at body (unit vectors)
    
    # --- Full representation (coherent-ready) ---
    psi: complex[N, 3]              # Polarisation-amplitude vector ψ_n ∈ ℂ³ (⊥ k̂_n)
                                     # Units: V·m⁻¹·W⁻¹/² 
                                     # Power of path n: |ψ_n|²·Z₀/(4π) [W/m²]
    element_index: int[N]            # j(n) ∈ {0,...,M-1} — originating antenna element
    
    # --- Optional metadata ---
    delay: float[N]                  # Propagation delay τ_n (for channel, not dosimetry)
    is_los: bool[N]                  # Line-of-sight flag

    # --- Derived convenience ---
    @property
    power: float[N]                  # Sᵢ = |ψᵢ|² · Z₀/(4π)  [W/m²]
    
    @property
    n_elements: int                  # M = max(element_index) + 1
```

**The key design choice:** `psi` (the full complex 3D amplitude) is the *canonical* representation. Power is *derived* from it. This means:

- **Incoherent kernel** uses `paths.power` and `paths.k_hat` — ignoring phase and element structure. This is exactly the monograph's multi-source formula with `Sᵢ` and `k̂ᵢ`.
- **Coherent kernel** uses `paths.psi`, `paths.k_hat`, and `paths.element_index` — the full information. This is the monograph's field channel construction.

**Creating paths for incoherent-only use:**
```python
# If you only have powers and directions (no Sionna):
paths = PropagationPaths.from_powers(
    k_hat=directions,   # [N, 3]
    power=powers,        # [N]    in W/m²
)
# Internally: ψ_n = √(4π·Sₙ/Z₀) · arbitrary_perpendicular_to(k̂_n)
# element_index = [0, 1, 2, ...] (each path from a "virtual" element)
```

**Creating paths from Sionna:**
```python
# Sionna gives us everything:
paths = PropagationPaths.from_sionna(sionna_paths_output)
# Extracts k̂, ψ, j(n) directly from Sionna's data structures
```

**Why no refactoring:** The same `PropagationPaths` object feeds both kernels. Adding Sionna integration later doesn't change the interface — it's just a new constructor.

### 1.4 `Precoder` (coherent only, but defined early)

```
Precoder:
    x: complex[M_ant]               # Precoding vector, ||x||² = P
    
    @staticmethod
    mrt(h) → Precoder               # x = √P · h*/||h||
    
    @staticmethod
    ecbf(h, Q, P_abs_max, P) → Precoder  # Solve QCQP
```

Defined early so that the coherent APIs can reference it, but not implemented until Phase 3.

### 1.5 `DosimetryResult`

**The same output type for every fidelity level.**

```
DosimetryResult:
    # --- Per-triangle ---
    sab: float[M]                    # Absorbed power density per triangle [W/m²]
    sab_averaged: float[M]           # 4cm²-averaged (ICNIRP) [W/m²]
    
    # --- Aggregate ---
    p_abs: float                     # Total absorbed power [W]
    sar_wb: float                    # Whole-body SAR [W/kg]
    
    # --- Compliance ---
    peak_sab: float                  # max(sab_averaged) [W/m²]
    compliant_sab: bool              # peak_sab < 10 W/m²
    compliant_sar: bool              # sar_wb < 0.08 W/kg
    
    # --- Diagnostics ---
    fidelity_level: int              # Which level was used (0–8)
    approx_errors: dict              # Estimated approximation errors
    
    # --- Coherent-specific (None for incoherent) ---
    Q: complex[M_ant, M_ant] | None  # Exposure operator
    rho: float | None                # Exposure-signal alignment
    eigenvalues: float[M_ant] | None # Q eigenspectrum
```

**Why no refactoring:** Incoherent results just have `Q = None`, `rho = None`. No polymorphism needed.

---

## 2. Kernel Architecture (The Computation)

### The engine contract

```python
class DosimetryEngine:
    """Computes Sab on a body mesh from propagation paths."""
    
    def __init__(self, tissue: TissueModel, frequency: float):
        self.tissue = tissue
        self.freq = frequency
        # Precompute frequency-dependent quantities
        self.T0 = tissue.T0(frequency)
        self.Tbar = tissue.Tbar(frequency)
        self.n_tilde = tissue.n_tilde(frequency)
    
    def compute(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int = 2,                    # Fidelity level (0–8)
        precoder: Precoder | None = None,  # Required for level ≥ 7
        body_mass: float | None = None,    # For SAR computation
    ) -> DosimetryResult:
        """Main entry point. Dispatches to the right kernel."""
        ...
```

### Kernel dispatch

```
Level 0:  _bound_only(body, paths)
Level 1:  _aggregate_sh(body, paths)
Level 2:  _geometric_relu(body, paths)           ← IMPLEMENT FIRST
Level 3:  _exact_fresnel(body, paths)
Level 4:  _polarisation_aware(body, paths)
Level 5:  _curvature_correction(body, paths)
Level 6:  _diffraction_gelu(body, paths)
Level 7:  _coherent_map(body, paths, precoder)
Level 8:  _coherent_ecbf(body, paths, precoder)
```

**Each higher level CALLS the lower level and adds a correction.** This is the monograph's own structure: Level 3 is Level 2 with `T0 → Tavg(θ)`. Level 5 is Level 3 with `+ H/k · ReLU²`. This additive structure means no code duplication.

### Internal kernel structure (pseudocode)

```
Level 2: _geometric_relu(body, paths)
    mu_plus = relu(body.normals @ (-paths.k_hat).T)     # [M, N]
    sab = self.T0 * (mu_plus @ paths.power)              # [M]
    return sab

Level 3: _exact_fresnel(body, paths)
    mu_plus = relu(body.normals @ (-paths.k_hat).T)      # [M, N]
    mu_raw = body.normals @ (-paths.k_hat).T              # [M, N] (before ReLU)
    Tavg_mn = self.tissue.Tavg(mu_raw, self.freq)         # [M, N]
    sab = (Tavg_mn * mu_plus) @ paths.power               # [M]
    return sab

Level 5: _curvature_correction(body, paths)
    sab_base = self._exact_fresnel(body, paths)
    mu_plus = relu(body.normals @ (-paths.k_hat).T)       # [M, N]
    k = 2 * pi * self.freq / c
    curvature_term = (body.curvature[:, None] / k) * mu_plus**2  # [M, N]
    sab_correction = self.T0 * (curvature_term @ paths.power)     # [M]
    return sab_base + sab_correction

Level 7: _coherent_map(body, paths, precoder)
    # Build G̃(r) per triangle
    G_tilde = self._build_body_channel(body, paths)       # [M, 3, M_ant]
    # Sab = ||G̃(r) x||²
    field = einsum('m3a, a -> m3', G_tilde, precoder.x)   # [M, 3]
    sab = (field.conj() * field).sum(axis=-1).real         # [M]
    return sab
```

The pattern: each level is a **thin function** that either calls a lower level or adds its own computation. The data types flowing between them are always the same: `float[M]` for `sab`, `float[M, N]` for intermediate per-triangle-per-path quantities.

---

## 3. Build Order

### Phase 0: Tissue Physics (Week 1–2)

**Files to create:**
```
aegis/
├── __init__.py
├── tissue/
│   ├── __init__.py
│   ├── cole_cole.py           # 4-pole Cole-Cole model
│   ├── dielectric.py          # TissueModel class
│   └── fresnel.py             # All Fresnel functions (vectorised)
└── constants.py               # Z0, c, epsilon_0, etc.
```

**Deliverable:** `TissueModel("skin")` that reproduces every number in the monograph's tables.

**Tests:**
- Table 1: Fresnel coefficients for skin at 28 GHz (Ts, Tp, Tavg at 0°,30°,45°,60°,70°,75°)
- Table 7: T0, |ñ| across tissues (skin, muscle, fat, water)
- Table 8: Frequency dependence (6–100 GHz)
- Table 9: T̄ vs frequency (0.3–100 GHz)
- Sphere ratio R: 0.99 for unpolarised at 28 GHz

**Why first:** Zero dependencies. Pure physics. Validates against the monograph directly. Every subsequent phase needs this.

### Phase 1: Body Geometry (Week 2–4)

**Files to create:**
```
aegis/
├── geometry/
│   ├── __init__.py
│   ├── mesh.py                # BodyMesh class (load, normals, areas)
│   ├── occlusion.py           # Ambient occlusion η(r)
│   ├── projected_area.py      # A⊥(k̂) table, shadow casting
│   ├── directivity.py         # D(k̂), SH fitting
│   └── cauchy.py              # Aab, generalised Cauchy formula
```

**Deliverable:** Load the Thelonious OBJ, compute η, A_ab, D(k̂), SH coefficients.

**Tests:**
- Thelonious: η mean 0.80, median 0.92
- Cauchy: A_ab from η-weighted integration
- D(k̂): Dmax ≈ 1.22 (side-on), Dmin ≈ 0.45 (overhead)
- SH fit: RMS < 1% at L=4

**Why second:** Still no EM coupling. Pure geometry. The mesh and its precomputed quantities are shared by all fidelity levels.

### Phase 2: Incoherent Dosimetry (Week 4–8)

**Files to create:**
```
aegis/
├── paths.py                   # PropagationPaths class
├── result.py                  # DosimetryResult class
├── engine.py                  # DosimetryEngine class (main entry point)
├── kernels/
│   ├── __init__.py
│   ├── level0_bound.py        # O(1) worst-case bound
│   ├── level1_aggregate.py    # O(N) via SH directivity
│   ├── level2_geometric.py    # O(MN) ReLU map with T0
│   ├── level3_fresnel.py      # O(MN) with Tavg(θ)
│   ├── level4_polarisation.py # O(MN) + q·ΔT/2
│   ├── level5_curvature.py    # + H/k · ReLU²
│   └── level6_diffraction.py  # ReLU → GELU
├── compliance/
│   ├── __init__.py
│   ├── icnirp.py              # Limits, spatial averaging
│   └── anthropometric.py      # Du Bois formula, body-size tables
```

**Deliverable:** Full incoherent dosimetry on Thelonious with N plane waves.

**Tests:**
- Table 6: Framework vs. full Fresnel on Thelonious (total power error 0.35%)
- Mie theory: error curves vs. size parameter (reproduce Fig. 7)
- Multi-source: N=100 random plane waves, compare Level 2 vs Level 3
- Compliance: Table 4 values for adult/child/infant

### Phase 3: Coherent MIMO (Week 8–14)

**Files to create:**
```
aegis/
├── precoder.py                # Precoder class (MRT, ECBF)
├── kernels/
│   ├── level7_coherent.py     # ||G̃(r)x||²
│   └── level8_ecbf.py         # + QCQP solver
├── coherent/
│   ├── __init__.py
│   ├── field_channel.py       # G(r) from paths
│   ├── fresnel_operator.py    # F_n(r) per path per triangle
│   ├── body_channel.py        # G̃(r) with depth coupling
│   ├── exposure_operator.py   # Q = ∫ G̃ᴴG̃ dA, eigendecomposition
│   └── ecbf.py                # QCQP solver for x*
```

**Note:** This phase adds files but does NOT modify Phase 0–2 files. The `DosimetryEngine.compute()` dispatcher just gains two more `elif level == 7/8` branches.

**Deliverable:** Exposure operator Q, eigenspectrum, ρ, ECBF precoder.

**Tests:**
- Single-wave limit (Corollary 4.1): coherent with N=M=1 matches incoherent
- Incoherent limit (Corollary 4.2): random phases → cross-terms vanish
- Approx 1 error: ≤ 4% on TM-TM cross-terms (Table 10)
- Approx 2 error: ≤ 0.44% on Γ_nn' (Fig. 11)

### Phase 4: Animation & Visualisation (Week 14–20)

**Files to create:**
```
aegis/
├── body/
│   ├── __init__.py
│   ├── skeleton.py            # Joint hierarchy, FK
│   ├── skinning.py            # Linear blend skinning
│   ├── animation.py           # BVH/FBX import, walk cycles
│   └── smpl.py                # SMPL model wrapper (optional)
├── viz/
│   ├── __init__.py
│   ├── heatmap.py             # Sab → vertex colours
│   ├── viewer.py              # Open3D/PyVista interactive 3D
│   └── dashboard.py           # Compliance panel, ρ gauge, eigenspectrum
├── integration/
│   ├── __init__.py
│   ├── sionna.py              # Sionna RT path import
│   └── blender.py             # Blender export
```

This phase touches NO existing files. It's purely additive.

---

## 4. The API: How It Feels to Use

### Minimal example (Level 2, one plane wave)

```python
import aegis

# Tissue
skin = aegis.TissueModel.from_database("skin")  # IT'IS v5.0

# Body
body = aegis.BodyMesh.load("thelonious.obj")
body.compute_ambient_occlusion(n_dirs=512)

# Single plane wave from above
paths = aegis.PropagationPaths.from_powers(
    k_hat=[[0, 0, -1]],  # downward
    power=[1.0],          # 1 W/m²
)

# Compute
engine = aegis.DosimetryEngine(skin, frequency=28e9)
result = engine.compute(body, paths, level=2)

print(f"Total absorbed power: {result.p_abs*1e3:.1f} mW")
print(f"Peak Sab: {result.peak_sab:.3f} W/m²")
print(f"Compliant (Sab): {result.compliant_sab}")
```

### Coherent MIMO example (Level 8)

```python
# Paths from Sionna (with full complex amplitudes)
paths = aegis.PropagationPaths.from_sionna(sionna_output)

# UE channel vector (for MRT)
h = aegis.compute_ue_channel(paths, ue_antenna, ue_position)

# Compute with ECBF
result = engine.compute(
    body, paths,
    level=8,
    precoder=aegis.Precoder.ecbf(h, Q=None, P_abs_max=0.1, P=1.0),
    # Q will be computed internally if not provided
)

print(f"ρ (alignment): {result.rho:.3f}")
print(f"Q eigenvalues: {result.eigenvalues[:5]}")
```

### Level comparison

```python
# Same data, different fidelity
for level in range(7):
    result = engine.compute(body, paths, level=level)
    print(f"Level {level}: Pabs = {result.p_abs*1e3:.2f} mW")
```

---

## 5. Dependency Strategy

### Core (Phase 0–2)
```
numpy           # Array operations (CPU fallback)
scipy           # Sparse matrices, quadrature, SH
```

### GPU acceleration (Phase 2+)
```
jax[cuda]       # GPU kernels, autodiff, vmap
```

### Visualisation (Phase 4)
```
open3d          # 3D viewer
matplotlib      # 2D plots (directivity, eigenspectrum)
```

### Sionna integration (Phase 4)
```
sionna          # Ray tracing (optional dependency)
```

**Strategy:** NumPy-first for all core logic. JAX as an *optional* accelerator — every kernel has a NumPy reference implementation and a JAX-jitted fast path. This means:
1. You can develop and test on a laptop (CPU, NumPy)
2. Production runs use JAX on GPU
3. The NumPy path serves as ground truth for validating the JAX path

```python
# In each kernel file:
def _geometric_relu_numpy(normals, k_hat, power, T0):
    """Reference implementation (CPU)."""
    mu = normals @ (-k_hat).T
    mu_plus = np.maximum(mu, 0)
    return T0 * (mu_plus @ power)

try:
    import jax
    import jax.numpy as jnp
    
    @jax.jit
    def _geometric_relu_jax(normals, k_hat, power, T0):
        """GPU-accelerated implementation."""
        mu = normals @ (-k_hat).T
        mu_plus = jnp.maximum(mu, 0)
        return T0 * (mu_plus @ power)
    
    _geometric_relu = _geometric_relu_jax
except ImportError:
    _geometric_relu = _geometric_relu_numpy
```

---

## 6. File-Level Dependency Graph

```
                    constants.py
                         │
                  tissue/dielectric.py
                   │            │
            tissue/cole_cole.py │
                   │     tissue/fresnel.py
                   │            │
                   └────┬───────┘
                        │
                   geometry/mesh.py
                   │    │    │
        ┌──────────┤    │    ├──────────────┐
        │          │    │    │              │
  occlusion.py    │    │  projected_area.py│
        │         │    │    │              │
        │    directivity.py │          cauchy.py
        │         │         │              │
        └────┬────┘─────────┘──────────────┘
             │
          paths.py ──── result.py
             │              │
          engine.py ────────┘
          │  │  │
    ┌─────┘  │  └─────┐
    │        │        │
 kernels/ kernels/ kernels/
 level2   level3   level7
    │        │        │
    │        │   coherent/
    │        │   field_channel.py
    │        │   exposure_operator.py
    │        │        │
    └────────┴────────┘
             │
        compliance/
```

Notice: **no cycles, no upward dependencies.** Every arrow points down. This is the key to no-refactoring development. Adding coherent (Phase 3) adds new leaf nodes; it doesn't modify existing ones.

---

## 7. What NOT to Build Yet (Temptations to Resist)

| Temptation | Why resist | When to add |
|------------|-----------|-------------|
| Sionna integration | Couples to external API; can change | Phase 4 |
| 3D visualisation | Rabbit hole; UI before physics | Phase 4 |
| SMPL body model | Complex dependency; GLTF is enough | Phase 4 |
| Web frontend | Massive scope; needs stable API | Phase 5+ |
| Custom CUDA kernels | JAX JIT is fast enough; premature | Never (unless profiling says otherwise) |
| Config files / YAML | Over-engineering for early stage | Phase 3+ |
| Plugin system | No plugins yet | Phase 5+ |

---

## 8. Testing Strategy

### Every monograph table is a test

```python
# tests/test_tissue.py
def test_fresnel_skin_28ghz():
    """Reproduce Table 1 of the monograph."""
    skin = TissueModel.from_database("skin")
    f = 28e9
    angles = [0, 30, 45, 60, 70, 75]
    expected_Ts = [0.539, 0.489, 0.422, 0.321, 0.233, 0.182]
    expected_Tp = [0.539, 0.591, 0.666, 0.791, 0.902, 0.952]
    for theta, exp_ts, exp_tp in zip(angles, expected_Ts, expected_Tp):
        mu = cos(radians(theta))
        assert abs(skin.Ts(mu, f) - exp_ts) < 0.002
        assert abs(skin.Tp(mu, f) - exp_tp) < 0.002
```

### Cross-validation with existing scripts

The `scripts/` directory has 37 Python scripts that computed the monograph's results. These serve as ground truth:
- `verify_fresnel.py` → validates `TissueModel`
- `verify_tables.py` → validates all numerical tables
- `compute_body_directivity.py` → validates `BodyMesh.compute_directivity_sh()`
- `compute_exposure_fraction_eta.py` → validates `BodyMesh.compute_ambient_occlusion()`
- `mie_theory_corrected.py` → validates Mie comparison
- `validate_approx2.py` → validates coherent Approximation 2

### Consistency tests

```python
def test_coherent_reduces_to_incoherent():
    """Corollary 4.2: random phases → cross-terms vanish."""
    # Run coherent with random phases, average over 1000 realisations
    # Compare to incoherent result
    # Assert: relative error < 1%

def test_single_wave_coherent_matches_incoherent():
    """Corollary 4.1: N=M=1 → same as Part I formula."""
    # Single path, single element
    # Coherent result must equal incoherent result to < 2% (TM correction)
```

---

## 9. Naming Conventions

| Monograph symbol | Code name | Type |
|------------------|-----------|------|
| $\hat{n}(\mathbf{r})$ | `normals` | `float[M, 3]` |
| $\hat{k}$ | `k_hat` | `float[N, 3]` |
| $\mu = \hat{n} \cdot (-\hat{k})$ | `mu` | `float[M, N]` |
| $T_0$ | `T0` | `float` |
| $\bar{T}$ | `Tbar` | `float` |
| $T_s, T_p$ | `Ts`, `Tp` | `float[M, N]` |
| $T_{avg}$ | `Tavg` | `float[M, N]` |
| $\Delta T$ | `DeltaT` | `float[M, N]` |
| $\tilde{n}$ | `n_tilde` | `complex` |
| $\xi$ | `xi` | `complex[M, N]` |
| $\eta(\mathbf{r})$ | `eta` | `float[M]` |
| $A_\perp(\hat{k})$ | `A_perp` | `float[n_dirs]` |
| $A_{ab}$ | `A_ab` | `float` |
| $D(\hat{k})$ | `directivity` | `float[n_dirs]` |
| $\boldsymbol{\psi}_n$ | `psi` | `complex[N, 3]` |
| $\mathbf{G}(\mathbf{r})$ | `G` | `complex[M, 3, M_ant]` |
| $\tilde{\mathbf{G}}(\mathbf{r})$ | `G_tilde` | `complex[M, 3, M_ant]` |
| $\mathbf{F}_n(\mathbf{r})$ | `F_n` | `complex[M, N, 3, 3]` (sparse: rank 2) |
| $\mathbf{Q}$ | `Q` | `complex[M_ant, M_ant]` |
| $\rho$ | `rho` | `float` |
| $\mathbf{h}$ | `h` | `complex[M_ant]` |
| $\mathbf{x}$ | `x` | `complex[M_ant]` |

---

## 10. Summary: Why This Order Works

```
PHASE 0: TissueModel
   ↓  (pure physics, no geometry)
PHASE 1: BodyMesh  
   ↓  (pure geometry, no EM)
PHASE 2: PropagationPaths + DosimetryEngine (Levels 0–6)
   ↓  (incoherent EM on geometry — validates against monograph)
PHASE 3: Coherent kernels (Levels 7–8)
   ↓  (adds new kernels, touches nothing in Phases 0–2)
PHASE 4: Animation + Visualisation
   ↓  (adds new modules, touches nothing in Phases 0–3)
PHASE 5: Sionna integration + optimisation
```

At every phase boundary, you have a working, tested system. No phase requires modifying code from a previous phase. The data types (`TissueModel`, `BodyMesh`, `PropagationPaths`, `DosimetryResult`) are defined in Phase 0–2 but designed for Phase 3+.

This is not aspirational — it's structural. The monograph's own mathematical structure guarantees it: each Part builds on, but does not modify, the previous Parts. The code mirrors the math.
