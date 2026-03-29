# Quickstart

Minimal library workflow: synthetic triangle, one plane wave, level 2, peak $S_{\mathrm{ab}}$. See [Getting started](../getting_started.md) for install and STL loading.

```python
import numpy as np

import aegis
from aegis import PropagationPaths

# Tissue at 28 GHz (same numbers as the skin preset in the viewer)
tissue = aegis.TissueModel.from_params("Skin 28 GHz", 17.0, 25.0, 28e9)

# Single upward-facing triangle in the z = 0 plane (metres)
vertices = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]], dtype=float)
normals = np.array([[0.0, 0.0, 1.0]])
centroids = np.array([[1.0 / 3.0, 1.0 / 3.0, 0.0]])
areas = np.array([0.5])
body = aegis.BodyMesh(
    vertices=vertices,
    normals=normals,
    centroids=centroids,
    areas=areas,
    name="triangle",
)

# Incident plane wave from +z: 1 W/m² power density
paths = PropagationPaths.from_powers(
    k_hat=np.array([[0.0, 0.0, -1.0]]),
    power=np.array([1.0]),
)

engine = aegis.DosimetryEngine(tissue)
result = engine.compute(body, paths, level=2)

print(f"peak S_ab: {result.peak_sab:.4f} W/m²")
```

For a real mesh, replace `body` with `aegis.BodyMesh.load("path/to/body.stl")` and point `k_hat` / `power` at your propagation model (or ray tracer output).

Coherent levels 7-8 need complex `psi`, element indices, and a precoder. See [coherent MIMO](coherent.md) and [fidelity levels](fidelity_levels.md).
