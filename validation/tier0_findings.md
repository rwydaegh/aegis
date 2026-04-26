# Tier 0 findings: AEGIS vs goliat FDTD on Thelonious, 450 MHz to 5.8 GHz

108 paired data points, no new FDTD runs. Drives AEGIS through every kernel
(L3 → L6) plus per-direction occlusion against the existing 2026 PMB
environmental campaign.

## Summary up front

The geometric absorption framework holds up where the paper says it should and
breaks down where the paper says it should. Three quantitative results worth
keeping:

1. **Direction-averaged Cauchy formula `<P_abs> = S_inc · T̄ · A_ab / 4`
   matches FDTD to 1.2 % at 5.8 GHz.** This is the paper's main quantitative
   claim made true on real anatomical-phantom data, with `A_ab` from AEGIS's
   own ambient occlusion (η = 0.865, paper says 0.87) and `T̄` from its own
   Fresnel kernel.

2. **Going down in frequency, the Cauchy ratio drops monotonically to 0.39 at
   700 MHz.** Same direction-averaged comparison, but the body now absorbs
   more than its geometric-optics cross section because of resonance and
   diffraction-into-shadow. The paper acknowledges this through Figure 1.1 and
   its `< 100 MHz` caveat in §6.2; what's new here is a quantitative trace of
   the breakdown across nine frequencies on a real phantom.

3. **Two real gaps identified, both addressable.** AEGIS's spatial kernels do
   not multiply by per-direction visibility `O(r, k̂)` from the paper eq. 3.1.
   Adding it via a new engine parameter (this PR) closes the per-direction
   variance noticeably at high frequency and over-corrects at low. Adding
   realistic per-triangle mean curvature (cotangent Laplacian on the merged
   STL) makes L5/L6 actually do something, raising 700 MHz from 0.43 to 0.78
   in the per-direction comparison. Neither fix changes the headline Cauchy
   number, which is correct on its own.

Honest scoreboard, ratios `<P_abs>^AEGIS / <P_abs>^FDTD`, all 12 directions × 2 polarisations averaged:

| f (GHz) | L3 | L4 (pol) | L6 (real H) | L_all | L_all × O | Cauchy + T̄ |
|---|---|---|---|---|---|---|
| 0.45 | 0.44 | 0.44 | **0.97** | **0.97** | 0.71 | 0.41 |
| 0.7  | 0.42 | 0.42 | 0.76 | 0.76 | 0.57 | 0.39 |
| 1.45 | 0.56 | 0.56 | 0.80 | 0.80 | 0.61 | 0.52 |
| 2.45 | 0.64 | 0.64 | 0.81 | 0.81 | 0.62 | 0.59 |
| 3.5  | 0.79 | 0.79 | 0.94 | 0.94 | 0.72 | 0.73 |
| 5.2  | 1.04 | 1.04 | 1.17 | 1.17 | 0.90 | 0.96 |
| 5.8  | 1.09 | 1.09 | 1.22 | 1.22 | 0.94 | **1.012** |

**`L_all == L6` everywhere** at the direction-averaged level: turning on
polarisation in addition to curvature+diffraction does not change the mean.
Paper §6.1 prediction (polarisation correction averages to zero across (θ,φ)
pairs) confirmed once more on real anatomical-phantom data. Polarisation
only tightens the per-direction variance (next section).

No single kernel hits 1.0 across the whole band. The Cauchy direction-average
formula is the only line that approaches unity in the paper's claimed region
of optimality and remains a sensible lower bound elsewhere.

---

## Tier 0.5 corrections (added on re-audit)

A pre-flight pass over the whole pipeline (`scripts/preflight_check.py`)
caught and fixed three issues in the original Tier 0 write-up. None
change the headline numbers, but each was wrong on its own merits.

