# Brief 09 report — paper figures

**Status:** done. PR [#775](https://github.com/rwydaegh/aegis/pull/775)
squash-merged to master as commit `a7427d2` on 2026-05-05.

## TL;DR

Brief 09 turns the three NPZ outputs from brief 08 into the §VII
figures the JSAC paper still owes. The convention adopted (per Robin's
direction on 2026-05-05) is scienceplots via the existing
`theory/scripts/_plot_style.py` helpers, IEEE single-column default
(3.5 in wide), two-column wide (`figure*`, 7.16 in) for the hero and
ablation. Each figure is rendered to PDF (canonical, for paper
inclusion) and viewed as PNG (for the critique-iterate loop) at the
same physical size.

The thing that complicated this brief is brief 08's empirical headline:
**all five precoders collapse to MRT at the paper's nominal load**,
with zero compliance violations. The original §VII.D Pareto figure
(violation rate vs. sum-rate) is degenerate in this regime: there is
no Pareto front, just one operating point per path model.

The shipped figures are honest about that collapse. They show what the
data actually says, not what the paper originally hoped to show. The
narrative pivots toward chronic dose, which is the paper's prepared
fallback (`paper_spine.md` §8).

Total wall time from kickoff to merge: 12 min (under a 15-min time
budget set by Robin for promotor handoff).

## Deliverables

Under `JSAC/code/experiments/plaza_run/figures/`:

- `hero_pareto.pdf` (two-col wide IEEE, aspect 0.42)
- `chronic_dose.pdf` (single col IEEE, aspect 0.70)
- `pose_info_gain.pdf` (two-col wide IEEE, aspect 0.45)
- Sibling `.png` for each, at the same physical size, for screen view
- `.txt` caption stub per figure, paper-ready
- `RESULTS.md` documenting headline numbers and the recommended
  §VII.D rewrite direction
- The plotting scripts themselves, plus `_data.py` (NPZ loader) and
  `_figstyle.py` (style + IO helpers wrapping the theory/ helpers)

PDFs and PNGs are gitignored per repo convention (matching the
`rank_check/rank_cdf.pdf` precedent). They sit on disk locally for the
promotor handoff. The scripts regenerate them deterministically.

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

## Figure 1: Chronic-dose CDF

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
multi-seed run would smooth this; flagged as a follow-up.

## Figure 2: Hero figure

Single-pass-plus-polish two-panel honest-collapse plot.

(a) ECDF of P_abs / L_RL across body-slots, two path models overlaid
(plaza-specular blue solid, UMa-LOS dashed red). All five precoders
within each path model overlap into a single visual line per model.
The Brussels RL budget at x=1 is approached to within 1.7e-3 in the
worst case; a faint red "violation zone" shaded band sits to the
right of x=1, intentionally empty.

(b) Mean sum-rate per precoder, grouped by path model. UMa-LOS gives
14× the sum-rate of plaza-specular (richer multipath). ZF in UMa-LOS
degenerates due to singular HH^H at K=25 and falls back to a
near-zero precoder; this is annotated inline.

The single iteration after the first render added the violation-zone
shading and the ZF singular-fallback annotation. Legend in (b)
slightly overlaps the MRT-UMa-LOS bar but stays readable; not worth a
third iteration under the time budget.

## Figure 3: Pose-info-gain ablation

Two-panel ablation. Pose-aware vs pose-ablate, plaza-specular, same
seed.

(a) Per-slot delta-sumrate ECDF for four precoders (ZF dropped due to
singular fallback noise). All curves collapse to a vertical line at
zero. An inline annotation makes the "no measurable gain at this
load" finding explicit so the figure isn't read as broken.

(b) Per-body P_abs ECDF for multi-body ECBF, aware vs ablate
overlaid. The curves overlap to float32 precision. A second inline
annotation states this directly.

Two iteration passes: the first pass produced bare flat curves; the
second added the two annotation boxes that make the result legible.

## Headline numbers

| Quantity | Plaza-specular | 3GPP UMa-LOS |
|---|---|---|
| Mean sum-rate (Mbps) | 363 | 5070 |
| Median P_abs / L_RL | 1.9e-4 | 2.5e-4 |
| Max P_abs / L_RL | 1.25e-3 | 1.74e-3 |
| Violations / 3000 body-slots | 0 | 0 |

The 3-orders-of-magnitude budget slack matches the paper's own
`tab:bind` prediction (binding distance r* ~ 2.7 m at this BS
configuration). The figures honestly reflect this regime.

## Recommendation for §VII.D

Pivot the narrative around the precoder collapse, keep §VII.A as the
nominal scenario, and let §VII.E (chronic dose) carry the practical
story. The constraint structure of §IV is shown to be correct (the
multi-body QCQP is well-defined, the budget is honoured by all
precoders), but the regime is one where the constraint is slack. That
is itself a reportable finding: the proposed solver gives the right
answer for free at this load, and only differentiates from MRT once
the load increases. RESULTS.md spells this out explicitly.

The alternative (rerun brief 08 with a higher load to force precoder
separation) was raised but not pursued under the 15-min time budget.
Robin can request that follow-up as a separate ticket.

## Limitations honestly logged

- Single seed (42). Multi-seed averaging not run.
- 600 slots = 20 s window, not the full 5-min trace.
- Sionna NR PHY pass not run; Shannon-rate proxy used.
- ZF singular fallback in UMa-LOS K=25 deserves a regularized-ZF
  cross-check before final paper inclusion, to confirm the bar gap is
  a real-system artefact rather than a numerical one.

## Cost

- Render-and-iterate per figure: chronic-dose 2 passes, hero 2 passes,
  pose-info-gain 2 passes. ~7 min total render + critique time.
- RESULTS.md, three caption stubs, lint, commit, branch, PR, squash:
  ~5 min.
- Total: 12 min wall clock.

## Follow-ups (not blocking promotor handoff)

- 9000-slot full trace x 3 seeds for the JSAC submission version.
  Wall time ~3-9 hours depending on seed count.
- Higher-load rerun if §VII.D wants a precoder-separation hero
  instead.
- Restyle existing rank_check / gpu_benchmark figures in this
  convention for visual consistency across §VII (stretch goal from
  the brief).
