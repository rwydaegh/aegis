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

The absorbed power density equals $T_0 = 0.539$ because the wave arrives at normal incidence. The ReLU factor $[\hat{n} \cdot (-\hat{k})]_+ = 1$ and the normal-incidence Fresnel transmission $\mathcal{T}_0 = 0.539$ for skin at 28 GHz.

## Loading real meshes

For real dosimetry, load a human body mesh from an STL file:

```python
body = aegis.BodyMesh.load("thelonious.stl")
print(f"{body.n_triangles} triangles, area = {body.total_area:.4f} m²")
```

Mesh files live outside the git repo in `../data/`. Set the `AEGIS_DATA_DIR` environment variable or place files at the default location (two directories above the repo root).

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

Levels 7 and 8 use full complex amplitudes and antenna element structure for MIMO analysis.

### Level 7: coherent map

```python
import numpy as np
import aegis

skin = aegis.TissueModel.from_params("Skin", 17.0, 25.0, 28e9)
body = aegis.BodyMesh.load("thelonious.stl")

# 20 paths from 4 antenna elements with complex amplitudes
N, M_ant = 20, 4
rng = np.random.default_rng(42)
k_hat = rng.standard_normal((N, 3))
k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
psi = rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))
element_index = rng.integers(0, M_ant, size=N)

paths = aegis.PropagationPaths(
    k_hat=k_hat, psi=psi, element_index=element_index,
    delay=np.zeros(N), is_los=np.ones(N, dtype=bool),
)

# MRT precoder from a channel vector
h = rng.standard_normal(M_ant) + 1j * rng.standard_normal(M_ant)
precoder = aegis.Precoder.mrt(h, P=1.0)

engine = aegis.DosimetryEngine(skin)
result = engine.compute(body, paths, level=7, precoder=precoder, h=h)

print(f"P_abs: {result.p_abs:.4f} W")
print(f"rho: {result.rho:.3f}")          # exposure-signal alignment
print(f"Top eigenvalues: {result.eigenvalues[:3]}")
```

### Level 8: exposure-constrained beamforming

```python
result = engine.compute(body, paths, level=8, h=h, P_abs_max=0.05)

print(f"P_abs: {result.p_abs:.4f} W (constrained to <= 0.05)")
print(f"rho: {result.rho:.3f}")
```

Level 8 solves a QCQP to find the precoder that maximizes signal power while keeping absorbed power below `P_abs_max`.

## Comparing fidelity levels

```python
for level in range(7):
    r = engine.compute(body, paths, level=level, ...)
    print(f"Level {level}: P_abs = {r.p_abs:.4f} W, peak = {r.peak_sab:.2f} W/m²")
```

Higher levels add physical corrections (Fresnel, polarisation, curvature, diffraction) that typically change total power by less than 5%. See [fidelity levels](user_guide/fidelity_levels.md) for when each correction matters.

## Running tests

```bash
py -3.12 -m pytest tests/ -m "not slow" -x   # fast tests (~8s)
py -3.12 -m pytest tests/                     # all tests (~30s)
py -3.12 -m ruff check src/ tests/            # lint
```

## Interactive 3D viewer

```bash
py -3.12 -m pip install -e ".[rt]"   # optional: ray tracing in the UI
py -3.12 -m aegis.viewer --config configs/default.json
```

See [Interactive viewer](user_guide/viewer.md) for scenarios, ports, and API overview.

## Where to go next

- [Interactive viewer](user_guide/viewer.md) for the Flask + Three.js UI
- [Fidelity levels](user_guide/fidelity_levels.md) for detailed physics of each level
- [Tissue and Fresnel](user_guide/tissue.md) for dielectric properties and transmission coefficients
- [Geometry](user_guide/geometry.md) for mesh operations, occlusion, and spatial averaging
- [Architecture](developer_guide/architecture.md) for module structure and design principles
- [API reference](reference/api.md) for the complete public API
