# plaza_run figures — headline numbers

Four §VII figures from `outputs/plaza_run_seed42_*.npz`. Single-seed,
600-slot (20 s window) data per regime. All numbers below are directly
readable from the NPZ and reproducible via the figure scripts.

## Pol-fix note (2026-05-05)

A polarisation-mismatch bug in `plaza_specular_paths::_perpendicular_pol`
(emitted φ̂ horizontal pol while the UE dipole was modelled as ẑ) was
fixed before this regen. The fix scales channel coupling by ~26 orders
of magnitude on average; all numbers below supersede the brief 09 v1
table. Story-level conclusions (precoder collapse at nominal load, ZF
singular fallback in UMa-LOS K=25) survive the fix; magnitudes did not.

## Slack regime — paper nominal load

50 bodies, K=25 served, 5-55 m range, 30 dBm tx, 8x8 panel at 26 GHz,
budget multiplier ×1 (per-body L_RL = 163.4 mW). Random walk.

All five precoders collapse on the *constraint* side (zero violations
across 3000 body-slots in either path model). On the *rate* side, ZF
separates from MRT/WC/ECBF/oracle when the channel is well-conditioned
(plaza-specular, K < M); ZF degenerates under K=25 in UMa-LOS due to
near-singular HH^H.

| Quantity | Plaza-specular | 3GPP UMa-LOS |
|---|---|---|
| Mean sum-rate, MRT (Mbps) | 11 477 | 5 070 |
| Mean sum-rate, ZF (Mbps) | 74 000 | 0 (singular) |
| Mean P_abs / L_RL, MRT | 2.7e-4 | 3.1e-4 |
| Max P_abs / L_RL, any precoder | 2.1e-3 | 1.7e-3 |
| Violations / 3000 body-slots | 0 | 0 |

Even with the pol fix, the slack at nominal load is ~3 orders of
magnitude. The §VII.A scenario sits well inside the safe regime.

## Binding regime — Pareto-active load

Same scenario, but tx 43 dBm (×100 power), per-body budget multiplier
×0.1 (L_RL = 16.3 mW), realistic ingress/egress walks through Brussels
street entry nodes. This is the regime where the constraint matters.

| Precoder | mean p_abs (mW) | sum-rate (Mbps) | viol % | infeas % |
|---|---:|---:|---:|---:|
| MRT | 29.1 | 7 181 | **65.8** | 0 |
| ZF | 0.4 | **69 246** | 0.1 | 0 |
| WC back-off | 7.3 | 7 181 | 2.0 | 0 |
| Multi-body ECBF | 0.0 | 14 | 0.0 | **100** |
| Oracle | 0.2 | 150 | 0.0 | 98 |

The genuine Pareto frontier emerges:

- MRT pushes well past the budget on 66 % of body-slots while keeping
  sum-rate at 7.2 Gbps (SE-cap saturated on each served user).
- ZF dominates everything in this regime: 69 Gbps (close to the
  74 Gbps SE cap × 25 users × 400 MHz) at 0.1 % violations. Reason:
  M=64, K=25 leaves 39 spare antenna DOFs, so ZF naturally null-steers
  energy away from non-served bystanders too.
- WC back-off honours the budget at MRT-level rate (7.2 Gbps); since
  rate is SE-cap-limited, the power scale-down does not cost rate.
- Multi-body ECBF and oracle return the min-absorption fallback on
  100 % / 98 % of slots (solver tolerance treats the tight budget as
  infeasible). They achieve 0 violations at near-zero rate.

The §VII.D paper finding is therefore: in M ≫ K configurations, ZF
naturally provides compliance via interference suppression. The §IV
multi-body QCQP solver's value emerges in regimes where M ~ K or
geometry pushes bystanders into served-user nulls, *not* in the M=64,
K=25 plaza scenario as originally framed. A future smarter-fallback
ECBF (e.g. ZF-with-budget-scaling rather than min-absorption) would
recover ECBF's competitiveness in the binding regime.

## Per-figure summary

