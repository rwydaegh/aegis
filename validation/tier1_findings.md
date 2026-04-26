# Tier 1 findings: AEGIS vs FDTD on full thelonious at 7/9/11 GHz (in progress)

This is a draft.  The 36-sim Tier 1 sweep is launched and running on
the upgraded TD VM.  Numbers are filled in as each frequency block
completes.  Final write-up will replace placeholders.

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
  * Frequencies: 7000, 9000, 11000 MHz.
  * 6 directions × 2 polarisations = 12 incident scenarios per f.
  * Convergence target -30 dB.  `auto_induced.enabled: false`.

Driver: `aegis/validation/scripts/run_tier1.py`
Plot: `aegis/validation/scripts/plot_tier1.py`

## Headline numbers

(filled in incrementally — see `tier1_thelonious.parquet` for raw
table)

| f (MHz) | x | direction-avg AEGIS L_all+O / FDTD | direction-avg Cauchy / FDTD | n=12 std |
|---:|---:|---:|---:|---:|
| 7000 | 86.7 | TBD | TBD | TBD |
| 9000 | 111.4 | TBD | TBD | TBD |
| 11000 | 136.2 | TBD | TBD | TBD |

(`x = π h / λ` with `h = 1.18205 m` for full thelonious.)

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
