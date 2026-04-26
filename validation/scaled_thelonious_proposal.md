# Scaled-thelonious validation strategy (proposal)

**Status (2026-04-26):** active proposal. Tier 1 onwards depends on this idea
working out — the previous "creep up the frequency on full-body thelonious"
plan is on hold pending the experiment described here.

## TL;DR

Run goliat-FDTD on a *geometrically scaled* thelonious phantom (e.g. linear
size × 1/3) at the same frequency sweep we'd use for the full body
(700 MHz → 28 GHz). Compare against AEGIS predictions on the *same scaled
mesh*. Because AEGIS is a geometric-optics framework whose prediction
structure depends only on the dimensionless size parameter $x = \pi d/\lambda$
(plus the dispersive material), this validates the framework across the
entire $x$ range that matters for body-scale dosimetry — but at $1/N^4$ the
compute cost of doing it on a real-size phantom.

For $N = 3$, that's a 81× compute reduction. A 28 GHz simulation on full
thelonious would run for roughly 27 wallclock hours on 1×3090; the same on a
1/3-scaled phantom should finish in ~20 minutes.

## Hypothesis

**Tier 0 found:** AEGIS's L_all kernel (visibility + Fresnel + curvature)
predicts goliat's per-region SAR within ~30% at sub-6 GHz. The L4-vs-L_all
gap (the diffraction-correction contribution) is non-trivial in this regime.

**Predicted at high frequency:** as $x \to \infty$ the geometric-optics
limit holds and AEGIS/goliat ratio → ~1 modulo a small Fresnel-curvature
residual ($R_{\mathrm{sphere}}$, see monograph §sec:mie). The diffraction
correction L_all−L4 should vanish (Fock theory: $x^{-2/3}$ scaling). The
sign of the residual flips near 39 GHz where $R_{\mathrm{sphere}} = 1$
(monograph table 8).

**The single experiment that tests all three:** a frequency sweep on the
same mesh, plotting AEGIS/goliat vs $x$ and overlaying onto the existing
Mie-on-spheres validation curve. If the body-phantom curve sits between the
sphere curve and 1.0 and converges to the asymptotic Fresnel limit, the
framework is validated. If it doesn't, we learn precisely where it breaks.

## Why scaling is principled

AEGIS's per-triangle prediction is

$$S_{\mathrm{ab}}(\rr) = S_{\mathrm{inc}} \cdot T_0(\tilde{n}(f)) \cdot \mathrm{ReLU}\bigl[\hat{n}(\rr) \cdot (-\hat{k})\bigr]$$

with optional curvature ($\eta$, $H$) and visibility ($O$) corrections. The
geometric pieces ($\hat{n}$, $H$, $O$) come from the mesh; the material
piece ($T_0$, $\eta$) comes from $\tilde{n}(f)$. **Absolute mesh size
appears nowhere.** Scaling the mesh by $1/N$ at fixed $f$ produces the
same AEGIS prediction structure as the unscaled mesh would at $1/N$ of
the wavelength, i.e. at frequency $Nf$ — *for the geometric error term*.

The material piece doesn't scale: $T_0(f)$ and $\tilde{n}(f)$ are evaluated
at the actual frequency, not the equivalent. So the validation tests:

- Geometric kernel at the dimensionless point $(x = \pi d_{\mathrm{scaled}}/\lambda)$
- With the *physically correct* dispersion at frequency $f$

This isn't a substitute for "is real thelonious correctly modelled by AEGIS
at 28 GHz" — that would need a full-size 28 GHz sim. But it *is* a clean
test of "does AEGIS's geometric kernel match goliat's full physics across
the relevant $x$ range when both see identical inputs."

The Mie validation in monograph §sec:mie does exactly this trick: it varies
sphere radius (and frequency independently) to span $x \in [10^{-2}, 10^2]$
without needing absurdly small/large physical objects. Same logic, bigger
phantom.

## Compute argument

For an FDTD solver at fixed grid resolution $\Delta x$:

- **Voxel count** $\propto V \propto L^3$
- **Time steps to capture transients** $\propto L / \Delta x$ (body-crossing
  time / Courant step)
- **Total cost** $\propto L^4 / \Delta x^4$

If we keep $\Delta x$ fixed (driven by frequency, $\Delta x = \lambda /
\mathrm{CPW}$) and shrink $L$ by factor $\alpha$, total cost scales by
$\alpha^4$. The grid is *unchanged*; we just have less of it to fill.

