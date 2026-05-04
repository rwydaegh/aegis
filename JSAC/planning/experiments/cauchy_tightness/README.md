# Cauchy operator-bound tightness (paper §II Theorem 2)

This experiment measures the empirical tightness of the rank-1 Cauchy bound

```
x^H Q^(u) x  <=  T_0 * (A_ab^(u)/4) * D_max^(u) * |a_BS^(u)^H x|^2
```

(paper `paper_v2.tex` eq. `cauchy-bound-op`, restated as Theorem 2 in §II).
This is the **pose-agnostic safety net** the paper invokes for tier-C/D
bystanders -- the bodies the BS does not have pose telemetry on. The
paper writes the bound as if it holds "for any precoder x", but never
shows how *tight* it is in practice. This experiment fills that gap.

## TL;DR

The rank-1 Cauchy bound, **as written in the paper**, is empirically
*not* a universal upper bound on `x^H Q x`. The structural reason: Q's
principal eigenvector in C^M is rarely aligned with `a` (the LOS array
steering vector). Even at MRT-toward-LOS the bound holds with
~9-32 dB of *slack* (not tightness), because the body absorbs power
along directions in C^M that are mostly orthogonal to `a`. And for
any precoder with `|a^H x|^2 -> 0` (e.g. ZF avoiding the body, or any
x in the null space of `a^H`), `x^H Q x` stays positive while the
bound's RHS goes to zero -- the ratio is unbounded above.

Empirically (Thelonious + Duke, 6 positions each, 26 GHz, 8x8 UPA,
10 W, plaza-specular and 3GPP UMa-LOS):

- **MRT-to-LOS** (`x ~ a/||a||`, the supposed rank-1 saturator): bound
  holds with **median 21-27 dB slack**, never violated -- but slack
  varies 9-32 dB across positions because `a` only intermittently
  overlaps Q's principal direction. Empirically `|<v_top, a/||a||>|^2`
  ranges 0.000 to 0.19 across our 24 (body, position, channel) jobs.
- **Isotropic random / MRT random user / ECBF / ZF**: bound is
  violated for ~50-70% of precoders, by a median of 0-6 dB and by
  20-30 dB at p90, with maxima up to 99 dB.

**Implication for the paper.** Theorem 2's "for any precoder x" claim
does not hold empirically when Q has rank > 1 (the regime that
actually matters; cf. `fig:rank-cdf` showing dominant rank 3-4 at
`epsilon=10^-2`). The clean fixes are:

1. **Restate**: bound the absorbed power *for the worst bystander
   direction at fixed x*, not for any x at fixed bystander direction.
   Specifically: `x^H Q x <= T_0 (A_ab/4) D_max sup_{a in
   A_admissible} |a^H x|^2`. Tractable, matches the way the bound is
   physically invoked, and the monograph's appendix proof actually
   proves this stronger statement.
2. **Or augment**: add a path-aggregate floor that does not vanish
   with `|a^H x|^2`, e.g. `T_0 (A_ab/4) sum_paths D_max(k_path)
   |a_path^H x|^2 / Ptx`, which is just the per-path Cauchy bound
   summed over the dominant paths.

The current §II claim of pose-agnostic protection for tier-C/D
bystanders does **not** follow from Theorem 2 as written. The
correction is straightforward and does not break the paper's narrative
-- the multi-body ECBF in §IV does not actually rely on the "for any
x" form, only on the per-bystander-direction form.

Scope notes: brief asked for a single rank-1 tightness CDF on
Thelonious; we deliver a 5-ensemble CDF on Thelonious + Duke across
plaza-specular and 3GPP UMa-LOS. Eartha + Ella deferred due to host
RAM (8 GB shared); rerun with `CAUCHY_TIGHTNESS_FULL=1` on a beefier
host. All findings are robust to phantom choice (Thelonious and Duke
agree to within ~2 dB at every percentile and ensemble).

## What this is

A figure + numerical sweep that answers: **for the precoders the BS
would actually use, how loose is the rank-1 Cauchy ceiling on
`x^H Q x`?**

The rank-1 ceiling is what tier-C/D bystanders force the precoder to
respect (they can't be modelled with a real Q, only with the
pose-agnostic bound). If the ceiling is loose by 6 dB on average,
every tier-C bystander costs the precoder ~6 dB of `|a^H x|^2`
capacity -- a real and acknowledgeable tax. If it's tight to ~1 dB,
the safety net is essentially free.

## What we measure

For each (phantom, body position, channel model, precoder ensemble):

