# FDTD validation of AEGIS geometric dosimetry

Validating AEGIS (closed-form surface dosimetry) against GOLIAT (Sim4Life FDTD) on matched plane-wave scenarios. This is a concrete plan to instantiate the "Wout comparison" sketched in `aegis/spinoff/older_but_less_important_kinda/GOLIAT_AEGIS_synergies.md` (synergy #2).

## What we are validating

The geometric absorption law (`summary_paper.tex` eq. 1.1):

```
S_ab(r) ≈ S_inc · T_0 · ReLU[n̂(r) · (-k̂)]
```

The paper makes three quantitative claims worth checking against an independent solver:

1. **Local Sab map.** Pointwise on the skin surface, accurate within the Fresnel error (2–6 % in 10–60 GHz, larger at the edges). Optimal near 40 GHz where `T_avg ≈ T_0` is exact.
2. **Total absorbed power (eq. 3.4 / 6.4).** `<P_abs> = S_inc · T̄ · A_ab / 4` is exact at any frequency above ~100 MHz when `T̄` (flux-averaged transmission) is used in place of `T_0`. The directionally-averaged Mie test currently asserts ~1 % consistency; the FDTD test should match within the same ballpark.
3. **Polarisation correction is small.** `D_B ≤ 16 %` on Thelonious worst case (paper §6.1), suppressed below 2.5 % for ≥ 20 multipath paths. Single plane waves are the worst case; we should see this 16 % envelope.

## Why FDTD as the third reference

We already have two reference points: the Mie regression test in `tests/test_mie.py` (exact for spheres at 28 GHz, asserts ~0.5 % accuracy on `R = T_0 / Q_GO`), and the analytical sub-6 GHz `T̄` table (paper Table 6.1). FDTD on an anatomical phantom is the third, qualitatively different point: realistic body geometry, full multi-tissue voxel model, and an entirely different numerical scheme. If AEGIS lands inside the FDTD's own uncertainty (~10 % from tissue properties, plus discretisation), the framework is in good shape.

## The frequency overlap window

Two regimes:

- **AEGIS is most accurate** in 10–60 GHz (paper §1.2). Below 10 GHz the surface map loses physical meaning because skin depth approaches the surface layer thickness, but the direction-averaged total `P_abs` stays exact via `T̄` (paper §6).
- **FDTD is feasible on a single 24 GB GPU** up to ~10–11 GHz on Thelonious full body. Beyond that we need bbox reduction, multi-GPU, or a smaller anatomical region. (Mesh cell counts measured below.)

The clean overlap, where both sides are simultaneously in their comfort zone, is **7–11 GHz on Thelonious**. That is where the headline numbers should come from. Lower frequencies validate the `T̄` direction-average formula; higher frequencies test the geometric sweet spot but cost more.

## What GOLIAT actually emits (the comparison surface)

From `goliat/extraction/`:

| Goliat field | File | Maps to AEGIS |
|---|---|---|
| `whole_body_sar` (W/kg, mass-averaged across all tissues) | `sar_results.json` | `result.sar_wb` |
| `peak_sar_10g_W_kg` (psSAR10g, IEEE/IEC 62704-1) | `sar_results.json` | not native to AEGIS — derived via `result.peak_sab_averaged` × thickness ratio (rough) |
| `input_power_W` (theoretical from incident E field over phantom cross-section) | `sar_results.json` | `S_inc · A_perp(k̂)` |
| Power balance: `Pin`, `DielLoss`, `RadPower` | `sar_results.json` (when `extraction.power_balance: true`) | `result.p_abs` ↔ `DielLoss` |
| `peak_sapd_W_m2`, `peak_sapd_location_m` (4 cm² avg, 10 mm depth threshold) | `sapd_results.json` (when `extraction.sapd: true`) | `result.peak_sab_averaged` |
| Sliced E/H field volume around peak | `sliced_output_<f>MHz.h5` | needs custom extraction → sample at AEGIS triangle centroids for full surface map |

Critical unit detail: GOLIAT excites with **E = 1 V/m** plane waves, so the natural `S_inc` is `1/(2η₀) ≈ 1.327·10⁻³ W/m²`. The post-processing scripts (`scripts/extract_apd_table_data.py`) multiply by 754 ≈ 2η₀ to renormalise outputs to "per 1 W/m² incident". AEGIS uses `S_inc` directly in W/m². We must thread the same convention end-to-end (recommend: drive AEGIS with `power = 1.0` and renormalise Goliat outputs by 754, document explicitly).

GOLIAT does **not** dump a full surface SAPD map by default — only the peak. For a per-triangle spatial comparison we have to read `sliced_output_*.h5` and project the field onto the phantom skin mesh ourselves. That's a stretch goal for tier 2+, not the smoke test.

## Mesh-cell budget (measured, not estimated)

Bbox + 50 mm padding, GOLIAT per-frequency grid, full body and half-body (symmetric reduction):

| Phantom | f (MHz) | grid (mm) | full MCells | half (sym) MCells | feasibility on 1×3090 (24 GB) |
|---|---|---|---|---|---|
| thelonious | 700 | 2.5 | 12 | 6 | trivial — sub-minute |
| thelonious | 3500 | 1.0 | 191 | 96 | comfortable — ~30 s/sim |
| thelonious | 7000 | 0.6 | 884 | 442 | comfortable — ~2 min/sim |
| thelonious | 11000 | 0.5 | 1527 | 764 | tight, fits — ~3 min/sim |
| thelonious | 15000 | 0.4 | 2980 | 1490 | needs ≥ 48 GB or height reduction |
| thelonious | 28000 | ~0.22 | 17900 | 8950 | multi-GPU only |
| duke | 11000 | 0.5 | 3767 | 1883 | needs ≥ 48 GB |
| duke | 7000 | 0.6 | 2181 | 1091 | tight on 24 GB |

The 28 GHz full-body row is the "intractable" claim from the paper, made concrete: ~18 BCells for Thelonious, the smallest phantom — even the 6-year-old. Duke at 28 GHz is ~44 BCells, an order of magnitude beyond a 6×H100 cluster. This is exactly the regime AEGIS exists for.

The runtime estimates assume ~6500 MCells/s (RTX 3090 / 4090 tier from `goliat/docs/GPU_speeds/fdtd_measurements.md`).

## Tiered validation plan

### Tier 0 — analyse existing sub-6 GHz data (no new FDTD runs) ✅ done

The 2026 PMB campaign ran 12 directions × 2 polarisations × 9 frequencies × 4 phantoms environmentally between 450 MHz and 5800 MHz. We re-use it directly. AEGIS counterpart runs in milliseconds per scenario.

Full results in [tier0_findings.md](tier0_findings.md). Headline:

| f (GHz) | L3 | L6 (real H) | L_all (all on) | L_all × O | Cauchy + T̄ |
|---|---|---|---|---|---|
| 0.45 | 0.44 | 0.97 | 0.97 | 0.71 | 0.41 |
| 0.7  | 0.42 | 0.76 | 0.76 | 0.57 | 0.39 |
| 1.45 | 0.56 | 0.80 | 0.80 | 0.61 | 0.52 |
| 3.5  | 0.79 | 0.94 | 0.94 | 0.72 | 0.73 |
| 5.2  | 1.04 | 1.17 | 1.17 | 0.90 | 0.96 |
| 5.8  | 1.09 | 1.22 | 1.22 | 0.94 | **1.012** |

(`r` ≡ `<P_abs^AEGIS> / <P_abs^FDTD>`, direction-averaged over 12 dirs × 2 pols. `L_all` = mode='spatial' with fresnel + polarisation + curvature + diffraction all on, real per-triangle 2H from cotangent Laplacian, real q(r) from incident E direction.)

Three load-bearing findings from Tier 0:

1. **Cauchy direction-averaged formula matches FDTD to 1.2 % at 5.8 GHz**, with `A_ab = 0.681 m²` from AEGIS's own ambient occlusion (paper says η = 0.87 for Thelonious, we got 0.865) and T̄ from AEGIS's own Fresnel kernel. This is the paper's main quantitative claim made true on real anatomical-phantom data.

2. **L_all ≡ L6 at the direction-averaged level.** Polarisation correction averages to zero over the (θ, φ) pair — paper §6.1 prediction confirmed. Polarisation only tightens per-direction variance (about −22 % at 5.8 GHz), not the mean. So "going all out" with every spatial-mode flag does not improve the headline beyond `L6 + real H`.

3. **Below ~5 GHz, FDTD direction-averaged P_abs exceeds the Cauchy prediction by 2–3×.** This is body-scale Mie/resonance, which the paper's §6.2 caveat acknowledges qualitatively but doesn't quantify. Concrete trace of the breakdown across nine frequencies. The "exact above 100 MHz" claim is therefore a high-`x` asymptote, not literal.

**FDTD bookkeeping anomaly fully diagnosed.** Goliat's `(DielLoss + RadPower)/Pin` ranges 0.83–3.4× because `Pin` uses the *phantom* bbox area while the TF/SF source generates the plane wave through the *simulation* bbox (phantom + 50 mm padding). FDTD physics conserves energy internally; only the post-processed Pin is wrong. Easy fix on the goliat side. Does not affect any of the absolute-Pabs comparisons above.

### Tier 0.5 — pre-flight, surface-APD pipeline, sphere calibration

Two days max. No anatomical-phantom FDTD runs; the goal is to close the
gaps Tier 0 surfaced before Tier 1 launches. Three sub-tracks, each
self-contained.

**A. Pre-flight script (done, no compute).**
[`scripts/preflight_check.py`](scripts/preflight_check.py) asserts on
eight invariants: direction basis, polarisation basis, q sign convention,
renormalisation constant, IT'IS v5.0 dielectric ranges, curvature sign on
a unit sphere, visibility on a closed mesh, and STL ↔ phantom-voxel
cross-section matching against the campaign-config snapshot (the canonical
truth, not the on-disk `far_field_config.json` which has drifted). Run
this before Tier 1, after any change to `geometry.py` or AEGIS kernels,
and as a CI canary if/when validation moves into a regression suite. It
already caught one bug (z_neg pole basis) and corrected the STL/voxel
mismatch story (they match to 0.96 %).

**B. Surface-APD comparison pipeline (done, tested on synthetic data).**
Goliat's stock `GenericSAPDEvaluator` reports only the *peak* SAPD value
plus its location. The user's preference is integrated NRMSE on the full
skin surface plus a 3-D plot of where the errors live, which needs the
per-triangle field. Three scripts:

- [`scripts/h5_surface_apd.py`](scripts/h5_surface_apd.py) — preferred:
  load a goliat-side per-triangle SAPD dump (`*_skin_apd.npz`); fallback:
  read `_Output.h5`, form the Poynting vector ourselves, sample at
  triangle centroids 0.5 mm into the body. The fallback is unit-tested
  against an analytical free-space plane wave on a sphere: median
  per-triangle error 0.04 %, integrated power matches `Sinc · π R²` to
  0.55 %.
- [`scripts/surface_apd_compare.py`](scripts/surface_apd_compare.py) —
  takes (s_aegis, s_fdtd, areas) and returns NRMSE, area-weighted Pearson
  correlation, R², slope of `aegis ~ slope·fdtd`, raw and 4-cm²-averaged
  peak ratios, and integrated-power ratio. Plus utilities to paint a
  3-D phantom mesh by error ratio and a log-log scatter for visual
  diagnostics. Self-tested against analytical noise/scale cases.
- [`scripts/discover_sapd_outputs.py`](scripts/discover_sapd_outputs.py) +
  [`scripts/s4l_surface_apd_recipes.md`](scripts/s4l_surface_apd_recipes.md) —
  goliat-side helpers. The fallback path C (manual computation from
  `_Output.h5`) re-implements what Sim4Life already does internally and
  introduces our own interpolation noise. The S4L API exposes per-triangle
  SAPD via `GenericSAPDEvaluator.Outputs[<port>].Data.Field(0)` (port name
  set by C++ at runtime, not in the static docs) or by chaining
  `SurfaceFieldFluxEvaluator` directly on the Poynting vector + skin
  surface. Run `discover_sapd_outputs.dump_outputs_report()` once on the TD
  VM to read off the actual port name and capture it for the next campaign;
  then `dump_per_triangle_apd()` writes a portable `*_skin_apd.npz` next to
  `sapd_results.json`. AEGIS-side `h5_surface_apd.load_skin_apd_npz()`
  consumes it.

For Tier 1 to land with full surface metrics, add to the goliat config:
```jsonc
{ "execution_control": { "auto_cleanup_previous_results": [] },
  "extraction": { "sapd_field": true }   // new flag — gates the skin_apd.npz dump
}
```
so `_Output.h5` is retained (the manual fallback) and the goliat-side
SAPD-field dump runs (the preferred path). The recipes doc has the API
details and the discovery snippet.

**C. Sphere-vs-Mie calibration of goliat (done offline, 1 h compute pending).**
[`scripts/sphere_calibration.py`](scripts/sphere_calibration.py) generates
everything goliat needs:

- 30 cm icosphere STL (drop into `goliat/data/phantom_skins/sphere_skin_30cm/`)
- `cross_section_pattern.npz` matching goliat's existing format (so
  `_calculate_phantom_cross_section` works without further patching)
