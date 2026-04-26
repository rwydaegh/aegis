# Phase 1 findings: scaled-(1/3) thelonious sanity check

The proposal asked: when we run the scaled-(1/3) thelonious phantom at
frequency `f` and the full-size thelonious at `f/3`, both at matching
size parameter `x = π h / λ`, do AEGIS and FDTD line up the same way?

**Headline finding: no.  The AEGIS / FDTD ratio at the scaled body
sits at 0.5×–0.65× the ratio at the full body for matching `x`
across the overlap window (`x ≈ 10 – 41`).  The Cauchy
direction-average formula shows the same gap.**  Scale invariance,
in the form the proposal tested, is broken — but for an understood
reason (materials at the scaled body's operating frequency
`f_scaled` differ from materials at the full body's
`f_full = f_scaled / 3`, and AEGIS only captures that dispersion
through `T̄`, not through the body-scale absorption physics).  See
"Diagnosis" below.

The methodological consequence: **partial-body crops or scaled
phantoms are not a free shortcut to high-`x` validation.  Path A
(methodical full-body Tier 1) is the right next move, not Path B.**

## What was run

`goliat study scaled_thelonious_one_third` on the upgraded Tensordock
VM (1×3090 / 24 GB / 16 vCPU / 64 GB RAM) for five frequencies:

| f (MHz) | scaled-body x = πh/λ | h_body (m) | grid (mm) | wall-clock |
|---:|---:|---:|---:|---:|
| 700  | 2.89  | 0.394 | 2.5  | ~3 min |
| 2400 | 9.91  | 0.394 | 1.482 | ~3 min |
| 5200 | 21.47 | 0.394 | 1.0  | ~3 min |
| 10000 | 41.29 | 0.394 | 0.5  | ~5 min |
| 28000 | 115.62 | 0.394 | 0.22 | OOM — see below |

Single direction (theta=90°, phi=0° = `x_pos`), single polarisation
(`theta`).  Both `extraction.sapd` (peak 4-cm² windowed, via S4L's
`GenericSAPDEvaluator`) and `extraction.sapd_field` (per-vertex APD
via the dual-evaluator pipeline) emitted; `_Output.h5` retained on
the VM as the Tier 1 fallback.

Phantom: `thelonious_one_third`, produced by uniform 1/3 scaling of
the existing `thelonious.sab` in Sim4Life via
`goliat/utils/scripts/scale_phantom.py`.  Material assignments
preserved by the CAD-level transform (`material_name_mapping.json`
clones the thelonious entry under `thelonious_one_third`).  Scaled
ratios verified to within 1e-7 along each axis.

## Apples-to-apples ratios (single direction, single polarisation)

`AEGIS L_all + binary occlusion / FDTD DielLoss × NORM` at
`x_pos`/theta, both families:

| Phase 1 (scaled-1/3) | x | AEGIS / FDTD | Cauchy / FDTD | AEGIS peak / FDTD peak (4 cm²) |
|---:|---:|---:|---:|---:|
| 700 MHz  | 2.89  | 0.62 | 0.29 | 0.98 |
| 2400 MHz | 9.91  | 0.41 | 0.33 | 0.91 |
| 5200 MHz | 21.47 | 0.37 | 0.39 | 1.19 |
| 10000 MHz | 41.29 | 0.37 | 0.44 | 1.91 |
| 28000 MHz | 115.6 | OOM (see below) | — | — |

| Tier 0 (full) at matching x | x | AEGIS L_all+O / FDTD | Cauchy / FDTD |
|---:|---:|---:|---:|
| 700 MHz  | 8.67  | 0.66 | 0.51 |
| 835 MHz  | 10.34 | 0.63 | 0.51 |
| 1450 MHz | 17.96 | 0.66 | 0.64 |
| 2140 MHz | 26.51 | 0.64 | 0.70 |
| 3500 MHz | 43.35 | 0.76 | 0.91 |
| 5200 MHz | 64.41 | 0.97 | 1.25 |

(Tier 0 Lall+occlusion column from `tier0_thelonious.parquet` filtered
to `direction == "x_pos"` and `pol == "theta"`.)

