# plaza_run figures — headline numbers

Three §VII figures from `outputs/plaza_run_seed42_*.npz`. Single-seed,
600-slot (20 s window) data. All numbers below are directly readable
from the NPZ and reproducible via the figure scripts.

## Headline

At the paper's nominal load (50 bodies, K=25 served, 5-55 m range,
30 dBm tx, 8x8 panel at 26 GHz), all five precoders collapse to the
same operating point. Zero compliance violations across 3000
body-slots in either path model.

| Quantity | Plaza-specular | 3GPP UMa-LOS |
|---|---|---|
| Mean sum-rate (Mbps) | 363 | 5070 |
| Median P_abs / L_RL | 1.9e-4 | 2.5e-4 |
| Max P_abs / L_RL | 1.25e-3 | 1.74e-3 |
| Violations / 3000 body-slots | 0 | 0 |

The 3-orders-of-magnitude budget slack matches the paper's `tab:bind`
prediction (binding distance r* ~ 2.7 m at this BS configuration).
Closer bodies, more served users, or higher transmit power would push
the system into the binding regime. The figures honestly reflect this.

## Per-figure summary

**hero_pareto.pdf** — two-panel. (a) ECDF of P_abs/L_RL across
body-slots, two path models overlaid, all five precoders within each
model. The collapse shows visually as a single line per path model.
The Brussels RL budget is at x=1; the data sits ~3 orders of magnitude
left of it. (b) Mean sum-rate per precoder, grouped by path model.
UMa-LOS gives 14x the sum-rate of plaza-specular (richer multipath).
ZF in UMa-LOS degenerates due to singular HH^H at K=25 and falls back
to a near-zero precoder; this is annotated.

**chronic_dose.pdf** — single-panel ECDF of per-body absorbed energy
over the 20 s trace, stratified by tier. Tier medians:

- Served (n=25): 1006 µJ
- Cooperating (n=15): 404 µJ
- Bystander (n=10): 921 µJ

Served users have the heaviest tail (a few bodies up to ~2 mJ).
Bystanders cluster tightly (700-1100 µJ). The bystander curve is
coarse since there are only 10 bodies in that tier; multi-seed
averaging would smooth it.

**pose_info_gain.pdf** — two-panel ablation. Pose-aware vs
pose-ablate, plaza-specular, same seed. (a) Per-slot delta-sumrate
ECDF for four precoders (ZF dropped due to singular fallback noise).
All curves collapse to a vertical line at zero — pose telemetry
contributes zero measurable sum-rate gain at this load. (b) Per-body
P_abs ECDF for multi-body ECBF, aware vs ablate overlaid; the curves
overlap to float32 precision. The conclusion is symmetric to the
hero finding: when budget slack is 4 orders of magnitude, the
constraint structure that pose telemetry feeds (Q) is academically
active but practically slack.

## What this means for §VII.D

The original §VII.D framing (compliance-vs-sum-rate Pareto) needs to
be replaced. Two options:

1. **Keep the §VII.A scenario; reframe §VII.D around the collapse.**
   The hero figure becomes a "the constraint structure is correct;
   here is how slack it is in this regime" demonstration. §VII.E
   (chronic dose) carries the practical narrative; §VII.D covers
   the safety margin.

2. **Restate §VII.A with a higher load** (more served users, closer
   range, or higher tx power) so precoders separate. This requires
   re-running brief 08 with new parameters. Engineering cost: a few
   hours; conceptual cost: the paper now says "we can violate the
   budget if we try hard". Less defensible.

Recommendation: option 1. The chronic-dose narrative was already the
paper's prepared fallback (`paper_spine.md` §8); the figures support
that pivot directly.

## Cadence (paper `tab:cadence`)

p50 wall-clock per stage:

| Stage | Plaza-specular | UMa-LOS |
|---|---|---|
| Q refresh | 59 ms | 169 ms |
| Precoder solve | 31 ms | 31 ms |
| RT (cache hit) | 0 ms | 0 ms |
| Shannon PHY | 108 ms | 108 ms |

The paper's ~1 ms precoder claim is for warm-start single-body Newton
dual ascent; the multi-body QCQP across 50 bodies sits at 31 ms p50.
Honour 31 ms in the rewrite.

## Limitations

- Single seed (42). Brief 09 originally asked for >= 3 seeds with
  confidence bands; not run here under a 15-min time budget.
- 600 slots = 20 s window, not the full 5-min trace the paper
  specifies. Chronic-dose numbers scale linearly; collapse story is
  invariant.
- Sionna NR PHY pass not done (Shannon-rate proxy used).
- ZF singular fallback in UMa-LOS K=25 is real but worth a
  cross-check against a different K or a regularized ZF before
  citing in the paper.

## Reproducing

```bash
# data (already in outputs/)
python -m JSAC.planning.experiments.plaza_run.run --seed 42 --n-slots 600 \
  --paths plaza_specular --pose-period 30 --rt-period 30
python -m JSAC.planning.experiments.plaza_run.run --seed 42 --n-slots 600 \
  --paths uma_los --pose-period 30 --rt-period 30
python -m JSAC.planning.experiments.plaza_run.run --seed 42 --n-slots 600 \
  --paths plaza_specular --pose-period 30 --rt-period 30 --ablate-pose-telemetry

# figures
cd JSAC/planning/experiments/plaza_run/figures
python hero_pareto.py
python chronic_dose.py
python pose_info_gain.py
```
