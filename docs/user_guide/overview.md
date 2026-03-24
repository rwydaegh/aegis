# Overview

AEGIS computes absorbed power density on human body meshes. Two APIs are available. Use `level=` (0-8) to select a predefined fidelity level by integer. Use `mode=` (`bound`, `aggregate`, `spatial`, `coherent`, `ecbf`) with optional correction flags when you need finer control over which physics are applied. Both call the same kernels. See [fidelity levels](fidelity_levels.md) for the full mapping.

## Typical workflow

1. Load a tissue model (skin properties at your frequency)
2. Load a body mesh (triangle mesh in STL format)
3. Define propagation paths (directions and powers, or full complex amplitudes from a ray tracer)
4. Run the engine with your chosen mode and corrections
5. Inspect the result (per-triangle S_ab, total P_abs, compliance status)

For coherent and ECBF modes, you also provide a precoding vector (via `Precoder.mrt()`) and optionally a UE channel vector h.

## Key outputs

- `result.sab` - per-triangle absorbed power density [W/m$^2$]
- `result.p_abs` - total absorbed power [W]
- `result.peak_sab` - maximum $S_{ab}$ across all triangles
- `result.sar_wb` - whole-body SAR [W/kg] (if body mass provided)
- `result.compliant_sab` - True/False if spatial averaging was applied, None otherwise
- `result.Q` - exposure operator (coherent and ECBF modes)
- `result.eigenvalues` - Q eigenspectrum (coherent and ECBF modes)
- `result.rho` - exposure-signal alignment (coherent and ECBF modes)

See [fidelity levels](fidelity_levels.md) for details on each mode and correction.

## Comparing fidelity levels

`sweep_levels()` runs multiple fidelity levels in one call and returns a dict of results. Levels that need unavailable parameters (e.g. $A_{ab}$ for level 0) are silently skipped.

```python
results = engine.sweep_levels(body, paths)
for level, r in results.items():
    print(f"Level {level}: peak = {r.peak_sab:.2f} W/m², P_abs = {r.p_abs:.4f} W")
```

To quantify the differences between results, use `DosimetryResult.compare()`:

```python
from aegis import DosimetryResult

comparison = DosimetryResult.compare(
    {f"L{k}": v for k, v in results.items()}
)
print(f"Relative errors: {comparison['relative_error']}")
```

This returns peak $S_{ab}$, $P_{abs}$, pairwise RMSE, max absolute error, and relative error across all pairs.

## Scaling and compliance shortcuts

`DosimetryResult.scale(factor)` returns a new result with all power quantities scaled. Combined with `evaluate_compliance()`, this lets you sweep transmit power without rerunning the engine:

```python
result = engine.compute(body, paths, mode="spatial")

# Scale to 2 W and check compliance
scaled = result.scale(2.0)
compliance = scaled.evaluate_compliance()
print(f"Compliant at 2 W: {compliance.overall_pass}")
```

See [compliance](compliance.md) for the full compliance workflow including `max_compliant_power()`.

## Serialization

Both `PropagationPaths` and `DosimetryResult` support round-trip serialization:

```python
# Save
d = result.to_dict()
s = result.to_json(indent=2)

# Load
result2 = DosimetryResult.from_dict(d)
result3 = DosimetryResult.from_json(s)
```

`PropagationPaths` has the same `to_dict()` / `from_dict()` pattern. Complex arrays (psi, Q, eigenvalues) are serialized as `{"real": [...], "imag": [...]}`.
