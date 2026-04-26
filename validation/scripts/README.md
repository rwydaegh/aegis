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
  the same `skin_apd.npz` schema the goliat-side patch produces. Mesh
  extraction iterates `grid.GetPoint(i)` / `grid.GetCellPoints(i)` since
  S4L's `GetVtkUnstructuredGrid()` returns a raw C++ pointer Boost.Python
  cannot unwrap (see Tooling lessons below). Read alongside
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

## Tooling lessons learned (2026-04-26)

Things that surprised me during the goliat→AEGIS plumbing pass.
Future-me / agent: read this before re-doing what I already debugged.

### Sim4Life Python API

- `data.Grid.GetVtkUnstructuredGrid()` returns a raw `vtkUnstructuredGrid*`
  C++ pointer that Boost.Python's by-value converter cannot unwrap. The
  attempted "fast path" of `vtk_to_numpy` on points + cell array fails
  at runtime with: `No to_python (by-value) converter found for C++ type:
  class vtkUnstructuredGrid * __ptr64`. **Workaround**: iterate the
  documented `grid.GetPoint(i)` / `grid.GetCellPoints(i)` accessors with
  a Python list comprehension. ~few seconds for a 50k-vertex thelonious
  skin patch — slow enough to be visible in logs but tolerable.
- `GenericSAPDEvaluator.SetAPD = True` *swaps the report port out of the
  Outputs collection*, rather than adding the field port alongside.
  After `UpdateAttributes()`, `Outputs["Spatial-Averaged Power Density
  Report"]` returns `None` and `Outputs` has 3 anonymous ports
  (`Name == ""`). **Fix**: build two parallel evaluators sharing the same
  `ModelToGridFilter` — one without `SetAPD` for the report, one with
  for the field. Cost is ~10–15 s per scenario; both metrics from one
  run, both apples-to-apples on the same surface mesh discretisation.
- `port.Update()` is required before reading `port.Data`. Skip it and
  `Field(0)` raises something like "FieldData has no snapshots".
- The renorm factor `753.46 = 2 η₀` converts S4L's E=1 V/m drive output
  to Sinc = 1 W/m² reference. Apply it on the goliat side when writing
  the npz, *not* on the AEGIS side, so consumers see standardised units.

### Hardware / SSH / VPN (TensorDock VM)

- The Tensordock OpenSSH-server hands SSH sessions an *elevated* token
  by default (`net session` returns success). UAC is **not** the wall.
  This means `my_connect_vpn.bat`-style flows can be replicated headless
  over SSH; you don't need RDP for license / VPN bring-up.
- VPN reconnect from SSH after a VM reboot:
  ```bash
  ssh goliat 'cd "/c/Users/$USERNAME/Desktop/certs/" && \
      nohup "/c/Program Files/OpenVPN/bin/openvpn.exe" \
        --config Intec-iGent.ovpn --auth-user-pass openvpn_auth.txt \
        > /tmp/openvpn.log 2>&1 &'
  # Wait ~10 s, then verify with `ipconfig` for TAP-Windows6 IP.
  ```
  See `goliat/cloud_setup/ssh/README.md` for the full bring-up sequence.
- Without the VPN, `import s4l_v1` hangs >60 s waiting on the license
  server. Symptom: goliat run starts but produces zero log output.
  First diagnostic to try: `ipconfig | grep "OpenVPN" -A 4` on the VM.

### Linux ↔ goliat git access

- Linux `~/.gitconfig` uses a **per-host helper** (`!gh auth git-credential`)
  for `github.com`, which queries the `gh` CLI's stored credentials.
  `gh` *prefers the `GITHUB_TOKEN` env var* over its on-disk credential
  store, so updating `~/.git-credentials` alone is not enough — `gh auth
  status` will still report the env-var token as active.
- **Workaround**: `env -u GITHUB_TOKEN git <cmd>` for any push/pull/fetch
  that needs a different token (e.g. when the env-var token only has
  scope for one repo and you need access to another). The fine-grained
  PAT lives at `goliat/cloud_setup/ssh/goliat_aegis_PAT.txt`
  (gitignored) and is loaded via `gh auth login --with-token`.

### File transfer between Linux and the Windows VM

- `scp /local/file goliat:/c/Users/.../path` *fails*: scp uses sftp on
  the remote, which doesn't accept the MSYS-style `/c/...` path.
  **Workaround**: pipe through SSH:
  ```bash
  cat /local/file | ssh goliat 'cat > path/relative/to/$HOME/file'
  ```
  Goliat repo files transfer fine via this method (path is relative to
  `$HOME = /c/Users/user/`).
- `goliat/...` paths over SSH default to `$HOME/goliat/` (i.e. the
  cloned repo). No need for absolute Windows paths.
