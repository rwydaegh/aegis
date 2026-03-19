# Phase 4 hand-off: coherent MIMO dosimetry

Phase 4 built the complete coherent MIMO dosimetry pipeline (Levels 7-8). Given propagation paths with complex amplitudes, a precoding vector, and tissue properties, AEGIS now computes coherent per-triangle absorbed power density, the exposure operator Q, its eigendecomposition, exposure-signal alignment rho, and exposure-constrained beamforming (ECBF).

## What was built

### Source modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `tissue/fresnel.py` (extended) | +60 | `fresnel_amplitude()` returns complex t_s, t_p. `xi_from_mu()` returns xi. |
| `coherent/fresnel_operator.py` | 140 | TE/TM basis vectors, F_n operator, apply F_n to psi |
| `coherent/field_channel.py` | 60 | G(r) field channel matrix from paths |
| `coherent/body_channel.py` | 100 | G_tilde(r) with Fresnel filtering and depth coupling |
| `coherent/exposure_operator.py` | 100 | Q = integral G_tilde^H G_tilde dA, eigendecomposition, rho |
| `coherent/ecbf.py` | 110 | QCQP solver via bisection in Q eigenbasis |
| `coherent/__init__.py` | 30 | Public API re-exports |
| `precoder.py` | 75 | Precoder dataclass with MRT and ECBF constructors |
| `kernels/level7_coherent.py` | 65 | S_ab = norm(G_tilde @ x)^2, returns Q and eigenvalues |
| `kernels/level8_ecbf.py` | 60 | Solves ECBF QCQP then computes S_ab with optimal x* |

### Tests

| File | Tests | What it validates |
|------|-------|-------------------|
| `test_coherent.py` | 26 | Fresnel amplitude (4), TE/TM basis (3), Fresnel operator (3), body channel (2), Q properties (5), rho (2), single-wave limit (1), incoherent limit (1), ECBF (3), Precoder (4), Level 7 engine (2), Level 8 engine (2) |

133 fast tests total (all passing). Lint clean. Version bumped to 0.2.0.

### Public API

```python
import aegis

skin = aegis.TissueModel.from_params("Skin", 17.0, 25.0, 28e9)
body = aegis.BodyMesh.load("thelonious.stl")

# Coherent paths (from ray tracer or synthetic)
paths = aegis.PropagationPaths(
    k_hat=k_hat, psi=psi, element_index=element_index,
    delay=np.zeros(N), is_los=np.ones(N, dtype=bool),
)

# Level 7: coherent absorption map with MRT precoder
h = np.array([...])  # UE channel vector
precoder = aegis.Precoder.mrt(h, P=1.0)
engine = aegis.DosimetryEngine(skin)
result = engine.compute(body, paths, level=7, precoder=precoder, h=h)

result.sab           # (M,) per-triangle S_ab [W/m^2]
result.p_abs         # total absorbed power [W]
result.Q             # (M_ant, M_ant) exposure operator
result.eigenvalues   # (M_ant,) eigenvalues of Q (descending)
result.rho           # exposure-signal alignment in [0, 1]

# Level 8: exposure-constrained beamforming
result = engine.compute(body, paths, level=8,
                        h=h, P_abs_max=0.1)
result.sab           # S_ab with ECBF-optimised precoder
result.p_abs         # <= P_abs_max (constraint satisfied)

# Precoder convenience constructors
p_mrt = aegis.Precoder.mrt(h, P=1.0)
p_ecbf = aegis.Precoder.ecbf(h, Q=result.Q, P_abs_max=0.1, P=1.0)
```

## Monograph equations implemented

| Module | Equation | Monograph reference |
|--------|----------|---------------------|
| `fresnel_amplitude` | t_s = 2*mu/(mu+xi), t_p = 2*n*mu/(n^2*mu+xi) | eq:fresnel-t |
| `te_tm_basis` | e_s = k x n / norm(k x n), e_p = e_s x k | eq:TE-TM-basis |
| `fresnel_operator` | F_n = t_s*e_s@e_s^T + t_p*e_p@e_p^T | def:fresnel-op |
| `field_channel` | g_j(r) = sum psi_n * exp(-ik0*k.r) | eq:G-def |
| `body_channel` | g_tilde_j(r) = sum sqrt(sigma/4alpha) * F_n @ psi_n * exp(-ik0*k.r) | eq:Gtilde-def |
| `exposure_operator` | Q = integral G_tilde^H @ G_tilde dA | def:Q |
| `rho` | rho = h^T Q h* / (norm(h)^2 * lambda_max) | def:rho |
| `ecbf` | x* = sqrt(P) * (lambda*Q + nu*I)^{-1} h* / norm(...) | eq:optimal-x |
| `level7` | S_ab = norm(G_tilde @ x)^2 | thm:coherent-law |
| `level8` | max signal(h^T x)^2 s.t. x^H Q x <= P_abs_max | eq:QCQP |

## Approximations used

- **Approximation 1 (TM direction):** Transmitted TM field direction approximated by incident TM direction. Error <= 4% on TM-TM cross-terms for skin at 28 GHz.
- **Approximation 2 (depth coupling):** Gamma_{nn'} set to 1. Error <= 0.44% for skin at 28 GHz. Allows double sum to factor into squared norm.

## Validation summary

- **Corollary 4.1 (single-wave limit):** N=M=1 coherent matches incoherent Level 3 within 10%
- **Corollary 4.2 (incoherent limit):** Random phases averaged over 200 realisations match Level 3 within 25%
- **Q is Hermitian PSD** with non-negative eigenvalues
- **P_abs = x^H Q x** matches integral of S_ab over surface
- **rho in [0,1]**, equals 1 when h aligns with dominant eigenvector
- **ECBF reduces absorption** below P_abs_max when constraint is feasible
- **ECBF returns MRT** when constraint is slack
- **Power budget:** norm(x*)^2 = P for all precoders
- **S_ab >= 0** everywhere for both Level 7 and Level 8
- Back-facing paths contribute zero to G_tilde

## Key design decisions

- **Fresnel operator is rank-2.** F_n(r) projects psi onto TE/TM and scales by complex t_s, t_p. Different from power-only T_s, T_p used in incoherent levels.

- **Depth coupling weight sqrt(sigma/(4*alpha)).** This is the depth-integral normalization from the monograph's Lemma (depth-integral identity). Varies per (triangle, path) pair because alpha depends on incidence angle.

- **ECBF solved via bisection in Q eigenbasis.** The QCQP reduces to finding a single scalar lambda. The precoder is reconstructed as x* = sqrt(P) * (lambda*Q + I)^{-1} h* / norm. Handles infeasible constraints by returning the minimum-absorption direction.

- **Phase 0-3 code untouched.** All coherent modules are additive. The only modification to existing files is the engine dispatch (two new branches) and the version bump.

## What comes next (Phase 5)

Phase 5 builds the visualization and animation layer. This adds new files without modifying Phase 0-4 code.

### Potential modules

```
src/aegis/
    viz/
        heatmap.py            # S_ab -> vertex colours
        viewer.py             # Interactive 3D viewer
        dashboard.py          # Compliance panel, rho gauge, eigenspectrum
    body/
        skeleton.py           # Joint hierarchy, FK
        skinning.py           # Linear blend skinning
        animation.py          # BVH import, walk cycles
    integration/
        sionna.py             # Sionna RT path import
        differt.py            # DiffeRT path import
```
