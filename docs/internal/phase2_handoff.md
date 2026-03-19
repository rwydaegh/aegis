# Phase 2 hand-off: body geometry

Phase 2 extracted body geometry operations from oracle scripts into `src/aegis/geometry/`. The full mesh loading, projected area, directivity, Cauchy formula, BVH-accelerated ambient occlusion, and ICNIRP spatial averaging pipeline is in place.

## What was built

### Source modules

| Module | Lines | Extracted from | Purpose |
|--------|-------|----------------|---------|
| `geometry/mesh.py` | 100 | `scripts/_geom.py` | BodyMesh dataclass, STL loading, triangle areas |
| `geometry/occlusion.py` | 260 | `scripts/compute_exposure_fraction_eta.py` | BVH, ray-mesh intersection, cosine-weighted AO |
| `geometry/projected_area.py` | 65 | `scripts/compute_projected_area_table.py` | A_perp LUT, Fibonacci sphere sampling |
| `geometry/directivity.py` | 115 | `scripts/compute_body_directivity.py` | D(k_hat), SH fit/eval, reconstruction error |
| `geometry/cauchy.py` | 30 | `scripts/verify_cauchy_fixes.py` | Cauchy formula, mean projected area |
| `geometry/averaging.py` | 60 | `scripts/sab_demo.py` | ICNIRP 4 cm^2 spatial averaging via KD-tree |
| `geometry/__init__.py` | 35 | (new) | Public API re-exports |

### Tests

| File | Tests | What it validates |
|------|-------|-------------------|
| `test_geometry.py` | 35 unit | Cube/triangle mesh, Fibonacci sphere, projected area, Cauchy, directivity, SH fit, BVH, tangent frame |
| `test_geometry.py` | 7 slow | Thelonious: 23,826 triangles, unit normals, positive areas, Cauchy identity, directivity mean=1 |

42 geometry tests total. 77 tests across the full suite (70 fast + 7 slow), all passing. Lint clean.

### Public API

```python
from aegis.geometry import BodyMesh, compute_projected_area, fibonacci_sphere

# Load mesh
mesh = BodyMesh.load("thelonious.stl")
mesh.n_triangles   # 23826
mesh.total_area     # surface area in mesh units^2
mesh.scale          # bounding box diagonal

# Projected area LUT
k_hat = fibonacci_sphere(2048)
A_perp = compute_projected_area(mesh.normals, mesh.areas, k_hat)

# Directivity
from aegis.geometry import compute_directivity, spherical_angles_from_k_hat
D = compute_directivity(A_perp)       # mean = 1.0 by construction

# SH compression
from aegis.geometry import sh_reconstruction_error
result = sh_reconstruction_error(D, theta, phi, L=4)
result["rms"]  # reconstruction error

# Cauchy formula
from aegis.geometry import cauchy_projected_area, cauchy_relative_error
cauchy_projected_area(mesh.total_area)    # A_total / 4
cauchy_relative_error(A_perp, mesh.total_area)  # ~0 for closed surfaces

# Ambient occlusion (slow, BVH ray tracing)
from aegis.geometry import compute_ambient_occlusion
eta = compute_ambient_occlusion(mesh, n_rays=64)  # (N,) in [0, 1]

# ICNIRP 4 cm^2 averaging
from aegis.geometry import apply_spatial_averaging
sab_avg = apply_spatial_averaging(sab, mesh.centroids, mesh.areas)
```

## Key design decisions

- `BodyMesh` is a frozen dataclass wrapping arrays. No methods that mutate state.
- `compute_ambient_occlusion` takes a `BodyMesh` directly (not raw arrays). This is the only geometry function with a mesh dependency. All others operate on normals/areas arrays for flexibility.
- The Cauchy formula `mean(A_perp) = A_total/4` holds exactly for any closed surface when computed without ray-traced self-occlusion. Self-occlusion only matters when computing `A_perp` with visibility rays.
- SH compression uses scipy's `sph_harm` directly. No custom implementation needed.

## Validation summary

- Thelonious loads with 23,826 triangles (matches oracle)
- All normals are unit vectors (atol=1e-6)
- All triangle areas are positive
- Cauchy identity: mean(A_perp) = A_total/4 within 1% for Thelonious
- Fibonacci sphere produces deterministic, uniform unit vectors
- SH fit: constant function perfectly captured at L=0, higher L reduces error monotonically
- Cube projected area = 1.0 along all axes (exact)

## What comes next (Phase 3)

Phase 3 builds the incoherent dosimetry engine (Levels 0-6):

1. `kernels/level2_geometric.py`: S_ab(r) = S_inc * T_0 * ReLU[n.(-k)]
2. `paths.py`: PropagationPaths dataclass
3. `result.py`: DosimetryResult dataclass
4. `engine.py`: DosimetryEngine with level dispatch
5. E2E tests: single plane wave on Thelonious, Mie regression, property tests

The deliverable: `engine.compute(body, paths, level=2)` returns correct S_ab, P_abs, and SAR_wb for Thelonious under a plane wave.