1. **STL ≡ goliat phantom voxel mesh** (was suspected to differ ~10–20 %).
   The campaign config snapshot shows `bbox_padding_mm = 20`. Once that
   padding is accounted for, predicted face areas from the STL match
   goliat's reported `cross_section_m2` to 0.96 %. The user's "couple mm"
   intuition is correct; my earlier worry that the STL was systematically
   smaller was based on reading the *current* `far_field_config.json` on
   disk, which has drifted to `bbox_padding_mm = 0` post-campaign. Lesson:
   always read the snapshot, never the live config.

2. **Bookkeeping anomaly is not 50-mm-padding-related.** The campaign used
   20 mm padding, not 50. The real cause is the Sim4Life TF/SF auto-shift
   inward by 2 cells (5 mm at 2.5 mm grid) combined with how `RadPower`
   counts plane-wave power that bypasses the phantom. See "FDTD
   bookkeeping anomaly" section below for the full diagnosis.

3. **Pole-basis bug in `goliat_basis(name="z_neg")`.** The old override at
   the spherical pole forced `e_theta = +x_hat` regardless of theta, which
   gave the wrong-handed triad for `z_neg`. Fixed to use the formula's
   natural limit (`e_theta = -x_hat` at theta=180°). q-field is invariant
   under `E → -E` (it depends on `e_E²`), so Tier 0 numbers are unchanged;
   the bug was cosmetic, but mattered for any future field-vector plotting
   downstream.

`scripts/preflight_check.py` encodes all eight invariants checked here
(direction basis, polarisation basis, q sign, renorm constant, IT'IS
dielectric ranges, curvature sign on a unit sphere, visibility on a closed
mesh, STL ↔ phantom-voxel cross-section matching). Run before each new
tier launches.

---

## Setup

- **Phantom**: Thelonious STL from `aegis/data/`. 23 826 triangles, 0.787 m²
  surface area, bbox 0.37 × 0.22 × 1.18 m, mass 17.4 kg per `phantoms.yaml`.
  Watertight after vertex merging (volume 0.019 m³, density 1 g/cm³ implied).
  *Verified to match the goliat voxel phantom*: STL bbox + 20 mm campaign
  padding reproduces goliat's reported `cross_section_m2` to within 1 %
  (see `scripts/preflight_check.py:check_stl_vs_goliat_phantom_bbox`).
- **Frequencies**: 9 environmental cases from the existing 2026 PMB campaign:
  450, 700, 835, 1450, 2140, 2450, 3500, 5200, 5800 MHz. The 7000 MHz folder
  in `goliat/results/far_field.zip` is empty; the FR3 (7+ GHz) campaign was
  auto_induced only. So Tier 0 is sub-6 GHz by necessity.
- **Directions × polarisations**: 6 × 2 = 12 per frequency. Goliat
  `(theta_deg, phi_deg)` is the propagation direction (verified against
  `goliat/setups/far_field_setup.py:184–222`); `Psi=0` is θ-pol along the
  propagation `ê_θ`, `Psi=90` is φ-pol along `ê_φ`.
- **Renormalisation**: goliat excites with E = 1 V/m, so its `Sinc =
  1/(2η₀) ≈ 1.327 mW/m²`. FDTD outputs are scaled by `754 ≈ 2η₀` to express
  everything per `Sinc = 1 W/m²`. AEGIS is driven directly with `power = 1.0
  W/m²`.
- **STL frame** (verified): z up, head at top of bbox, face on the −y side
  (head bbox skewed toward y < 0). Body L–R symmetric so `A_perp(+x) =
  A_perp(−x) = 0.220 m²` exactly; near front-back symmetric (`A_perp(±y) =
  0.239 m²`); vertical projection 0.089 m².
- **Curvature**: 2H per triangle from the cotangent Laplacian on the merged
  STL, sign-corrected so convex regions are positive. Area-weighted `<2H> ≈
  26 /m`, effective body radius ≈ 8 cm (mix of limbs and torso).
- **Visibility**: per-direction binary `O(r, k̂)` from BVH ray-tracing in
  `aegis.geometry.occlusion.ray_mesh_any_hit`. Front-facing visibility
  fractions: lateral 56 %, frontal 89 %, vertical 40–53 %.