| linear scale $\alpha$ | thelonious height | compute factor | est. 28 GHz wallclock | best-use regime |
|---|---|---|---|---|
| 1.0 | ~110 cm | 1 | ~27 h | full-body, paper-baseline (700 MHz only) |
| 1/2 | ~55 cm | 1/16 | ~1.7 h | conservative, looks toddler-ish |
| 1/3 | ~37 cm | 1/81 | ~20 min | **proposed default**, doll-sized |
| 1/4 | ~28 cm | 1/256 | ~6 min | aggressive; mesh quality starts to matter |

Caveat: at low frequencies the grid step is set by *geometric* features
(skin layer thickness, fine concavities) rather than $\lambda /
\mathrm{CPW}$. There the $\alpha^4$ scaling doesn't apply — but at low
frequency the full-body sim is already fast (~20 min/sim per the
`goliat/simulation_stats/` baseline) so the issue is moot.

## Proposed Tier 1 protocol

### Setup

- **Phantom**: thelonious, linear scale 1/3 (default; revisable to 1/2 if
  voxel-quality issues at 1/3 force a step back, or 1/4 if 1/3 is still
  too slow at 28 GHz). Apply scaling to the STL via `trimesh` before
  voxelisation; voxel grid is built fresh from the scaled mesh.
- **Material**: IT'IS v5.0 dispersion at the actual operating frequency,
  applied to the scaled body's tissues unchanged. The "scaled-skin-on-a-
  doll-at-28-GHz" is non-physical for real-human dosimetry but irrelevant
  for AEGIS-vs-goliat solver agreement.
- **Wave**: same as Tier 0.5 smoke (`environmental`, `x_pos`, `theta`-pol).
  One direction, one polarisation throughout. The geometric kernel
  comparison doesn't need direction averaging — *all* incidence directions
  produce the same kind of geometric error (curvature mismatch + diffraction
  shadow), so a single direction lets us trace the freq-dependence cleanly.

### Frequency points (revisable; add/remove as wallclock allows)

| $f$ (MHz) | $\lambda$ (cm) | scaled-thelonious $x = \pi d/\lambda$ (d ~ 27 cm) | est. wallclock @ 1/3 scale |
|---|---|---|---|
| 700 | 43 | 2.0 | ~minutes |
| 2400 | 12.5 | 6.8 | ~minutes |
| 5200 | 5.8 | 14.6 | ~minutes |
| 10000 | 3.0 | 28.3 | ~5 min |
| 28000 | 1.07 | 79.2 | ~20 min |

Total: 5 sims, **~30 min wallclock end-to-end** at scale 1/3 if the
estimates hold. Even if they're off by 4× we're still under 2 h — well
inside the human-impatience bound.

### Validation outputs per sim

Per scenario, produce:

1. **Goliat peak SAPD** (paper-baseline, `sapd_field: false` default) — single
   number, the IEC/IEEE 4-cm² windowed peak.
2. **Goliat per-vertex APD field** (`sapd_field: true`, dumped to
   `<results>/skin_apd.npz`). Mesh + per-vertex W/m² values.
3. **AEGIS L_all prediction** on the same scaled mesh (the centroid sample
   pipeline already in `validation/scripts/run_tier0.py` generalises
   trivially — feed it the scaled STL and the scaled body's tissue map).
4. **Comparison metrics**:
   - peak ratio AEGIS / goliat (single number)
   - 4-cm²-window peak ratio (apples-to-apples with the report)
   - area-weighted NRMSE on the per-vertex field
   - 3D paint of (AEGIS - goliat) / goliat, written as a PNG

### Anchor point

The existing full-body thelonious 700 MHz x_pos-theta result (Tier 0.5
smoke, `validation/thelonious_700MHz_x_pos_theta_skin_apd.npz`) gives the
$\alpha = 1$ data point at $f = 700$ MHz. Re-running 700 MHz on the scaled
phantom should give a *different* AEGIS-vs-goliat ratio (different $x$),
but the difference should be predictable from the Mie-sphere curve.

## Where this lands on the existing Mie figure

The monograph's Mie validation figure (`mie_validation_corrected.pdf`,
generated from `aegis/presentations/promotors/figures/mie_*.png`) plots
framework error vs $x$ at 28 GHz for spheres of varying radius. Body-part
sizes are marked.

The thelonious freq sweep adds a second curve to the same axes: instead of
varying sphere radius at fixed $f$, we vary $f$ at fixed (scaled) thelonious
geometry. Both curves trace the same *physics* but at different points in
the (geometry, frequency) plane. They should converge to the same
asymptotic Fresnel limit ($R_{\mathrm{sphere}} - 1$ at the corresponding
frequency).

A successful result is: thelonious points sit *near* the sphere curve at
matching $x$, falling within the band the monograph already characterises.
A divergent result would be a real finding — body-shape vs. sphere-shape
matters more than $x$ alone — and worth understanding.