**hero_pareto.pdf** (slack regime, two-col wide). (a) Overlapping
ECDFs of P_abs/L_RL across body-slots in plaza-specular and UMa-LOS;
all five precoders collapse to a single line per path model, sitting
3+ orders of magnitude left of the budget. (b) Bar chart of mean
sum-rate; ZF dominates plaza-specular (74 Gbps), MRT/WC/ECBF/oracle
sit at 11 Gbps; in UMa-LOS, ZF goes singular and MRT/WC/ECBF/oracle
sit at 5 Gbps.

**hero_binding.pdf** (binding regime, two-col wide; new in v2).
(a) ECDFs separate cleanly: MRT and a long ZF tail span the [10⁻⁴, 5]
range, with MRT and WC back-off straddling the budget line. (b) Pareto
scatter: MRT at (66 %, 7 Gbps), ZF at (0.1 %, 69 Gbps), WC back-off at
(2 %, 7 Gbps), ECBF/oracle near (0, 0). The 4-orders-of-magnitude
sum-rate spread on the same y-axis makes the 14 Mbps ECBF point hard
to see; this is intentional and matches the data.

**chronic_dose.pdf** (slack regime, single col). Per-body absorbed
energy ECDF over 20 s, stratified by tier. Tier medians (multi-body
ECBF on slack regime; collapse means precoder choice does not matter):

- Served (n=25): 1 177 µJ
- Cooperating (n=15): 389 µJ
- Bystander (n=10): 775 µJ

**pose_info_gain.pdf** (slack regime, two-col wide). Pose-aware vs
pose-ablate, plaza-specular, same seed. Both panels show curves
collapsed to zero — pose telemetry contributes zero measurable gain at
this load. Conclusion is symmetric to the slack hero: when budget is
slack, the constraint structure that pose telemetry feeds (Q) is
academically active but practically slack.

## Cadence (paper `tab:cadence`)

p50 wall-clock per stage, plaza-specular vs binding regime:

| Stage | Slack (30 dBm) | Binding (43 dBm) |
|---|---|---|
| Q refresh | 59 ms | 59 ms |
| Precoder solve | 25 ms | 1 099 ms |
| RT (cache hit) | 0 ms | 0 ms |
| Shannon PHY | 108 ms | 109 ms |

The binding-regime precoder solve cost is dominated by ECBF Newton
sweeps that exhaust the `max_outer=8` budget before declaring
infeasibility (the slot_loop fallback caps outer iterations to keep
wall-clock bounded). At nominal load, ECBF returns trivially in
1 outer sweep and the precoder solve is 25 ms.

## Limitations

- Single seed (42). Multi-seed averaging not run; brief 09 originally
  asked for ≥ 3 seeds with confidence bands.
- 600 slots = 20 s window, not the full 5-min trace.
- Sionna NR PHY pass not done (Shannon-rate proxy used).
- Multi-body ECBF's min-absorption fallback gives near-zero rate in
  the binding regime. A smarter fallback (e.g. ZF-with-budget-rescale
  when QCQP infeasible) would change the Pareto picture for ECBF.
- ZF singular fallback in UMa-LOS K=25 is real; a regularised ZF or
  smaller K would restore non-zero rate for the comparator.

## Reproducing

```bash
# data
python -m JSAC.code.experiments.plaza_run.run --seed 42 --n-slots 600 \
  --paths both --pose-period 30 --rt-period 30
python -m JSAC.code.experiments.plaza_run.run --seed 42 --n-slots 600 \
  --paths plaza_specular --ablate-pose-telemetry --pose-period 30 --rt-period 30
python -m JSAC.code.experiments.plaza_run.run --seed 42 --n-slots 600 \
  --paths plaza_specular --tx-power-dbm 43 --budget-multiplier 0.1 \
  --realistic-walks --label-suffix bind --pose-period 30 --rt-period 30

# figures
cd JSAC/code/experiments/plaza_run/figures
python hero_pareto.py
python hero_binding.py
python chronic_dose.py
python pose_info_gain.py
```