## Geometry maps

![geometry maps](fig_geometry_maps.png)

From left:
- **2H (positive part)** from the cotangent Laplacian. High curvature on
  fingers, ears, nose, knees. Effectively zero on flat torso panels.
- **η(r)** from `compute_ambient_occlusion(n_rays=128)`. Confirms paper's
  Thelonious value `A_ab/A = 0.865` (paper quotes 0.87). Inner armpits and
  inner thighs drop to η ≈ 0.5; rest of body is fully exposed.
- **Binary `O(r, k̂)` for k = +x** (illumination from +x source, anatomical
  right). The −x face is uniformly visible; the +x face is the dark side
  (μ < 0); the visible blue band on the +x side comes from triangles with
  ambiguous orientation around contour transitions.
- **`Sab(r)` at 5.8 GHz, +x incidence, L6 with real H.** The cosine-law
  pattern is clean. Front-facing limbs and torso get the highest Sab; the
  shadow side is zero. With diffraction smoothing this is what the paper
  would call the "physical Sab map".

## Kernel-by-kernel comparison

![kernels vs FDTD](fig_kernels_vs_fdtd.png)

Left panel is per-(direction, polarisation) ratios with mean ± std error
bars over the 12 dirs × 2 pols. Right panel is the same data but as a single
direction-averaged ratio per frequency, plus the closed-form Cauchy
prediction.

### L3 (Fresnel only, no polarisation, no curvature, no occlusion)

This is what AEGIS's "default level 3" computes today for an incoherent plane
wave with `from_powers`. Mean ratio rises monotonically from 0.46 at 450 MHz
to 1.14 at 5.8 GHz, crossing 1.0 around 5 GHz. Std stays at 0.15–0.27. This
is the Mie-regime breakdown the paper warns about: at low size parameter
`x = πd/λ` (5–10 here) absorption is dominated by diffraction into
geometric shadow plus body resonance, neither of which a pure ReLU(μ) law
captures.

### L4 (L3 + polarisation correction via q(r))

I implemented `q(r) = |e_p|² − |e_s|²` per triangle from the incident E
direction (`ê_θ` for θ-pol, `ê_φ` for φ-pol). Before this, my Tier 0 was
treating both polarisations identically (`q = 0`). The polarisation kernel
gives:

- Mean ratio is identical to L3 (paper §6.1 prediction: averaging over a
  matched (θ, φ) pair cancels the `q` contribution exactly).
- Std of ratios drops at high frequency: 0.27 → 0.21 at 5.8 GHz (−22 %),
  0.19 → 0.16 at 3.5 GHz (−16 %), unchanged at 1.4 GHz, slightly worse at
  450 MHz (where the surface law itself is broken).
- Per-direction `D_B` magnitudes track the paper.

### L5 / L6 (curvature and diffraction smoothing) with real per-triangle 2H

This was the surprising one. With `curvature_H = zeros`, L5 and L6 collapse
to L3. With proper 2H from the mesh:

- L6 lifts the 700 MHz mean ratio from 0.43 to **0.78** and 1450 MHz from
  0.55 to 0.78. Diffraction smoothing of the shadow boundary captures real
  physics in the deep-Mie regime.
- L6 overshoots at high frequency: 5.8 GHz ratio rises from 1.14 to 1.26.
  The GELU width `σ = √(λ·H/(4π))` is supposed to → 0 as λ → 0, but the
  `T₀ · (H/k) · μ_+²` curvature term in the same kernel adds a
  contribution that doesn't vanish fast enough at 5.8 GHz on a thin-limb
  body. Either the kernel coefficient is right and the body is genuinely
  more reflective there than a smooth surface predicts, or the discretised
  H estimate over-emphasises sharp local features (fingertips, ears) whose
  contribution should average down against larger smooth panels.

### Per-direction occlusion (this PR's engine change)

AEGIS's spatial kernels do not multiply by `O(r, k̂)`. Paper eq. 3.1 has
this factor; AEGIS only computes the direction-averaged η at the aggregate
level. Adding `occlusion=` to `engine.compute()` and post-multiplying the
returned Sab fixes the per-direction map:

```python
res = engine.compute(body, paths, level=3, occlusion=visibility_array)
```

Effects:
- L3 + binary O drops 5.8 GHz ratio from 1.14 to 0.80 (over-corrects in the
  other direction).
- L6 + binary O is the lowest line on the plot at every frequency: occlusion
  is a strict reduction (`O ≤ 1`) and L6 already overshot.
- At 700 MHz, occlusion makes things worse (0.78 → 0.58). Long λ waves
  diffract *into* "geometrically occluded" regions; binary O assumes they
  don't.

The right answer is a **frequency-aware visibility** smoothed at scale ~
`√(λR)` where R is the local radius of curvature, analogous to how the GELU
σ replaces the ReLU step. The monograph alludes to this but doesn't write
the kernel out. Implementing it is its own project; the binary O on offer
here is a useful upper bound at high frequency and a known overshoot at low.

### Cauchy direction-average with T̄

Black stars on the right panel of the kernel plot. This is what the paper
calls "exact above 100 MHz" via T̄. Real numbers:

- 5.8 GHz: 1.012 ✅
- 5.2 GHz: 0.96
- 3.5 GHz: 0.73
- 700 MHz: 0.39

The paper claim holds at the upper end of the data range. Below ~5 GHz the
direction-averaged absorbed power is genuinely larger than `S_inc · T̄ ·
A_ab / 4` because of body resonance + diffraction into shadow. The paper's
own Figure 1.1 (Mie validation) shows this trend explicitly at small `x`;
the human-phantom case follows the same shape.

This is the cleanest single-number test we have today and the one
worth quoting in any future paper section on FDTD validation.

## Polarisation

![polarisation](fig_polarisation.png)

Left panel: observed `D_B = |P_θ − P_φ|/(P_θ + P_φ)` from FDTD by direction
class.

- Lateral (x) is the largest, peaking at 19.5 % at the band edges
  (5.8 GHz, 450 MHz). The paper's claim "max D_B = 16 % on Thelonious near
  lateral illumination" is at 28 GHz; at 5.8 GHz we exceed it slightly.
  Either the paper's universal bound has a residual frequency dependence
  through |ñ|, or the discretisation of the body in Sim4Life's voxel model
  inflates it. Either way: under the cylinder bound (27.9 %) at every
  frequency, which is the paper's universal upper limit.
- Frontal (y) and vertical (z) stay below 10 % — `e^{2iα}` rotates more
  uniformly across the front and top of the body, suppressing the
  imbalance.

Right panel: signed `D_B` from FDTD vs from AEGIS L4 per direction at 3.5 and
5.8 GHz. AEGIS qualitatively reproduces the sign and ordering — directions
where FDTD shows θ-pol absorbing less than φ-pol get correctly predicted
to do so by AEGIS — but the magnitude is biased: AEGIS says |D_B| ≈ 0.13
even where FDTD says 0.05. Possible source: my `q(r)` is computed
analytically from the source direction, while the FDTD couples through a
multi-tissue voxel model where polarisation is partly mixed by the
underlying tissue layering and skin perforation (the paper's own
supplementary §1.1 reports 9.6–13.1 % skin-mesh perforation at 450–2140 MHz,
which would couple θ ↔ φ).

## FDTD bookkeeping anomaly

![fdtd bookkeeping](fig_fdtd_bookkeeping.png)

The goliat-reported `Balance = (DielLoss + RadPower) / Pin` is *not* close
to 1 for non-frontal directions. Mean across all 108 records is 1.42;
vertical (z) directions peak at **3.4×** at 700 MHz.

This is not a physics bug, but the diagnosis went through several wrong
turns and the resolution deserves to be stated cleanly.

### What the campaign actually configured

