# Phase 1 hand-off: tissue physics

Phase 1 extracted tissue electromagnetic properties from the oracle scripts into `src/aegis/tissue/`. The full Cole-Cole pipeline is validated against monograph tables and Mie theory.

## What was built

### Source modules

| Module | Lines | Extracted from | Purpose |
|--------|-------|----------------|---------|
| `tissue/fresnel.py` | 75 | `scripts/_fresnel.py` | Fresnel power transmission (T_s, T_p, T_0) |
| `tissue/cole_cole.py` | 48 | `scripts/mie_theory_corrected.py:109-129` | 4-pole Cole-Cole permittivity model |
| `tissue/database.py` | 130 | `scripts/mie_theory_corrected.py:55-161` | IT'IS v5.0 SQLite loader |
| `tissue/dielectric.py` | 80 | `scripts/apd_pipeline.py:42-69` | TissueModel dataclass |
| `tissue/__init__.py` | 20 | (new) | Public API re-exports |

### Tests

| File | Tests | What it validates |
|------|-------|-------------------|
| `test_fresnel.py` | 14 | Monograph Table 1 golden values, physics invariants |
| `test_tissue.py` | 10 | TissueModel construction, predefined instances, immutability |
| `golden/test_tables.py` | 11 | Monograph Tables 4+5 via Cole-Cole pipeline |
| `test_mie.py` | 4 | R_sphere, large-sphere convergence, error monotonicity |
| `test_properties.py` | 8 | Hypothesis: T_0 bounded, T_s/T_p bounded, |n| >= 1 |

50 tests total, all passing. Lint clean.

### Public API

```python
from aegis.tissue import TissueModel, SKIN_28GHZ, fresnel_transmission, n_complex

# Predefined tissues (hardcoded params from literature)
SKIN_28GHZ.T0       # 0.539
SKIN_60GHZ.T0       # 0.622
MUSCLE_28GHZ.T0     # 0.481
FAT_28GHZ.T0        # 0.876

# Construct from explicit params
skin = TissueModel.from_params("Skin", 17.0, 25.0, 28e9)

# Construct from IT'IS database (Cole-Cole model)
skin_db = TissueModel.from_database("Skin", 28e9)
skin_db.T0  # 0.536 (IT'IS Cole-Cole gives eps_r=16.55, sigma=25.8)

# Angle-dependent Fresnel
T_s, T_p = fresnel_transmission(cos_theta, skin.n_complex)
```

### Note on hardcoded vs database values

The predefined instances (`SKIN_28GHZ`, etc.) use rounded literature values (eps_r=17.0, sigma=25.0) and give T_0 = 0.539. The IT'IS database via Cole-Cole gives slightly different values (eps_r=16.55, sigma=25.8) and T_0 = 0.536. Both are correct within the tissue parameter uncertainty (~20%). The monograph tables use IT'IS values.

## Validation summary

- Fresnel golden tests match monograph Table 1 within 0.002
- Cole-Cole pipeline matches monograph Table 4 (T_0 vs frequency) within 0.003
- Cole-Cole pipeline matches monograph Table 5 (eps_r, |n|) within 2%
- Mie regression: R_sphere = 0.988 at 28 GHz (framework is 1.2% conservative)
- Hypothesis found no violations across 1000+ random parameter combinations

## What comes next (Phase 2)

Phase 2 extracts body geometry into `src/aegis/geometry/`:

1. **Mesh loading** (`geometry/mesh.py`): `BodyMesh` dataclass wrapping STL loading, normals, centroids, areas. Extracted from `scripts/_geom.py`.

2. **Ambient occlusion** (`geometry/occlusion.py`): BVH-accelerated cosine-weighted ambient occlusion (exposure fraction eta). Extracted from `scripts/compute_exposure_fraction_eta.py`.

3. **Directivity** (`geometry/directivity.py`): Body directivity D(k_hat) with spherical harmonic compression. Extracted from `scripts/compute_body_directivity.py`.

4. **Projected area** (`geometry/projected_area.py`): A_perp lookup table.

5. **Cauchy formula** (`geometry/cauchy.py`): A_ab from the Cauchy surface area formula.

The deliverable: `BodyMesh.load("thelonious.stl").total_area` returns the correct surface area, ambient occlusion runs in under 10s, and directivity matches the oracle scripts.

### Key oracle scripts for Phase 2

| Source | Target | Key functions |
|--------|--------|---------------|
| `scripts/_geom.py` | `aegis.geometry.mesh` | `load_stl_binary()`, `triangle_areas()` |
| `scripts/compute_exposure_fraction_eta.py` | `aegis.geometry.occlusion` | BVH + cosine-weighted AO |
| `scripts/compute_body_directivity.py` | `aegis.geometry.directivity` | SH fitting, D(k_hat) |
| `scripts/sab_demo.py` | `aegis.geometry.averaging` | `build_averaging_matrix()` |

### Tests needed for Phase 2

- Thelonious triangle count: 23,826
- Total surface area matches oracle
- Normals are unit vectors
- Ambient occlusion eta in (0, 1) for all faces
- Directivity integrates to 4*pi over the sphere
- Cauchy formula: A_ab = A_total / 4 for convex body
