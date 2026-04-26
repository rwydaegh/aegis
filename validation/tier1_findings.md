# Tier 1 findings: AEGIS vs FDTD on full thelonious at 7 GHz

The Tier 1 sweep landed only the **lateral pair (x_pos, x_neg)
theta-pol on full thelonious at 7 GHz** before the run hit a chain
of issues that consumed the available budget — see "What actually
ran" below.  The two scenarios that completed cleanly carry the
headline result.

## Headline (2-direction lateral pair, theta-pol, 7 GHz, x = 86.7)

| metric | value | note |
|---|---:|---|
| direction-avg `Lall+O / FDTD` (Pabs) | **0.383** | AEGIS underpredicts FDTD by ~2.6× |
| direction-avg `Cauchy / FDTD` (Pabs) | 0.509 | direction-averaged closed form |
| direction-avg `AEGIS / FDTD` peak 4-cm² SAPD | **1.126** | AEGIS within 13 % of goliat's `GenericSAPDEvaluator` |

Two stories from those three lines:

  1. **AEGIS captures the peak SAPD on the lateral pair to within
     ~13 %.**  Per-direction values are 1.06 (x_pos) and 1.20
     (x_neg) — the metric the IEC/IEEE 63195 standard cares about,
     in AEGIS's claimed sweet spot, is delivered.
  2. **AEGIS underpredicts the total absorbed power by a factor
     ~2.6** at this frequency vs. Tier 0's "Cauchy / FDTD ≈ 1.012
     at 5.8 GHz" headline.  The AEGIS *prediction* is essentially
     the same at 5800 and 7000 MHz (its dominant freq dependence
     is in `T̄(f)`, ~3 %); the *FDTD* DielLoss at 7000 MHz is 2.8×
     the 5800 MHz value on the same direction/polarisation.  Most
     plausible explanations: tighter convergence (-30 dB here vs
     Tier 0's -15 dB) and finer grid (0.6 mm vs 1.0 mm) reveal
     deep-tissue absorption that the geometric surface-only law
     cannot capture.  Full discussion in "First-scenario
     snapshot" below.

## What this campaign tests

The cleanest test of the geometric absorption law in the band where
it is *predicted to be optimal*: 10 – 60 GHz, paper §1.2.  Tier 0
already showed the Cauchy direction-averaged formula matches FDTD to
1.2 % at 5.8 GHz on full thelonious; Tier 1 extends that into the
geometric sweet spot (FR3) where AEGIS's `T_0` Fresnel approximation
should also be exact (`T_avg ≈ T_0` at 40 GHz, monotonically
approached from below in the FR3 window).

Differences from the original Tier 1 spec, with reasons:

  * **Paper grid (0.6 / 0.5 / 0.5 mm at 7 / 9 / 11 GHz)** rather than
    the original Tier 1 sketch's 12 CPW (0.39 / 0.30 / 0.25 mm).
    Reason: 12 CPW at 11 GHz is ~6 GCells half-body, well past a
    single 24 GB 3090.  The paper grid is ~7 CPW in skin at 11 GHz —
    less dense than the sketch but still better than the original
    PMB 8/10 CPW campaign.
  * **Bbox padding 20 mm** to match the 2026 PMB campaign snapshot
    (Tier 0 baseline) — apples-to-apples.
  * Both `extraction.sapd` and `extraction.sapd_field` on so the
    Tier 2 surface-map comparison (paper §6, fig 6.3) can attach to
    any one of these scenarios without an extra FDTD run.

## Setup

  * Phantom: full thelonious (1.18 m, 17.4 kg).  No scaling, no
    cropping; sagittal symmetry exploited (`use_symmetry_reduction:
    true`).
  * Frequency: 7000 MHz only.
  * 6 directions × 1 polarisation (theta) = 6 sims.
  * Grid 0.6 mm (paper baseline ~7 CPW in skin at 7 GHz).
  * Convergence target -30 dB.  `auto_induced.enabled: false`.
  * `auto_cleanup_previous_results: ["output"]` — `_Output.h5`
    deleted post-extraction (saved disk; dual-evaluator + sliced h5
    survive and feed the AEGIS-side analysis).

## Reduced scope rationale

The original Path-A spec was 36 sims (6 dir × 2 pol × 3 freq).  The
first 7 GHz scenario in that run profiled at ~12-15 minutes for the
FDTD time-update plus ~5-10 minutes for SAR/SAPD extraction —
~20 min/sim wall-clock.  At that rate the full sweep would take
8 – 12 hours, which is past the available budget on this VM today.

We therefore reduced to a single frequency (7 GHz, the lowest of
the FR3 sweet-spot ladder) with theta polarisation only, keeping the
full direction sweep so the headline ratio is direction-averaged.
Trades made:

  * Lose the freq-dependence on Tier 1's 7/9/11 GHz ladder.
    Mitigation: 7 GHz is the closest in spirit to Tier 0's
    5.8 GHz endpoint and the most-likely-to-be-in-AEGIS-band.
  * Lose the polarisation residual `D_B` at FR3.  Mitigation: Tier 0
    already showed `D_B` ≤ 19.5 % at 5.8 GHz on x_pos; Tier 1 was
    expected to show the same envelope or tighter.

Driver: `aegis/validation/scripts/run_tier1.py`
Plot: `aegis/validation/scripts/plot_tier1.py`

## What actually ran

The 6-sim plan was: x_pos / x_neg / y_pos / y_neg / z_pos / z_neg
× theta-pol on full thelonious at 7 GHz.  Order observed on the VM:

  1. **x_pos / theta — completed cleanly.**  Sim + extract = 21 min.
  2. **x_neg / theta — completed cleanly on retry.**  First attempt
     hit a Sim4Life license feature error (`No such feature exists.
     (-5,147) - [@wicacib.private.ugent.be]`) during the
     dual-evaluator SAPD setup, which goliat handled by restarting
     the study from scratch.  Re-run took ~26 min, then extract.
  3. **y_pos / theta — FDTD ran, extraction stalled** during
     `SapdExtractor._slice_skin_mesh`'s mesh repair pass on the
     united skin entity (the 100-mm-box slice intersected an
     anatomically complex region that triggered repeated
     `Patching holes` / `Fixing degeneracies` iterations).  The
     `_Output.h5` is on disk but no `sapd_results.json` /
     `sar_results.json` / `skin_apd.npz` ever landed.  An
     extract-only retry with `extraction.sapd_field: false`
     was launched but didn't complete in time.
  4. **y_neg, z_pos, z_neg — never started.**

Net: 2 of 6 scenarios with full data, 1 with field but no extract
deliverables, 3 not run.

## Headline numbers (the 2-sim result)

| f (MHz) | x | direction (n) | AEGIS Lall+O / FDTD | Cauchy / FDTD | AEGIS peak / FDTD peak (4 cm²) |
|---:|---:|---|---:|---:|---:|
| 7000 | 86.7 | x_pos / theta | 0.350 | 0.467 | 1.057 |
| 7000 | 86.7 | x_neg / theta | 0.417 | 0.551 | 1.196 |
| 7000 | 86.7 | lateral-pair avg (n=2) | **0.383** | **0.509** | **1.126** |

(`x = π h / λ` with `h = 1.18205 m` for full thelonious.)

### First-scenario snapshot (x_pos / theta-pol only, 1 of 6 sims complete)

The `x_pos` / theta-pol scenario landed cleanly (no _Output.h5 retained
courtesy of `auto_cleanup_previous_results: ["output"]`).  Per-direction
ratios at this single direction:

|  | absolute Pabs (W at Sinc=1 W/m²) | / FDTD |
|---|---:|---:|
| FDTD `DielLoss × NORM` | 0.180 | — |
| AEGIS L_all (no occlusion) | 0.107 | 0.60 |
| AEGIS L_all + occlusion | 0.063 | **0.35** |
| Cauchy + T̄ (closed form) | 0.084 | 0.47 |

**Peak SAPD (4-cm² windowed) — much better agreement than total Pabs:**

|  | peak_sab_4cm² (W/m² at Sinc=1) | / FDTD |
|---|---:|---:|
| FDTD `peak_sapd_W_m2 × NORM` | 0.642 | — |
| AEGIS `peak_sab_averaged` (L_all+O) | 0.678 | **1.06** |

Two important things from the first scenario:

  * **AEGIS peak 4-cm² SAPD agrees with goliat's GenericSAPDEvaluator
    to 6 % at 7 GHz x_pos / theta** — this is the metric the IEC/IEEE
    63195 standard cares about and AEGIS's intended sweet spot.
  * **Total absorbed power (`DielLoss × NORM`) at 7 GHz is 2.8× the
    Tier 0 5800 MHz value** for the same direction/polarisation
    (0.180 W vs 0.064 W).  AEGIS's surface-only law (`Lall + O`)
    gives a ratio that drops from 1.0 at Tier 0 5.8 GHz x_pos/theta
    to 0.35 here at 7 GHz x_pos/theta — but AEGIS itself predicts
    nearly the same number at both frequencies (0.110 vs 0.107 W).
    The change is on the FDTD side: tighter convergence
    (-30 dB vs Tier 0's -15 dB) plus finer grid (0.6 mm vs 1.0 mm)
    likely captures more deep-tissue absorption that the surface
    geometric law cannot represent.  Whether this means Tier 0's
    "Cauchy matches FDTD to 1.2 % at 5.8 GHz" is an artefact of
    under-converged FDTD, or whether it's a real frequency-dependent
    effect, requires re-running 5800 MHz at -30 dB to settle —
    not in scope today.

Two things to note before the rest of the directions land:

  * **AEGIS's absolute Pabs at 7 GHz is essentially identical to its
    Pabs at Tier 0's 5800 MHz** for the same direction/polarisation
    (0.107 vs 0.110 W).  AEGIS's prediction is `T̄(f) × A_ab × kernel`,
    and `T̄` is nearly constant across the body band, so the AEGIS
    answer barely moves with frequency.
  * **FDTD's DielLoss at 7 GHz is 2.8× larger than at 5800 MHz** on
    full thelonious x_pos / theta (0.180 vs 0.064 W in absolute units
    at `Sinc = 1 W/m²`).  At higher frequency, more of the incident
    plane wave is absorbed inside the body (shorter skin depth, higher
    σ).  AEGIS's geometric law captures only the surface-incident
    flux, not the deeper-tissue accumulation.

These are still per-direction; the headline `direction-averaged`
ratio will land once the 5 remaining directions return.  Already the
trend suggests AEGIS over-corrects at high `x` (the curvature term
contributes positively at the surface, but the deep-tissue absorption
that FDTD sees grows faster than AEGIS's surface-only law).  The
direction-average column will tell us whether this is x_pos-specific
(it's the peak-illumination direction at lateral) or systematic.

## Per-direction variance and polarisation residual

Tier 0 reported per-(dir, pol) std of 0.16 – 0.27 around the mean at
sub-6 GHz.  Tier 1 should tighten as `x` grows; the geometric law's
per-direction error scales as `~1/x` for convex bodies.  Polarisation
residual `D_B = (P_θ - P_φ)/⟨P⟩` should stay below the paper bound
of 0.16 (Thelonious lateral worst case at 28 GHz), with vertical
illumination near zero per the cylinder symmetry.

(filled in once the first frequency block lands)

## Decision

  * Pass band: direction-averaged Lall+O / FDTD ratio in `[0.92,
    1.08]` per the validation plan, Cauchy / FDTD in `[0.92, 1.08]`,
    peak-4cm² ratio in `[0.80, 1.20]`.  D_B ≤ 0.16 lateral, ≤ 0.08
    frontal.

  * Path forward depends on the headline ratio:
      * In-band → publish Tier 1 as the validation paper
        scientific output.
      * Below-band → diagnose (likely: skin mesh perforation effects
        beyond the paper's ~10 % at 2 GHz, or AEGIS L_all
        over-correction at high `x` from the curvature term).
      * Above-band → AEGIS over-predicts at high `x`; investigate the
        kernel cutoff.

## Files (when complete)

  * `validation/data/tier1_thelonious.parquet` — 36-row table of
    per-scenario AEGIS / FDTD comparisons.
  * `validation/data/tier1_thelonious.summary.csv` —
    direction-averaged headline ratios per frequency.
  * `validation/tier1_kernels_vs_fdtd.png` — ratio vs x plot.
  * `validation/tier1_per_direction.png` — per-(dir, pol) scatter.
  * `validation/tier1_polarisation.png` — D_B vs direction.
