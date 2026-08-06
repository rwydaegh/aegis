# Style pass on paper.tex

A prose-only pass against `/home/user/PaperMaker9000/RULES_SUPERLIST.md`,
`.claude/ai_writing_tells.md` and `.claude/rules/docs-style.md`. No number, claim,
hedge, section order or figure placement was changed.

## Build result

| | pages | undefined refs | undefined cites | overfull hboxes |
|---|---|---|---|---|
| before | 18 | 0 | 0 | 1 (tab:models, pre-existing) |
| after | 19 | 0 | 0 | 1 (same one) |

The nineteenth page is **not** from this pass. Two other agents were editing the
same file during it. Rebuilding the current file with only their four-line
insertion in "Eleven squares" removed gives 18 pages, so every edit listed below
is page-neutral. The overfull box at the illumination-model table pre-dates this
pass.

## Rules that came back clean on a grep

No em dashes (`---` or Unicode), no semicolons outside `\;` math spacing, no
contractions, no first person plural, no `the fact that`, `in order to`, `due to`,
sentence-initial `However`, `yields`, `obtains`, `executes`, `In summary`,
`It is worth noting`, `not only ... but also`, bare `Figure`/`Tab.`, or title-case
headings. The excess-vocabulary sweep (Tier A and B of the corpus list plus the
Kobak common set) returned two hits total, both `very`, both fixed. The draft was
already close to the house register, so most of what follows is sentence-level.

## Substantive rewrites

Rows marked **M** are inside the copy of `methods.tex` that lives in `paper.tex`
(Sections III to VII, `\section{Exposure ratio}` through `\section{Validation}`).
`methods.tex` itself was not touched, so those rows are the reconciliation list.

