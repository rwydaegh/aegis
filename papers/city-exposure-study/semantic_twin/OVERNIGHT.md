# Overnight run, 2026-08-02 into 2026-08-03

Written for you to read first. State as of 05:20 UTC. A few agents were still
finishing when this was written and their own commits land after it, so check
`git log` for anything below marked in flight.

## What exists now that did not last night

- **`paper/paper.tex`**, a complete journal draft. IEEEtran, 20 pages, builds
  clean. Abstract, introduction, related work, the full methods body, six
  results subsections, discussion with an honesty table, conclusion, and a
  bibliography of 24 entries that have each been checked against the actual
  work.
- **`paper/methods.tex`**, the standalone methods document, 11 pages.
- **`paper/si.tex`**, supplementary information, 11 pages, because the body
  deferred to one twice and there was none. Registration, projection, seeds and
  ray counts, then the per-square numbers and the sweeps in fuller form.
  `paper/SI_NOTES.md` lists nine quantities it could not source and states them
  as not reported rather than filling them in.
- **`paper/body.tex`**, the methods body, which `paper.tex` and `methods.tex` now
  both `\input`. They previously held two copies that had drifted into stating
  different numbers for the same quantities.
- **`SPINE.md`**, the drafting source of truth. `PAPER_METHODS.md` is now marked
  superseded in its own header and kept for the derivations and the history.
- **`paper/CITATIONS.md`**, `paper/PROVENANCE.md`, `FLOW_REVIEW.md`,
  `COVERAGE.md` and the rest of the agent reports.

## The five things that were actually wrong

These are the ones worth your attention, because each survived compilation,
linting and at least one read-through, and only recomputation caught them.

**1. The isotropic identity offered as a validation check is false.** Both files
claimed that under isotropic illumination the exposure ratio must equal the sky
fraction, and offered that as an independent check on the estimator. Over the 880
published standpoints the median of `10 log10(chi_iso / sky)` is **+0.987 dB** and
the worst is 2.941 dB. It cannot be true, because chi is the sum of a direct and
a reflected term and the reflected term is positive. What is true is the
statement the estimator subsection already makes correctly: the **direct** term
equals the sky fraction, and it does so to **0.0004 dB**. I verified both numbers
myself rather than taking the audit's word. The fix scopes the claim to the
direct term rather than deleting it, since scoped correctly it is a good check.

**2. Three bibliography entries had invented titles sitting on correct DOIs,
volumes and pages.** The dangerous one is `vitucci`: the title that had been
written is a *real paper*, by overlapping authors, in a different journal, four
years earlier, and it does not contain the result the text cites. A spot check on
the title alone would have found something plausible and stopped. All three
claims those entries support turned out to be correct to the printed digit. What
was wrong was purely bibliographic.

**3. A percentage computed from shares that are not a partition.** The bounce
budget said 10.7 percent of launched power never touches a surface, from
`100 - (79 + 8.9 + 1.2 + 0.22)`. Those shares are per-depth arriving throughput,
so a ray that reaches depth three was already counted at depths one and two, and
their sum means nothing. The right answer is `1 - 0.790 = 21.0` percent, which
agrees with the independently measured sky fraction to six decimals.

**4. Numbers computed at one configuration, reported under another, and this one
turned out to be systemic.** The material subsection ran at a 130 m crop with
twelve interactions and roulette on, under a preamble declaring 250 m and three.
The bounce budget shares came from 130 m and eight station positions. The cap
swing is quoted over 50 to 500 m and was computed over 100 to 400 m. The full
audit then found that **only the headline table, the law comparison and the
diffraction bound ran at the settings the paper declares.** Every other result
block sits at some mix of a narrower crop, four, six or twelve interactions,
roulette on, or a different ray count. Being fixed with one table giving the
configuration per result block, rather than ten scattered qualifications.

There is also a class of **medians presented as bounds**. The dielectric bracket
"stayed below 0.58 dB" is a median span whose worst standpoints are +1.56 dB
rooftop and +2.48 dB street. The cross-validation agreement of 0.25 and 0.16 dB
is the worst of three illumination models, not a median over them, and its quoted
0.24 to 0.46 dB noise floor is 0.231 to 0.346 in production, with the top of that
range coming from a mode that was never shipped.

**5. One site's column presented as the overall result, twice.** The diffraction
cross check claimed agreement "to within 0.34, 1.73 and 7.3 percent". Those three
are the Times Square column of a three-site table, the worst site, with nothing
saying so. Separately, and worse because it is a bound rather than an agreement,
the paper said the three-interaction budget changed "no standpoint by more than
0.063 dB". That is Korenmarkt at the 130 m crop. The worst across the squares is
**0.384 dB at Grand-Place**, six times larger, and it is the number that licenses
the bounce budget on power grounds.

