# AEGIS Implementation Plan

## Context

The monograph proves that electromagnetic dosimetry reduces to geometry: `Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]`. This eliminates 10^12-cell volumetric simulation and replaces it with O(M*N) surface operations. AEGIS is the software engine that operationalizes this.

**What exists today:** 40+ Python scripts in `scripts/` with all the core physics (Fresnel, ReLU kernel, Mie validation, ambient occlusion, directivity). Standalone research scripts, not a package. No git repo, no tests, no CI.

**What we're building:** A Python package (`aegis`) with typed data model, fidelity-level dispatch (Levels 0-8), CI/CD, comprehensive tests, and a web frontend with Google 3D Tiles environment.

**Approach:** Vibe coding — AI-assisted, test-driven. E2E tests as safety nets, golden tests from monograph tables, property tests for physics invariants.

---

## 1. Project Setup & DevOps

### Git repo: `aegis/` subdirectory
```
Geometric Dosimetry/
    aegis/                    <-- NEW git repo
        .git/
        pyproject.toml
        src/aegis/
        tests/
    scripts/                  <-- existing reference oracle
    data/                     <-- mesh/db assets
    3dtiles-dl/               <-- cloned VoxelEarth tile downloader
    nodejs-voxelearth/        <-- cloned VoxelEarth voxelizer
```

### Package structure
```
aegis/
    .github/workflows/ci.yml
    .pre-commit-config.yaml
    .gitignore
    pyproject.toml              # hatchling, Python >=3.11
    src/aegis/
        __init__.py
        py.typed
        constants.py
        tissue/
            cole_cole.py        # 4-pole Cole-Cole model
            dielectric.py       # TissueModel dataclass
            fresnel.py          # Fresnel transmission
            database.py         # IT'IS v5.0 SQLite loader
        geometry/
            mesh.py             # BodyMesh dataclass
            occlusion.py        # Ambient occlusion eta
            projected_area.py   # A_perp LUT
            directivity.py      # D(k_hat), SH compression
            cauchy.py           # A_ab, Cauchy formula
            averaging.py        # 4cm^2 spatial averaging
        kernels/
            level0_bound.py
            level1_aggregate.py
            level2_geometric.py     # Core: T0 * ReLU(N @ K^T) @ s
            level3_fresnel.py
            level4_polarisation.py
            level5_curvature.py
            level6_diffraction.py
            level7_coherent.py
            level8_ecbf.py
        coherent/
            field_channel.py
            exposure_operator.py
            ecbf.py
        paths.py                # PropagationPaths dataclass
        result.py               # DosimetryResult dataclass
        engine.py               # DosimetryEngine (level dispatch)
        compliance/
            icnirp.py           # ICNIRP 2020 limits + spatial averaging
    tests/
        conftest.py
        golden/                 # Expected values from monograph tables
        test_tissue.py
        test_fresnel.py
        test_geometry.py
        test_kernels.py
        test_mie.py             # CI canary
        test_e2e.py
        test_properties.py      # Hypothesis property-based
    examples/
```

### Key decisions
- **Build:** hatchling | **Python:** >=3.11 | **Package manager:** uv
- **Core deps:** numpy, scipy | **Optional:** `[gpu]` jax, `[viz]` matplotlib+pyvista, `[dev]` pytest+ruff+hypothesis
- **CI:** GitHub Actions — ruff lint + pytest on py3.11/3.12 x ubuntu/windows
- **Pre-commit:** ruff + codespell + fast pytest (`-m "not slow"`)
- **Data:** mesh files outside git, referenced via `AEGIS_DATA_DIR` env var

---

## 2. Vibe Coding Safety Nets

### E2E tests
1. **Single plane wave on Thelonious:** Load mesh → Sab → check P_abs against golden value
2. **Isotropic illumination:** 100 random directions → verify Cauchy formula within 2%
3. **Level consistency:** Same inputs, levels 2-6 → total power agrees within 5%
4. **Coherent→incoherent:** Level 7 with random phases → matches Level 2 within 1%

### Golden tests (monograph table reproduction)
Table 1 (Fresnel), Table 7 (T0), Table 9 (T_bar), Table 6 (framework error 0.35%), Figure 7 (Mie curve)

### Property-based tests (Hypothesis)
- `Sab(r) >= 0` always
- `P_abs <= S_inc * A_total` (energy conservation)
- `Sab(r) <= S_inc * T0` (max at normal incidence)
- Q is Hermitian PSD

### Visualization as debugging
`.plot()` methods on DosimetryResult and BodyMesh — see the physics, not just numbers.

---

## 3. Google 3D Tiles → Voxel Environment

### Pipeline (using VoxelEarth tools, already cloned)

```
Google 3D Tiles API  (API key + lon/lat/radius)
       ↓
  3dtiles-dl  (Python: download .glb tiles)
       ↓
  nodejs-voxelearth  (Node.js: voxelize with color preservation)
       ↓
  JSON per tile: { x, y, z, wx, wy, wz, r, g, b, a }
       ↓
  Python: merge → classify by color → triangle mesh with material labels
       ↓
  Scene for ray tracing  (Sionna XML or DiffeRT format)
```

### Why voxels instead of raw meshes
Raw photogrammetry meshes are a nightmare (holes, overlaps, degenerate triangles). Voxels are clean, regular, predictable. RGBA color per voxel enables material classification. ~1m resolution is fine for >6 GHz ray tracing.

### Material assignment from voxel color
- Gray/brown (r≈g≈b) → concrete (ε_r≈6)
- Dark gray → asphalt (ε_r≈5)
- Green (g > r, g > b) → vegetation
- Blue (b > r, b > g) → water (ε_r≈80)
- Red/terracotta → brick (ε_r≈4)

