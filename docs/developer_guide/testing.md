# Testing

## Test categories

AEGIS uses several categories of tests:

- **Golden tests** reproduce monograph table values. Located in `tests/golden/`. These validate the Cole-Cole pipeline against published numerical data.
- **Property tests** check physics invariants using Hypothesis. These hold for any valid input: T_0 in (0,1), |n| >= 1, T_s and T_p bounded.
- **Regression tests** compare against the Mie theory analytical solution. The Mie test is the CI canary.
- **Engine tests** validate the incoherent dosimetry pipeline (levels 0-6) from PropagationPaths through DosimetryResult on synthetic meshes.
- **Coherent tests** validate the MIMO pipeline (levels 7-8), including Q properties, corollaries 4.1-4.2, ECBF constraint satisfaction, and the Precoder dataclass.
- **Unit tests** cover individual modules: Cole-Cole, compliance, config, paths, backend, Cauchy, integration, Sionna.
- **Viewer tests** cover config loading, authentication, compute endpoints, and E2E browser testing.
- **Visualization tests** verify heatmap, dashboard, and comparison plot generation.
- **E2E tests** (marked slow) run the full pipeline on the Thelonious mesh.

## Running tests

```bash
# Fast tests only (~7s, no data dependencies)
py -3.12 -m pytest tests/ -m "not slow" -x

# All tests including mesh-dependent tests (~30s)
py -3.12 -m pytest tests/

# Specific subsystems
py -3.12 -m pytest tests/test_engine.py -v       # Engine + incoherent kernels
py -3.12 -m pytest tests/test_coherent.py -v      # Coherent MIMO pipeline
py -3.12 -m pytest tests/test_fresnel.py -v       # Fresnel golden + properties
py -3.12 -m pytest tests/test_mie.py -v            # Mie regression canary
py -3.12 -m pytest tests/golden/ -v                # Monograph table reproduction
py -3.12 -m pytest tests/test_properties.py -v     # Hypothesis property tests
py -3.12 -m pytest tests/test_geometry.py -v       # Geometry operations
```

## Current test inventory

| File | Tests | Category | Slow |
|------|-------|----------|------|
| `test_smoke.py` | 3 | Smoke | No |
| `test_fresnel.py` | 19 | Golden + property | No |
| `test_tissue.py` | 10 | Unit | No |
| `test_cole_cole.py` | 8 | Unit | No |
| `test_properties.py` | 8 | Property (Hypothesis) | No |
| `test_geometry.py` | 42 | Unit + mesh | Partially |
| `test_engine.py` | 35 | Engine + incoherent kernels | 1 slow |
| `test_coherent.py` | 30 | Coherent MIMO pipeline | No |
| `test_paths.py` | 4 | Unit | No |
| `test_compliance.py` | 5 | Unit | No |
| `test_config.py` | 8 | Unit | No |
| `test_backend.py` | 5 | Unit | No |
| `test_cauchy.py` | 1 | Unit | No |
| `test_integration.py` | 13 | Integration | No |
| `test_sionna.py` | 5 | Integration | No |
| `test_run.py` | 4 | CLI | No |
| `test_viz.py` | 13 | Visualization | No |
| `test_viewer_config.py` | 7 | Viewer | No |
| `test_viewer_auth.py` | 4 | Viewer | No |
| `test_viewer_compute.py` | 2 | Viewer | No |
| `test_voxel_pipeline.py` | 6 | Viewer | No |
| `test_voxel_rt_mesh.py` | 14 | Viewer | No |
| `test_jax_grad.py` | 3 | Unit | No |
| `test_e2e_lab_fixture.py` | 3 | E2E | No |
| `golden/test_tables.py` | 11 | Golden | Yes |
| `test_mie.py` | 4 | Regression | Yes |
| **Total** | **267** | | |

242 fast tests. 25 slow/skipped (data-dependent).

## Engine test structure

The engine tests (`test_engine.py`) use synthetic meshes to avoid data dependencies:

- **Flat plane** (100 triangles, normals +z): Tests normal incidence (S_ab = T_0), grazing (S_ab = 0), backside (S_ab = 0), P_abs = T_0 * A_total.
- **Icosahedron** (20 triangles, ~sphere): Tests non-negative S_ab, energy bounds, multi-path scenarios, level consistency.

Test classes map to fidelity levels: `TestLevel0` through `TestLevel6`, plus `TestLevelConsistency` for cross-level checks.

Key incoherent invariants tested:

- S_ab >= 0 always
- P_abs <= S_inc * T_0 * A_total (energy conservation)
- Level 3 matches Level 2 at normal incidence
- Level 4 with q=0 matches Level 3 exactly
- Level 5 with H=0 matches Level 3 exactly
- Levels 2-6 total power agrees within 20% on simple bodies
- TM-dominant polarisation absorbs more than unpolarised

## Coherent test structure

The coherent tests (`test_coherent.py`) validate the full MIMO pipeline:

- **Fresnel amplitude**: consistency with power coefficients, vectorised operation
- **TE/TM basis**: orthogonality to k_hat, mutual perpendicularity, unit norms
- **Fresnel operator**: zero for back-facing, non-zero for front-facing, correct amplitude at normal incidence
- **Body channel**: correct output shape, back-facing contributes nothing
- **Exposure operator Q**: Hermitian, PSD, non-negative descending eigenvalues, P_abs = x^H Q x matches surface integral
- **rho**: in [0,1], equals 1.0 for dominant eigenvector
- **Corollary 4.1**: single-wave coherent matches incoherent Level 3 within 10%
- **Corollary 4.2**: random-phase average over 200 realisations matches incoherent within 25%
- **ECBF**: returns MRT when unconstrained, respects power budget, reduces absorption below constraint
- **Precoder**: correct power, correct MRT direction, validation errors
- **Level 7 engine**: returns Q and eigenvalues, S_ab non-negative
- **Level 8 engine**: requires h, reduces absorption vs MRT

## Data dependencies

Tests marked `@pytest.mark.slow` need external data:

- `golden/test_tables.py` needs `itis_v5.db` (IT'IS database) in the data directory
- `test_mie.py` needs `miepython` and `scipy` (both in `[dev]` extras)
- `test_geometry.py` slow tests need `thelonious.stl` mesh
- `test_engine.py::TestE2EThelonious` needs `thelonious.stl` mesh

Data files ship in `data/` inside the repo. Override with `AEGIS_DATA_DIR` if needed.

## Golden test values

**Table 1 (Fresnel, skin at 28 GHz):** T_s, T_p, T_avg at 0, 30, 45, 60, 75 degrees. Tolerance: 0.002.

**Table 4 (T_0 vs frequency, IT'IS skin):** T_0 at 6, 10, 28, 40, 60, 100 GHz. Tolerance: 0.003.

**Table 5 (skin dielectric properties):** eps_r and |n| at 6, 28, 60, 100 GHz. Tolerance: 2% relative for eps_r, 0.05 absolute for |n|.

## Mie regression (the canary)

The Mie test validates the entire framework against an independent analytical solution. It computes R_sphere = T_0 / Q_abs_GO for skin at 28 GHz and checks:

- R_sphere ~ 0.988 (framework underestimates by ~1.2%)
- R_sphere < 1.0 (conservative at 28 GHz)
- Error decreases monotonically with sphere size
- Large-sphere Q_abs converges toward the GO limit

If this test fails, something fundamental is broken in the Fresnel or tissue model.
