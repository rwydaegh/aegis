# Frequently asked questions

## Which fidelity level should I use?

Levels 0 to 8 trade cost and conservatism against physical detail. For many compliance-style checks on incoherent exposure, **level 2** (geometric ReLU plus $T_0$) or **level 3** (full Fresnel angle dependence) is the practical default. Levels 0 and 1 are aggregate or bound-style models and need extra geometry inputs (`A_ab`, directivity data). Levels 4 to 6 add polarisation, curvature, and diffraction terms. Levels 7 and 8 are **coherent MIMO** and require complex path amplitudes plus precoder or channel data, not just scalar powers.

See [Fidelity levels](fidelity_levels.md) for the full list and [Level overview](overview.md) for how they fit the pipeline.

## How do I add a custom tissue type?

Build a `TissueModel` in one of two ways:

1. **Explicit constants** at your frequency: `TissueModel.from_params(name, eps_r, sigma, freq_hz)` or construct `TissueModel(name, eps_r, sigma, freq_hz)` directly.
2. **IT'IS database**: `TissueModel.from_database("Skin", freq_hz)` (or another tissue name from the database) if you have `itis_v5.db` available.

There is no separate plugin registry. Your code holds the `TissueModel` instance and passes it to `DosimetryEngine(tissue)`.

## What coordinate system does the viewer use?

**Python and NumPy geometry in AEGIS use Z-up** (e.g. STL vertices, `BodyMesh`, ray directions in API examples).

The **browser viewer uses Three.js**, which by convention is **Y-up** in the 3D view. Internal transforms bridge the two. When you compare numeric vectors from Python to what you see on screen, expect axes to be permuted in the visualiser.

## How do I export and import dosimetry results?

Both `DosimetryResult` and `PropagationPaths` support round-trip serialization:

```python
# Export
d = result.to_dict()    # plain Python types, skips None fields
s = result.to_json(indent=2)

# Import
result2 = DosimetryResult.from_dict(d)
result3 = DosimetryResult.from_json(s)

# Same pattern for paths
paths_dict = paths.to_dict()
paths2 = PropagationPaths.from_dict(paths_dict)
```

Complex arrays (psi, Q, eigenvalues) are serialized as `{"real": [...], "imag": [...]}` and reconstructed automatically. For raw arrays you can still use `numpy.save`, `numpy.savetxt`, or your own dataframe pipeline from `result.sab` and `body.centroids`.

## How do I construct paths from angles instead of Cartesian directions?

Use `from_spherical()` when your paths are specified as arrival angles:

```python
paths = PropagationPaths.from_spherical(
    theta=np.array([0.0, np.pi / 4]),   # zenith (0 = +z)
    phi=np.array([0.0, np.pi / 2]),      # azimuth
    power=np.array([1.0, 0.5]),
)
```

For uniform illumination analysis, `uniform_sphere()` generates evenly distributed paths:

```python
paths = PropagationPaths.uniform_sphere(n_paths=256, total_power=1.0, seed=42)
```

## How do I combine paths from multiple sources?

`PropagationPaths.concatenate()` merges paths from multiple ray tracers, antenna panels, or scenarios:

```python
combined = PropagationPaths.concatenate([paths_panel_1, paths_panel_2])
```

By default, `reindex_elements=True` keeps antenna element indices disjoint across inputs. Set it to `False` if all paths share a common indexing scheme.

You can also filter by line-of-sight status:

```python
los_only = paths.los_paths
nlos_only = paths.nlos_paths
```

## How do I find which paths dominate the exposure?

The `aegis.analysis` module identifies per-path contributions:

```python
from aegis.analysis import path_contributions, path_importance

# Top 5 paths contributing to peak S_ab
info = path_contributions(body, paths, tissue, top_k=5)
print(f"Top 5 paths account for {info['cumulative'][-1]:.0%} of peak exposure")

# Per-path importance for total absorbed power
importance = path_importance(body, paths, tissue)
```

This is useful for importance sampling in ray tracing and understanding which propagation paths drive the compliance result.
