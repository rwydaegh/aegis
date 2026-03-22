# Adding a fidelity kernel

This describes the pattern the repo uses today for **incoherent levels** dispatched from `DosimetryEngine`. Coherent levels 7 and 8 live in `level7_coherent.py` and `level8_ecbf.py` and are invoked from `engine._compute_coherent` instead of `_dispatch`.

## File naming and placement

- One module per level under `src/aegis/kernels/`, e.g. `level2_geometric.py`.
- The public entry point is a function, not a class, named like `level2_geometric`.

## Function signature

Signatures differ by level. Open an existing neighbour for reference:

- **Level 2**: `level2_geometric(normals, k_hat, power, T0)` returns `(M,) sab`.
- **Level 3**: `level3_fresnel(normals, k_hat, power, n_tilde)` uses complex index.
- **Levels 5 to 6**: include `curvature_H`, `T0`, and `freq_hz`.

Match the argument order and dtypes used by `DosimetryEngine._levelN` so you do not have to reshape in the engine.

## Register in `kernels/__init__.py`

Import the function and add its name to `__all__`.

```python
from aegis.kernels.level2_geometric import level2_geometric
```

This keeps `from aegis.kernels import level2_geometric` stable for tests and notebooks.

## Dispatch in `engine.py`

1. Add a branch in `DosimetryEngine._dispatch` for your `level` integer.
2. Implement `DosimetryEngine._levelN` that imports your kernel lazily (same style as existing levels), passes `body.normals`, `paths.k_hat`, `paths.power` or `paths.psi` as required, and returns `sab` as `np.ndarray` with shape `(body.n_triangles,)`.

If the kernel needs extra user inputs (level 0 to 1 style), thread them through `compute(..., **kwargs)` and read them in `_levelN` with `kwargs.get(...)`. Raise `ValueError` when required data is missing.

## Coherent exception

Levels **7 and 8** must return extra arrays (`Q`, eigenvalues, optionally `x_star`, `rho`). See `engine._compute_coherent` for how `DosimetryResult` is filled.

## Testing

Add or extend `tests/test_engine.py` (or a focused test file) to call the kernel directly with small synthetic `normals`, `k_hat`, and `power`. Assert shape `(M,)`, finite values, and $S_{ab} \geq 0$ where that invariant holds for your physics.

Run `py -3.12 -m pytest tests/ -m "not slow" -x` before committing.