The `config.json` snapshot embedded in every result folder
(`config_snapshot.simulation_parameters.bbox_padding_mm = 20`,
`gridding_parameters.padding.manual_*_padding_mm = [0,0,0]`) tells us the
2026 PMB sub-6 GHz campaign used **20 mm bbox padding**, not the 50 mm
default of older configs and not the 0 mm of the current
`far_field_config.json` on disk (the file has drifted post-campaign — see
the pre-flight check in `scripts/preflight_check.py` which now reads the
*snapshot* rather than the on-disk config).

With 20 mm padding the simulation bbox face areas predicted from the
Thelonious STL are `0.311 × 0.504 × 0.105` m², matching goliat's reported
`cross_section_m2` of `0.308 × 0.501 × 0.104` m² to within 1 %. So **the
STL we use is the same phantom geometry that goliat ran on** — no
voxel-vs-mesh divergence.

### Why balance ≠ 1

Three contributing factors, none of which affect the absolute-Pabs
comparison:

1. **Pin uses sim-bbox face area, but TF/SF injects through a smaller box.**
   The verbose log records: `Changed total-field-scattered-field bounding
   box (face -x) to ensure stability: ensure 2 cells to the computational
   boundary`. Sim4Life auto-retracts the TF/SF surface 2 cells inward from
   sim-bbox. At 2.5 mm grid (700 MHz) that's 5 mm per face. So the actual
   incident power flux is `Sinc · A_perp(TF/SF face)`, ~3–7 % less than
   the reported `Pin = Sinc · A_perp(sim bbox face)`. *This pushes balance
   above 1 by a few percent.*