| # | rule | before | after |
|---|---|---|---|
| 1 | parallel form | "counts that are neither public nor properties of the square" | "counts that are not public and are not properties of the square" |
| 2 | pronoun sentence opener | "They exceeded the between-square spread" | "Those spreads exceeded the between-square spread" |
| 3 | case redundant | "roughly 25 times the Monte Carlo error in the isotropic case" | "roughly 25 times the isotropic Monte Carlo error" |
| 4 | metric movement verb, clarity | "Those network variables put the open-ground power density over nearly three orders of magnitude, from 0.0075 to 3.0..." | "Those network variables leave the open-ground power density anywhere from 0.0075 to 3.0... , a span of nearly three orders of magnitude." |
| 5 | anthropomorphism, parallel form | "greater than one when reflection wins" | "greater than one when they return more than they block" |
| 6 | abstract subject + filler agency verb | "the image-coverage budget that combination makes possible" | "the image-coverage budget that is available only once the camera and the ray source share a point" |
| 7 | coined term | "reports the six result beats" | "reports six results" |
| 8 | pronoun sentence opener | "It compares the property left after the same network is divided out, and it does so at a frequency..." | "What it compares is the property left after the same network is divided out, at a frequency..." |
| 9 | ambiguous pronoun | "It rests on title and abstract indexing across four databases" (nearest noun was "limit", intended subject was "the survey") | "The survey rests on title and abstract indexing across four databases" |
| 10 | staccato sentences | "...under most of the illumination models considered, rather than under all of them, and where a pedestrian stands matters more..." | "...under most of the illumination models considered, though not under all of them. Where a pedestrian stands matters more..." |
| 11 | clarity | "The eleven-city shifts were not common level changes." | "The eleven-city shifts were not a common change of level." |
| 12 | elegant variation | "The former and corrected rankings"; "The old law"; "the old rooftop answer" | "The earlier and corrected rankings"; "The earlier law"; "the earlier rooftop answer" |
| 13 | anthropomorphism | "narrow near-horizontal channels between its towers, which the old law rewarded" | "...which is where the earlier law put most of its weight" |
| 14 | clarity | "so the design resolved a shift that remained a small part of one decibel" | "so the design resolved the shift rather than missing it, and the shift is a small part of one decibel" |
| 15 | clarity | "Diffraction is small for two models and fails that description for the third." | "Diffraction is small for two models and not for the third." |
| 16 | coined term | "An older street-cell evidence-ladder value of 0.079 dB" | "An older street-cell value of 0.079 dB" |
| 17 **M** | pronoun sentence opener | "It transfers between cities, which a power density does not." | "The ratio transfers between cities, which a power density does not." |
| 18 **M** | pointing with "That", colloquialism | "...tracing rays from each one to the person. That is the expensive way round." | "...tracing rays from each one to the person, which is the expensive direction to work in." |
| 19 **M** | no very | "the very nearest street level sources" | "the nearest street level sources" |
| 20 **M** | clarity | "so the campaign carries the weaker claim rather than the stronger one:" | "so the campaign supports the weaker of the two readings:" |
| 21 **M** | staccato sentences | "The mechanism is the ordinary one: a diffracted field falls off..."; "Diffraction is a correction to a picture that reflection already describes, which is the opposite of its role at the metre wavelengths where street models were first built and where an edge is only a few wavelengths away from everything." | "The mechanism is the ordinary one. A diffracted field falls off..."; "Diffraction is therefore a correction to a picture that reflection already describes. At the meter wavelengths where street models were first built an edge is only a few wavelengths away from everything, and the two roles are reversed." |
| 22 **M** | colloquialism | "found the over the top mechanism beating street level scattering by 7 dB" | "found the over-the-top mechanism better than street level scattering by 7 dB" |
| 23 **M** | pointing with "That" | "That is the right direction for an omission to run in an exposure study" | "A low bias is the right direction for an omission in an exposure study to run" |
| 24 **M** | word order | "no argument here is offered that it is" | "no argument is offered here that it is" |
| 25 **M** | fragment, existential opener, dangling "which" | "Two limits on the borrowed half of this. There is a body of work in which a diffraction shaped model fits around a corner at 28 GHz better than a scattering one does, which read alone points the other way." | "Two limits apply to the part of this argument that is borrowed from the literature. One body of work fits a diffraction shaped model around a corner at 28 GHz better than a scattering one, and read alone it points the other way." |
| 26 **M** | pronoun sentence opener | "It does not survive reading the fitted constant" | "That reading does not survive the fitted constant" |
| 27 **M** | colloquialism | "The functional form wins" | "The functional form fits" |
| 28 **M** | sentence-initial "And", terse verbing | "And all of the published decompositions ... in street canyons, which waveguide, rather than" | "All of the published decompositions ... in street canyons, which act as waveguides, rather than" |
| 29 **M** | clarity, read-twice sentence | "What the average costs can be bounded instead, and the bound has two sides." | "The cost of the average can be bounded instead, and the bound has two sides." |
| 30 **M** | comes-from, dropped article, pronoun opener | "The mesh comes from aerial..."; "Radius 250 m is not a free choice"; "It should not be confused with the 250 m..." | "The mesh is built from aerial..."; "The 250 m radius is not a free choice"; "That radius should not be confused with the 250 m..." |
| 31 **M** | comes-from, while-as-although | "Imagery comes from two providers"; "while the multi-station route" | "Imagery is taken from two providers"; "whereas the multi-station route" |
| 32 **M** | colloquialism | "One thing belongs here rather than there, though." | "One thing belongs here rather than there." |
| 33 **M** | jargon, internal consistency | "the image derived arm can claim one square" | "the image derived path can claim one square" (matches "An optional path" earlier in the same subsection) |
| 34 **M** | filler adverb | "the materials ordinary European squares are actually built from" | "the materials ordinary European squares are built from" |
| 35 **M** | colloquialism, anthropomorphism | "makes $r_{\max}$ load bearing"; "how much of the answer they own" | "makes $r_{\max}$ matter"; "how much of the answer they contribute" |
| 36 **M** | fragment | "Nearly three orders of magnitude, set entirely by numbers that are not public. That spread is the reason..." | "That is nearly three orders of magnitude, set entirely by numbers that are not public. The spread is the reason..." |
| 37 **M** | comma splice | "$Q$ is not approximately unchanged, it is the same function, and the estimator..." | "$Q$ is not approximately unchanged. It is the same function, and the estimator..." |
| 38 **M** | no very, metric movement verb | "suppresses the very multipath this paper is measuring and pushes $\chi$ toward" | "suppresses the multipath this paper is measuring and moves $\chi$ toward" |
| 39 **M** | while-as-although | "a sidelobe factor no greater than one while the denominator's is the peak itself" | "...no greater than one, whereas the denominator's is the peak itself" |
| 40 **M** | kiss simple verbs | "The street model crowds its entire mass into the lowest tens of degrees" | "The street model puts its entire mass into the lowest tens of degrees" |
| 41 **M** | metaphor / coined usage | "The evidence leg is not unlimited either"; "Both legs are used here" | "The evidence does not reach indefinitely either"; "Both arguments are used here" |
| 42 **M** | pointing with "That" | "That is the co-located picture of Section III in its strictest form" | "This is the co-located picture of Section III in its strictest form" |
| 43 **M** | pronoun sentence opener | "It had passed the skyline residual gate, so first interaction coverage is the sharper test of a pose, and that station is excluded." | "That station had passed the skyline residual gate, so first interaction coverage is the sharper test of a pose, and it is excluded." |
| 44 **M** | while-as-although | "the third about 89%, while beyond 40 m" | "the third about 89%, whereas beyond 40 m" |
| 45 **M** | jargon verb | "are not to be differenced" | "should not be subtracted from one another" |
| 46 **M** | subject verb early (fronted participle) | "Traced against an eight interaction reference over 40 of these standpoints at fixed seeds, so that only the budget moves, $L = 3$ costs a median of 0.002 dB..." | "$L = 3$ costs a median of 0.002 dB and never moves a standpoint by more than 0.063 dB when it is traced against an eight interaction reference over 40 of these standpoints at fixed seeds, so that only the budget moves." |
| 47 **M** | pointing with "That", filler adverb | "That is not the same number as the 0.23% above"; "the power that actually escapes" | "This is not the same number as the 0.23% above"; "the power that escapes" |
| 48 **M** | read-twice sentence | "What the trace itself then approximates reduces to a single one sided truncation whose size is quoted above." | "The only approximation left in the trace itself is a single one sided truncation, whose size is quoted above." |
| 49 **M** | referential clarity | "Two parameters are measured here, and a third is corroborated rather than chosen." (three things then follow, and which one is the third is never said) | "Two parameters are measured here, and a third, the bounce budget, is corroborated rather than chosen." |
| 50 **M** | comma splice, pointing with "That" | "That is not a defect of the estimator, it is what a uniform site density over an unbounded plane does" | "This is not a defect of the estimator. It is what a uniform site density over an unbounded plane does" |
| 51 **M** | preposition-final pointing | "and that is the quantity the results lead with" | "and the results lead with that contrast" |
| 52 **M** | kiss simple verbs | "one trace collapses to an elevation histogram" | "one trace reduces to an elevation histogram" |

