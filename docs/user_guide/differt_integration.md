# DiffeRT integration

DiffeRT is a JAX-based differentiable ray tracer. It enumerates all paths up to a given bounce order by exhaustive search, which makes it exact but O(N^K) in scene triangles N and bounce order K. It works on any platform where JAX runs, including Windows.

## Requirements

```bash
pip install aegis[rt]    # installs differt >= 0.7.0
```

DiffeRT runs on CPU by default. JAX GPU acceleration is supported if a CUDA-compatible GPU and the `jax[cuda]` package are present, but it is not required.

## High-level usage

`paths_from_differt_scene()` is the main entry point. It loads a Mitsuba/Sionna XML scene, runs ray tracing for each TX element and bounce order, and returns a `PropagationPaths` object ready for any AEGIS fidelity level.

```python
import numpy as np
from aegis.integration.differt import paths_from_differt_scene
from aegis import DosimetryEngine
from aegis.tissue.dielectric import SKIN_28GHZ

paths = paths_from_differt_scene(
    scene_path="scene.xml",
    tx_positions=np.array([[0.0, 0.0, 10.0]]),   # (M_ant, 3) [m]
    rx_position=np.array([5.0, 0.0, 1.5]),        # body position [m]
    freq_hz=28e9,
    max_bounces=3,
    tx_power_dbm=30.0,
    initial_polarisation="vertical",
)

engine = DosimetryEngine(SKIN_28GHZ)
result = engine.compute(body, paths, level=2)
```

The `scene_path` accepts the same Mitsuba XML format used by Sionna RT, so scenes created for Sionna work with DiffeRT without modification.

## Low-level usage

If you already have DiffeRT path data, `paths_from_differt()` converts it directly to `PropagationPaths` without re-running the scene loading or path enumeration. This is useful when you want to control the DiffeRT scene setup yourself or integrate into an existing JAX pipeline.

```python
from aegis.integration.differt import paths_from_differt

paths = paths_from_differt(
    vertices=scene_vertices,          # (N_triangles, 3)
    normals=scene_normals,            # (N_triangles, 3)
    path_vertices=path_verts,         # (N_paths, N_bounces+2, 3)
    tx_positions=tx_pos,              # (M_ant, 3)
    freq_hz=28e9,
    tx_power_dbm=30.0,
    object_indices=obj_idx,           # (N_paths, path_length)
    material_indices=face_materials,  # (N_triangles,)
    material_n_tilde=n_tilde_list,    # list of complex per material
    initial_polarisation="vertical",
)
```

When `object_indices` and `material_n_tilde` are omitted, AEGIS assigns an arbitrary perpendicular polarisation to each path. This is sufficient for incoherent fidelity levels (0-6), where only $|\boldsymbol{\psi}|^2$ enters the computation.

## How psi is computed

For each path, AEGIS computes the E-field amplitude from free-space path loss:

$$|\psi_0| = \frac{\sqrt{2 Z_0 P_T / (4\pi)}}{d}$$

where $d$ is the total path length, $Z_0 = 376.73\;\Omega$, and $P_T$ is the transmit power in watts. The initial polarisation vector is set from the TX antenna orientation (vertical or horizontal).

At each reflection, the field is decomposed into TE and TM components. Fresnel reflection coefficients are applied using the surface normal and the material refractive index. The reflected field is reconstructed in the new propagation frame. Material properties default to concrete ($\varepsilon_r = 5.31$, $\sigma = 0.0326$ S/m at 28 GHz) when the scene provides no material assignments.

The arrival direction $\hat{k}$ is taken from the last non-degenerate path segment. DiffeRT pads variable-length paths to the same array shape, so zero-length padding segments are skipped.

## Element indexing

For multi-element TX arrays, each path is assigned to a TX element. If `element_indices` is not provided, AEGIS assigns each path to the nearest TX element by Euclidean distance from the path's first vertex. Pass explicit `element_indices` when paths are pre-sorted per element for best accuracy.

## Platform compatibility

DiffeRT works on Linux, Windows, and macOS. It does not require a GPU. The JAX backend defaults to CPU. Set `JAX_PLATFORM_NAME=gpu` or call `jax.config.update("jax_platform_name", "gpu")` before importing to use GPU acceleration.

For city-scale scenes where the O(N^K) enumeration becomes too slow, switch to Sionna RT. See [Sionna RT integration](sionna_integration.md) for details and a feature comparison table.
