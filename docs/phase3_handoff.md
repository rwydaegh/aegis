# Phase 3 hand-off: incoherent dosimetry engine

Phase 3 built the complete incoherent dosimetry pipeline (Levels 0-6). Given a body mesh, propagation paths, and tissue properties, AEGIS now computes per-triangle absorbed power density, total absorbed power, whole-body SAR, and ICNIRP compliance status.

## What was built

### Source modules

| Module | Lines | Extracted from | Purpose |
|--------|-------|----------------|---------|
| `paths.py` | 110 | `implementation_plan.md` design | PropagationPaths dataclass, from_powers() constructor |
| `result.py` | 75 | `implementation_plan.md` design | DosimetryResult dataclass, compliance properties |
| `engine.py` | 170 | (new) | DosimetryEngine, level dispatch 0-6 |
| `kernels/level0_bound.py` | 45 | monograph Table hierarchy | O(1) worst-case power bound |
| `kernels/level1_aggregate.py` | 70 | monograph eq. for P_abs via D(k_hat) | O(N) aggregate via SH directivity |
| `kernels/level2_geometric.py` | 45 | `scripts/apd_pipeline.py:73-105` | O(MN) ReLU map with constant T_0 |
| `kernels/level3_fresnel.py` | 50 | `scripts/apd_pipeline.py:280-288` | O(MN) with angle-dependent T_avg(theta) |
| `kernels/level4_polarisation.py` | 55 | monograph eq. Teff-decomp | + q * DeltaT/2 polarisation correction |
| `kernels/level5_curvature.py` | 60 | monograph eq. curvature-nn | + H/k * ReLU^2 curvature correction |
| `kernels/level6_diffraction.py` | 90 | monograph eq. gelu | ReLU replaced by physical GELU |
| `kernels/__init__.py` | 20 | (new) | Public API re-exports |

### Tests

| File | Tests | What it validates |
|------|-------|-------------------|
| `test_engine.py` | 39 | PropagationPaths construction, power preservation, DosimetryResult properties, Level 2 (flat plane normal/grazing/backside, non-negative, energy bound, P_abs = T_0 * A_perp), Level 3 (matches L2 at normal incidence, non-negative, close total power), Level 4 (unpolarised = L3, TM increases power), Level 5 (zero curvature = L3, positive curvature adds power), Level 6 (zero curvature ~ L3, non-negative), Level 0 (bound exceeds L2), Level 1 (isotropic D check), consistency across all levels, invalid/coherent level errors, Thelonious E2E (slow) |

116 tests total (101 fast + 15 slow/skipped). All passing. Lint clean. Version bumped to 0.1.0.

### Public API

```python
import aegis

# Full pipeline in 6 lines
skin = aegis.TissueModel.from_params("Skin", 17.0, 25.0, 28e9)
body = aegis.BodyMesh.load("thelonious.stl")
paths = aegis.PropagationPaths.from_powers(
    k_hat=[[0, 0, -1]], power=[1.0]
)
engine = aegis.DosimetryEngine(skin)
result = engine.compute(body, paths, level=2)

result.sab           # (M,) per-triangle S_ab [W/m^2]
result.p_abs         # total absorbed power [W]
result.peak_sab      # max S_ab
result.fidelity_level  # 2

# With SAR and spatial averaging
result = engine.compute(body, paths, level=2,
                        body_mass=70.0, spatial_averaging=True)
result.sar_wb        # whole-body SAR [W/kg]
result.compliant_sab # True if peak averaged < 10 W/m^2
result.compliant_sar # True if SAR_wb < 0.08 W/kg

# Level comparison
for level in range(7):
    r = engine.compute(body, paths, level=level, ...)
    print(f"Level {level}: P_abs = {r.p_abs:.4f} W")
```

## Kernel formulas (from the monograph)

| Level | Formula | Cost | Requires |
|-------|---------|------|----------|
| 0 | P_abs <= T_0 * A_ab * D_max / 4 * sum(S_i) | O(1) | A_ab, D_max |
| 1 | P_abs = T_0 * A_ab / 4 * sum(S_i * D(k_i)) | O(N) | A_ab, SH coefficients or D_table |
| 2 | S_ab = T_0 * ReLU(N @ (-K)^T) @ s | O(MN) | normals, k_hat, power |
| 3 | S_ab = T_avg(mu) * ReLU(mu) @ s | O(MN) | + complex refractive index |
| 4 | S_ab = [T_avg + q/2 * DeltaT] * ReLU(mu) @ s | O(MN) | + TM excess q |
| 5 | S_ab_3 + T_0 * (H/k) * ReLU(mu)^2 @ s | O(MN) | + curvature H per triangle |
| 6 | Like L5 but ReLU -> GELU(mu, sigma_j) | O(MN) | + local radius of curvature |

## Key design decisions

- **PropagationPaths stores psi (complex amplitude), not power.** Power is derived as |psi|^2 / (2*Z_0). This is future-proof for coherent levels 7-8 which need the full complex amplitude. The `from_powers()` constructor creates synthetic psi from scalar powers for incoherent use.

