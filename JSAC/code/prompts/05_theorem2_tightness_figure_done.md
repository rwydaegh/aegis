# 05 -- Theorem 2 tightness figure -- DONE

Experiment lives at `JSAC/planning/experiments/cauchy_tightness/`.

## Outputs

- `tightness.{pdf,png}` -- two-panel CDF (plaza specular | 3GPP UMa-LOS).
- `ratios.npz` -- raw `10 log10(LHS/RHS)` arrays per (channel, ensemble).
- `q_and_a.npz` -- per-job Q matrices and `a_los` vectors so
  `finalise.py --resweep` can iterate on precoder logic without
  recomputing Q (~7 min sweep).
- `summary.json` -- median, p10, p90, max per ensemble x channel x body;
  bound-violation fractions.
- `README.md` -- full writeup with the dominant finding and the paper
  recommendation.

## Headline finding (read this if nothing else)

**Theorem 2 as written ("for any precoder x") is empirically not a
universal upper bound.** The bound holds at MRT-toward-LOS with
9-32 dB of slack (not tightness), because Q's principal eigenvector in
C^M is rarely aligned with `a` (median `|<v_top, a/||a||>|^2 = 0.001`,
max 0.19 across our 24 jobs). And for any precoder with `|a^H x|^2 ->
0`, `x^H Q x` stays positive while RHS goes to zero -- the ratio is
unbounded above.

For ECBF / ZF / random / MRT-random-user precoders, the bound is
violated for ~50-70% of samples, by a median of 0-6 dB and by 20-30 dB
at p90.

## Recommended fix to the paper

Restate Theorem 2 as a bound on *the absorbed power for the worst
bystander direction at fixed x*, not for any x at fixed bystander
direction:

```
x^H Q x <= T_0 (A_ab/4) D_max sup_{a in A_admissible} |a^H x|^2
```

This is what the appendix proof actually proves (line 1149 in
`paper_v2.tex`), and the §IV multi-body ECBF design does not rely on
the as-written form. One-line edit. See README.md TL;DR for details.

## Scope

- Phantoms: Thelonious + Duke (Eartha + Ella deferred -- runtime host
  is 8 GB RAM shared; rerun with `CAUCHY_TIGHTNESS_FULL=1` on a
  beefier host).
- 6 positions per phantom, plaza-specular and 3GPP UMa-LOS channels,
  26 GHz, 8x8 UPA, 10 W tx -- mirrors `rank_check/`.
- 5 precoder ensembles: isotropic random, MRT-to-random-user, x = a
  (matched to body LOS), ECBF (random user, swept budget), ZF among
  two random users (body unknown to BS).

## Reproduce

```bash
cd /home/user/aegis
.venv/bin/python JSAC/planning/experiments/cauchy_tightness/run_tightness.py
# ~7 min on a 4-core/8 GB host with 1 worker
.venv/bin/python JSAC/planning/experiments/cauchy_tightness/finalise.py
# replots + refreshes README's auto-results from saved ratios.npz
```