## Risks and pitfalls

- **PML proximity to a small phantom.** The bbox padding is in absolute mm.
  At scale 1/3, default `bbox_padding_mm: 50` is fine: domain ≈ scaled body
  + 100 mm padding = 47 × 27 × 47 cm-ish, with PML at the edge. Plenty of
  buffer between body and PML. Sanity-check that nothing in the scaled
  body voxellation lands inside the PML.
- **Voxellation of small features.** The original thelonious STL has
  triangle edge lengths down to ~few mm. Scaled by 1/3, that's ~1 mm.
  Goliat's `manual_fallback_max_step_mm: 3.0` cap means at low frequency
  the grid is 3 mm — coarser than the scaled triangle features. Should
  still work (S4L's voxellation is robust to feature-grid mismatch) but
  worth eyeballing the voxel snap of one scenario before committing.
- **Skin layer thickness.** Real skin ~2 mm. At 1/3 scale, ~0.7 mm. At
  28 GHz, skin depth ~ few hundred μm — the scaled skin is still a few
  skin depths thick, so absorption physics is preserved. At 700 MHz, skin
  depth ~5 cm — scaled skin is far thinner than skin depth, and
  attenuation in the scaled body is geometrically faster than in a
  real-size thelonious. *This affects the absolute SAPD magnitude but
  NOT the AEGIS-vs-goliat ratio*, so it doesn't break the validation.
- **Mesh re-voxellation per frequency.** Goliat builds a fresh voxel grid
  per simulation. We don't get to amortise that across frequencies. Each
  sim incurs the full setup cost. But for small phantoms the setup is
  fast; expected ~minutes total across the sweep.
- **Comparison overhead.** The AEGIS-side per-scenario validation
  (`load_skin_apd_npz` + `surface_apd_compare.py`) takes seconds per
  scenario. Negligible.

## What this is NOT

- Not a replacement for full-body simulation when the question is "what
  does a real human absorb at 28 GHz". For that, only $\alpha = 1$ counts.
  This proposal is purely about **validating AEGIS as a numerical solver**
  against goliat as the reference, across the dimensionless $x$ range that
  spans body-scale dosimetry.
- Not a generic frequency-scaling trick for the FDTD itself. Sim4Life's
  voxellation, dispersion, gridding, etc. are all done at the actual $f$.
  The scaling is *only* in the geometry.
- Not necessarily the final Tier 1 answer. If the scaled curve diverges
  from the sphere curve in unexpected ways, we'd need a follow-up tier
  with a few full-body anchor points to determine whether the divergence
  is body-shape or scaling-artifact.

## Concrete next steps

1. **Build `scale_thelonious.py`** in `validation/scripts/`: trimesh load
   the existing thelonious STL, apply uniform scaling, write
   `data/scaled_phantoms/thelonious_one_third.stl`. ~30 lines.
2. **Goliat config** `configs/scaled_thelonious_one_third.json`: extend
   `test_sapd_far_field.json`, override the phantom mesh path, set the
   single direction (`x_pos`, `theta`) and a single frequency. Loop the
   frequency externally (5 configs total).
3. **Drive script**: a small shell loop that launches each frequency,
   waits for the dump, scp's it back to Linux. Probably 20-30 lines.
4. **Aggregator notebook**: load the 5 npzs, compute the ratios, plot
   AEGIS/goliat vs $x$ overlaid on the Mie sphere curve.

Steps 1, 2, 4 are local AEGIS-side prep. Step 3 is the actual campaign.
Total ~half a day of agent work for steps 1-2 and 4, plus the campaign
wallclock (~30 min – 2 h).

## Decision criteria for proceeding past Tier 1

- **If scaled freq sweep validates AEGIS** (AEGIS/goliat ratio behaves
  per the Mie/Fresnel prediction across $x$): the framework's geometric
  kernel is solid. We can publish this as Tier 1 and treat the higher
  tiers (full-body anchors, polarisation sweeps, multi-phantom) as
  optional refinements, not gates.
- **If the scaled curve disagrees with the sphere curve** at matching $x$:
  body shape introduces error beyond what spheres predict. This is a real
  finding. Tier 1.5: small full-body anchor sweep at 1-2 frequencies to
  determine whether the disagreement is *body-shape* or *scaling-artefact*.
- **If even the 700 MHz scaled / full-body comparison disagrees**: scaling
  artefact; abandon this approach, fall back to the full-body creep-up
  plan. This is the worst case but it's also a quick check (we already
  have full-body 700 MHz; need scaled 700 MHz, which is the cheapest sim
  in the sweep).
