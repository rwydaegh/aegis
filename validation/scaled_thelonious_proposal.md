# Scaled-thelonious validation strategy (proposal — revised)

**Status (2026-04-26, revised):** *downgraded.* The original framing — "1/N⁴
compute saving for the same physical regime" — was wrong. Maxwell scale
invariance plus FDTD cost ∝ x⁴ means the apparent compute saving comes
from validating at lower x, not from a method-level shortcut. This
document records the corrected analysis and what (modest) value a
scaled-thelonious campaign would still have.

For the actual validation campaign going forward, see
`fdtd_validation_plan.md`. The original Tier 1+ designs (full-body
high-x anchor sims) are *not* obviated by this proposal and are back
in scope.

## TL;DR

A scaled-(1/N) thelonious freq sweep at 700 MHz – 28 GHz validates
AEGIS at dimensionless size parameters $x = \pi d/\lambda$ that are
**already covered** by the existing Tier 0 sub-6 GHz dataset on full
thelonious, modulo:

- A modest x-range extension (Tier 0 reaches $x \approx 50$;
  scaled-(1/3) × 28 GHz reaches $x \approx 79$).
- A small dispersion-correction signal ($R_{\mathrm{sphere}}(f)$ varies
  ~3 % across the body band; this would test it empirically on a body
  shape rather than the sphere of the existing Mie validation).
- An empirical self-consistency check on Maxwell scale invariance for
  dispersive, lossy anatomical bodies.

It is **not** a substitute for high-x full-body validation. Real-sized
thelonious at 28 GHz sits at $x \approx 240$; reaching that x costs
FDTD compute ∝ x⁴ regardless of how $(L, f)$ is split. The 1/81
wallclock vs. full-body × 28 GHz comes from validating at 1/3 the x,
not from a free shortcut.

If we run it, the role is "30-minute sanity check before committing
GPU hours to real high-x sims," not "headline Tier 1 result."

## What scale invariance buys and doesn't buy

AEGIS's per-triangle prediction is

$$S_{\mathrm{ab}}(\rr) = S_{\mathrm{inc}}\,T_0(\tilde{n}(f))\,\mathrm{ReLU}[\hat{n}\cdot(-\hat{k})] + \text{curvature/visibility/diffraction corrections}$$

**What scales exactly.** The geometric pieces ($\hat{n}$, $H$, $O$,
shadow boundaries) are dimensionless — they depend only on $x = \pi d/\lambda$.
Scaling $L$ by $\alpha$ at fixed $f$ produces the same dimensionless
problem as scaling $f$ by $1/\alpha$ at fixed $L$. Both AEGIS and FDTD
respect this (FDTD because Maxwell does, modulo dispersion). The
diffraction error AEGIS makes, which is the dominant error at low x,
is purely a function of x — not of f.

**What does NOT scale.** The material piece. $\varepsilon, \sigma$ for
skin at 28 GHz differ from at 2.67 GHz. So scaled-(1/3) × 8 GHz is at
the **same x as full-body × 2.67 GHz** but uses **8 GHz tissue
properties**. The asymptotic Fresnel error $R_{\mathrm{sphere}} - 1$
varies with $f$ even at fixed x (monograph Table 8: $-3.2\%$ at 6 GHz,
$-1.2\%$ at 28 GHz, 0 at 39 GHz, $+3.5\%$ at 100 GHz).

**FDTD compute cost ∝ x⁴.** Cells scale as $L^3/\lambda^3 \sim x^3$;
time steps as $L/\lambda \sim x$; total $\sim x^4$. This is
independent of the $(L, f)$ split — it depends only on the
dimensionless x.

- Validate at $x = 50$: same compute whether full × 5.8 GHz or
  scaled-(1/3) × 17 GHz.
- Validate at $x = 240$ (real human × 28 GHz): same compute whether
  full × 28 GHz or scaled × 84 GHz. Both expensive.

The "1/N⁴ saving" of the original proposal was conflating *"scaled
at the same f as full"* (which is at 1/N the x) with *"scaled at the
same x as full"* (which costs the same). The compute reduction was
real but came from omitting the high-x end, not from finding a
shortcut.

## What scaled-thelonious DOES validate (the residue)

1. **Body-shape vs. sphere-shape at slightly higher x than Tier 0
   reached.** Tier 0 caps at $x \approx 50$ on full thelonious × 5.8 GHz.
   Scaled-(1/3) × 28 GHz reaches $x \approx 79$. AEGIS is already
   $\approx 1\%$ accurate by $x = 50$ on Tier 0 data, so x = 79 is an
   asymptote-confirmation point.

2. **Tissue-dispersion footprint on a body shape.** The existing Mie
   validation characterises the dispersion correction on spheres only.
   Running the scaled body across f empirically confirms the same
   correction applies to body shapes. Single-digit-percent effect; a
   closed data point, not a paper headline.

3. **Empirical scale-invariance check.** Pair-wise: scaled-(1/3) × f
   vs. full × f/3, both at matching x. If the AEGIS/FDTD ratios
   disagree, a Sim4Life voxellation artefact is contaminating one of
   the two (likely scale-1/3 skin layer relative to grid step). If
   they agree, scale invariance is empirically confirmed for the
   solver chain — useful methodological footing for any partial-body
   crops in Tier 3.

## What scaled-thelonious does NOT validate

- *"AEGIS at 28 GHz on a real human."* That requires $x \approx 240$
  on full body. Expensive in FDTD regardless of any scaling trick;
  the compute floor is set by x, not by L.
- *"AEGIS in its theoretical sweet spot (10–60 GHz) on body shapes."*
  The sweet spot is high x AND high f. Scaled body at high f gives
  high-f material at low x — the wrong regime for that question.

