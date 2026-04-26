# Sim4Life-side surface-APD extraction: API recipes

**Status (2026-04-26):** Path A is now the production path. `goliat/extraction/sapd_extractor.py`
is patched to dump `<results_dir>/skin_apd.npz` when the config flag
`extraction.sapd_field` is true; AEGIS-side `h5_surface_apd.load_skin_apd_npz()`
consumes it. Path C (manual h5 Poynting) is kept only as a `_compat` fallback
for retroactive analysis of older runs that lack the npz dump — see deprecation
note below. Path B (SurfaceFieldFluxEvaluator) is no longer needed but documented
for reference in case Path A's APD definition turns out to be inappropriate
for some downstream comparison.

Originally three paths looked viable; ranked by cost and confidence:

## What the static API docs do tell us

S4L Python API v8.2 (`PythonAPIReference_8_2.zip`) and goliat's own snippets:

- `GenericSAPDEvaluator` properties:
  - `AveragingArea` (m²), `Threshold` (m, surface discretization),
    `AveragingMethod` ∈ {Planar, NonPlanar},
    `NonPlanarAveragingGeometry` ∈ {Sphere, Cube},
    `NormalsOrientation` ∈ {Automatic, Keep, Inverse}.
  - `AveragedQuantity` ∈ {Flux, NormOfVector, NormOfComplexVector}
    — pick **Flux** for the absorbed component (`S · n̂`).
  - `SetAPD` (bool) — "Value of: Absorbed Power Density". Toggling this
    almost certainly changes which output ports are exposed.
- `GenericSAPDEvaluator.Outputs` is a `CollectionOfOutputPorts`. Goliat
  reads `Outputs["Spatial-Averaged Power Density Report"]` for the peak.
  Other ports exist but the static docs don't list their names — they're
  registered at C++ algorithm-construction time.
- The general field-extraction pattern, confirmed by a ZMT forum acoustic
  example:
  ```python
  port = algo.Outputs["<name>"]
  port.Update()
  data = port.Data       # FieldData / ComplexFloatFieldData / FloatFieldData
  arr  = data.Field(0)   # numpy.ndarray for snapshot 0
  grid = data.Grid       # XPostProcessor grid; gives vertices / connectivity
  ```
- For the v6+ PD algorithm: "EM field data are first interpolated onto
  the discretized evaluation surface before surface averages are
  computed, in compliance with IEC/IEEE 63195." So the discretized
  surface (with per-triangle field values) exists internally; the
  question is whether a public output port exposes it.

The web (ZMT forum, GOLIAT docs, dyollb/s4l-scripts, sim4life.swiss
release notes) has no recorded example of pulling a per-triangle SAPD
field — every snippet in circulation reads only the "Spatial-Averaged
Power Density Report".

## Path A — `GenericSAPDEvaluator.Outputs["APD(x,y,z,f0)"]` ✅ PRODUCTION

The port name is `"APD(x,y,z,f0)"` when `SetAPD = True`, parallel to the
Poynting port `"S(x,y,z,f0)"` on the field sensor. Confirmed end-to-end
via the sphere test (V=16538, T=33072, lit fraction 0.607, corr(μ, APD) =
+0.9960). Wired in production at `goliat/extraction/sapd_extractor.py:_dump_sapd_field`,
gated by the new `extraction.sapd_field` config flag.

### What we know about the data

  - **Type**: `FloatFieldData`. Real-valued, scalar per node (no
    components). Single snapshot at f0.
  - **ValueLocation**: `kNode` (per-vertex), so `data.Field(0)` returns a
    `(V,)` numpy array. The AEGIS-side reader averages 3 vertex values to
    a triangle centroid before comparing against AEGIS Sab (per-triangle).
  - **Grid**: `SurfaceGrid` with vertices accessible via
    `data.Grid.GetVtkUnstructuredGrid()` → vtk_to_numpy on the points and
    cell-array. ~100x faster than iterating `GetPoint(i)` /
    `GetCellPoints(i)` in pure Python for a 16k-vertex sphere.
  - **Magnitude**: in the sphere test, peak APD = 2.16 × Sinc — strictly
    above the inward-Poynting bound of 1 × Sinc. This rules out
    "S4L's APD = inward S · n̂ at the surface". Most likely the IEC/IEEE
    63195 depth-integrated definition (volumetric absorbed power density,
    averaging includes a small skin-depth thickness with possible
    standing-wave amplification at the lit face). The
    `apd_peak_over_sinc` field returned by `load_skin_apd_npz()` tracks
    this for regression detection.