```
LHS = x^H Q x                                    [W per unit ||x||^2]
RHS = T_0 * (A_ab/4) * D_max * |a^H x|^2 / (2 Z_0)   [W per unit ||x||^2]
ratio_dB = 10 log10(LHS / RHS)
```

Bound holds iff `ratio_dB <= 0`. `ratio_dB > 0` means **bound is
violated** -- the precoder absorbs *more* than the rank-1 Cauchy
ceiling permits. We plot the empirical CDF of `ratio_dB` per ensemble.

Dimensional convention: `a` is the LOS path's E-field amplitude vector
at the array,

```
a[m] = (psi_1m / r_body) * gain(k_LOS) * exp(j k0 k_LOS . d_m)
psi_1m = sqrt(2 Z_0 P_tx / (4 pi))  [V/m at 1 m on free-space LOS]
```

so `|a^H x|^2 / (2 Z_0)` is in W/m^2 (LOS-aligned power flux at the
body for unit precoder), times `A_ab/4 (m^2)` gives Watts, matching
`x^H Q x`. This convention makes the bound dimensionally consistent
without absorbing any constants into `a`.

## Setup

- 26 GHz, 8x8 UPA half-wavelength, 10 deg down-tilt, 10 W tx.
- Skin tissue at 26 GHz (eps_r ~ 17, sigma ~ 25 S/m), `T_0` from
  `aegis.tissue.dielectric.TissueModel.T0` (normal-incidence
  transmission coefficient).
- Bodies stand on the ground; positions sampled uniformly in `r^2`
  over 20-80 m, +/- 60 deg azimuth (matching `rank_check/`).
- Two channel models per body, matching `rank_check/`:
  - **plaza specular**: LOS + ground bounce + 2 facade bounces.
    Reflection coefficients 0.55 (ground) and 0.35 (facades).
  - **3GPP UMa-LOS**: 12 clusters x 5 subpaths = 60 stochastic
    paths, drawn from preset `3GPP_38.901_UMa_LOS`.
- Per-body geometry constants: `(A_ab/4) = mean(A_perp(k))` and
  `D_max = max(A_perp(k)) / mean(A_perp(k))` from a Fibonacci-sphere
  sample of 256 directions over `S^2`.
- Precoder ensembles (all unit-norm):
  - **iso_random**: Gaussian unit vectors, the fully-uninformed
    baseline. 200 samples per body x channel.
  - **mrt_random**: MRT toward a random user direction in the front
    hemisphere of the array. 60 samples.
  - **mrt_los**: precoder matched to the body's LOS array steering
    direction (`x = a/||a||`). The rank-1 RHS is maximised at this `x`
    (Cauchy-Schwarz), so it is the bound's *RHS-saturating* direction;
    as the results show, it is rarely a Q-eigenvector, so the bound
    holds with significant slack here. 1 sample (deterministic).
  - **ecbf**: ECBF QCQP outputs against a random user channel with
    swept `P_abs_max` budgets (5-80% of `lambda_max(Q)`). 30 samples.
  - **zf_2user**: Two-user ZF among real users (the body is *not* in
    the user list -- it is a tier-C bystander, by definition unknown
    to the BS). 60 samples.

## How to reproduce

```bash
cd /home/user/aegis
.venv/bin/python JSAC/planning/experiments/cauchy_tightness/run_tightness.py
# ~5-10 minutes on a 4-core/8 GB host with 1 worker
```

Override `CAUCHY_TIGHTNESS_WORKERS=N` for parallelism, and
`CAUCHY_TIGHTNESS_FULL=1` to add Eartha + Ella for full demographic
spread (recommend >=16 GB RAM).

Outputs:

- `tightness.{pdf,png}` -- two-panel CDF (specular | stochastic).
- `ratios.npz` -- raw `ratio_db` arrays per (channel, ensemble) plus
  `lambda_max(Q)` and `||a||^2` per body x channel.
- `summary.json` -- median, p10, p90, max per ensemble x channel x
  body. Bound-violation fraction (`ratio_dB > 0`).
- This README.

## Results

(filled in by `_finalise_readme()` after the run; see
`summary.json` for the live numbers).

<!-- BEGIN AUTO-RESULTS -->

**Per-body geometry constants** (`A_ab/4 = mean(A_perp)`, `D_max = max(A_perp) / mean(A_perp)`, from 256 Fibonacci directions):

| phantom | total area (m^2) | A_ab/4 (m^2) | D_max |
|---|---|---|---|
| thelonious | 0.787 | 0.1966 | 1.219 |
| duke | 1.872 | 0.4681 | 1.249 |