For either of those, real full-body sims at the target frequency are
required. Tier 1 / Tier 3 of the validation plan is the venue, and
they are not obviated by this proposal.

## If we run it: the protocol

Positioned as a sanity check, not a Tier 1 replacement.

### Setup

- Phantom: thelonious, scaled by 1/3 (revisable to 1/2 if voxellation
  issues). Apply scaling via `trimesh` to the STL before voxelisation;
  goliat builds a fresh voxel grid.
- Materials: IT'IS v5.0 unchanged at the actual operating frequency.
  Scaled-skin-on-doll is non-physical for human dosimetry but
  irrelevant for solver-vs-solver comparison.
- Wave: single direction (`x_pos`, `theta`-pol), as in Tier 0.5 smoke.

### Frequency points

| $f$ (MHz) | $\lambda$ (cm) | scaled-thel $x = \pi d/\lambda$ ($d \approx 27\,\mathrm{cm}$) | also covered by full-body at | est. wallclock @ 1/3 |
|---|---|---|---|---|
| 700   | 43   | 2.0  | 233 MHz (below Tier 0)        | minutes |
| 2400  | 12.5 | 6.8  | 800 MHz (Tier 0 covered)      | minutes |
| 5200  | 5.8  | 14.6 | 1.7 GHz (Tier 0 covered)      | minutes |
| 10000 | 3.0  | 28.3 | 3.3 GHz (Tier 0 covered)      | ~5 min  |
| 28000 | 1.07 | 79.2 | 9.3 GHz (NEW — past Tier 0 max ≈ 50) | ~20 min |

The "also covered by full-body at" column makes the Tier 0 redundancy
explicit. Only the 28 GHz row gives a genuinely new x.

### Outputs and metrics

Per scenario:

1. Paper-baseline 4-cm² peak SAPD (`sapd_results.json`).
2. Per-vertex APD field (`skin_apd.npz`, dual-evaluator path already
   wired in `goliat/extraction/sapd_extractor.py`).
3. AEGIS L_all on the scaled mesh.
4. Comparison metrics: peak ratio, 4-cm² peak ratio, area-weighted
   NRMSE, 3D-painted residual.

### Pairing with Tier 0 for the scale-invariance check

For each scaled scenario at frequency $f$, find the nearest-x Tier 0
data point (full body at $f/3$). Plot AEGIS/FDTD ratio vs x for both
families on the same axes; they should overlay within FDTD-numerical
noise.

## Decision criteria

- **Scaled and Tier 0 agree at matching x:** scale invariance is
  empirically confirmed for our solver chain. Useful for any later
  partial-body or scaled-anatomy work. Move on to validating the
  regimes Tier 0 doesn't cover (full-body high-x).

- **Scaled and Tier 0 disagree at matching x:** scale invariance is
  broken by a numerical artefact (most likely voxellation of small
  features at scale 1/3, or skin layer thickness relative to grid).
  Debug there. Implication for the broader campaign: no shortcuts —
  high-x validation must be done on real-sized phantoms.

- **Scaled-(1/3) × 28 GHz at $x \approx 79$ shows AEGIS within the
  Mie-asymptote band:** confirms AEGIS is on its geometric-optics
  asymptote, as predicted. Modest evidence; doesn't bear on the
  high-x regime ($x > 100$).

In none of these branches does the campaign substitute for full-body
high-x validation. That's the framing correction this revision is
making.

## Concrete next steps (if we proceed)

1. `validation/scripts/scale_thelonious.py` — trimesh load + uniform
   scale + write `data/scaled_phantoms/thelonious_one_third.stl`.
   ~30 lines.
2. `goliat/configs/scaled_thelonious_one_third.json` — extend
   `test_sapd_far_field.json`, swap phantom mesh, single dir/pol,
   single f. Loop f externally (5 configs).
3. Drive loop on the VM, scp results back.
4. Aggregator notebook: AEGIS/goliat ratio vs x, overlaid on
   (a) the sphere Mie curve and (b) the corresponding-x points from
   Tier 0 full-body data.

Half a day of agent work, ~30 min – 2 h compute.

## Risks

- **PML proximity.** Bbox padding 50 mm gives plenty of buffer at
  scale 1/3 (domain ≈ 47 × 27 × 47 cm).
- **Voxellation of small features.** Thelonious STL triangle edges
  scale to ~1 mm at 1/3. Goliat's `manual_fallback_max_step_mm: 3.0`
  means low-f grid is coarser than scaled features. Eyeball one
  scenario before committing.
- **Skin layer thickness.** ~2 mm real → ~0.7 mm scaled. At 28 GHz,
  $\delta \approx 0.4$ mm — scaled skin still a few skin-depths thick,
  absorption physics preserved. At 700 MHz, $\delta \approx 5$ cm
  ≫ scaled skin: attenuation in scaled body is geometrically faster
  than in real-size thelonious. Affects absolute SAPD magnitude but
  *not* AEGIS-vs-FDTD ratio (both solvers see the same scaled body),
  so doesn't break the validation framing.
- **Mesh re-voxellation per frequency.** Not amortisable; expected
  ~minutes total across the sweep.

## Lesson — why this proposal was written in the first place

The original framing's seductive bit was *"1/N⁴ compute saving"* +
*"validates the same regime as full-size."* Both true in isolation:

- 1/N⁴ at fixed frequency is real — there's less mesh to fill.
- "Same regime" is true if regime means dimensionless x.

The trap: those two truths apply to different scenarios and got
conflated. 1/N⁴ saving comes from working at 1/N the x (different
regime). Same x (same regime) costs the same regardless of scaling.

Mental archive: *if a proposal claims a free factor of N⁴ from
geometric scaling, check whether the dimensionless variable changed.*