- `mie_reference.json` — exact Q_abs and P_abs/Sinc at 700 MHz, 3.5 GHz,
  11 GHz from `miepython` (the same library AEGIS's own Mie regression
  test depends on). At 700 MHz: Q_abs = 0.863, P_abs/Sinc = 0.0610 W/(W/m²);
  at 3.5 GHz: 0.648, 0.0458; at 11 GHz: 0.590, 0.0417.

Goliat-side recipe (one-time on the TD VM, takes about an hour):

```jsonc
// goliat/configs/sphere_calibration.json
{
  "extends": "far_field_FR3_base.json",
  "phantoms": ["sphere_skin_30cm"],
  "frequencies_mhz": [700, 3500, 11000],
  "extraction": { "sar": true, "power_balance": true, "sapd": false },
  "execution_control": { "auto_cleanup_previous_results": [] },
  "far_field_setup": {
    "type": "environmental",
    "environmental": {
      "incident_directions": ["x_neg"],   // sphere is rotationally symmetric
      "polarizations": ["theta"]
    }
  },
  "simulation_parameters": { "bbox_padding_mm": 20 }
}
```

Pass band: `goliat/Mie ratio` within ±5 % at 11 GHz, ±10 % at 3.5 GHz,
±15 % at 700 MHz (Mie resonance regime — modest goliat-side error there
is acceptable but worth measuring). If the sphere passes, we have a
phantom-independent baseline that lets us interpret any remaining
AEGIS-vs-FDTD divergence on Thelonious as AEGIS error rather than goliat
error. If the sphere fails, debug there before touching the phantom.

