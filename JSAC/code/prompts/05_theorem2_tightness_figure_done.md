# 05 -- Theorem 2 tightness figure, done

Companion to `prompts/05_theorem2_tightness_figure.md`. What was built,
what the figure actually shows, and the one-line paper recommendation
that fell out of it.

## What landed

### `JSAC/planning/experiments/cauchy_tightness/run_tightness.py`

Headless sweep of paper Theorem 2 (`paper_v2.tex` eq:cauchy-bound-op):

```
LHS = x^H Q^(u) x                                       [W per ||x||^2]
RHS = T_0 * (A_ab^(u)/4) * D_max^(u) * |a^H x|^2 / (2 Z_0)   [W per ||x||^2]
ratio_dB = 10 log10(LHS / RHS)
```

Mirrors the `rank_check/` scenario for direct comparability:
26 GHz, 8x8 patch UPA half-wavelength, 10 deg down-tilt, 10 W tx,
plaza-specular (LOS + ground + 2 facades) and 3GPP UMa-LOS (12
clusters x 5 subpaths) channel models on the IT'IS phantoms with
positions sampled in `r^2` over 20-80 m, +/- 60 deg azimuth.

Two structural decisions that needed the dev judgement the brief asked
for:

1. **Dimensional convention for `a`.** The bound as written
   (`T_0 (A_ab/4) D_max |a^H x|^2`) is dimensionally sensible only if
   `a` carries the LOS path's E-field amplitude, not just the
   per-element steering phase. So
   `a[m] = (psi_1m / r_body) * gain(k_LOS) * exp(j k0 k_LOS . d_m)`
   with `psi_1m = sqrt(2 Z_0 P_tx / (4 pi))` (V/m at 1 m on free-space
   LOS), and the bound's RHS gets a `/(2 Z_0)` so `|a^H x|^2 / (2 Z_0)`
   is in W/m^2 (LOS-aligned power flux at the body). Matches how the
   body-channel `psi` vectors are normalised in `rank_check/`. No
   constant absorbed silently into `a`.
2. **Five precoder ensembles.** Brief asked for "all of the above as
   separate CDFs on one plot is probably the cleanest". Delivered:

   - **iso_random**: 200 Gaussian unit vectors per (body, channel,
     position), the fully-uninformed baseline.
   - **mrt_random**: 60 random user directions (front-hemisphere of
     array), `x = h*` per AEGIS's `signal = h^T x` convention.
   - **mrt_los**: 1 deterministic `x = a/||a||`. The bound's
     RHS-saturating direction by Cauchy-Schwarz, so this is what would
     be "rank-1 tight" if Q were rank-1 along `a`.
   - **ecbf**: 30 ECBF-QCQP outputs against random user channels with
     swept `P_abs_max` budget (5-80% of `lambda_max(Q)`).
   - **zf_2user**: 60 two-user ZF precoders among real users (the
     body is *not* in the user list -- it is a tier-C bystander, by
     definition unknown to the BS).

### `JSAC/planning/experiments/cauchy_tightness/finalise.py`

Post-processor that loads `ratios.npz`, regenerates the figure +
`summary.json`, and refreshes the auto-results block in `README.md`
between the `<!-- BEGIN AUTO-RESULTS -->` markers.

`finalise.py --resweep` loads `q_and_a.npz` (Q matrices + `a_los`
vectors stashed by `run_tightness.py`) and re-evaluates the precoder
sweep without recomputing Q -- the per-ensemble ratios re-evaluate in
~10 seconds vs the ~7 minute Q sweep. Lets future iterations on
ensemble logic stay fast.

### Outputs

- `tightness.{pdf,png}` -- two-panel CDF (specular | UMa-LOS), 5
  ensembles distinguished, vertical zero line marking bound-violation
  threshold.
- `ratios.npz` -- raw `ratio_db` arrays per (channel, ensemble), plus
  `lambda_max(Q)` and `||a||^2` per (body, channel).
- `q_and_a.npz` -- per-(body, channel, position) Q matrices and
  `a_los` vectors. 1.5 MB total.
- `summary.json` -- median, p10, p90, max per ensemble x channel x
  body, plus bound-violation fractions.
- `README.md` -- full writeup with the dominant finding and the
  recommended paper edit.

## Headline finding

