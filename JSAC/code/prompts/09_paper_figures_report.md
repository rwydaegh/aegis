# Brief 09 report — paper figures

**Status:** in flight. Figure 1 (chronic-dose CDF) is locked. Figures 2
(hero) and 3 (pose-info-gain ablation) are pending the same
critique-iterate workflow. RESULTS.md and caption stubs are pending.
No PR yet.

## TL;DR

Brief 09 turns the three NPZ outputs from brief 08 into the §VII
figures the JSAC paper still owes. The convention adopted (per Robin's
direction on 2026-05-05) is scienceplots via the existing
`theory/scripts/_plot_style.py` helpers, IEEE single-column default
(3.5 in wide), two-column wide (`figure*`, 7.16 in) only for the hero
if it warrants it. Each figure is rendered to PDF (canonical, for
paper inclusion) and viewed as PNG (for the critique-iterate loop) at
the same physical size.

The thing that complicates this brief is brief 08's empirical headline:
**all five precoders collapse to MRT at the paper's nominal load**,
with zero compliance violations. The original §VII.D Pareto figure
(violation rate vs. sum-rate) is degenerate in this regime: there is
no Pareto front, just one operating point per path model.

The figures we end up shipping therefore have to be honest about that
collapse. They show what the data actually says, not what the paper
originally hoped to show. The narrative pivots toward chronic dose,
which is the paper's prepared fallback (`paper_spine.md` §8).

## Conventions adopted

A small `figures/` subdirectory inside `plaza_run/` houses three
plotting scripts and two helper modules:

- `_figstyle.py` re-exports `apply_monograph_style(mode='pdf'|'png')`
  and `fig_size_ieee(columns=1|2, aspect=h/w)` from
  `theory/scripts/_plot_style.py`. Adds a `save_both()` helper that
  emits PDF and PNG at the same physical size.
- `_data.py` loads the canonical NPZ outputs into a tidy `Run`
  dataclass with named precoder/tier dictionaries.
- One script per figure: `chronic_dose.py`, `hero_pareto.py`,
  `pose_info_gain.py`.

The critique-iterate workflow in practice is: render, read the PNG,
critique typography and layout, edit script, render again, repeat
until the figure is print-clean. Once locked, the PDF is the paper
artifact.

## Figure 1: Chronic-dose CDF (locked)

ECDF of per-body absorbed energy over the 20 s window, stratified by
tier (Served / Cooperating / Bystander). The proposed multi-body ECBF
precoder is the reference, but since precoders collapse, the curve is
invariant to that choice.

Two iteration passes:

- Pass 1 had a `\,s` LaTeX artifact in the title (from `text.usetex=
  False` in PNG mode) and the aspect ratio was a touch tall (0.78).
- Pass 2 dropped the title (paper caption carries that), tightened
  aspect to 0.70, and adjusted the bystander grey to a slightly darker
  shade for legibility.

What it shows: Served users have the heaviest tail (a few bodies up
to ~2 mJ over 20 s). Cooperating cluster around 100-700 µJ.
Bystanders cluster around 700-1000 µJ. Tier ordering matches physics:
served users have power directed at them, bystanders pick up
sidelobes, cooperating bodies happen to fall in the sidelobe nulls
on average for this geometry.

Tier medians, 20 s trace, multi-body ECBF:

- Served (n=25): 1006 µJ
- Cooperating (n=15): 404 µJ
- Bystander (n=10): 921 µJ

The 10-body bystander curve is coarse (only 10 ECDF steps). A
multi-seed run would smooth this; flagged.

## Figure 2: Hero figure (pending — pivot needed)

The original brief specified a Pareto: x = compliance violation rate,
y = sum-rate, one point per precoder. Given the collapse, all five
points stack on top of each other at (0%, 363 Mbps).

The pivot under consideration: **show the collapse honestly**. A
single-panel scatter with one dot per precoder, x = max p_abs/L over
all body-slots (worst-case approach to the budget), y = mean
sum-rate. Five dots overlap. Annotate the binding distance r* ~ 2.7
m from `tab:bind` next to the cluster, and label the budget slack
(4 orders of magnitude). The visual message is: at this load, the
constraint structure of §IV is academically active but practically
slack, and `tab:bind` correctly predicts that.

Open call for Robin: do we want this honest-collapse plot, or do we
want to crank the load (more served users, smaller plaza, higher
power) until precoders separate, which would mean re-running brief
08 with a different scenario? The first option keeps the paper
faithful to the original §VII.A setup. The second turns §VII into
a stress-test demonstration. The brief is meant to consume brief 08,
not invent a new one, so the first option is the default unless
overridden.

## Figure 3: Pose-info-gain ablation (pending)

Compare pose-aware vs. pose-ablate on plaza-specular at the same
seed. The headline numbers from brief 08 are identical (363 Mbps
both, 1.9e-4 p_abs/L median both). The figure has to either:

- Show slot-level distribution differences via a CDF of per-slot
  delta-sumrate (likely flat at zero, which is the honest finding)
- Or pivot to a 2D pose-info-gain x slot-density heatmap if there's
  any structure in the slot-by-slot deltas

Pending Figure 2 lock so the visual conventions are settled.

## Open questions for the manager

1. **600 slots vs. 9000 slots.** Production runs at 600 slots take
   ~3 min each; at 9000 slots they're ~45 min each. Three passes at
   9000 slots is ~3 hours. The figures' visual layout is identical;
   only the noise floor on confidence bands shrinks. Worth the wall
   time for the paper version, or are 600-slot figures sufficient for
   the JSAC submission?

2. **Multi-seed averaging.** The brief asks for >= 3 seeds for
   confidence bands. Same wall-time question, multiplied: 3 seeds x
   9000 slots x 3 passes = ~9 hours. Robin's call.

3. **Hero figure framing.** Honest-collapse plot (faithful to §VII.A)
   vs. stress-test rerun of brief 08 (more served users / closer
   range / higher power until precoders separate). Default is option
   1 unless overridden.

4. **Whether to also restyle the existing rank-CDF and GPU-bench
   figures** in this convention for visual consistency across §VII.
   The brief calls this a stretch goal. Easy if Figure 1's style is
   the right baseline.

## What's NOT in scope

- The `paper_v2.tex` rewrite of §VII.D narrative. Once the figures
  exist, that's a separate pass.
- Statistical-significance testing. Confidence bands from multi-seed
  averaging is enough.
- Slide deck or conference-talk artifacts.

## Estimated remaining cost

- ~30-60 min of figure iteration (Figures 2 and 3) at the
  critique-iterate cadence.
- Optional ~3 h for 9000-slot rerun, ~9 h for full 3-seed x 3-path
  matrix.
- ~10 min for RESULTS.md, caption stubs, lint, commit, PR.