**Spheres are not a substitute for phantoms.** A sphere has `η ≡ 1`,
`D_B = 0` exactly, no curvature variation, no anatomy. AEGIS reduces to
`P_abs = S_inc T_0 π R²` for the GO limit — the same closed form
`tests/test_mie.py` already validates against Mie. Sphere calibration
tests *goliat's FDTD setup*, not AEGIS.

### Tier 1 — geometric sweet spot (one day, 1×3090 + bumped TD)

Cleanest test of the geometric absorption law in the band where it's expected to be optimal. **Re-run from scratch** because no environmental FDTD data exists at FR3 — the 2026 PMB campaign used auto_induced (beamforming worst-case) at 7+ GHz, not 12-direction environmental.

- Phantom: Thelonious
- Frequencies: 7, 9, 11 GHz (FR3 ladder from `configs/far_field_FR3_base.json`)
- Directions × polarisations: 6 × 2 = 12 per frequency, 36 sims total
- **Cell budget upgraded to 12 CPW in skin and eye vitreous** (vs the 8–10 CPW the paper used). This means cell sizes 0.39 / 0.30 / 0.25 mm at 7 / 9 / 11 GHz instead of 0.6 / 0.5 / 0.5 mm. Cubic blow-up: ~3.4× more cells than the paper's grid.
- Cell counts: 1500 / 2900 / 6100 MCells half-body. The 11 GHz row needs ≥ 48 GB GPU or aggressive height factor reduction.
- Pragmatic compromise: keep half-body symmetry (defensible per paper §2.8.1 since penetration depth is sub-mm at these freqs), drop CPW target to 12 in skin/eye but keep 10 elsewhere (still better than the paper's 8/10), use bbox padding 30 mm instead of 50 mm.
- Estimated compute: 12 sims × 3 min avg × 3 freqs ≈ 2 hours on 4090-tier; longer on 3090. Plus extraction overhead per sim (~30 s).
- **Convergence check**: re-run one scenario (11 GHz, x_neg, theta-pol) at 8 / 12 / 16 CPW and confirm the answer agrees within 2%. The paper has no such check, and we'd be giving a reviewer something solid to point at.
- Comparisons:
  1. **Per-direction `P_abs`** — both directly per direction and via Cauchy `<P_abs> = S_inc · T̄ · A_ab / 4` for the directional average. This is the headline accuracy claim.
  2. **WBSAR** — derived from `P_abs` and total mass.
  3. **Peak SAPD (4 cm² averaged)** — Goliat `peak_sapd_W_m2` ↔ AEGIS `result.peak_sab_averaged`. Triggered by setting `extraction.sapd: true`.
  4. **Polarisation residual** — for each direction, take the difference `P_abs(theta) − P_abs(phi)`. AEGIS Part II says this magnitude divided by the unpolarised mean should be at most `D_B(k̂) ≤ 16 %` on Thelonious. The biggest residuals should be at lateral illumination (paper §6.1).
  5. **Polarisation conservatism** — paper claim that for vertically polarised illumination the unpolarised AEGIS formula is conservative. Check the sign of the residual.

The scientific output of Tier 1 alone is publishable as a validation paper. It's also the unit at which a regulatory reviewer would expect to see evidence.

### Tier 2 — full surface map comparison (1–2 days, 1×3090)

Gets us the spatial correlation result needed for the monograph figures.

- Same scenarios as Tier 1, but for one frequency and one direction combo (say 11 GHz, x_neg, theta-pol) we
  - Read `sliced_output_*.h5`, extract the SAPD field on the (regularly gridded) sliced volume
  - Sample at AEGIS triangle centroids on the Thelonious mesh
  - Compute pointwise residuals, RMS error, peak ratio
- Optional rotated reference: rerun AEGIS at a few extra directions (`uniform_sphere`) for a directional-spread comparison

This tier requires writing a small `goliat_h5_to_triangles.py` helper. Save it in `aegis/validation/`.

### Tier 3 — stretch (multi-GPU TD machine or cloud)

Demos that justify the framework outside its comfort zone:

- **15 GHz on Thelonious with bbox height-reduction** to head + upper torso. Tests the local Sab law in its theoretical sweet spot (40 GHz is optimal; 15 GHz is closest we can get FDTD to). Needs ≥ 48 GB GPU or a multi-3090 setup.
- **Duke (adult, 1.8 m, 72 kg) at 7 GHz**, full body. The headline number for an adult at sub-mmWave. ~1100 MCells half-body, fits a 4090.
- **Thelonious at 28 GHz on a 30 cm head crop.** Use `phantom_bbox_reduction.height_limit_per_frequency_mm: {28000: 300}`. Cell count drops from 9 BCells to ~570 MCells half-symmetric. Demonstrates AEGIS in its true regulatory target (5G FR2). Even a partial-body match is a strong existence proof.

Tier 3 is also where we'd ask the user to scale the TD fleet — multiple 3090s, an RTX 6000 Ada (48 GB), or H100 spot allocation, depending on which scenario we want.

## Scripts (`aegis/validation/scripts/`)

Tier 0 + Tier 0.5 deliverables. Each is independently runnable and either
self-tests or drives a real comparison.

| Script | Tier | Purpose |
|---|---|---|
| `geometry.py` | 0 | curvature 2H (cotangent Laplacian), visibility (BVH ray-tracing), goliat (k̂, ê_θ, ê_φ) basis, q-field, geometry cache |
| `run_tier0.py` | 0 | drives AEGIS at L3, L4, L6, L_all (± occlusion) on the existing 2026 PMB sub-6 GHz campaign zip, writes parquet |
| `plot_tier0.py` | 0 | regenerates the four figures from the parquet |
| `preflight_check.py` | 0.5 | 8-invariant runtime sanity check; assert before any new tier launches |
| `h5_surface_apd.py` | 0.5 | extract per-triangle surface APD from a goliat `_Output.h5` + skin mesh (synthetic-tested to 0.04 %) |
| `surface_apd_compare.py` | 0.5 | NRMSE / R² / peak-4cm² / integrated ratio between AEGIS Sab and FDTD SAPD on the same mesh + plotting helpers |
| `sphere_calibration.py` | 0.5 | sphere STL + cross-section pattern + Mie reference; drop the outputs into `goliat/data/phantom_skins/sphere_skin_30cm/` |
| `README.md` | — | how to run everything |

Tier 1 will reuse `geometry.py` + `h5_surface_apd.py` + `surface_apd_compare.py`.
New thin wrapper to write for Tier 1:

- `run_tier1.py` — drives `goliat study far_field_aegis_tier1` (or just
  pulls results if the goliat run is launched manually), parses the 36 ×
  `sar_results.json` + `sapd_results.json`, and for each scenario runs
  `h5_surface_apd.load_surface_apd(...)` against the matching `_Output.h5`,
  calls `surface_apd_compare.compare(...)` against the AEGIS L_all kernel
  output on the same mesh, and writes a `tier1_<phantom>.parquet` plus
  per-scenario 3-D error painted figures.

The matched goliat config:

```jsonc
// goliat/configs/far_field_aegis_validation.json
// Tier 1: 12-direction environmental at FR3 with tighter CPW than the paper
{
  "extends": "far_field_FR3_base.json",
  "phantoms": ["thelonious"],
  "frequencies_mhz": [7000, 9000, 11000],
  "extraction": {
    "sar": true, "power_balance": true, "sapd": true, "point_sensors": false
  },
  "far_field_setup": {
    "type": "environmental",
    "environmental": {
      "incident_directions": ["x_pos","x_neg","y_pos","y_neg","z_pos","z_neg"],
      "polarizations": ["theta", "phi"]
    }
  },
  "gridding_parameters": {
    "global_gridding_per_frequency": {"7000": 0.39, "9000": 0.30, "11000": 0.25},
    "phantom_bbox_reduction": {"auto_reduce_bbox": false, "use_symmetry_reduction": true}
  },
  "simulation_parameters": {"bbox_padding_mm": 20, "convergence_level_dB": -30},
  "execution_control": {"auto_cleanup_previous_results": []}   // KEEP _Output.h5
}
```

Two non-obvious bits:

- `bbox_padding_mm: 20` matches the 2026 PMB campaign's actual padding (per
  the run-time config snapshot in `goliat/results/far_field.zip`). Don't
  use 50 (older default) or 0 (the post-campaign value of the on-disk
  `far_field_config.json`); Tier 1 should be apples-to-apples with the
  Tier 0 sub-6 GHz dataset.