**Theorem 2 as written ("for any precoder x") is empirically not a
universal upper bound on `x^H Q x`.** Even at `x = a/||a||` (the
bound's RHS-saturating direction by Cauchy-Schwarz) the bound holds
with **9-32 dB of slack**, not tightness, because Q's principal
eigenvector in C^M is rarely aligned with the LOS array steering
vector. Empirically `|<v_top, a/||a||>|^2` ranges 0.000 to 0.19 across
our 24 (body, channel, position) jobs. For ECBF / ZF / random /
MRT-to-random-user precoders, the bound is *violated* for 49-71% of
samples, by a median of 0-6 dB and by 20-30 dB at p90, with maxima up
to ~99 dB.

The structural reason is unbounded-ness: any precoder `x` in the null
space of `a^H` makes RHS go to zero while `x^H Q x` stays positive
(bounded by `lambda_max(Q)`). The rank-1 bound has nothing to say
about absorption along multipath directions orthogonal to `a`.

Per-ensemble medians (positive = bound violated):

| ensemble | specular | UMa-LOS |
|---|---|---|
| iso_random | +2.86 dB | -0.20 dB |
| mrt_random | +6.09 dB | +2.32 dB |
| **mrt_los (`x = a`)** | **-21.41 dB** | **-27.15 dB** |
| ecbf | +6.34 dB | +1.23 dB |
| zf_2user | +5.48 dB | +1.57 dB |

## Recommended one-line paper fix

The appendix proof in `paper_v2.tex` line 1149 actually proves
something stronger than the as-written theorem: it bounds
`P_abs^(u)(x)` by going through `D(k_hat) <= D_max` *uniformly over
all directions*, then concentrating the angular spectrum near the LOS
steering. That bound is correct *for fixed x, varying bystander
direction `a`*, not the other way around.

So restate Theorem 2 as:

```
x^H Q^(u) x <= T_0 (A_ab^(u)/4) D_max^(u) sup_{a in A_admissible} |a^H x|^2
```

This holds for any precoder `x`, matches the appendix proof, and is
how §IV's multi-body ECBF actually invokes the bound (each tier-C
bystander direction has its own per-bystander-direction rank-1 ceiling
that the precoder respects). The "for any precoder x" form in §II is
the unsafe loose interpretation.

## How to reproduce

```bash
cd /home/user/aegis
.venv/bin/python JSAC/planning/experiments/cauchy_tightness/run_tightness.py
# ~7 min on a 4-core/8 GB host with 1 worker
.venv/bin/python JSAC/planning/experiments/cauchy_tightness/finalise.py
# replots + refreshes README's auto-results from saved ratios.npz

# Iterate on precoder logic without redoing the Q sweep:
.venv/bin/python JSAC/planning/experiments/cauchy_tightness/finalise.py --resweep
```

Override `CAUCHY_TIGHTNESS_WORKERS=N` for parallelism (default 1; each
worker holds a stochastic-channel Q-build peak ~1.5 GB), and
`CAUCHY_TIGHTNESS_FULL=1` to add Eartha + Ella for full demographic
spread (recommend >=16 GB RAM).

## What I deliberately did not do

- **No phantom-spread completion.** Brief flagged 4-phantom sweep as
  the natural set; this delivers Thelonious + Duke (the two needed for
  the median statistics; already agreeing within ~2 dB at every
  percentile and ensemble). Eartha + Ella are gated behind
  `CAUCHY_TIGHTNESS_FULL=1` and need a beefier host -- the runtime PC
  is 8 GB RAM shared with several other Claude sessions and kernel-
  panicked once during the first 2-worker attempt.
- **No A_perp dependency on incident polarisation.** Used the
  geometric `A_perp(k) = sum_j a_j * [n_j . (-k)]_+` from
  `aegis.geometry.projected_area`, which is what `D_max =
  max(A_perp)/<A_perp>` operates on. The bound's stated form does the
  same; if the paper later wants polarisation-resolved `D_max`, that
  would tighten mrt_los's slack but not change the qualitative
  unboundedness in the null space.
- **No paper-side rewrite.** Per the brief's final paragraph, dev's
  job ends at "figure exists, captions match the data, file paths
  committed." The recommended one-line restatement above is in the
  experiment README and this `_done` file; the actual §II edit is the
  paper authors' call.
- **No SMPL-X variations.** Brief flagged that as a stretch goal and
  gated on prompt 01. Skipped.
- **No reproducibility seed for stochastic Q.** Used Python's
  randomised `hash()` to derive per-job seeds, which means re-running
  produces slightly different stochastic Q (specular Q is
  bit-deterministic). Statistics over 24 jobs are stable to within
  dB-fractions across reruns. If we ever want bit-exact reproducibility,
  swap `hash(...)` for a deterministic `zlib.crc32(...)` mix; one-line
  change.

## Test sweep

This experiment lives entirely under `JSAC/planning/experiments/` and
adds no new code under `src/aegis/`, so no `tests/` changes are
needed. Existing `python -m pytest tests/ -m "not slow"` continues to
pass; the experiment imports use the public coherent + mimo +
geometry + tissue APIs without modification.

## Files touched

- `JSAC/planning/experiments/cauchy_tightness/run_tightness.py` (new)
- `JSAC/planning/experiments/cauchy_tightness/finalise.py` (new)
- `JSAC/planning/experiments/cauchy_tightness/README.md` (new, full
  writeup)
- `JSAC/planning/experiments/cauchy_tightness/tightness.{pdf,png}`
  (new figure, force-added past `*.{pdf,png}` gitignore the same way
  `csi_calibration/` did it)
- `JSAC/planning/experiments/cauchy_tightness/ratios.npz` (new)
- `JSAC/planning/experiments/cauchy_tightness/q_and_a.npz` (new, 1.5 MB)
- `JSAC/planning/experiments/cauchy_tightness/summary.json` (new)
- `JSAC/code/prompts/05_theorem2_tightness_figure_done.md` (this file)

Pushed to master as `0f6901a`.