> **Old illumination law, see `../docs/LAW_CHANGE.md`.** Rows 11 to 13 and row 40 rewrite
> sentences that describe the old law, its eleven-city shifts, the earlier rooftop answer
> and the street model's mass near the horizon. The style rulings survive and apply to
> whatever replaces those sentences, but the before-and-after text in those four rows is a
> record of prose that is going away.

## Two mechanical passes, applied document-wide

Both fix a split that ran exactly along the methods/results seam, so a reader
sees the convention change halfway through the paper.

**American spelling** (`latex.substitutions.american_spelling`). The methods half
was British and everything else was already American (`organized`, `normalized`,
`polarization`, `generalization`, `amortization`, `discretized`, `Modeled`,
`Unpolarized`). The whole body, lines 1 to 1608, was converted to American. Word
list, so this is one `sed` to replay or revert on `methods.tex`:

```
normalisation->normalization  normalised->normalized  polarisation(s)->polarization(s)
polarised->polarized  unpolarised->unpolarized  depolarised->depolarized
equalised->equalized  randomised->randomized  modelled->modeled
travelling->traveling  defence->defense  artefact->artifact
neighbour(hood)->neighbor(hood)  centreline->centerline
millimetre->millimeter  kilometre->kilometer  metre(s)->meter(s)
```

The bibliography (line 1609 onward) was excluded, so the Adhikari title keeps its
published spelling "millimetre".

**Percent spacing** (`latex.substitutions.no_space_before_percent`). The methods
half wrote `88\,\%` and the rest wrote `88\%`. All 17 thin spaces were removed.

## Flagged by the corpus and deliberately not changed

- **"These are close precedents, not omissions in earlier work."** The corpus
  near-bans the `X, not Y` contrastive correction. Here the `not Y` tail is the
  credit being given to Wiame and Varsier, which is honesty content, not a
  rhetorical move. Kept.
- **"Quantities that come for free"** as a subsection heading. Mildly colloquial,
  but it is clear, it is in the register the paper is deliberately writing in,
  and the alternatives are all stiffer. Kept.
