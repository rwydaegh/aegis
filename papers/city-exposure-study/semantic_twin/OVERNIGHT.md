# Overnight run, 2026-08-02 into 2026-08-03

Written for you to read first. State as of 05:20 UTC. A few agents were still
finishing when this was written and their own commits land after it, so check
`git log` for anything below marked in flight.

## What exists now that did not last night

- **`paper/paper.tex`**, a complete journal draft. IEEEtran, 19 pages, builds
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
  thirty hours apart. Four squares were built yesterday, the remaining seven were
  in flight when this was written. `propagation_blends.zip` and its README.
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

## Build

```
cd paper
pdflatex -interaction=nonstopmode paper.tex && pdflatex -interaction=nonstopmode paper.tex
```

Tests and lint at the time of writing: **980 passed, 2 skipped, 0 failed**,
`ruff check` and `ruff format --check` both clean.
