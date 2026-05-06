# plaza_run figures — headline numbers

§VII figures from `outputs/plaza_run_seed42_*.npz`. Single-seed,
**9000-slot (5-min) realistic-walk** traces per regime — bodies cycle
through entry-street to exit-street walks with steady-state population
flux (~30-45 in plaza at any moment, fading in/out through the OSM
street openings). All numbers below are directly readable from the NPZ
and reproducible via the figure scripts.

## Pol-fix + 5-min steady-state regen (2026-05-05)

Two corrections superseded the brief 09 v1 numbers:

1. **Polarisation mismatch** in `plaza_specular_paths::_perpendicular_pol`
   (emitted φ̂ horizontal pol while the UE dipole was modelled as ẑ).
   Fixed; channel coupling now scales correctly.
2. **5-min steady-state OD walks**. The original 600-slot (20 s)
   traces had each body do a near-static random walk; bodies barely
   moved 20 m. The 9000-slot (5-min) regen has each body cycle
   through random (entry, exit) pairs from the seven OSM-verified
   plaza street nodes, fading in/out off-camera through pre/post-
   entry segments. ~30 bodies are mid-walk at t=0 (steady state, not
   t=0 cluster spawn), climbing to ~45 by run end as the schedule
   stabilises.

Story-level conclusions (precoder collapse at nominal load, ZF
dominance under M ≫ K, ECBF infeasibility in tight regime) survive;
the 5-min data tells a more honest binding-regime story (ZF violates
16.7 % of body-slots — not 0.1 % — when bodies actually walk through
served-user beams) and reveals genuine spatial heterogeneity in the
absorbed-power deposition.

## Slack regime — paper nominal load

50 bodies, K=25 served, 5-55 m range, 30 dBm tx, 8x8 panel at 26 GHz,
budget multiplier ×1 (per-body L_RL = 163.4 mW). Realistic OD walks.

All five precoders collapse on the *constraint* side (max p_abs/L
< 1.5×10⁻³, three orders of magnitude inside the safe regime). On the
*rate* side, ZF separates from MRT/WC/ECBF/oracle when the channel is
well-conditioned (plaza-specular, K < M); ZF degenerates under K=25
in UMa-LOS due to near-singular HH^H.

| Quantity | Plaza-specular | 3GPP UMa-LOS |
|---|---|---|
| Mean sum-rate, MRT (Mbps) | 11 290 | 5 070 |
| Mean sum-rate, ZF (Mbps) | 44 486 | 0 (singular) |
| Mean P_abs / L_RL, MRT | 2.1e-4 | 3.1e-4 |
| Max P_abs / L_RL, any precoder | 1.4e-3 | 1.8e-3 |
| Violations / 450 000 body-slots | 0 | 0 |

The slack at nominal load is ~3 orders of magnitude. The §VII.A scenario
sits well inside the safe regime; precoder choice is rate-driven, not
compliance-driven.

## Binding regime — Pareto-active load

Same scenario, but tx 43 dBm (×100 power), per-body budget multiplier
×0.1 (L_RL = 16.3 mW), realistic ingress/egress walks. Constraint matters.

| Precoder | median p_abs/L | sum-rate (Mbps) | viol % | infeas % |
|---|---:|---:|---:|---:|
| MRT | 0.634 | 11 290 | **35.1** | 0 |
| ZF | 0.136 | **44 486** | **16.7** | 0 |
| WC back-off | 0.242 | 11 290 | 2.0 | 0 |
| Multi-body ECBF | 0.000 | 882 | 0.8 | **97** |
| Oracle | 0.000 | 1 705 | 1.4 | **92** |

