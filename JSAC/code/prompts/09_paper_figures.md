# 09 — Paper figures (hero + chronic dose + pose-info-gain)

**Goal.** Take the NPZ outputs from brief 08 (`plaza_run`) and turn them into the three paper figures the JSAC submission still owes:

1. **Hero Pareto** (paper §VII.D, currently `\TODO` placeholder) — compliance violation rate vs. served sum-rate, five precoders.
2. **Chronic-dose CDF** (paper §VII.E, currently narrative only) — per-body absorbed energy over the 5-minute trace.
3. **Pose-information-gain ablation** (paper open empirical risk) — sum-rate margin recovered by tier-A/B pose telemetry vs. tier-everything-Cauchy.

## Blockers

- **08 (plaza_run assembly)** — outputs in NPZ form. Strict.

## Why this matters

The hero figure is *the* missing piece in `paper_v2.tex`. Line 1010 has a literal `\TODO`. The Pareto's labels (`X%`, `Y%`, `R3`, `R5`) are placeholder symbols, not numbers. Without this brief, the paper has nothing to show in §VII.

Chronic dose is the secondary value-prop the paper falls back on if the Brussels RL doesn't bind much under MRT (see `paper_spine.md` §8 for the contingency tree). The 5-minute trace is already there — this brief integrates it.

Pose-information-gain is the open empirical question the paper has been hedging on for three rounds of brainstorm: is pose telemetry worth 0.5 dB or 3–5 dB of capacity? Re-running plaza with vs. without tier-A/B pose answers it directly.

## What's already in place after brief 08

- NPZ outputs in `JSAC/code/experiments/plaza_run/outputs/`. Per-body, per-slot, per-precoder: `P_abs(t)`, sum-rate, compliance flag, cadence breakdown.
- Five precoders compared per run: MRT, ZF, WC back-off, proposed multi-body ECBF, pose-known oracle.
- For the pose-info-gain ablation, brief 08 either (a) ships a flag that disables tier-A/B pose telemetry and falls back to Cauchy worst case, or (b) you run plaza_run twice with different configs. Coordinate with the brief 08 dev on this.

## What's already in place codebase-wide

- `src/aegis/viz/` — has `dashboard.py`, `comparison.py`, `frequency_plots.py`, `heatmap.py`. Matplotlib-flavoured. Useful as starting points or just reference style.
- The two existing JSAC experiments have figures: `JSAC/code/experiments/rank_check/rank_cdf.pdf`. Look at how it's styled; match it for consistency.
- `paper_v2.tex` has the captions written for figures that don't exist yet. Read those captions — they constrain what your figure has to actually show.

## Open questions for the dev

- **Number of seeds.** The paper hero figure is one curve set; reviewers will appreciate seeing it averaged over 5–10 seeds with confidence bands. Cost is linear in seeds; depends on how long brief 08 runs. Aim for at least 3 seeds and report mean + range.
- **What goes on each axis of the hero**. Paper says compliance violation rate (x) vs sum-rate (y). It might be cleaner as a bar chart with each precoder a column, x = sum-rate, colour = violation %. Use whatever reads most cleanly given the actual numbers.
- **Chronic-dose plot type.** CDF over bodies of total absorbed energy is the obvious one. Alternatively, percentile-of-body energy vs. time. Or a ranked bar chart of "the K most-exposed bodies." Pick what the data invites.
- **Pose-info-gain plot.** Could be a single "Δ sum-rate" number, a CDF of slot-level differences, or a side-by-side compliance × sum-rate Pareto with the two configs overlaid. Probably the third — it's the most honest visual.
- **Whether to also regenerate the rank-CDF and GPU-bench figures** in the same paper-figure style for visual consistency. Stretch goal; not strictly needed since those are already in the paper.
- **Hero figure: include the oracle or not.** Including makes the gap to ECBF visible (the paper's claim is "within 1 dB of oracle"). Excluding keeps the figure cleaner. Try both, pick.
- **What numbers ride along.** The Pareto figure's caption should quote the 50-body / 5-min / Brussels-RL setup. The numbers `tab:bind` predicts for binding distance should be cross-checked against the actual data — if MRT violates at K=25 and r=2.7m as predicted, call it out. If not, that's also worth saying.

## What "done" looks like

- Three PDFs in `JSAC/code/experiments/plaza_run/figures/` (or wherever you want to land them):
  - `hero_pareto.pdf`
  - `chronic_dose.pdf`
  - `pose_info_gain.pdf`
- Each with a caption-ready short caption in a sibling `.txt` file (so paper rewrite can drop them in without re-deriving).
- A short `RESULTS.md` summarising the headline numbers: MRT violation rate, ECBF violation rate, sum-rate gap to oracle, chronic-dose reduction factor, pose-info-gain Δ. Two paragraphs at most. This is what tells the paper team which way to rewrite §VII.D — toward the binding RL or toward chronic dose.
- Plotting scripts committed alongside the figures so they can be regenerated when brief 08 reruns with different seeds.

## What this is NOT

- The paper rewrite. Once the figures exist, somebody (probably you, Robin) edits `paper_v2.tex` to drop them in and rewrite §VII.D narrative around what they actually show. That's a separate pass.
- A new experiment. This brief consumes brief 08's outputs; if the outputs aren't enough, that's a brief-08 escalation, not a brief-09 invention.
- A statistical-significance-testing exercise. Confidence bands from seed averaging is enough; don't run hypothesis tests against null precoders.
- A presentation. PDF figures, not slides. Conference talks are a different artefact.