- `auto_cleanup_previous_results: []` is what enables the surface-APD
  comparison pipeline (`h5_surface_apd.py`). The current default
  `["output"]` deletes `_Output.h5` after extraction, which is fine for
  peak-only SAPD but costs us the per-triangle map. Tier 1 may produce
  ~50–200 GB of h5 files across 36 sims at FR3 (single-frequency in
  frequency domain); plan for the disk.

## Comparison metrics and tolerances

Updated after Tier 0 — tolerances are now anchored on observed data, not theoretical guarantees alone:

| Metric | AEGIS claim | Observed Tier 0 (sub-6 GHz) | Tier 1 pass band (7–11 GHz) |
|---|---|---|---|
| Direction-avg `<P_abs>` | exact via `T̄` for x → ∞ | 1.012 at 5.8 GHz; falls to 0.39 at 700 MHz | 0.92 – 1.08 (paper sweet spot starts at ~10 GHz) |
| Per-direction `P_abs` | Fresnel error 2–6 % at 10–60 GHz | std 0.16–0.27 across (dir, pol) | 0.80 – 1.20 (allows ±D_B + 5 % tissue) |
| WBSAR | follows `P_abs` exactly | matches Pabs ratio modulo voxel-mass mismatch | same as `<P_abs>` |
| Peak SAPD (4 cm² avg) | local Sab law, Fresnel error | not testable in Tier 0 (only peak in JSON) | 0.80 – 1.20 |
| Polarisation residual `D_B = (P_θ − P_φ) / P_avg` | ≤ 16 % on Thelonious (paper §6.1) | 19.5 % lateral at 5.8 GHz, 7 % frontal, 1.2 % vertical | ≤ 16 % lateral, ≤ 8 % frontal |
| Spatial RMS of Sab vs SAPD on skin (Tier 2) | Fresnel error + diffraction | n/a | < 0.20 |