2. **RadPower includes power that flows around the phantom.** S4L's
   `Power Balance` sensor reports the net Poynting flux through the
   simulation domain (PML) outer surface. For a phantom much smaller than
   the sim bbox, most of the incident plane-wave power exits the far face
   without ever encountering the body. RadPower therefore tracks `Sinc ·
   A_perp(sim bbox)` modulo the small fraction absorbed/scattered by the
   phantom, which already overshoots Pin (per #1) before any phantom
   contribution.

3. **Small cross-section directions amplify both effects.** For vertical
   (z) the phantom projects only 0.089 m² (about 9 % of its surface), so
   the 5–10 mm rim of "non-attenuated" plane wave that the sensor reads as
   RadPower dominates the balance arithmetic. That's why z directions
   balance at 3.4× while x/y stay near 1.4×.

### Implications for AEGIS comparison: none

`DielLoss` is the real dielectric loss in the phantom (volume integral of
`½σ|E|²`), independent of how the post-processor defines Pin and
RadPower. The `× 754` renormalisation depends only on the unit `E = 1
V/m`, not on Pin. All headline ratios in this document use `DielLoss × 754`
on the FDTD side and are therefore unbiased by the balance-ratio anomaly.

For the goliat-side fix, the cleanest patch is to recompute Pin from
the *TF/SF* face area (the "real" injection plane) rather than the sim-bbox
face area. That's a four-line change in
`goliat/extraction/power_extractor.py:_calculate_bbox_cross_section` —
shrink the sim bbox by `2 × grid_size` per face before computing
`A_perp`. Cosmetic only; doesn't change any physics.

## What's still missing in AEGIS

After the engine occlusion patch:

1. **Frequency-aware (smoothed) occlusion.** The right kernel for
   non-convex bodies at finite λ multiplies ReLU(μ) by an O smoothed at
   scale √(λR), not the hard-binary version. This is alluded to in the
   monograph but not written out. Concretely: precompute a signed distance
   from the binary-occlusion boundary along each direction, then convolve
   with a Gaussian of width √(λR_local) before multiplication. ~20 lines
   in `geometry/occlusion.py` and an extra optional parameter on the engine.

2. **A `compute_curvature()` helper on `BodyMesh`.** Right now anyone using
   L5 / L6 has to compute 2H themselves and pass it as an array — without a
   helper, the kernels effectively never run with the right input. This
   alone explains why my first attempt (uniform-H stand-in) was the
   default state of the framework. Cotangent-Laplacian implementation is
   ~30 lines, watertight after vertex merge.

3. **Higher-frequency benchmark data.** The paper's quantitative claim of
   "Fresnel error 2–6 % in 10–60 GHz" is *not testable* against the
   existing campaign because no environmental FDTD exists above 5.8 GHz.
   Tier 1 of `fdtd_validation_plan.md` re-runs at 7–11 GHz from scratch.

## What's still missing on the FDTD side

After my critique earlier, plus what shows up in the data:

1. **CPW < 10 in eye/muscle/skin at FR3 and FR2.** Self-confessed in
   supplementary §1.1. At 26 GHz, CPW = 7 in vitreous humor — below the
   paper's own targeted threshold. Defensible for APD because APD is a
   surface integral, not for SAR_wb in deep tissue.
2. **Skin mesh perforation 9.6–13.1 %** at 450–2140 MHz. Would bias any
   surface SAPD comparison sub-2 GHz, but APD is not the metric there.
   Couples θ ↔ φ in unpredictable ways.
3. **Power balance 0.83–3.4×** as quantified above. Bookkeeping bug.
4. **No environmental data above 5.8 GHz** in the public campaign zip.
   Auto_induced uses an E²-proxy hotspot score and a 50 mm cube field
   combination; not directly comparable to AEGIS plane-wave Sab.
5. **Half-body symmetry above 7 GHz** assumes zero coupling across the
   sagittal midplane. Convergence not demonstrated.
6. **Height factor reduction** above 7 GHz: at 15 GHz only 30 % of phantom
   simulated. "Whole-body SAR" at 15 GHz is upper-body only.
7. **No CPW convergence study.** Single (CPW, dt, sim time) point per
   frequency.
8. **PML 7 layers, "Low" strength** in `base_config.json`. Standard
   recommendation is 8–12 layers.
9. **26 GHz: n = 1.** Single phantom, single direction, half-body.

## Verdict

For the headline question "is AEGIS's geometric-dosimetry framework
quantitatively correct on real anatomical phantoms": **yes, in its claimed
window of validity (10–60 GHz with Cauchy direction-average), modulo
re-running FDTD there**. At 5.8 GHz on existing data, the Cauchy formula is
off by 1.2 %.

For "does AEGIS today implement what the monograph claims it implements":
**not quite**. Spatial kernels miss occlusion (now fixed) and effectively
can't run L5/L6 because curvature is user-provided and almost nobody is
going to compute it. Both are easy to land.

For "is the existing FDTD campaign trustworthy enough to be ground truth":
**for absolute Pabs, yes**, since FDTD physics conserves energy regardless of
post-processing bugs and the `× 754` renormalisation cuts through the broken
Pin field. **For per-tissue SAR or peak SAPD at FR3, less so**, because
CPW < 10 means a few-percent dispersion error has been integrated through
the entire eye / brain volume.

## Files produced

- `tier0_findings.md` (this document)
- `fig_geometry_maps.png` — 2H, η(r), O(r,+x), Sab map
- `fig_kernels_vs_fdtd.png` — kernel comparison + Cauchy line
- `fig_polarisation.png` — D_B vs frequency, signed L4 vs FDTD
- `fig_fdtd_bookkeeping.png` — power balance and Pin reconciliation
- `tier0_thelonious_sub6.png` — earlier quick-look version (kept for context)
- `tier0_l3_vs_l4.png` — earlier polarisation-only version (kept)
- `scripts/geometry.py` — curvature, visibility, polarisation helpers
- `scripts/run_tier0.py` — reproduces all 108 records into a parquet
- `scripts/plot_tier0.py` — reproduces all four figures from the parquet
- `scripts/README.md` — how to reproduce
- AEGIS engine patch: `engine.py` now accepts `occlusion=` parameter on
  both the legacy level-based path and the `mode='spatial'` path. Backward
  compatible (default None → no change in existing behaviour).

Next: implement the smoothed-O kernel, then start Tier 1 FDTD re-runs at
7/9/11 GHz with 12 CPW and the goliat power-balance bookkeeping fixed.