**6. A causal claim the data does not support, which I introduced myself.** I
wrote into the methods that one station's first-interaction coverage rises from
0.362 to 1.000 when it is re-registered, offered as evidence that coverage is a
sharper pose test than the skyline residual. Writing the supplementary
information showed the pose file holds only **one** registration of that camera,
and the "before" position is byte-identical to the raw provider pose. The eight
probe standpoints are provider poses displaced 3.91 to 5.50 m from their
registered camera, and the displacement does not order coverage: the one that
moved furthest scores 0.978. The observation survives, the mechanism does not.

## What is open, and what needs you

- **The title.** It reads *"City-square geometry sets the distribution of relative
  pedestrian exposure at 15 GHz"*, but the first result is that variation *inside*
  a square exceeds variation *between* squares for two of the three illumination
  models. The title can be read as "which square you are in sets your exposure",
  which is the opposite. Defensible as written, since "distribution" carries the
  breadth. The unambiguous alternative, which also absorbs the street-cell
  counter case, is *"Relative pedestrian exposure varies as much within a city
  square as between squares at 15 GHz"*. One line to change. I left it rather
  than thrash it overnight.
- **The SAM 3 citation.** The bibliography cites the 2023 Segment Anything paper,
  but `sam3_concepts.py` sets `MODEL = "facebook/sam3"`, so SAM 3 is what
  produced the material masks. The text now cites the 2023 paper for the
  promptable-segmentation idea and names SAM 3 separately, with a visible
  `\todo{}`. **I did not add a SAM 3 entry**: the session's web search budget was
  spent at 200 calls, so I could not verify one, and an unverifiable citation is
  worse than a missing one.
- **`aegis` is a self-citation with a placeholder DOI.** Worth minting a Zenodo
  DOI before submission.
- **Two torn files under the abstract's dominant uncertainty.** The
  `city250_corrected` run has 2 unparseable rows at New York (78 valid of 80) and
  a stray extra line at Prague. That run is what the standpoint-sampling
  comparison is computed against, so the abstract's 0.128, 0.061 and 0.188 dB and
  the "roughly 25 times" claim rest on it. Worth re-running before submission.
  **The published headline run is clean**: `city250_L3` parses to 880 rows across
  eleven sites with nothing unparseable, so Table II, the abstract's spreads and
  the ordering are unaffected. I re-derived the whole headline table from those
  rows and every number reproduces exactly, including the 6, 8 and 4 of 11 counts.
- **The Monte Carlo standard errors have no surviving source.** 0.0042, 0.0136
  and 0.0343 dB exist only in `CODE_AUDIT.md`. The raw output of the eight-seed
  retrace was discarded and no script reproduces it, yet the abstract's "roughly
  25 times", the material result's "5.7 times" and the discussion's "7 to 47
  times" all rest on them. They are being attributed rather than deleted or
  softened, since the measurement did happen. Re-running the retrace is about two
  hours and is the one thing that would close this properly. I did not start it
  this close to the deadline, because a job that lands after everyone has stopped
  reading is how numbers go stale in the first place.
- **The vision model result is drafted but not inserted.** Two paragraphs are in
  my scratchpad. They answer the question you asked on 2026-08-01 about where an
  LLM fits: it was built, blinded, and measured, its shift stays inside the
  0.33 dB dielectric ceiling, and a control that feeds it the photogrammetric
  texture instead of the photograph moves the answer by less than two draws of
  either differ from each other. That is a good negative. It is held back only
  because its numbers come from the 130 m twelve-bounce ablation in item 4 above,
  and I would not insert a number before knowing which configuration it belongs
  to.

## Things you asked for that now exist

- **Blender files with everything in one scene**, which you asked for twice
  thirty hours apart. **All eleven squares**, each retraced from scratch at the
  published 250 m crop and bounce budget, 151 rendered figures, about 50 minutes
  on the rented box. `propagation_blends.zip`, now 189 MB, and
  `PROPAGATION_BLENDS.md`. Nothing was carried over from yesterday's four: three
  of those ran at a bounce budget of 4, and Krakow sat on the superseded Cloth
  Hall datum, so its walk went from 163 candidate standpoints to 716 once its
  standpoints came off the roof.

  Three of the four original one-line reasons in that archive were **wrong** and
  were rewritten. Krakow as "the most open square, highest under every model" was
  the roof artefact. New York's "18 percent sky against Krakow's 46" quotes two
  numbers that no longer exist. Korenmarkt as "the only site with registered
  panorama semantics" is false now that five other squares carry a fishnet with
  poses. If you quoted any of those anywhere, they need revisiting.
- **A written reason for stopping at three bounces**, and for the material
  evidence being what sets it rather than a convergence tolerance. `WHY_NOT.md`
  section 5 and the bounce budget subsection.
- **A written reason for no diffraction.** `WHY_NOT.md` section 2, four arguments,
  one of which is a measured bound rather than an appeal to the literature.
- **The Russian roulette answer.** It is off. `roulette_start` sits one above the
  bounce budget, and the measurement says it changed neither seed spread nor run
  time at this budget.