The "going all out" L_all kernel matches L6 exactly on direction-averaged Pabs (polarisation cancels by symmetry), so Tier 1 should report L_all as the headline kernel and use L_all variance as the polarisation-fidelity metric.

Failure modes worth chasing if a metric fails its band:
- `<P_abs>` low at 7 GHz: Mie/diffraction still active; expect ratio ~0.85 with L_all on Thelonious.
- Lateral `D_B` > 0.16: paper's universal bound is at 28 GHz; residual freq dependence through |ñ| not captured.
- Peak SAPD off-by-x: AEGIS's 4 cm² spatial averaging may differ from goliat's `GenericSAPDEvaluator` numerics.

## Open questions and pre-flight checks

Status after Tier 0.5:

1. ✅ **Plane-wave reference plane.** Verified from
   `goliat/setups/far_field_setup.py:184–222` and
   `goliat/docs/reference/useful_s4l_snippets.md:731`: `(theta_deg, phi_deg)`
   is the wave *propagation* direction (S4L PlaneWaveSourceSettings); `Psi=0`
   is θ-pol along `ê_θ`; `Psi=90` is φ-pol along `ê_φ`. STL frame: z up, head
   at top, face on -y side. Body L-R symmetric. Encoded as runtime
   assertions in `scripts/preflight_check.py`.