### Original confirmation (Robin's GUI "To Python" export)

```python
generic_sapd_evaluator.SetAPD = True
generic_sapd_evaluator.UpdateAttributes()
# After Update(), the per-triangle absorbed power density field lives at:
port = generic_sapd_evaluator.Outputs["APD(x,y,z,f0)"]
```

Without `SetAPD = True` this port doesn't exist — the evaluator falls
back to the spatial-average report only. The naming convention `<X>(x,y,z,f0)`
indicates a complex-valued frequency-domain field at frequency f0, on a
surface grid.

Bonus parameter from the GUI export: `model_to_grid_filter.MaximumEdgeLength`
controls the surface discretization on the `ModelToGridFilter` side
(in metres). Goliat currently only sets `sapd_evaluator.Threshold` (on
the evaluator), which controls the same thing from the other end of the
pipeline — explicit `MaximumEdgeLength` gives finer control over per-
triangle resolution and is what we want for a high-quality NRMSE surface
comparison.

Data extraction follows the documented `FieldData` API:

```python
port.Update()
data = port.Data           # FieldData / ComplexFloatFieldData
arr  = data.Field(0)       # numpy.ndarray for snapshot 0
grid = data.Grid           # surface grid → vertices + connectivity
```

The remaining open question (one quick `dir()` away) is what the Grid
type exposes for triangulation extraction — see the probe snippet
below. The general `FieldData.Field(snapshot_index)` → numpy array
pattern is confirmed by the ZMT forum acoustic example; the
`port.Update()` step before reading is critical.

## Path B — `SurfaceFieldFluxEvaluator` directly on Poynting + skin grid

Skips the SAPD evaluator entirely. From the API docs:

> `s4l_v1.analysis.core.SurfaceFieldFluxEvaluator`: Algorithm which
> computes flux of a vector FieldData (input 0), whose grid is a surface

This is exactly what we want for per-triangle inward Poynting flux. No
spatial averaging — pure  S · n̂  per element, which is the raw absorbed
power density we'd then either dump or feed into our own averaging
operator (matching whatever ICNIRP/IEC averaging window we want).

Confidence: high that this gives per-triangle flux as a `FieldData`,
because the analogous `SurfaceFieldFluxEvaluator` for SAR (used on closed
volumes) is documented to return numpy-pullable `FieldData`. The catch:
the Poynting vector `S(x,y,z,f0)` is on the volume Yee grid, while the
skin entity is a triangulated surface. The evaluator handles the
volume→surface interpolation under the hood (this is the IEC/IEEE 63195
"interpolate first, then average" workflow).

```python
# Build the surface (same as for GenericSAPDEvaluator)
m2g = s4l_v1.analysis.core.ModelToGridFilter(inputs=[])
m2g.Entity = skin_entity
m2g.UpdateAttributes()
document.AllAlgorithms.Add(m2g)

# Pull the Poynting vector from the overall-field sensor
poynting = em_sensor_extractor.Outputs["S(x,y,z,f0)"]

# Surface flux: inward (NormalsOrientation = Inverse so the normal
# points INTO the body, hence flux > 0 = absorption)
flux = s4l_v1.analysis.core.SurfaceFieldFluxEvaluator(
    inputs=[poynting, m2g.Outputs["Surface"]]
)
# (NormalsOrientation may not exist on this class; falling back to a
# postprocessing sign flip is safe.)
flux.UpdateAttributes()
document.AllAlgorithms.Add(flux)
flux.Update()

# Extract — the right port name needs the same discovery pass; common
# candidates for a flux evaluator are "Flux", "Surface Flux", or just
# the input quantity name.
for port in flux.Outputs:
    if hasattr(port.Data, "Field"):
        sapd_per_triangle = port.Data.Field(0)
        grid = port.Data.Grid
        break
```

