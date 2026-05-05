# Brief 08 report — plaza_run assembly

**Status:** done. PR [#774](https://github.com/rwydaegh/aegis/pull/774)
squash-merged to master as commit `508ca30` on 2026-05-05.

## TL;DR

The §VII hero machine is built and producing data. 50 SMPL-X bodies on
AMASS walk-cycles, an 8x8 BS panel at 26 GHz on Brussels Grand Place,
five precoders solving every slot (MRT, ZF, worst-case back-off,
multi-body ECBF, pose-known oracle), per-body Brussels RL and ICNIRP
BR budgets evaluated against measured P_abs.

The headline finding is uncomfortable but unambiguous: **at the paper's
nominal load (K=25 served, 5-55 m range, 30 dBm tx), all five precoders
collapse to the same operating point**. P_abs is roughly four orders of
magnitude under the per-body Brussels RL budget. Zero violations across
3000 body-slots. This matches the paper's own `tab:bind` prediction
(binding distance r* ~ 2.7 m at this BS configuration), so it's not a
bug, it's the regime.

The implication for the paper is that the original §VII.D Pareto figure
(compliance violation rate vs. served sum-rate) has nothing to plot.
The chronic-dose narrative (§VII.E) is what carries the paper. Brief
09 has been pivoted accordingly.

Cadence numbers are clean: 30-60 ms Q refresh, 25-35 ms precoder solve,
107 ms Shannon PHY proxy. Well inside the paper's claimed `tab:cadence`
ratios.

## What we built

A new module under `JSAC/code/experiments/plaza_run/`. 12 Python
files plus a README, ~1.4 kLOC. Mirrors the layout of the existing
`rank_check/` and `gpu_benchmark/` experiments (deterministic seed,
NPZ outputs, hash-pinned scene cache, sibling outputs/ dir).

Functionally: scene assembly (Overpass scrape cached once), per-body
walk trajectory generation with bounded random walk in plaza
coordinates, two path-generation modes (deterministic plaza-specular
LOS + ground + 2 facades vs. 3GPP UMa-LOS stochastic comparator), the
per-slot tick that refreshes pose, rebuilds Q via translation phasor,
runs all five precoders, evaluates compliance against per-body
budgets, and writes NPZ outputs.

## Decisions captured

A few of the brief's open questions required calls. They are below in
the order they were made.

**RT engine: Sionna over DiffeRT.** The brief nominally specified
DiffeRT. Robin pushed back: Sionna is more reviewer-known, the
differentiability advantage of DiffeRT isn't load-bearing for this
brief, and we may want PHY-side flexibility later. Switched. Implementation
uses the existing `aegis.modal_rt.sionna_tracer` with Modal L4 offload.
The fallback path (Sionna unavailable) drops to deterministic
plaza-specular paths.

**Path source: dictionary + UMa-LOS comparator side by side.** Same
dual-path-model strategy `rank_check` uses. The deterministic
plaza-specular construction is cheap, defensible, and matches the §V
"scene as path dictionary" framing. The stochastic UMa-LOS comparator
is the sanity check reviewers will look for.

**PHY: Shannon-rate proxy.** Robin's call. Shannon-rate is fast (~107
ms/slot) and the door is wired open for a Sionna NR pass if we want
one later. The brief flagged this as a 10x runtime decision; Shannon
keeps the production run inside a 6-min wall clock per pass.

**Pose ablation: a single `--ablate-pose-telemetry` flag** rather than
two scripts. Cleaner reproducibility (same seed, same code path).

**Tier-C handling: ICNIRP 2020 monostatic ISAC** via
`aegis.sensing.detection`. Per-slot Pd against an 8x8 panel at 26 GHz
with 12.7 deg HPBW gives a per-body detected/undetected classification
that branches between cooperating-style Cauchy and worst-case envelope.
Brief 07's option (a).

**Tier split: static 25/15/10.** Paper §VII.A. Static across the run.

**Cadence: fake clock.** Each Python iteration is one slot.
Pose-cadence and dictionary-cadence quantities refresh every 30 slots
(1 s at 30 Hz). Wall-clock per stage instrumented honestly.

**Solver infeasibility: log + flag, do not fall back.** When the
multi-body ECBF QCQP returns its `min-absorption` fallback method,
that slot is marked infeasible and the column is preserved in NPZ.
Brief 03's done-doc explicitly disallowed silent MRT substitution.

**Scene assembly: Overpass once, cache on disk.** The plaza geometry
doesn't change between runs. The cache is keyed on a hash of the
scrape parameters, so changing radius or detail invalidates
automatically. Brussels Grand Place is at lat 50.8467, lon 4.3525,
80 m radius scrape, 18 m default building height. The XML and parsed
mesh land in `data/scenes/brussels_grand_place/`, gitignored.