2. ✅ **Mass denominator.** `data/phantoms.yaml` says 17.4 kg; the FDTD-side
   voxel mass is implied by `whole_body_sar = DielLoss / mass_voxel`. The
   two agree to ~10 % in Tier 0 ratios.
3. ✅ **Tissue match.** AEGIS uses `TissueModel.from_database("Skin",
   freq_hz=...)` from IT'IS v5.0. Spot-checked against published Cole-Cole
   values (Skin at 5.8 GHz: eps_r 35.1, σ 3.72) by
   `preflight_check.check_tissue_dielectric_v5()`. Goliat uses Sim4Life's
   tissue library, also IT'IS v5.0 in the paper. Confirm they're bit-for-bit
   identical only on Tier 1's first sim by reading the Sim4Life material
   parameters from the verbose log (`Skin (Thelonious_6y_V6): dielectric
   (eps_r=..., sigma_E=..., ...)` line).
4. ✅ **Existing GOLIAT runs at 7–15 GHz.** None usable. The 7000MHz folder
   in the campaign zip is empty; the FR3 (7–15 GHz) campaign was
   *auto_induced only*, not 12-direction environmental. The campaign zip
   also has no `_Output.h5` files because `auto_cleanup_previous_results:
   ["output"]` was on. Tier 1 must re-run from scratch with `[]`.