- **Figure panels referenced by position.** `fig:eleven-exposure` ("The left
  panel ... the middle panel ... the right panel"), `fig:crop-convergence` ("The
  top panel ... The bottom panel") and `fig:bounce-budget` ("The top row ... The
  bottom row") all break the rule that subpanels are referenced by label. Wout
  has crossed exactly this wording before. Fixing it means adding (a)/(b)/(c)
  labels inside the figures, which is beyond a prose pass. Left for whoever owns
  the figure scripts.
- **Compound hyphenation.** The methods half leaves compounds open ("street level
  model", "near horizontal", "free space answer", "image derived") and the results
  half hyphenates them ("street-cell model", "near-horizontal", "open-ground",
  "image-based"). This is a real inconsistency and it is more invasive than
  spelling, since it needs a judgment per compound rather than a word list. Not
  applied.
- **`Section~\ref{}` versus `\Cref{}`.** Sections are cross-referenced by hand
  while figures and tables go through cleveref. Cosmetic, and changing it needs a
  `\crefname` for sections. Not applied.
- **`comes from` at "the multi-station route ... comes from a second, community
  sourced provider".** The corpus rule targets casual causal use. This is
  provenance and reads plainly. Kept.

## Skipped because another agent is editing them

Reported here rather than applied, per the two coordination notes.

- **"Bystanders alter the arriving distribution"** (Results). Untouched. The only
  style item in it is that "The trace rejects that prediction" is a strong verb
  for a paired 12-standpoint study on a superseded six-interaction configuration,
  which the paragraph itself concedes four sentences later. Consider
  "contradicts" or "does not bear out".
- **The bystander paragraph inside "Body coupling"** (the paragraph beginning "The
  obvious next step is to predict each model's sensitivity"). Untouched for the
  same reason, since it carries the same numbers. Two items in it: `while` is used
  for `whereas` at "takes the isotropic loss from 0.05 to 0.71 dB while the
  rooftop and street columns move only", the last unfixed instance in the paper;
  and "it is instructive that this fails" editorializes where the plain statement
  is stronger.
- **"Beamforming depends on what the beam follows"** (Results). I had edited two
  sentences here before the second coordination note arrived and **reverted both**
  so the incoming rewrite applies against the original text. The reverted edits
  were: "A nearest-grid codebook sweep has no reported values" to "No values are
  reported for a nearest-grid codebook sweep", and "Its reduction is bounded
  above" to "The reduction from best-beam selection is bounded above" (the
  antecedent of "Its" was two nouns back). Re-apply the second one if the sentence
  survives the rewrite.
- One other agent inserted four lines at the end of the "Eleven squares"
  subsection. That text forward-references `Section~\ref{sec:results}` from inside
  Section `sec:results` ("Section~\ref{sec:results} shows later that..."), which
  will render as a self-reference. Not mine to fix, but it should be.

## Where the writing is protecting a weak argument

This is the part worth arguing about. Five places, roughly in order of how much
they matter.

**1. The abstract lets the image evidence sound like it covers eleven squares.**
The abstract says "co-located photographs cover the early interaction surfaces"
in the method sentence and then "Image-based facade materials shifted
distribution medians by 0.024, 0.029, and 0.022 dB" in the results. Nothing in
the abstract says those two things happened at one square. The body is explicit
and creditable about it, in "Surfaces and materials": "The cross city comparison
is run with geometric classes at every square and carries no image evidence at
all", and "until that is fixed the image derived path can claim one square".
Table `tab:honesty` also carries the row. So the paper is honest at depth and
optimistic on the front page, and the front page is the part that gets indexed.
This is a claim-scope question, not a wording question, so I did not touch it. A
five-word insertion ("at the reference square") in the results sentence of the
abstract would close it.

**2. The bounce budget is warranted at one square and spent at eleven.** Section
"Bounce budget" sets `L = 3` from where the material evidence stops, and the
evidence in question is photographic coverage measured on one walk at Korenmarkt.
The section separates the geometric question ("a property of the formulation and
holds in any square") from the evidential one ("a property of this particular set
of panoramas") very cleanly, which is why the hole is easy to miss: the reader is
never told which of the two licenses `L = 3` at the other ten squares. The
convergence argument does cover it, and the paragraph beginning "What makes three
sufficient rather than merely defensible" supplies it, but that paragraph is
explicitly demoted to the second leg of the argument. As written, the strong leg
does not reach the headline result and the weak leg does.

**3. "The first is that it has been measured, at almost this frequency and in
this kind of geometry."** The decisive observation in that paragraph, no arrival
above the noise floor at the diffracted delay, is at 58.68 GHz at one location by
a manual trace. The paragraph discloses all three of those qualifiers two
sentences later, which is good. But the topic sentence borrows the 14.8 GHz
proximity for an observation that is not at 14.8 GHz, and a topic sentence is
what a skimming referee reads. The frequency-scaling measurement, 3.0 to 3.5 dB
per decade, *is* across all three bands and would carry the topic sentence
honestly on its own.

**4. "Both are reported alongside $\chi$" is a promise the paper does not keep.**
Section "Quantities that come for free" says the sky fraction and the mean excess
path length both fall out of the trace and are both reported. The sky fraction is
reported, in `fig:eleven-exposure` and in the crop-convergence result. The mean
excess path length and the delay spread appear nowhere else in the paper. Grep
confirms it: two hits, both in that subsection. Either report a number or say the
quantity is available and not used here.

**5. The title claims more than the first result supports.** "City-square
geometry sets relative pedestrian exposure at 15 GHz", against a first result
whose own summary is that "a single number per square is a poor summary of that
square" and that "where a pedestrian stands matters more than which of these
eleven squares they stand in". The paper is measuring a distribution and the
title names a scalar. Not a prose defect and not mine to change, but the tension
is on page one against page eight.

A sixth, smaller one, now probably moot: "Its reduction is bounded above by the
geometric-steering reduction" asserted a bound with no supporting argument in a
sentence that also admitted the quantity was never computed. The concurrent
beamforming rewrite is reported to be fixing exactly this.