Compared to the 600-slot (20 s) baseline, the 5-min walks reveal that
MRT's violation rate drops 65.8 % → 35.1 % (bodies now spend time in
cooler off-axis zones, not just the BS broadside) but ZF's violation
rate jumps **0.1 % → 16.7 %**: when a tier-C bystander walks through
a served user's nulled direction the null is geometric, not
exposure-aware, and momentary alignment puts that body above budget.
WC back-off remains the operationally-safe baseline (2 % violations,
full sum-rate); multi-body ECBF still triggers min-absorption fallback
on 92-97 % of slots and lives near (0, 0) on the Pareto.

The §VII.D paper conclusion stands: in M ≫ K configurations, ZF
provides good *average* compliance via interference suppression, but
**moving bodies surface ZF's lack of exposure-awareness** — 16.7 %
violations at the 5-min horizon is real risk, not numerical noise.
This is a stronger argument for the multi-body QCQP than the
600-slot static-position data showed.

## Spatial absorption heatmap (new in v3)

`spatial_heatmap.pdf` — mean P_abs(x, y)/L_RL binned on 1.5 m cells
across the plaza, accumulating contributions from every body that
visited each cell over the 5-min trace.

- **Slack regime** (multi-body ECBF, plaza-specular): clear BS forward-
  sector hotspot extending ~25 m north of the BS panel along the
  broadside, with ~3.5× spatial heterogeneity (1.4×10⁻⁴ at the cool
  edges to 4.8×10⁻⁴ at the brightest cells). The pattern mirrors the
  array's gain pattern projected onto pedestrian-height ground plane.
- **Binding regime** (ZF): plaza-wide median 0.50× of L_RL, p95 1.25×,
  max 2.18× — over half the cells in the plaza are at half the budget
  on average, and the brightest cells are persistently over-budget.
  ZF's null geometry happens to leave hot ridges between served users.

This figure is the new spatial argument for budget-aware precoding:
even when *aggregate* compliance looks acceptable, walking through a
hot ridge for ~5 s puts that body over budget by 2× — exactly the
exposure narrative the paper opens with.

## Chronic dose — tier stratification

`chronic_dose.pdf` — per-body absorbed energy over the full 5-min
trace, stratified by tier:

- Served (n=25): median **12.6 mJ**
- Bystander (n=10): median **9.1 mJ**
- Cooperating (n=15): median **8.4 mJ**

Compared to the 20 s data (Served 1.18 mJ / Bystander 0.78 / Cooperating
0.39), the served-vs-cooperating ratio dropped from **3.0× to 1.5×**.
The 20 s static-position result over-stated tier separation — when
bodies actually walk, they all visit hot zones briefly. Bystanders pick
up nearly as much chronic dose as served users; only cooperating users
retain a meaningful (~30 %) reduction.

This finding tightens the paper's chronic-dose argument: the digital
twin's value isn't separating served from bystander on integrated dose,
it's tracking *who is currently in a hot zone* and steering precoders
accordingly.

## Pose-info gain ablation

`pose_info_gain.pdf` — pose-aware vs pose-ablate, slack regime,
plaza-specular, same seed. All four non-MRT precoders show median
ΔSR = 0.000 Mbps. Pose telemetry contributes zero measurable rate gain
in the slack regime, exactly as theory predicts: when the constraint is
academic, the constraint-shaping role of Q is academic too. The
binding-regime ablation would change this — left as follow-up.

## Per-figure summary

**hero_pareto.pdf** (slack, 2-col wide). (a) ECDFs of P_abs/L_RL across
450 000 body-slots in plaza-specular and UMa-LOS; precoders collapse
to a single line per path model, all 3+ orders of magnitude left of
the budget. Multi-body ECBF visibly separates from the others on the
plaza-specular ECDF (left tail), reflecting its tighter exposure bound.
(b) Bar chart of mean sum-rate; ZF dominates plaza-specular (44 Gbps),
MRT/WC/ECBF/oracle sit at 11 Gbps; in UMa-LOS, ZF goes singular and
the others sit at 5 Gbps.

