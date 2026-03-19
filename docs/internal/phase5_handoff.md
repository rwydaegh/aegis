# Phase 5 hand-off: ray tracer integration and visualization

Phases 0-4 built the complete dosimetry engine (Levels 0-8). The physics pipeline is finished. What remains is connecting it to real-world inputs (ray tracers) and outputs (visualization).

## Current state

### What works

All nine fidelity levels are implemented and tested:

- Levels 0-6: incoherent dosimetry from scalar power per path
- Level 7: coherent MIMO from complex amplitude vectors
- Level 8: exposure-constrained beamforming (ECBF QCQP solver)
- 133 fast tests passing, lint clean, version 0.2.0

### What's missing

**No ray tracer integration.** PropagationPaths currently has only `from_powers()` which creates synthetic paths from scalar powers. There is no way to load paths from a ray tracer.

**No visualization.** Results are numpy arrays. There is no heatmap renderer, no 3D viewer, no compliance dashboard.

## Phase 5 plan

### 5A: ray tracer integration (priority)

The coherent pipeline needs real propagation paths with full complex amplitudes. Two options exist:

#### Option 1: DiffeRT (recommended)

DiffeRT is a JAX-native differentiable ray tracer. `pip install differt`. Reads Sionna XML scene files.

Build a `PropagationPaths.from_differt()` constructor that:

1. Runs DiffeRT on a scene file to get paths
2. Extracts k_hat (direction of arrival at body surface)
3. Extracts psi (complex polarisation-amplitude vector) from DiffeRT's `fresnel_coefficients()` and `sp_directions()` for TE/TM decomposition
4. Maps paths to antenna elements via `element_index`
5. Returns a PropagationPaths ready for any AEGIS level

Key DiffeRT functions to use:
- `differt.scene.load()` for scene loading
- Path output gives: directions, delays, amplitudes, polarisation
- `fresnel_coefficients()` for reflection/transmission at each interaction
- `sp_directions()` for TE/TM basis at each reflection

The comparison document at `../coding_project/ray_tracer_comparison.md` has the full DiffeRT vs Sionna analysis.

#### Option 2: Sionna RT (optional adapter)

Sionna is more mature but has heavier dependencies (Dr.Jit, TensorFlow) and Windows compatibility issues. Add as `PropagationPaths.from_sionna()` if users need it.

### 5B: visualization

#### Heatmap rendering

Build `aegis.viz.heatmap` that maps S_ab values to vertex colors on the body mesh. Options:

- **Plotly** (prototyping, already validated in Phase -1 spikes): interactive Mesh3d in browser
- **PyVista** (publication quality): Trame for web, VTK for offline
- **Matplotlib** (static): 2D projections, directivity plots

The Phase -1 spike at `examples/spike_b_heatmap.py` already demonstrates Plotly heatmap rendering on Thelonious with 23k triangles in ~5 seconds.

#### Compliance dashboard

Show whole-body SAR, peak S_ab, compliance status, and (for coherent) rho and Q eigenspectrum.

#### Level comparison view

Side-by-side or overlay of S_ab maps from different fidelity levels on the same body/paths.

### 5C: examples

Build working examples in `examples/`:

1. `01_quickstart.py` - single plane wave, Level 2, Plotly heatmap
2. `02_multi_source.py` - N random paths, level comparison
3. `03_coherent_mimo.py` - synthetic MIMO paths, Level 7, Q eigenspectrum
4. `04_ecbf.py` - MRT vs ECBF comparison, absorption reduction
5. `05_differt_scene.py` - load scene from DiffeRT, full pipeline

## Files to create

```
src/aegis/
    integration/
        __init__.py
        differt.py          # PropagationPaths.from_differt() or standalone loader
        sionna.py           # PropagationPaths.from_sionna() (optional)
    viz/
        __init__.py
        heatmap.py          # S_ab -> colored mesh (Plotly, PyVista)
        dashboard.py        # Compliance panel, rho gauge, eigenspectrum
        comparison.py       # Side-by-side level comparison
examples/
    01_quickstart.py
    02_multi_source.py
    03_coherent_mimo.py
    04_ecbf.py
    05_differt_scene.py
tests/
    test_integration.py     # DiffeRT path loading (may need mocking)
    test_viz.py             # Smoke tests for visualization
```

## Existing infrastructure to use

- `PropagationPaths` already stores psi (complex vector), element_index, and all metadata needed
- `DosimetryResult` has all fields (S_ab, Q, eigenvalues, rho) ready for visualization
- `examples/spike_b_heatmap.py` has working Plotly code for S_ab heatmaps
- `examples/spike_combined.py` has body-in-environment rendering
- The Plotly approach was validated in Phase -1 with 23k triangles

## Key decisions for Phase 5

1. **DiffeRT first, Sionna optional.** DiffeRT has fewer dependencies and works on Windows.
2. **Plotly for interactive, matplotlib for static.** No heavy 3D engine needed.
3. **Integration is a constructor, not a wrapper.** `from_differt()` returns PropagationPaths, not a DiffeRT wrapper object.
4. **Examples are runnable scripts, not notebooks.** Each example produces a visible output (plot, print, HTML file).

## Validation targets

- DiffeRT paths through AEGIS Level 2 should match DiffeRT's own power computation within a few percent
- Coherent Level 7 with DiffeRT paths should show hotspot formation for focused beams
- ECBF (Level 8) should visibly reduce hotspot intensity vs MRT
- Heatmap rendering should handle 24k triangle meshes interactively