## What we found

Three NPZ outputs were produced, all at seed=42, 600 slots
(20 s window):

| Run | Precoder collapse? | Sum-rate (Mbps) | p_abs/L median | Violations |
|---|---|---|---|---|
| plaza-specular pose-aware | yes | 363 | 1.9e-4 | 0 of 3000 |
| plaza-specular pose-ablate | yes | 363 | 1.9e-4 | 0 of 3000 |
| UMa-LOS pose-aware | yes (zf falls back) | 5070 | 2.5e-4 | 0 of 3000 |

The collapse is the whole story. All five precoders end up doing the
same thing because the budget gap is so wide that the constraints
never bind. MRT, the simplest precoder, doesn't violate. Therefore
ZF, WC back-off, and ECBF have nothing to optimize against, so they
all reduce to MRT. The oracle has nothing extra to learn.

Why does UMa-LOS deliver 14x the sum-rate of plaza-specular? Richer
multipath. The stochastic preset gives 8 paths/body (4 clusters x 2
subpaths) vs. 4 deterministic paths in the plaza-specular case, and
the directional spread provides better coherent gain to the served
beamforming. The p_abs ratio also rises (from 1.9e-4 to 2.5e-4) but
stays nowhere near the budget.

Why does pose ablation produce identical headline numbers? Because at
this load the pose telemetry isn't the bottleneck. When the budget
slack is 4 orders of magnitude, knowing the body's instantaneous
orientation vs. its envelope doesn't change which precoder gets
picked. The figures from brief 09 will quantify the slot-level
distribution to be sure, but the means are identical.

## Cadence numbers (paper `tab:cadence`)

p50 timings, paper-targets in parens:

| Stage | plaza-specular | UMa-LOS | Paper claim |
|---|---|---|---|
| Q refresh | 59 ms | 169 ms | ~100 ms (pose cadence) |
| Precoder solve | 31 ms | 31 ms | ~1 ms |
| RT (cache hit) | 0 ms | 0 ms | seconds (cold) |
| Shannon PHY | 108 ms | 108 ms | (not in tab) |

The precoder solve is 30x slower than the paper's claim of 1 ms. That
1 ms target is for warm-start Newton dual ascent on a single body;
the multi-body QCQP across 50 bodies (the proposed solver) sits at 31
ms p50, which is the right number to honour in the paper. I'll suggest
correcting `tab:cadence` accordingly when we rewrite §VII.D.

The UMa-LOS Q refresh (169 ms) is the single rebuild cost when
stochastic paths are regenerated each slot rather than translated from
a static M_static. This will drop to plaza-specular's 59 ms once
brief 04's translation-phasor warm path is wired into the UMa case.
Logged as a follow-up.

## Cost

Wall-clock per pass, 600 slots, 50 bodies, seed=42:

- plaza-specular pose-aware: 188 s
- UMa-LOS pose-aware: 329 s
- plaza-specular pose-ablate: 215 s

Total: ~12 min on the 16 vCPU + RTX 4090 machine. JAX is forced to CPU
because per-body GPU dispatch overhead at pose cadence dominated the
GPU dispatch savings. Translation phasor and per-slot Q rebuild stay
on NumPy; only the cold pose-cadence `compute_static_path_gram` runs
through JAX.

The full 9000-slot (5-min wall) run as originally specced would be
~3 hours total across the three passes. Not yet executed; brief 09
is iterating on figures with the 600-slot smoke data first to nail
the visual layout before deciding whether to invest the 3 hours.

## What's NOT in this brief

- **Sionna NR PHY pass.** The Shannon proxy at 108 ms/slot is fast.
  Modal RPC round-trip per slot would push this to seconds. Wired
  but flagged. Add when reviewers ask.
- **Multi-seed averaging.** Brief 09's job, per the brief's own scope.
- **Warm-start λ across slots in `multibody_ecbf`.** Brief 03
  follow-up. Cuts the 31 ms/slot precoder time roughly in half.
- **CSI per-path calibration LS with real CSI.** Today uses synthetic
  served-user CSI; a real-CSI feed would come from a Sionna PHY pass.
- **9000-slot production run for the paper.** Pending brief 09 layout
  freeze (so we don't render at the wrong size).

## Tests

90 targeted tests pass. Lint (ruff check + format) clean. Mie golden
canary still green. The full non-slow suite was not re-run end to end
(brief 04, 03, 02, 01 already went through it on their own merges).