**hero_binding.pdf** (binding, 2-col wide). (a) ECDFs separate
cleanly: MRT (red, peaking at p_abs/L ≈ 1) and ZF (orange, long left
tail then jumping past 1) span [10⁻⁴, 5]; WC back-off (light orange)
straddles the budget; ECBF/oracle (blue) collapse near 0. (b) Pareto
scatter: MRT (35 %, 11 Gbps), ZF (17 %, 44 Gbps), WC (2 %, 11 Gbps),
ECBF (0.8 %, 0.9 Gbps), oracle (1.4 %, 1.7 Gbps). ZF's 17 % violation
rate and high rate make it the upper-right corner; the digital-twin
argument is "can we move ZF's dot down to ≤ 2 % without losing rate".

**chronic_dose.pdf** (slack, 1-col). Per-body absorbed-energy ECDF
over 5 min, stratified by tier. The cooperating tier sits ~30 % below
served; bystander overlaps cooperating. The 5-min averaging reveals
the tier-stratification was largely an artefact of static positioning.

**pose_info_gain.pdf** (slack, 2-col wide). Both panels show curves
collapsed to zero — slack regime mutes constraint-aware structure.

**spatial_heatmap.pdf** (new, 2-col wide). 1.5 m grid over the plaza,
mean P_abs/L_RL per cell. (a) Slack regime, multi-body ECBF: clean
forward-sector pattern, 3.5× heterogeneity. (b) Binding regime, ZF:
plaza-wide median 0.5×, hot ridges 2× of budget — the spatial story
behind ZF's 17 % violation rate.

## Cadence (paper `tab:cadence`)

p50 wall-clock per stage, plaza-specular vs binding regime, 5-min run:

| Stage | Slack (30 dBm) | Binding (43 dBm) |
|---|---|---|
| Q refresh | 59 ms | 65 ms |
| Precoder solve | 24 ms | 116 ms |
| RT (cache hit) | 0 ms | 0 ms |
| Shannon PHY | 99 ms | 163 ms |

Slack-regime per-slot cost: ~190 ms (matches the brief's 100 ms-1 s
operating envelope). Binding-regime per-slot cost: ~340 ms with the
ECBF Newton sweep capped at `max_outer=8`; uncapped ECBF would push
the precoder-solve column past 1 s.

## Limitations

- Single seed (42). Multi-seed averaging not run; brief 09 originally
  asked for ≥ 3 seeds with confidence bands.
- 9000 slots = 5 min, single trace. Bodies still cycle through the
  same OD pairs; longer horizons or stochastic re-pairing would
  smooth ECDF tails further.
- Sionna NR PHY pass not done (Shannon-rate proxy used).
- Multi-body ECBF's min-absorption fallback gives near-zero rate in
  the binding regime. A smarter fallback (e.g. ZF-with-budget-rescale
  when QCQP infeasible) would change the Pareto picture for ECBF.
- ZF singular fallback in UMa-LOS K=25 is real; a regularised ZF or
  smaller K would restore non-zero rate for the comparator.

## Reproducing

```bash
# data — 9000 slots = 5 min steady-state OD walks
python -m JSAC.code.experiments.plaza_run.run --seed 42 --n-slots 9000 \
  --realistic-walks --paths plaza_specular --label-suffix viz5min
python -m JSAC.code.experiments.plaza_run.run --seed 42 --n-slots 9000 \
  --realistic-walks --paths uma_los
python -m JSAC.code.experiments.plaza_run.run --seed 42 --n-slots 9000 \
  --realistic-walks --paths plaza_specular --ablate-pose-telemetry
python -m JSAC.code.experiments.plaza_run.run --seed 42 --n-slots 9000 \
  --realistic-walks --paths plaza_specular --tx-power-dbm 43 \
  --budget-multiplier 0.1 --label-suffix bind5min

# figures
cd JSAC/code/experiments/plaza_run/figures
python hero_pareto.py
python hero_binding.py
python chronic_dose.py
python pose_info_gain.py
python spatial_heatmap.py
```