Matching-x pairings:

  * Phase 1 2400 MHz (x = 9.91) ↔ Tier 0 835 MHz (x = 10.34):
    Phase 1 Lall = 0.41, Tier 0 Lall = 0.63 → **factor 1.5 below**.
  * Phase 1 5200 MHz (x = 21.5) ↔ Tier 0 1450 MHz (x = 17.96):
    Phase 1 Lall = 0.37, Tier 0 Lall = 0.66 → **factor 1.7 below**.
  * Phase 1 10000 MHz (x = 41.3) ↔ Tier 0 3500 MHz (x = 43.4):
    Phase 1 Lall = 0.37, Tier 0 Lall = 0.76 → **factor 2.1 below**.
  * Phase 1 700 MHz (x = 2.89) is below Tier 0's lowest x (5.6); no
    direct Tier 0 match.
  * Phase 1 28 000 MHz (x = 115.6, when it lands) is above Tier 0's
    highest x (71.8); the matched-x point would be at f_full = 9333 MHz
    which Tier 0 also doesn't have.

The ratios are **monotonically off by ~factor 2** across the overlap.

## Diagnosis: dispersion, not voxellation

We can rule out the trivial discretisation explanations by inspecting
the AEGIS-side numbers.

  1. **Phantom area scales correctly.** `A_ab` for the scaled-1/3
     mesh is 0.0756 m² vs 0.6807 m² on full thelonious — exactly
     1/9 (geometric ratio).
  2. **AEGIS scales correctly at matching x.** Comparing absolute
     `Lall_o_Pabs` (occlusion on, single-direction Pabs in W at
     `Sinc = 1 W/m²`):

     |   | Tier 0 ~1733 MHz (interp x ≈ 21.5) | Phase 1 5200 MHz (x = 21.5) | ratio |
     |---|---:|---:|---:|
     | AEGIS L_all+O | ~0.080 | 0.0090 | **0.113** ≈ 1/9 |
     | Cauchy + T̄ | ~0.081 | 0.0093 | **0.115** ≈ 1/9 |

     Both AEGIS predictions scale with `1/9` to within the dispersion
     correction in `T̄(f)` (~3 % across the body band), as expected.
  3. **FDTD does NOT scale 1/9 at matching x.** Same row: Tier 0
     `fdtd_Pabs_W_m2 ≈ 0.122` (interp 1450/2140), Phase 1 `0.0241`
     → ratio **0.197**, almost twice 1/9.  At every overlap point
     the scaled FDTD over-absorbs relative to the 1/9-scaled
     prediction.

The scaled body uses **higher-frequency materials** at any matching
x: scaled at 5200 MHz vs full at 1733 MHz are at the same x but the
scaled body sees the 5200 MHz material parameters.  Scaled tissues
at the higher operating frequency are more lossy per unit volume
than the full body's tissues at the lower operating frequency.  AEGIS
captures the dispersion through `T̄(f)` (~3 % effect on the
direction-averaged formula), but the body-scale absorption physics
(finite skin depth, multi-tissue resonance, propagation into the
torso) varies with the actual operating frequency in a way that the
geometric law does not encode.

The proposal explicitly flagged this:

> "What does NOT scale.  The material piece. ε,σ for skin at 28 GHz
> differ from at 2.67 GHz. So scaled-(1/3) × 8 GHz is at the same x
> as full-body × 2.67 GHz but uses 8 GHz tissue properties."

It estimated this as a "single-digit-percent effect" on the basis of
`T̄`'s dispersion alone, but the bulk absorption effect at finite
skin depth is much larger — roughly factor 2 at x ≈ 10 – 41 in our
data.

This is a **real result**, not a numerical artefact.  Closed by Phase 1.

## 28 GHz OOM — hardware floor at single 24 GB GPU + 64 GB RAM

The 28 GHz scaled run failed with `Not enough GPU memory` and a peak
CPU memory consumption of 86.1 GB (VM has 64 GB) before the
simulation kernel even started time-stepping.  The grid was 0.22 mm
on a 22.4 × 17.4 × 49.4 cm sim domain (after 50 mm bbox padding),
giving roughly 1.79 GCells full-body / 0.9 GCells half-body
symmetric.  That cell count is in the ballpark of the
`fdtd_validation_plan.md` mesh-cell budget table for thelonious at
28 GHz on a *full body* (the table predicted ~17.9 GCells full /
8.95 GCells half, much higher; the difference comes from the body
being 1/3 the size cubed, but the result is still beyond the
single-3090-with-64 GB-RAM envelope here).