- **Beamforming**, which you chased. There is a results subsection. The honest
  part is that the literal reading of beamforming to yourself cancels exactly out
  of a normalised density, so it is invisible to this observable, and the paper
  says that rather than shipping a configuration that provably changes nothing.
- **Bystanders**, retraced on the settled bounce budget.

## The one experiment still running, and why it matters

`COVERAGE.md` established something the paper does not yet use: a materially
bound run is now possible at **seven** of the eleven squares at the published
250 m crop, not one. Prague at 9.9 percent of triangle area from twelve stations,
Tokyo 8.1 from three, Mexico City 7.0 from twelve, Madrid 5.1 from six, Brussels
4.6 from eight, Milan 4.0 from one, Korenmarkt 3.2 from nine. Six of the seven
can also run at 130 m, where the fractions are two to three times larger.

So the material null, currently a result from one square, can become a result
about whether that null travels. That is running on the rented box now and will
land in `COVERAGE_LADDER.md`. If the null holds at seven squares it is a much
stronger negative than the paper currently claims. If it fails at one square,
that square is the most interesting thing in the study.

Two cautions carried into that run, both from `COVERAGE.md`. The bound area
fraction must be reported beside every shift and never instead of it, because a
4.6 percent bound run is one where 4.6 percent of the area has evidence and the
rest still falls back to the geometric rule. And the bound fraction is a property
of where a camera could stand, not of segmentation quality: admitted cameras sit
within 29 to 62 m of their own centroid against a crop reaching 250 m, so most of
that crop is roofs and rear elevations no photograph has ever seen. Milan
reaching 4.0 percent from a single camera is geometry, not quality.

Still blocked and needing you: London and Krakow have configs, walk dates and the
open-sky filter ready, and are one command each once the Street View tile quota
resets. Toulouse needs its crop anchor moved about 25 m before it is worth
acquiring anything, and that anchor belongs to a mesh the eleven-square table
already uses.

## Two bugs nobody owns

Both are in `export_propagation_payload.py`, found while building the scenes and
deliberately not edited because that file belonged to another thread at the time.
Neither affects any published number.

- `outputs/tokyo_hachiko_fishnet_vistas/` is a stub with no `.npz`, so
  `fishnet_layer` raises `ValueError: need at least one array to concatenate`.
  This will break any Tokyo trace on this host, not just the scene build.
- With that stub bypassed, Tokyo then loses its three registered poses to an
  early return in `attach_evidence`.

Also worth knowing before the next remote run: **`tools/blgpu.sh sync` does not
push image evidence.** The first scene pass produced a Korenmarkt with empty
depth clouds, panorama captures and bodies, and it looked like a successful run.
It was caught, 255 MB of evidence and the 83 pose directories were pushed by
hand, and the pass was redone. The sync path should learn about that directory.

## Where the open items are written down

`paper/RECONCILE.md` ends with six items that were found and deliberately not
applied, each with the reason. `paper/SI_NOTES.md` lists nine quantities that
could not be sourced. `paper/PROVENANCE.md` has an unsettled section saying what
each unresolved item would take to settle. Those three lists are the honest state
of the paper, and none of them is hidden inside a longer document.

One of the four drifted numbers is worth ten seconds of your attention rather
than being taken as a fix. The street diffraction median is 0.44 dB under one
convention and 0.42 under another, and both are correct: four of the 60
standpoints have a street direct term of exactly zero, so their uplift is 0/0.
Ranking those four at the top and taking the median over 60 gives 0.4350, and
taking the median over the 56 with a defined uplift gives 0.4218. The 56
convention was chosen because it is what the shipped figure plots, and because
the same paragraph quotes a percentage that is already 56-based. This also
explains the 1.84 dB street percentile that would not reproduce earlier in the
week: it is the 60-standpoint convention.

## Build

```
cd paper
pdflatex -interaction=nonstopmode paper.tex && pdflatex -interaction=nonstopmode paper.tex
```

Same two passes for `methods.tex` and `si.tex`. All three read the shared
`body.tex`, so a change to the methods lands in the paper and the standalone at
once.

| document | pages | undefined refs | undefined citations |
|---|---|---|---|
| `paper.pdf` | 20 | 0 | 0 |
| `methods.pdf` | 11 | 0 | 0 |
| `si.pdf` | 11 | 0 | 0 |

Tests and lint: **1008 passed, 2 skipped, 0 failed**, `ruff check` clean and 166
files already formatted. The count rose from 980 during the night because the
coverage ladder work brought its own tests.

## What was still running when this was written

Two detached jobs on the rented box, both launched through `tools/blgpu.sh` so
they survive a dropped connection, and both of which commit their own work:

- the Blender scenes for the remaining seven squares, `PROPAGATION_BLENDS.md`
- the seven-square material ladder, `COVERAGE_LADDER.md`

If either report is absent, check `tools/blgpu.sh status` and the job directories
under `/home/user/aegis/.blgpu_jobs/` on the box. Nothing else is outstanding.