This is my top recommendation: cleanest physics (no averaging surprise),
cleanest data flow, and the SurfaceFieldFluxEvaluator is exactly what
its name suggests.

## Path C — manual h5 Poynting fallback (`h5_surface_apd.load_surface_apd`) ⚠️ deprecated

Read complex E, H from `_Output.h5` ourselves, form S = ½ Re(E × H*),
interpolate at triangle centroids, take −S · n̂.

**Deprecated for production** — superseded by Path A. Keep only as a
`_compat` fallback for retroactive analysis of campaigns that lack the
goliat-side `skin_apd.npz` dump. The function `h5_surface_apd.load_surface_apd()`
remains in the codebase for that purpose (the synthetic plane-wave self-test
still passes: 0.04 % per-triangle, 0.55 % integrated).

Why deprecated:
- Re-implements what Sim4Life already does internally, modulo
  interpolation choices.
- Our triangle mesh ≠ goliat's `ModelToGridFilter` discretisation, so
  we're doing nearest-neighbour-style sampling on a coarser grid; the
  result has its own systematic vs. what Sim4Life computes.
- The `_Output.h5` files are large (often hundreds of MB per sim) and
  must be retained and shipped from the TD VM to wherever AEGIS runs.
- Path A returns the IEC/IEEE 63195-compliant absorbed power density
  Sim4Life is designed to report; Path C returns raw inward Poynting flux,
  which has a different magnitude (factor ~2 on the sphere test) and
  won't match goliat's published peak SAPD numbers.

## Production wiring (Path A, current)

1. **Goliat config flag** `extraction.sapd_field: bool = false` — added to
   `goliat/config/defaults/base_config.json` and the user-facing
   `configs/base_config.json`. Set to `true` in any campaign config that
   wants per-vertex APD dumps. Requires `extraction.sapd: true` (the
   field dump piggybacks on the existing pipeline).

2. **Goliat-side dump** at `goliat/extraction/sapd_extractor.py:_dump_sapd_field`.
   Runs inside `_run_extraction_pipeline` after the existing peak-SAPD
   extraction. Sets `sapd_evaluator.SetAPD = True` (during evaluator
   construction so `UpdateAttributes()` registers the extra port), reads
   `Outputs["APD(x,y,z,f0)"]`, extracts vertices + faces via the
   `vtk_to_numpy` fast path, writes `<results_dir>/skin_apd.npz`. Robust
   to failure: wrapped in try/except, logs a warning if the dump fails,
   does not fail the rest of the campaign extraction.

3. **AEGIS-side reader** at `aegis/validation/scripts/h5_surface_apd.load_skin_apd_npz`.
   Handles both kNode (per-vertex) and kCell (per-face) layouts, averages
   to face centroids if needed, kdtree-resamples to the AEGIS body mesh.
   Returns the comparison-ready `sapd` array plus diagnostics including
   `apd_peak_over_sinc` for magnitude regression detection.

4. **Validation harness** at `aegis/validation/scripts/surface_apd_compare.py`.
   Already accepts a per-triangle array regardless of source — no changes
   needed.

## Open question (low priority, future investigation)

`AveragedQuantity = Flux` with `NormalsOrientation = Inverse` and
`AveragingArea` = small (e.g. `1e-9 m²` ≈ "no spatial averaging") *might*
turn `GenericSAPDEvaluator` into an effective per-triangle Poynting flux
evaluator. If we ever need raw S · n̂ (rather than IEC/IEEE 63195 APD),
this would be cheaper than Path C. Not blocking for Tier 1.