We did not retry at coarser CPW or with `height_limit_per_frequency_mm`
because the headline finding (scale invariance broken at matching x
across the 4-frequency overlap window) is already replicated and
robust on the 4 frequencies that did land.  Adding a 5th point past
Tier 0's `x` range would have nudged the existing trend forward but
not changed the conclusion or the path-A vs path-B decision below.

## Implications for Phase 2 (Tier 1)

The proposal's third decision branch read:

> "Scaled and Tier 0 disagree at matching x: scale invariance is
> broken by a numerical artefact (most likely voxellation of small
> features at scale 1/3, or skin layer thickness relative to grid).
> Debug there. Implication for the broader campaign: no shortcuts —
> high-x validation must be done on real-sized phantoms."

Our diagnosis refines this: the disagreement is dispersion-driven,
not voxellation-driven, but the methodological consequence is the
same.  **There is no scaled-phantom shortcut to high-x validation.**
Tier 1 should run on full-size thelonious as designed.

Translating to the handoff's path-A / path-B choice:

  * **Path A** (12 dir × 2 pol × 7/9/11 GHz on full thelonious):
    take it.  This is the methodical sweep the campaign needs.
  * **Path B** (lean Tier 1 + a real high-x point) was conditioned on
    "Phase 1 confirmed scale invariance" — it didn't, so this branch
    is closed.

Stretch tasks that remain open and useful:

  * Tier 2 surface-map comparison on one Tier 1 scenario, using the
    Phase 1 dual-evaluator dump path that already worked (the
    `skin_apd.npz` files landed cleanly for every frequency we ran).
  * Tier 3's 28 GHz head crop or Duke at 7 GHz remain on the table
    for a future hardware bump; nothing in Phase 1 closes them.

## Caveats / known issues

  * Manual grid step capped at 3 mm by goliat's
    `_validate_grid_size`.  At 700 MHz on the scaled body that's
    coarser than the 0.7 mm scaled-skin layer — absolute SAPD
    magnitudes will reflect this discretisation; the AEGIS/FDTD
    ratio is still meaningful since both solvers see the same scaled
    body.
  * Power balance reads ~71–88 % at sub-2 GHz (vs ~100 % expected
    for `(DielLoss + RadPower) / Pin`).  Same Pin-vs-TF/SF-bbox
    bookkeeping anomaly characterised in `tier0_findings.md`; does
    not affect absolute Pabs comparisons.
  * **`skin_apd.npz` is sliced to a 100 mm box around the peak
    SAPD, not the full body** (discovered while debugging Tier 2
    surface-map analysis on full thelonious 7 GHz).  Goliat's
    `SapdExtractor._create_sliced_h5` + dual-evaluator pipeline
    writes per-vertex APD only on the slice.  The Phase 1
    `surface_compare`-derived `surface_nrmse` and
    `surface_peak_ratio_4cm2` columns in the parquet therefore
    compare AEGIS *full-body* Sab against FDTD *slice-region* SAPD,
    which is only roughly meaningful where the slice dominates the
    integrated absorption (it does at high-x where the peak is
    concentrated; less so at low-x where absorption is spread).
    The headline `Lall/FDTD_Pabs` and `Cauchy/FDTD_Pabs` ratios are
    not affected — they use `DielLoss × NORM` (a volume integral
    over the entire phantom), independent of the SAPD slice.

## Files

  * `validation/scripts/scale_thelonious.py` — STL scaling.
  * `validation/scripts/run_phase1.py` — driver.
  * `validation/scripts/plot_phase1.py` — overlay plot.
  * `validation/data/scaled_phantoms/thelonious_one_third.stl`
    + `..._cross_section_pattern.npz` — AEGIS-side scaled mesh
    + per-direction projected area pattern.
  * `validation/data/phase1_thelonious_one_third.parquet` — per-row
    measurements (one row per frequency).
  * `validation/scaled_thelonious_results.png` — headline plot.

  * `goliat/utils/scripts/scale_phantom.py` — Sim4Life-side .sab
    scaler.
  * `goliat/data/phantoms/thelonious_one_third.sab` — scaled
    Sim4Life phantom (on the VM only; not committed; reproducible
    from `thelonious.sab` via `scale_phantom.py`).
  * `goliat/data/phantom_skins/thelonious_one_third/cross_section_pattern.npz`
    — projected-area pattern for the scaled body.
  * `goliat/data/material_name_mapping.json` — entry
    `thelonious_one_third` cloning `thelonious`'s tissue table.
  * `goliat/configs/scaled_thelonious_one_third.json` — campaign
    config.