**Tissue constants:** Skin at 26 GHz, `eps_r = 17.71`, `sigma = 24.41` S/m, `T_0 = 0.5302` (normal-incidence transmission).

**Bound tightness (10 log10(LHS/RHS) in dB; positive means bound violated, i.e. the actual `x^H Q x` exceeds the rank-1 Cauchy ceiling).**

_Plaza specular (LOS + ground + 2 facades)_

| ensemble | n | median dB | p10 dB | p90 dB | max dB | fraction > 0 dB |
|---|---|---|---|---|---|---|
| isotropic random (Gaussian) | 2400 | +2.86 | -4.06 | +11.55 | +49.24 | 68% |
| MRT to random user direction | 720 | +6.09 | -11.74 | +28.15 | +78.95 | 66% |
| x = a (matched to body LOS direction) | 12 | -21.41 | -23.08 | -9.68 | -8.84 | 0% |
| ECBF (random user, swept budget) | 360 | +6.34 | -8.61 | +25.48 | +83.59 | 70% |
| ZF among 2 random users (body unknown) | 720 | +5.48 | -11.07 | +25.82 | +77.18 | 68% |

_3GPP UMa-LOS (12 clusters x 5 subpaths)_

| ensemble | n | median dB | p10 dB | p90 dB | max dB | fraction > 0 dB |
|---|---|---|---|---|---|---|
| isotropic random (Gaussian) | 2400 | -0.20 | -8.79 | +9.41 | +37.58 | 49% |
| MRT to random user direction | 720 | +2.32 | -13.26 | +22.91 | +72.96 | 56% |
| x = a (matched to body LOS direction) | 12 | -27.15 | -32.64 | -9.80 | -8.62 | 0% |
| ECBF (random user, swept budget) | 360 | +1.23 | -15.78 | +22.36 | +61.47 | 54% |
| ZF among 2 random users (body unknown) | 720 | +1.57 | -15.80 | +21.83 | +99.10 | 55% |

**Key empirical findings.** The bound holds (negative dB) only for precoders concentrated near the body's LOS direction. For all other ensembles the bound is violated, often by tens of dB. The median violation depends strongly on multipath richness (plaza specular vs 3GPP UMa-LOS with 60 subpaths). See `tightness.{pdf,png}` for the CDFs.

<!-- END AUTO-RESULTS -->

## Discussion: what the tax is

For tier-A/B users (the BS knows their position and can compute their
real Q), the precoder solves the multi-body QCQP with the actual `Q`s.
There is no rank-1 substitution and no tax.

For tier-C/D bystanders, the BS has no `Q`, only the pose-agnostic
bound. It must therefore impose `|a^H x|^2 <= P_abs_max / (T_0
(A_ab/4) D_max / (2 Z_0))` for every plausible bystander direction
`a`. If the bound were tight at 0 dB, this would equal the actual
`x^H Q x` ceiling and there would be no extra tax. The empirical
finding shows that for any bystander direction *not aligned with the
precoder's main lobe*, the bound is grossly under-conservative,
meaning the bound *does not actually protect* such bystanders.

A safe pose-agnostic constraint would have to bound `x^H Q x` by a
quantity that does *not* vanish when `|a^H x|^2 -> 0`. Two natural
candidates:

1. **`|a^H x|^2 + sigma_multipath^2 ||x||^2`**: add a path-aggregate
   floor proportional to total transmit power. This would make the
   bound conservative across all precoders at the cost of
   `sigma_multipath^2` of slack on every served-user beam.
2. **`max over a in A_admissible of T_0 (A_ab/4) D_max |a^H x|^2`**:
   take the worst-case bystander direction and bound `x^H Q x` by the
   rank-1 ceiling at *that* direction. Tractable; this is what the
   monograph's appendix proof actually proves, and matches the way
   the bound is invoked physically.

The brief asked us to flag findings of unexpected looseness or
tightness; option (2) above resolves the looseness honestly without
breaking the paper's narrative, and is what we recommend brief'ing
the paper authors with.

## What this is NOT

- A theorem-disproving exercise. The bound's *correct* statement
  (over the worst bystander direction at fixed `x`) does hold. The
  point is that the *as-written* statement "for any precoder x" does
  not.
- A figure for §III's rank-CDF. That's already done in `rank_check/`.
- A multi-body study. Theorem 2 is per-body.
- A new theory contribution. The fix to the paper statement is
  one-line; this experiment just exposes the need for it.