5. ✅ **STL ↔ goliat voxel phantom.** Match to 0.96 % on cross-section after
   accounting for the campaign config's 20 mm bbox padding. The user's
   "couple mm" intuition stands. Earlier suspicion of a 10–20 % mismatch
   was an artefact of reading the *current* (drifted) `far_field_config.json`
   instead of the campaign-config snapshot.
6. ⏳ **TD machine.** Currently 4 vCPU / 16 GB / 1×3090. Tier 1 at 11 GHz /
   12 CPW = 6.1 GCells full-body, 3.0 GCells half-body — likely needs a
   bump to 8 vCPU / 32 GB and ideally 48 GB VRAM (RTX 6000 Ada) for the
   11 GHz row to land cleanly. Tier 0.5 sphere fits the existing VM.
7. ⏳ **Disk for h5 retention.** Tier 1's 36 sims with `_Output.h5` retained
   produce ~50–200 GB depending on grid. Confirm TD VM has the headroom.

Goliat-side cosmetic fixes (worth landing for paper hygiene; **none affect
the AEGIS comparison**):

8. **Power-balance bookkeeping.** `Pin` uses sim-bbox face area, but the
   TF/SF source actually injects through a TF/SF box that Sim4Life
   auto-retracts 2 cells inward. Recompute Pin from the actual TF/SF face
   area (i.e. `sim_bbox - 2 × grid_size_per_face`) inside
   `power_extractor._calculate_bbox_cross_section`. ~4 lines.
9. **Default `auto_cleanup_previous_results`.** The campaign default
   `["output"]` is right for peak-only SAPD studies, but should be `[]`
   for any run that wants surface-APD comparison downstream. Add a
   warning when SAPD extraction is enabled and `output` is in the cleanup
   list — the user clearly wants the h5.
10. **Drift between far_field_config.json and the campaign snapshot.** The
    on-disk `far_field_config.json` has `bbox_padding_mm: 0` and
    `bbox_padding_mm: None` in `base_config.json`; the actual campaign ran
    at 20 mm. Trail of corrections that lost the lineage. Pin the campaign
    config back to the file so a future re-run reproduces the same data.

## AEGIS code changes from Tier 0

Two patches landed during Tier 0 analysis (both backward-compatible, default=None):

1. **`engine.compute(..., occlusion=ndarray)`** — applies paper eq. 3.1's per-direction `O(r, k̂)` factor to spatial Sab. Works on both legacy `level=` and `mode='spatial'` paths. Patch in `aegis/src/aegis/engine.py`.
2. **No-op for the kernels** — they already handle the math; the change is purely engine-level post-multiplication.

Still missing in AEGIS (deferred to follow-ups, listed roughly in priority order):

1. **`BodyMesh.compute_curvature()` helper.** Without one, L5/L6 silently default to H=0 and become L3 — i.e. the curvature/diffraction kernels effectively don't run unless the user knows to pass an array. Cotangent Laplacian on the watertight (vertex-merged) STL, ~30 lines. The implementation in `validation/scripts/geometry.py` is good enough to upstream once tested on duke/ella/eartha.
2. **Frequency-smoothed visibility kernel.** Binary `O(r, k̂)` over-corrects at long λ. Right kernel: `O_smoothed(r, k̂) = ½[1 + erf(d_shadow(r, k̂) / √(λ R_local(r)))]` where `d_shadow` is the signed distance to the nearest binary-occlusion boundary along `k̂`. Same shape as the GELU σ. Would close the over-correction at low frequency without breaking the high-frequency limit.
3. **A `compute_q_field()` helper** taking (normals, k_hat, e_E) and returning the per-triangle TM excess. Currently in `validation/scripts/geometry.py`; ~20 lines to upstream.

