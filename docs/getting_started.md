# Getting started

## Installation

```bash
git clone https://github.com/rwydaegh/aegis.git
cd aegis
pip install -e ".[dev]"
```

### Optional dependency groups

```bash
pip install -e ".[viz]"   # matplotlib, pyvista, trame (visualization)
pip install -e ".[gpu]"   # JAX with CUDA (GPU acceleration)
pip install -e ".[rt]"    # DiffeRT (ray tracing integration)
pip install -e ".[docs]"  # mkdocs (documentation site)
pip install -e ".[all]"   # everything
```

## Your first computation

The simplest AEGIS workflow: one plane wave hitting a single triangle.

```python
import numpy as np
import aegis

# Skin tissue at 28 GHz
skin = aegis.TissueModel.from_params("Skin", 17.0, 25.0, 28e9)

# A single triangle facing upward
vertices = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=float)
normals = np.array([[0, 0, 1.0]])
centroids = np.array([[1/3, 1/3, 0.0]])
areas = np.array([0.5])
body = aegis.BodyMesh(
    vertices=vertices, normals=normals,
    centroids=centroids, areas=areas, name="triangle",
)

# One plane wave from directly above (1 W/m²)
paths = aegis.PropagationPaths.from_powers(
    k_hat=np.array([[0, 0, -1.0]]),
    power=np.array([1.0]),
)

# Compute at Level 2 (default)
engine = aegis.DosimetryEngine(skin)
result = engine.compute(body, paths, level=2)

print(f"S_ab: {result.sab[0]:.3f} W/m²")   # 0.539 (= T_0)
print(f"P_abs: {result.p_abs:.4f} W")
```

The absorbed power density equals $T_0 = 0.539$ because the wave arrives at normal incidence. The ReLU factor $[\hat{n} \cdot (-\hat{k})]_+ = 1$ and the normal-incidence Fresnel transmission $T_0 = 0.539$ for skin at 28 GHz.

## Loading real meshes

For real dosimetry, load a human body mesh from an STL file:

```python
body = aegis.BodyMesh.load("thelonious.stl")
print(f"{body.n_triangles} triangles, area = {body.total_area:.4f} m²")
```

Phantom meshes live in `data/` inside the repo (thelonious, duke, eartha, ella). Override with `AEGIS_DATA_DIR` if needed.

## Tissue model

Three ways to create tissue properties:

```python
from aegis.tissue import TissueModel, SKIN_28GHZ

# 1. Predefined constants
print(SKIN_28GHZ.T0)         # 0.539
print(SKIN_28GHZ.n_complex)  # complex refractive index

# 2. From explicit parameters (eps_r, sigma, freq)
skin = TissueModel.from_params("Skin 60 GHz", eps_r=7.9, sigma=36.4, freq_hz=60e9)

# 3. From IT'IS v5.0 database (needs itis_v5.db)
skin_db = TissueModel.from_database("Skin", 28e9)
```

## Coherent MIMO dosimetry

Levels 7 and 8 handle coherent multi-antenna systems with complex field amplitudes and precoding. See [Coherent MIMO](user_guide/coherent.md) for the full API and examples.

## Comparing fidelity levels

`sweep_levels()` runs all feasible incoherent levels in one call:

```python
results = engine.sweep_levels(body, paths)
for level, r in results.items():
    print(f"Level {level}: P_abs = {r.p_abs:.4f} W, peak = {r.peak_sab:.2f} W/m²")
```

Higher levels add physical corrections (Fresnel, polarisation, curvature, diffraction) that typically change total power by less than 5%. Use `DosimetryResult.compare()` to quantify convergence across levels. See [fidelity levels](user_guide/fidelity_levels.md) for when each correction matters.

## Running tests

```bash
python -m pytest tests/ -m "not slow" -x   # fast tests (~8s)
python -m pytest tests/                     # all tests (~30s)
python -m ruff check src/ tests/            # lint
```

## Interactive 3D viewer

```bash
python -m pip install -e ".[rt]"   # optional: ray tracing in the UI
python -m aegis.viewer --config configs/default.json
```

See [Interactive viewer](user_guide/viewer.md) for scenarios, ports, and API overview.

## Where to go next

- [Interactive viewer](user_guide/viewer.md) for the 3D visualization UI
- [Fidelity levels](user_guide/fidelity_levels.md) for detailed physics of each level
- [Tissue and Fresnel](user_guide/tissue.md) for dielectric properties and transmission coefficients
- [Geometry](user_guide/geometry.md) for mesh operations, occlusion, and spatial averaging
- [Architecture](developer_guide/architecture.md) for module structure and design principles
- [API reference](reference/api.md) for the complete public API