- **DosimetryEngine is stateless per-call.** It precomputes frequency-dependent quantities (T_0, n_tilde) in __init__ but has no mutable state. Each `compute()` call is independent.

- **Kernels are pure functions.** Each `levelN_*.py` exports a single function that takes arrays and returns arrays. No classes, no state. The engine imports them lazily.

- **Levels 0-1 return uniform S_ab.** These levels compute aggregate power (P_abs) but not the spatial map. The per-triangle S_ab is set to P_abs / A_total as a uniform placeholder.

- **Curvature is optional.** Levels 5-6 accept curvature_H as a parameter. If not provided, the engine defaults to zero curvature (reducing to Level 3 behavior).

## Validation summary

- Flat plane at normal incidence: S_ab = T_0 exactly (all triangles)
- Flat plane at grazing/backside: S_ab = 0 exactly
- Energy conservation: P_abs <= S_inc * T_0 * A_total
- Level 3 matches Level 2 at normal incidence (T_avg(0) = T_0)
- Level 4 with q=0 matches Level 3 exactly
- Level 5 with H=0 matches Level 3 exactly
- Level 6 with H=0 approximates Level 3 (GELU -> ReLU as sigma -> 0)
- TM-dominant (q=+1) absorbs more than unpolarised (q=0)
- Positive curvature adds power (correction is positive)
- All levels produce non-negative S_ab
- Levels 2-6 agree on total power within 20% on icosahedron

## What comes next (Phase 4)

Phase 4 builds coherent MIMO dosimetry (Levels 7-8). This adds new files without modifying Phase 0-3 code.

### New modules needed

```
src/aegis/
    coherent/
        field_channel.py       # G(r) from paths: complex field at each triangle
        fresnel_operator.py    # F_n(r): rank-2 Fresnel transmission operator
        body_channel.py        # G_tilde(r): body channel with depth coupling
        exposure_operator.py   # Q = integral of G_tilde^H @ G_tilde dA
        ecbf.py                # QCQP solver for exposure-constrained BF
    kernels/
        level7_coherent.py     # S_ab = ||G_tilde(r) x||^2
        level8_ecbf.py         # + QCQP solver for optimal x*
    precoder.py                # Precoder dataclass (MRT, ECBF)
```

### Ray tracer integration

Phase 4 also requires realistic propagation paths with full complex amplitudes (psi), not just scalar powers. Two options:

1. **DiffeRT** (recommended): JAX-native ray tracer. `pip install differt`. Reads Sionna XML scene files. Provides `fresnel_coefficients()`, `sp_directions()` for TE/TM decomposition. See `coding_project/ray_tracer_comparison.md` for the full analysis.

2. **Sionna RT** (optional adapter): Dr.Jit-based, heavier dependency, Windows-problematic. Better for users already in the Sionna ecosystem. Add as `PropagationPaths.from_sionna()` constructor.

A `PropagationPaths.from_differt()` constructor should be the primary integration point.

### Key validation targets for Phase 4

From the monograph:
- **Corollary 4.1 (single-wave limit):** Coherent with N=M=1 matches incoherent
- **Corollary 4.2 (incoherent limit):** Random phases, average over realisations -> cross-terms vanish, matches Level 2 within 1%
- **Approximation 1 error:** <= 4% on TM-TM cross-terms (monograph Table 10)
- **Approximation 2 error:** <= 0.44% on Gamma_nn' (monograph Fig. 11)
- **Q is Hermitian positive semi-definite**
- **Q eigenvalues are non-negative and sorted**

### Monograph sections for Phase 4

Read these before implementing:
- `monograph_v2.tex` sections on coherent absorption law (~line 1150-1260)
- `monograph_v2.tex` Theorem 4.1 and Corollaries 4.1-4.2
- `monograph_v2.tex` Approximations 1 and 2
- `monograph_v2.tex` exposure operator Q, eigendecomposition
- `monograph_v2.tex` ECBF QCQP formulation and closed-form solution

### Existing infrastructure to use

- `PropagationPaths.psi` already stores complex[N, 3] amplitude vectors
- `PropagationPaths.element_index` already tracks antenna element assignment
- `DosimetryResult` already has Q, rho, eigenvalues fields (currently None)
- `DosimetryEngine._dispatch()` just needs two more elif branches for levels 7-8
- `tissue/fresnel.py` has `fresnel_transmission()` returning T_s, T_p (power). For coherent, you need the amplitude coefficients t_s, t_p. Add these to `fresnel.py` or create a new function.

### Missing Fresnel amplitude function

The existing `fresnel_transmission()` returns power coefficients T = 1 - |r|^2. Coherent Level 7 needs the complex amplitude transmission coefficients:
- t_s = 2*mu / (mu + xi)
- t_p = 2*n_tilde*mu / (n_tilde^2*mu + xi)

These should be added to `tissue/fresnel.py` as a new function (e.g., `fresnel_amplitude()`), keeping the existing power function unchanged.
