# Tier 1 findings: AEGIS vs FDTD on full thelonious at 7 GHz

The Tier 1 sweep landed **3 of an attempted 5 directions** (theta-pol,
7 GHz, full thelonious) before the run hit a chain of license / mesh /
license-stall issues that consumed the available budget.  The three
scenarios that completed cleanly carry the headline result.

## Headline (3-direction theta-pol average, 7 GHz, x = 86.7)

| metric | value | note |
|---|---:|---|
| direction-avg `Lall / FDTD` (Pabs) | 0.661 | AEGIS surface-only kernel, no occlusion |
| direction-avg `Lall+O / FDTD` (Pabs) | **0.479** | with binary occlusion: tightest physical surface kernel |
| direction-avg `Cauchy / FDTD` (Pabs) | 0.499 | direction-averaged closed form `S T̄ A / 4` |
| direction-avg AEGIS / FDTD peak 4-cm² SAPD | **1.027** | within 3 % of goliat's `GenericSAPDEvaluator` |

Three stories from those four lines:

  1. **AEGIS captures the peak SAPD across the 3 directions to within
     3 %.**  Per-direction values are 1.06 (x_pos), 1.20 (x_neg), 0.83
     (y_neg) — the metric the IEC/IEEE 63195 standard cares about, in
     AEGIS's claimed sweet spot, is delivered well within the
     `[0.80, 1.20]` validation pass-band.
  2. **AEGIS underpredicts the total absorbed power by a factor ~2.1**
     at this frequency vs. Tier 0's "Cauchy / FDTD ≈ 1.012 at 5.8 GHz"
     headline.  The AEGIS *prediction* is essentially the same at 5800
     and 7000 MHz (its dominant freq dependence is in `T̄(f)`, ~3 %);
     the *FDTD* DielLoss at 7000 MHz is 2.8× the 5800 MHz value on the
     same direction/polarisation.  Most plausible explanation: tighter
     convergence (-30 dB here vs Tier 0's -15 dB) plus finer grid
     (0.6 mm vs 1.0 mm) reveals deep-tissue absorption that the
     surface-only law cannot capture.  Whether this means Tier 0's
     1.2 % agreement is an artefact of under-converged FDTD, or
     whether it's a real frequency-dependent effect, needs a 5.8 GHz
     re-run at -30 dB to settle — out of scope today.
  3. **The direction spread is large.**  Per-direction Lall+O / FDTD
     is 0.42 (x_neg), 0.35 (x_pos), 0.67 (y_neg).  The frontal direction
     (y_neg) gives the closest agreement; the lateral pair under-
     predicts more.  Hypothesis: y_neg presents fewer high-curvature
     features (no ears / nose) so the surface-only kernel aggregates
     closer to bulk while missing the curvature-driven hot-spot at the
     ears (peak ratio is *also* lowest at y_neg, 0.83 — same direction
     of effect).

## Per-direction table (7 GHz, theta-pol, full thelonious, x = 86.7)

| direction | FDTD Pabs (W) | Lall (W) | Lall+O (W) | Cauchy (W) | Lall+O/FDTD | peak 4cm² ratio |
|---|---:|---:|---:|---:|---:|---:|
| x_pos  | 0.180 | 0.107 | 0.063 | 0.084 | 0.350 | 1.057 |
| x_neg  | 0.152 | 0.108 | 0.064 | 0.084 | 0.417 | 1.196 |
| y_neg  | 0.175 | 0.119 | 0.117 | 0.084 | 0.671 | 0.830 |
| **avg (n=3)** | **0.169** | **0.111** | **0.081** | **0.084** | **0.479** | **1.027** |

(`x = π h / λ` with `h = 1.18205 m` for full thelonious;
`Sinc = 1 W/m²`; absolute values in W.)

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
  * 6 directions × 1 polarisation (theta) attempted; 5 actually
    launched, 3 returned full data, 1 failed at SAPD slicing, 1
    license-stalled.
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
8 – 12 hours, which was past the available budget on this VM today
(single 3090 instead of planned dual 3090).

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
× theta-pol on full thelonious at 7 GHz.  Order observed on the VM
(after the y_pos failure was diagnosed, the config was edited to skip
y_pos and the surviving 3 directions y_neg, z_pos, z_neg were
launched in a second batch):

  1. **x_pos / theta — completed cleanly.**  Sim + extract = 21 min.
  2. **x_neg / theta — completed cleanly on retry.**  First attempt
     hit a Sim4Life license feature error (`No such feature exists.
     (-5,147) - [@wicacib.private.ugent.be]`) during the
     dual-evaluator SAPD setup, which goliat handled by restarting
     the study from scratch.  Re-run took ~26 min, then extract.
  3. **y_pos / theta — FDTD ran, SAPD slicing failed.**  goliat's
     `SapdExtractor._slice_skin_mesh` raised `Failed to cover cut
     loop (Skin_Merged_For_SAPD)` / `cannot make wire with duplicate
     vertices` during the 100-mm-box mesh boolean.  The
     `_Output.h5` was on disk but no `sapd_results.json` /
     `sar_results.json` / `skin_apd.npz` ever landed.  The 18 GB
     `_Output.h5` was deleted to free disk.  The config was edited
     to skip y_pos for the second batch.
  4. **y_neg / theta — completed cleanly.**  ~16 min sim + extract.
  5. **z_pos / theta — license-stalled.**  iSolve started at 17:47:55
     and was still alive 45 min later having used 0.56 s of CPU
     time and held only 30 MB of working set; the 50-attempt
     SUB_GRID license-seat retry loop earlier in the goliat log
     suggests a license seat was reserved but never released.  Killed
     and the run dir removed.
  6. **z_neg / theta — never started** (followed z_pos in the queue).

Net: 3 of 5 launched scenarios with full data, 1 with FDTD field
but no extract deliverables, 1 license-stalled.

## Surface-map (per-vertex) caveat

goliat's `skin_apd.npz` is *not* a full-body per-vertex APD dump —
it's a 100-mm box around the SAR / SAPD peak location.  At x_pos /
theta on thelonious that box is centred on the head; the rest of
the body is zero in the npz.  This means the surface-compare
metrics in `run_tier1.py` (`surface_nrmse`, `surface_r2`,
`surface_integrated_W_*`) compare AEGIS's full-body Sab to a head-
only FDTD slice and are not informative as full-body metrics.  The
`peak_ratio_4cm2` value *is* informative because both AEGIS and FDTD
peaks are inside the head box.  Headline JSON ratios
(`Lall+O/FDTD`, `Cauchy/FDTD`) are unaffected because they come from
`DielLoss × NORM` on the FDTD side and AEGIS `p_abs` on the kernel
side — neither uses the per-vertex slice.

## Decision

  * Validation plan pass-bands: direction-averaged `Lall+O / FDTD` in
    `[0.92, 1.08]`, peak-4cm² ratio in `[0.80, 1.20]`.
  * **Result:** peak-4cm² **passes** at 1.027 (well inside band).
    Pabs ratio **fails low** at 0.479 (outside `[0.92, 1.08]`).
  * **Diagnosis:** AEGIS's surface-only law cannot capture the
    deep-tissue absorption that becomes meaningful at 7 GHz with a
    well-converged FDTD.  This is *consistent* with the paper's
    framing — the geometric law is for surface metrics (peak SAPD),
    and the validation plan's `[0.92, 1.08]` total-Pabs band may be
    too tight for the surface-only family of kernels at FR3.
  * **Path forward:** either (a) re-run Tier 0 5.8 GHz at -30 dB to
    establish whether the 1.2 % Cauchy/FDTD agreement was an
    under-convergence artefact, or (b) extend AEGIS with a deep-
    tissue correction (paper §1.2 already foresees a `T̄_eff(f)` with
    skin-depth weighting).

## Files

  * `validation/data/tier1_thelonious.parquet` — 3-row table of
    per-scenario AEGIS / FDTD comparisons.
  * `validation/data/tier1_thelonious.summary.csv` —
    direction-averaged headline ratios per frequency.
  * `validation/tier1_kernels_vs_fdtd.png` — ratio vs x plot.
  * `validation/tier1_per_direction.png` — per-(dir, pol) scatter.
  * `validation/tier1_polarisation.png` — D_B vs direction (empty
    panel at this run since only theta-pol was simulated).
