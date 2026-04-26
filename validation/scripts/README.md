# Validation scripts

Reproduces the Tier 0 analysis (`tier0_findings.md`) and prepares the Tier 1
surface-APD pipeline. No FDTD runs are required to reproduce Tier 0; the
goliat campaign data lives in `goliat/results/far_field.zip`.

## Setup

```bash
# from repo root, with the AEGIS venv active
pip install pandas pyarrow trimesh h5py miepython
# (h5py + miepython are new for Tier 0.5)
```

## Run order

```bash
cd aegis/validation/scripts

# 1. Tier 0 — analysis only, no FDTD
python preflight_check.py    # ~5 s: 8 invariants, abort on any failure
python run_tier0.py          # ~3 min: extracts zip, builds geometry, runs AEGIS
python plot_tier0.py         # ~30 s: regenerates four figs in aegis/validation/

# 2. Tier 0.5 — synthetic-data tests of the harness, no FDTD
python h5_surface_apd.py     # synthetic plane-wave self-test (sphere, ~3 s)
python surface_apd_compare.py    # metric self-test
python sphere_calibration.py     # builds sphere phantom + Mie reference
python sphere_calibration.py --self-test    # Mie sanity check vs miepython
```

The geometry cache lives at
`aegis/validation/data/geometry_cache/geometry_<md5>.npz` (2H, η(r), per-
direction visibility) and is keyed by the STL hash. Re-running after any
of these reuses the cache.

## Files

### Tier 0 (existing)

- `geometry.py` — pure functions: `compute_curvature_2H`,
  `compute_visibility`, `goliat_basis`, `q_field`, `cache_geometry`.
  Imported by the rest.
- `run_tier0.py` — drives AEGIS at L3 / L4 / L6 / L_all (± occlusion) on
  the goliat zip, plus the Cauchy direction-averaged prediction. Writes
  `tier0_<phantom>.parquet`.
- `plot_tier0.py` — regenerates `fig_kernels_vs_fdtd.png`,
  `fig_polarisation.png`, `fig_geometry_maps.png`,
  `fig_fdtd_bookkeeping.png` from the parquet.

### Tier 0.5 (new)

- `preflight_check.py` — eight runtime invariants. Run before each new
  tier launches and after any change to `geometry.py` or AEGIS kernels.
  Already caught one bug (z_neg pole basis) and corrected the STL/voxel
  matching story.
- `h5_surface_apd.py` — extracts per-triangle surface APD. Two paths:
  `load_skin_apd_npz()` consumes a goliat-side per-vertex SAPD dump
  (production; gated by `extraction.sapd_field` in goliat). Returns
  diagnostics including `apd_peak_over_sinc` (~2.16 on the sphere test —
  Sim4Life's APD is the IEC/IEEE 63195 depth-integrated definition, not
  raw inward Poynting flux). `load_surface_apd()` is the deprecated
  fallback for retroactive analysis of pre-`sapd_field` campaigns; it
  reads `_Output.h5` and forms the Poynting vector ourselves. Fallback
  synthetic test: 0.04 % per-triangle, 0.55 % integrated.
- `discover_sapd_outputs.py` — S4L-side helper used in the sphere probe
  and for retroactive analysis of saved projects. `dump_outputs_report()`
  enumerates the output ports of any algorithm; `dump_per_triangle_apd()`
  toggles `SetAPD = True`, pulls `Outputs["APD(x,y,z,f0)"]`, and writes
  the same `skin_apd.npz` schema the goliat-side patch produces. Uses
  `vtk_to_numpy` on `data.Grid.GetVtkUnstructuredGrid()` for the mesh
  extraction (~100x faster than per-vertex iteration). Read alongside
  `s4l_surface_apd_recipes.md`.
- `s4l_surface_apd_recipes.md` — written investigation of the three viable
  paths to per-triangle SAPD via the Sim4Life API. Includes the
  discovery-snippet recipe, the `SurfaceFieldFluxEvaluator` alternative,
  and what we know about port names from the v8.2 docs and ZMT forum.
- `surface_apd_compare.py` — area-weighted NRMSE, R², slope, raw and
  4-cm² peak ratios, integrated ratio. Plus `paint_error()` for a
  3D-painted phantom mesh and `scatter_plot()` for log-log diagnostics.
- `sphere_calibration.py` — builds `sphere_skin_30cm.stl`,
  `cross_section_pattern.npz`, and `mie_reference.json` for the (optional)
  goliat-vs-Mie sphere validation. Outputs land in
  `aegis/validation/data/sphere_phantom/`. Use `--self-test` for the Mie
  sanity check.

## Conventions baked in

- Goliat plane wave: `(theta_deg, phi_deg)` is the *propagation* direction
  (verified from `goliat/docs/reference/useful_s4l_snippets.md:731` and
  asserted in `preflight_check.py`). `Psi=0` → E along `ê_θ`, `Psi=90` →
  E along `ê_φ`.
- Renormalisation: × 753.46 (= 2η₀; the harness uses 754 to one decimal,
  off by 0.072 % from the exact value) to convert goliat's E=1 V/m output
  to a reference Sinc = 1 W/m². Applied to FDTD only; AEGIS is driven
  with `power=1.0` directly.
- Curvature: cotangent Laplacian on the watertight (vertex-merged) STL,
  sign-flipped so convex regions have 2H > 0, clipped to [-50, 200] /m.
  AEGIS's L5/L6 take `max(H, 0)` internally.
- Visibility: binary BVH ray-test from triangle centroid (offset by ε·n
  to avoid self-intersection) toward `-k̂`. Front-facing test applied
  separately so back-faces always get O = 0.
- Surface APD sample point: triangle centroid offset 0.5 mm into the body
  along `-n̂` (so we read in-tissue Poynting flux, not the air-side limit
  where the field is the full plane wave).
- STL ↔ voxel-phantom equivalence: enforced by
  `preflight_check.check_stl_vs_goliat_phantom_bbox()` reading the
  campaign-config snapshot's `bbox_padding_mm`. Drift of the on-disk
  config from the snapshot is what tripped Tier 0's STL/voxel mismatch
  red herring.

## What's NOT in here

- Goliat-side FDTD runs (Tier 1+): see `fdtd_validation_plan.md`.
- Frequency-smoothed visibility kernel (the principled fix for binary O
  over-correcting at long λ). Worth implementing in AEGIS proper.
- A `BodyMesh.compute_curvature()` helper. Belongs in
  `aegis/src/aegis/geometry/mesh.py`, not here.
- A `compute_q_field()` helper. Same — should live alongside `BodyMesh`.
