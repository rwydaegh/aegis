# Overview

AEGIS provides nine fidelity levels (0-8) for computing absorbed power density on human body meshes. Each level adds a physical correction to the previous one, trading accuracy for computational cost.

Levels 0-6 are incoherent: they work with scalar power per path. Levels 7-8 are coherent: they use full complex amplitudes and antenna element structure for MIMO beamforming analysis.

## Typical workflow

1. Load a tissue model (skin properties at your frequency)
2. Load a body mesh (triangle mesh in STL format)
3. Define propagation paths (directions and powers, or full complex amplitudes from a ray tracer)
4. Run the engine at your chosen fidelity level
5. Inspect the result (per-triangle S_ab, total P_abs, compliance status)

For coherent levels, you also provide a precoding vector (via `Precoder.mrt()` or `Precoder.ecbf()`) and optionally a UE channel vector h.

## Key outputs

- `result.sab` - per-triangle absorbed power density [W/m^2]
- `result.p_abs` - total absorbed power [W]
- `result.peak_sab` - maximum S_ab across all triangles
- `result.sar_wb` - whole-body SAR [W/kg] (if body mass provided)
- `result.compliant_sab` - True if peak averaged S_ab < 10 W/m^2
- `result.Q` - exposure operator (levels 7-8)
- `result.eigenvalues` - Q eigenspectrum (levels 7-8)
- `result.rho` - exposure-signal alignment (levels 7-8)

See [fidelity levels](fidelity_levels.md) for details on each level.