## Out of scope (deliberately)

- Near-field (phone-on-cheek) validation. AEGIS has a near-field extension (eq. 5.4) but we should validate plane-wave first; near-field adds another axis of disagreement (radiation pattern, distance) that muddles the geometric-vs-FDTD signal.
- Coherent MIMO / Part III of the paper. AEGIS coherent kernel hits levels 7–8, but GOLIAT does not currently provide a coherent multi-source FDTD. Synergy #3 in the spinoff doc covers that and is its own project.
- Ball / sphere validation. Already covered by the Mie regression test (`tests/test_mie.py`).

## Status and next runs

- **Tier 0 done** (data analysis only, no FDTD runs). Headline: Cauchy
  matches FDTD to 1.2 % at 5.8 GHz on Thelonious. Bookkeeping anomaly
  refined to TF/SF auto-shift + RadPower-bypass mechanism (was misdiagnosed
  as 50 mm padding initially).
- **Tier 0.5 done offline** (all the harness work that didn't need an FDTD
  run): pre-flight check script, surface-APD extraction pipeline tested on
  synthetic plane wave to 0.04 % accuracy, AEGIS-vs-FDTD comparison metric
  library, sphere phantom + Mie reference generator. Open: actually running
  the sphere-vs-Mie validation on the TD VM (~1 h, no machine bump needed).
- **Tier 1 next**: re-run 7/9/11 GHz environmental on Thelonious with 12
  CPW, 12 directions × 2 pols, full extraction (SAR + power balance + SAPD
  peak + retained `_Output.h5`). Total ~2–4 h compute on 4090-tier; longer
  on 3090 and may trip OOM at 11 GHz / 12 CPW. Bumping the TD machine to 8
  vCPU / 32 GB and a 4090 or RTX 6000 Ada (48 GB VRAM) would make Tier 1
  land cleanly. Tier 1's h5 files feed directly into the
  `surface_apd_compare.py` pipeline shipped in Tier 0.5.

## Recommended first runs (concrete configs)

**Tier 0.5 sphere (next)**: a new goliat config to drop into `configs/`:

```jsonc
// goliat/configs/sphere_calibration.json
{
  "extends": "far_field_FR3_base.json",
  "phantoms": ["sphere_skin_30cm"],   // needs new phantom registration
  "frequencies_mhz": [700, 3500, 11000],
  "extraction": {"sar": true, "power_balance": true, "sapd": false, "point_sensors": false},
  "far_field_setup": {
    "type": "environmental",
    "environmental": {
      "incident_directions": ["x_neg"],
      "polarizations": ["theta"]
    }
  }
}
```

Adding the sphere phantom is the biggest piece of work here — needs a Sim4Life-side homogeneous skin-property sphere CAD entity and a `phantoms.yaml`-style registration in goliat. Do this once over RDP on the TD VM, save the model, reuse it.

**Tier 1 (after Tier 0.5 passes)**: same template as the FR3 base config but with 12-direction environmental and tight CPW.

```jsonc
// goliat/configs/far_field_aegis_tier1.json
{
  "extends": "far_field_FR3_base.json",
  "phantoms": ["thelonious"],
  "frequencies_mhz": [7000, 9000, 11000],
  "extraction": {"sar": true, "power_balance": true, "sapd": true, "point_sensors": false},
  "far_field_setup": {
    "type": "environmental",
    "environmental": {
      "incident_directions": ["x_pos","x_neg","y_pos","y_neg","z_pos","z_neg"],
      "polarizations": ["theta", "phi"]
    }
  },
  "gridding_parameters": {
    "global_gridding_per_frequency": {
      "7000": 0.39, "9000": 0.30, "11000": 0.25
    },
    "phantom_bbox_reduction": {
      "auto_reduce_bbox": false,
      "use_symmetry_reduction": true
    }
  },
  "simulation_parameters": {"bbox_padding_mm": 30, "convergence_level_dB": -30}
}
```

36 sims; compute time depends heavily on hardware. If 11 GHz / 0.25 mm OOMs even with half-body, drop to 0.30 mm (10 CPW eye) for that frequency only and document the asymmetry.
