# Overview

AEGIS computes absorbed power density on human body meshes. You choose a computation mode (`bound`, `aggregate`, `spatial`, `coherent`, or `ecbf`) and toggle independent physics corrections. The `mode=` parameter is the primary API. Integer `level=` (0-8) still works for backward compatibility and maps to specific mode + correction combinations. See [fidelity levels](fidelity_levels.md) for full details.

## Typical workflow

1. Load a tissue model (skin properties at your frequency)
2. Load a body mesh (triangle mesh in STL format)
3. Define propagation paths (directions and powers, or full complex amplitudes from a ray tracer)
4. Run the engine with your chosen mode and corrections
5. Inspect the result (per-triangle S_ab, total P_abs, compliance status)

For coherent and ECBF modes, you also provide a precoding vector (via `Precoder.mrt()`) and optionally a UE channel vector h.

## Key outputs

- `result.sab` - per-triangle absorbed power density [W/m^2]
- `result.p_abs` - total absorbed power [W]
- `result.peak_sab` - maximum S_ab across all triangles
- `result.sar_wb` - whole-body SAR [W/kg] (if body mass provided)
- `result.compliant_sab` - True/False if spatial averaging was applied, None otherwise
- `result.Q` - exposure operator (coherent and ECBF modes)
- `result.eigenvalues` - Q eigenspectrum (coherent and ECBF modes)
- `result.rho` - exposure-signal alignment (coherent and ECBF modes)

See [fidelity levels](fidelity_levels.md) for details on each mode and correction.