### Key files
- `3dtiles-dl/src/tile_api.py` — tile hierarchy traversal (BFS with sphere-vs-OBB culling)
- `3dtiles-dl/src/wgs84.py` — WGS84→ECEF coordinate transforms
- `nodejs-voxelearth/voxelize_tiles.js` — Three.js voxelizer with texture color sampling
- `nodejs-voxelearth/run_pipeline.js` — end-to-end: download + voxelize

### Visualization options (Phase -1 will decide)
- **Option A:** Render colored voxels in Three.js (instanced cubes)
- **Option B:** PyVista Trame (vtk.js in browser, all-Python)
- **Option C:** CesiumJS for streaming photorealistic tiles + dosimetry overlay

---

## 4. Implementation Phases

### Phase -1: Spike / Proof of Concept (Day 1-2)
**Goal:** Test the core loop before investing in architecture.

**Spike A — Voxel environment:**
1. Get Google Maps API key (3D Tiles + Elevation APIs)
2. Download tiles: `python -m scripts.download_tiles -k KEY <lon> <lat> -r 200 -o tiles/`
3. Voxelize: `node voxelize_tiles.js tiles/ voxels/ 200`
4. Python: load voxel JSONs → numpy arrays → display in browser (Trame or plotly)
5. Test color→material classification

**Spike B — Dosimetry heatmap:**
1. Load Thelonious STL (reuse `scripts/_geom.py`)
2. Compute Sab (reuse `scripts/apd_pipeline.py`)
3. Render body mesh + heatmap in browser

**Decision point:** Which frontend approach works best?

### Phase 0: Skeleton & DevOps (Day 2-3)
1. `mkdir aegis && cd aegis && git init`
2. pyproject.toml, src/aegis/__init__.py, tests/conftest.py
3. .pre-commit-config.yaml, .github/workflows/ci.yml, .gitignore
4. `uv pip install -e ".[dev]"` works, `pytest` passes, CI green
5. Push to GitHub

### Phase 1: Tissue Physics (Day 3-6)
Extract from scripts into `aegis.tissue.*`:
- `scripts/_fresnel.py` → `aegis.tissue.fresnel`
- `scripts/mie_theory_corrected.py` → `aegis.tissue.database` + `aegis.tissue.cole_cole`
- `scripts/apd_pipeline.py:42-60` → `aegis.tissue.dielectric` (TissueModel)
- Golden tests: Tables 1, 7, 9
- **Deliverable:** `TissueModel.from_database("Skin").T0(28e9)` → ~0.539

### Phase 2: Body Geometry (Day 6-11)
Extract into `aegis.geometry.*`:
- `scripts/_geom.py` → `aegis.geometry.mesh`
- `scripts/compute_exposure_fraction_eta.py` → `aegis.geometry.occlusion`
- `scripts/compute_body_directivity.py` → `aegis.geometry.directivity`
- **Deliverable:** `BodyMesh.load("thelonious.stl").compute_ambient_occlusion(512)` works

### Phase 3: Incoherent Engine (Day 11-21)
Levels 0-6:
- `scripts/apd_pipeline.py:73-120` → `aegis.kernels.level2_geometric`
- New: DosimetryEngine, PropagationPaths, DosimetryResult
- E2E tests, Mie regression, property tests
- **Deliverable:** `engine.compute(body, paths, level=2)` returns correct results

### Phase 4: Coherent MIMO (Day 21-36)
Levels 7-8: field channel G, exposure operator Q, ECBF solver

### Phase 5: Web Visualization (Day 36+)
Based on Phase -1 findings — either all-Python (Trame) or JS+Python (CesiumJS/Three.js + FastAPI)

### Phase 6: MIMO Visualization + Optimization (Day 50+)
Q eigenspectrum, ECBF demo, antenna placement optimizer, fidelity slider

---

## 5. Extraction Map

| Source Script | Target Module | Key Functions |
|---|---|---|
| `scripts/_fresnel.py` | `aegis.tissue.fresnel` | `n_complex()`, `fresnel_transmission()` |
| `scripts/_geom.py` | `aegis.geometry.mesh` | `load_stl_binary()`, `triangle_areas()` |
| `scripts/apd_pipeline.py:42-60` | `aegis.tissue.dielectric` | `TissueParams` → `TissueModel` |
| `scripts/apd_pipeline.py:73-120` | `aegis.kernels.level2_geometric` | `positive_part()`, `compute_mu_positive()` |
| `scripts/compute_exposure_fraction_eta.py` | `aegis.geometry.occlusion` | BVH + cosine-weighted AO |
| `scripts/compute_body_directivity.py` | `aegis.geometry.directivity` | SH fitting, D(k_hat) |
| `scripts/sab_demo.py` | `aegis.geometry.averaging` | `build_averaging_matrix()` |
| `scripts/mie_theory_corrected.py` | `aegis.tissue.database` | IT'IS SQLite loader |
| `scripts/verify_tables.py` | `tests/golden/*.json` | Golden test data |

---

## 6. Verification

1. `cd aegis && uv pip install -e ".[dev]"`
2. `pytest tests/ -m "not slow"` — golden + property tests pass (~5s)
3. `AEGIS_DATA_DIR=../../data pytest tests/` — Mie regression + mesh tests (~30s)
4. `python examples/01_quickstart.py` — Sab heatmap plot
5. `ruff check src/ tests/` — no lint errors
6. Push to GitHub → CI green

### Most important test
`test_mie_regression()`: Mie theory curve matches monograph Figure 7 → Fresnel, tissue model, and geometric framework are all correct.
