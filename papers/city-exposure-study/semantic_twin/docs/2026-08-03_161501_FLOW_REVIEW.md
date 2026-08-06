# Flow review: paper/methods.tex

Reviewed against `methods.tex` at md5 `19aac0429790c5f4ade3509d294fb86f`, 779 lines,
builds clean to 7 pages (one 5.3 pt overfull hbox at Table 2, cosmetic). The file moved
twice while I was reading it, so line numbers are from that hash.

**Verdict up front.** The spine is sound and the draft mostly does not fall out of the sky
any more. Every number I could recompute reproduces exactly (see "What is already right").
There are two real contradictions, one terminology collision that costs the reader more
than anything else in the file, and a set of splice seams from today's inserts. About
fifteen edits fixes all of it.

House style is clean: no em dashes, no semicolons outside `\;` math spacing, all headings
sentence case, no banned vocabulary. Two coined-phrase hits and two `we`s, listed at the
bottom.

---

## 1. The bounce budget contradicts "the material barely matters"

This is the item you asked me to judge honestly, and yes, a sceptical reviewer reads it as
a contradiction. It is the most serious thing in the draft.

- Line 230-232: "Reflection at 15 GHz varies little across the materials ordinary European
  squares are actually built from, so moving between brick, stone and rendered masonry
  shifts $\chi$ by far less than any difference this paper reports."
- Line 546: "$L = 3$, and the reason is where the material evidence stops rather than where
  the number stops moving."

Read in sequence: the material is declared not to matter, and then the single most
consequential numerical choice in the method is justified by how far knowledge of the
material reaches. The reviewer's objection writes itself. If permittivity within the
masonry family is interchangeable, then the second and third interactions running on
assumed material costs nothing measurable, so the depth at which evidence stops is not a
reason for anything, and L=3 looks chosen for cost and rationalised afterwards.

The new coverage paragraph (574-588) makes this sharper rather than softer. It reports that
the exact first-hit guarantee holds "at a standpoint a camera actually occupied", that the
reach is a 20 m radius, and that pooled over the published walk first-interaction coverage
is **0.479**. So the guarantee that sets the budget is exact at eight camera positions and
under half-true at the standpoints actually reported.

**Shortest honest fix, about three sentences.** The two passages are not actually in
conflict, they are talking about two different things, and neither says which.

1. In Section IV-C, say what the evidence is evidence *of*. It is not evidence of a
   permittivity value, Section II-A already settled that those are interchangeable. It is
   evidence of **family membership**, that the surface is masonry and not glass or metal,
   which is the one material distinction Section II-A says does move $\chi$ and that the
   mesh cannot reveal on its own. Then "where the material evidence stops" means "where
   observed family membership stops", and the two passages stop fighting.
2. Put the 0.479 next to the L=3 claim rather than twelve lines below it. Right now the
   argument is made at 546 and undercut at 587, and a reviewer who reads in order feels the
   paper hid the number. Said in the same breath it reads as candour instead.
3. In Section II-A, one forward half-clause: "which is why Section IV-C sets the bounce
   budget from where family membership is observed rather than from a convergence
   threshold." That kills the sense that the two passages were written by different people.

**Related, same section.** Section IV-C now makes two arguments and the first dismisses the
second. Line 547-549 says "A convergence threshold would be the usual argument and it is
the weaker one", and then line 590 opens "What makes three sufficient rather than merely
defensible is where the power is", which *is* the convergence argument, now load-bearing.
One word fixes it: the convergence threshold is not weaker, it is **not sufficient on its
own**. Change 547-549 to say that and the section reads as two legs of one stool instead of
one leg kicking the other.

---

## 2. "Site" means two different things

This costs the reader more per occurrence than anything else in the file.

Line 147 (A3) binds the word: "Base station positions are unknown". Table 1 reinforces it
four times ($r$, $\rho$, $h$, $\nu$ all defined "to a site" / "of sites"). All of Section
III uses it that way.

Then it silently re-binds to "city square":

- Line 222: "Sites represented by a single panorama"
- Line 223, 576: "the reference site"
- **Line 243: "Each site contributes 80 standpoints"** — this sentence is briefly nonsense
  under the definition the reader is holding
- Line 737: "a property of the illumination model and not of the site"

Reserve "site" for base stations, use "square" or "location" for the city. Six word swaps.

---

## 3. A1 quotes 25 m, Table 2 says 10 m

- Line 139-140: "The nearest site considered is 25 m from the head"
- Line 408: street cell range **10 to 150 m**

Straight factual contradiction, and it is in the assumption that bounds the whole method. A
reviewer who glances at Table 2 catches it in ten seconds. The physics survives (with the
0.3 m aperture, $2D^2/\lambda = 9$ m at 15 GHz, so 10 m still clears far field) but the
sentence has to say 10 m, and the margin then becomes thin enough to be worth one clause.

> **Old illumination law, see `LAW_CHANGE.md`.** Both numbers are edges of the street range
> band. Stale, and the contradiction dissolves rather than being fixed, because the new law
> has no range band at all. The far field question survives and has to be asked again
> against the nearest facade tip instead.

---

## 4. The body coupling section is one 33-line paragraph

Lines 661-693 run unbroken from the eq (12) setup through the plane-wave passing convention,
the whole crowd argument with its five numbers, and the convexity omission. In the built PDF
this is half a column of solid grey on page 6. The splice point is visible in the source:
line 677 starts "Two things are left out of this step" mid-line, mid-paragraph.

Break before "Two things are left out of this step" (677) and before "The second omission"
(692). Nothing else needs to change, the content is good.

---

## 5. Two weighting laws for one population of sites, no reason given for either

Introduced by today's absolute-level insert, and it is the second-most-serious item.

- Eq (7), line 305: $Q \propto \rho_+^3 - \rho_-^3$, every site counted equally, per A4.
- Line 313-315: weighting by free space spreading $1/\rho^2$ gives $\rho_+ - \rho_-$
  instead, "and that variant is carried through as a sensitivity."
- Eq (11), line 370: $S_0 = \frac{P\nu}{4\pi}\oint(\rho_+-\rho_-)\dOmega$.

Eq (11) is correct, I checked the derivation and the four numbers. But it computes the
absolute level using the $1/\rho^2$ law, which is simply how power adds, while the baseline
$Q$ uses the other law and calls the physical one "a sensitivity". A4 (line 150-153) asserts
equal power per site and gives no reason at all.

This is not academic. I integrated both: the street model puts **88 %** of its measure below
5° under count weighting and **42 %** under $1/\rho^2$ weighting. Since elevation weighting
is what "separates one square from another" (line 435), the choice can reorder the cities.

**Fix, one clause plus one sentence.** Give A4 its reason. If the intent is power control
(each site serves its own cell, so received powers equalise), say so, and then note that
eq (11) deliberately uses the uncontrolled spreading law because it answers a different
question, an absolute level rather than a per-site share. Also say outright that the
$\rho_+ - \rho_-$ in eq (11) is the same object as the sensitivity variant at line 315 —
that connection is free and defuses half the tension by itself.

> **Old illumination law, see `LAW_CHANGE.md`.** The whole item is about how to weight a
> population spread over a range band, and the 88 and 42 percent below 5 degrees come from
> integrating that band two ways. Stale, because each azimuth now carries one source
> distance, so there is no distribution over range left to weight.

---

## 6. Convergence subsection: three separate seam artifacts

Lines 720-737, all three almost certainly from the rewrite.

- **Line 722 still contradicts line 546.** "Three parameters are measured rather than
  chosen" — but $L$ is explicitly *chosen* from evidence, per the opening sentence of IV-C.
  Say two are measured and $L$ is corroborated.
- **Line 729-730, dangling reference.** "Reading it against the single run error of *the
  next paragraph*" — the next paragraph is about identities and closed forms. The single-run
  error is in Section IV-A, lines 502-514, one section *earlier*. Point there.
- **Duplicated claim.** Line 724-725 "the threshold was that no standpoint move by 0.5 dB.
  None did" restates line 596-597 "Not one standpoint of the 40 moves half a decibel under
  any of the three illumination models". IV-C has the actual numbers (0.002 dB median,
  0.12 dB max), so V-C should shrink to a pointer.

---

## 7. The power-fraction numbers do not close, and two of them collide

Line 591-592: "Of all launched power, 79 % interacts once, a further 8.9 % twice, 1.2 %
three times, and 0.22 % ever again."

Sums to 89.32 %. The reader adds it up, gets 10.7 % missing, and has to guess that the
missing bucket is power that never interacts at all. Name it.

Then line 601-602: "The share of escaping power still in flight when the budget runs out is
**0.0038** at the median standpoint". That reads as the same quantity as the **0.22 %** ten
lines above, and the numbers differ by 1.7x. They reconcile if escaping power is about 58 %
of launched power, which is probably exactly right, but no reader will find that. One clause
naming the two denominators fixes it.

(The bounce sequence itself is self-consistent: 79 → 8.9 → 1.2 → 0.22 is a clean ~0.15
retention per bounce, which is right for masonry. Nothing wrong with the physics here.)

---

## 8. The open-sky standpoint filter exists only in the A6 defence

Line 177-178: "the standpoints used here are required to have open sky above them. Points
with no sky are discarded before any trace runs."

Lines 248-256 define standpoint selection in full — 3 m grid, drop a ray, keep near-horizontal
ground-level faces with head clearance, chain by nearest neighbour, no map layers — and never
mention an open-sky requirement.

The second of the three legs of the diffraction argument rests entirely on that filter. As
written, a reader who reads II-B carefully concludes the filter was invented to prop up A6.
Move it into II-B where standpoints are actually defined, and let A6 point at it.

---

## 9. Symbols used before or without definition

There is a Notation subsection and a 24-row symbol table, so these stand out.

| Symbol | First use | Status |
|---|---|---|
| $\theta_i$ | 525, 533, 625 | **Never defined**, not in Table 1. Angle of incidence. |
| $S_{\mathrm{inc}}$ | 667 | **Never defined**, not in Table 1. Its relation to $S$ and $\Phi$ is unstated. |
| "sky fraction" | 388, 491, 704 | **Defined at 653**, three sections after first use, and not in Table 1. |
| $k$ | 169, in $1/\sqrt{ks}$ | Unglossed wavenumber. Table 1 carries $\lambda$ and not $k$. Minor. |
| $P$ | 368 | Defined inline, fine, but not in Table 1 while $\nu$ is. Minor. |

The first three are worth fixing. `sky fraction` in particular is doing real work at 388 and
491 before the reader is told what it is.

---

## 10. Claims made twice in different words

Ranked by how much the repetition hurts.

1. **Lines 152-153 vs 313-315.** A4: "A variant that weights each site by its own free space
   spreading is reported alongside" / III-A: "Weighting each site by its own free space
   spreading $1/\rho^2$ instead replaces the cubed bracket ... and that variant is carried
   through as a sensitivity." Near-verbatim. **Cut the A4 clause** — an assumption list
   should state the assumption, and III-A is where the variant earns its place.
2. **Lines 66-67 vs 458-459.** "One trace per standpoint then answers the question for every
   base station position at once" / "so one outward trace answers (1) for every source
   position at once." Near-verbatim. **Keep the Section IV one**, it is earned by the two
   equations above it. End the Section I paragraph at "\Cref{fig:adjoint} shows the idea."
3. **Isotropic identity, three times:** 386-388, 490-492, 703-705. 490-492 already forward-refs
   to Section V, so **shrink 386-388** to "which makes it a control".
4. **Lines 336-341 vs 732-737.** Same reason, near-horizon measure, for the same conclusion,
   the crop radius. Plus a third promise at 197-198. Keep the promise at 197 and the payoff
   at 732. **Cut 339-341** back to "This is why the shape of the square changes the answer at
   all."
5. **Lines 537-541 vs 599-603.** Truncation sign stated twice, sixty lines apart, and the
   second one has the numbers. **Trim the Bounce loop version** to "Rays still travelling
   after $L$ interactions are dropped and the power they were carrying is measured.
   Section IV-C gives the number and the consequence."
6. **Lines 243-246 vs 511-514.** Same punchline, "a single standpoint is not the right unit",
   from two genuinely different reasons (physical spread vs Monte Carlo error). Keep both
   reasons, let one drop the conclusion. Mild.

---

## 11. "One known bias" / "only approximation" is over-claimed three times

- Line 539-540: "that share is the estimator's **one** known bias"
- Line 608-609: "The **only** approximation left in the trace is a single one sided truncation"
- against line 183: "Every value reported here is a **lower bound** with respect to this
  term" (diffraction), plus A5, A7, and the convex-body assumption at 692.

All are approximations, and two of them bias the same direction. Scope it: "the only
approximation the estimator itself introduces, on top of the assumptions of Section I".
Otherwise a reviewer who remembers A6 marks it as sloppy, and A6 is a paragraph you clearly
worked hard on.

---

## 12. Beam pointing leans on machinery two sections ahead

Line 423-425: "since the estimator reads $Q$ only when depositing an escaped ray and never
inside a random draw, the traced $\chi$ comes out bit identical." The estimator is defined in
Section IV-A. The claim is correct but unverifiable where it sits.

Also, the exact cancellation relies on A1: it is only because every source is a plane wave
from direction $\uext$ that "aimed at the pedestrian" means "peak gain along $-\uext$"
regardless of what the ray does inside the square. Without naming A1, a reviewer will ask
whether a beam aimed at the user still gives peak gain along a *reflected* path, and the
"exactly rather than approximately" at 427-428 invites that question. One clause, "under A1",
closes it.

---

## 13. Smaller items

- **Line 674, "the direction dictionary $\khat = -\uloc$".** Coined phrase, and "dictionary"
  is not the word for a sign convention. Plain fix: "with $\khat = -\uloc$, as reciprocity
  requires."
- **Lines 50 and 267, "We".** Single-author paper. "This ratio is called the exposure ratio"
  / "Where the base stations are is unknown, so the model integrates over where they could
  be." Only two instances.
- **Line 158, "The paragraph after this list gives the reason".** Three paragraphs follow
  (167-186). Classic seam symptom: it was one paragraph and grew. Say "The three paragraphs
  after this list".
- **Line 243, "80 standpoints", and line 594, "40 standpoints".** Neither number is derived.
  A 3 m grid over a 250 m crop keeps far more than 80 columns, and how it becomes 80 (cap?
  subsample? walk length?) is never said, nor why the budget study uses 40. Exactly the
  "falls from the sky" complaint, in a place that is cheap to fix.
- **Hard-coded section numbers at 340, 562, 734** ("Section~II", "Section~I", "Section~II").
  All currently correct, all break the moment a section moves. Use `\ref`.
- **"worth" construction four times**: 164 "it is worth the space", 228 "worth stating
  plainly", 503 "the reason is worth stating", 563 "it is worth recording that". None is the
  banned phrase, but four in seven pages is a tic and the family is on the tell list. Flatten
  two.
- **Line 566, "panorama-observed triangle".** The file consistently avoids hyphens elsewhere
  ("image derived", "street level", "free space"). Tiny inconsistency.
- **Section IV is "Adjoint ray estimator" and its subsection A is "Estimator".** Mildly odd
  in the table of contents.
- **Table 2 overfulls by 5.3 pt** (log line 532). Cosmetic.

---

## What is already right, and worth not touching

Every number I could independently recompute reproduces, several to three figures:

- Table 2 elevation limits from eq (9): 3.09 / 60.11 / 0.95 / 33.02, all four exact.
- A2: $3.1\times10^4$ rad per radian at 100 m and 15 GHz, and $10^{10}$ cells, both right.
- A6 leg one: $\sqrt{ks} = 56.0$ at 10 m, 35.0 dB. Exact.
- Crowd clearances: 13.2, 2.63, 0.40 m at 1°, 5°, 30°. Exact.
- Crowd measure split: I integrate 87.9 % and 9.4 % against your 88 % and 9 %.
- The new eq (11) numbers: 0.0075, 3.0, 0.010, 4.1 W/m². All four reproduce, and the
  derivation of eq (11) itself is correct and dimensionally clean.
- "Nearly three orders of magnitude": 547x, so 2.7. Fair.

> **Old illumination law, see `LAW_CHANGE.md`.** Two rows of this list are the old law: the
> four Table 2 elevation limits, and the 87.9 and 9.4 percent crowd measure split. Stale as
> quantities, even though the check itself was sound, and the other rows survive because
> they are geometry, aperture and closed form arithmetic.

Three passages read particularly well and I would leave them alone: the three-leg diffraction
defence (167-186), which is the right shape for the objection it answers; the eighth-station
admission at 578-582, which is the kind of thing reviewers trust a paper for; and the
Section III opener at 267-273, which sets up $Q$ in four sentences without a symbol falling
from the sky.

---

# Resolution

Applied against `methods.tex` at 1063 lines. It had moved a long way since the
reviewed hash: most of items 1 to 6 and 10 to 13 were already fixed in the file
before this pass. What follows says which, and what was left.

Build after the pass: 11 pages, zero undefined references, zero undefined
citations, no overfull boxes, one underfull hbox inside a bibliography entry
that predates this pass. No em dashes, no semicolons outside `\;`.

## Lead: three things worse than the review said

**Item 7 was not a presentation problem, it was the arithmetic error the review
half-spotted.** The file had already been "corrected" once, and the correction
named the missing bucket as "10.7 % never touches a surface, which is the direct
term". That 10.7 is `100 - (79 + 8.9 + 1.2 + 0.22)`, and that sum is exactly the
non-partition trap: power incident at depth 3 was already counted at depths 1
and 2, so the column cannot be subtracted from 100. The share that never touches
anything is `1 - 0.790 = 21.0 %`, and it checks out independently against the
measured sky fraction (mean 0.2364 over the 40 walk standpoints in
`korenmarkt_130m_budget_ladder.json`, against 0.210 at the panorama positions the
depth shares are pooled over). Corrected to 21.0 %, the depth shares restated as
what they are, and one sentence added saying they are not to be added and why.
`SPINE.md` §4 documents the same mistake and the same fix, so the file was the
last place carrying it. `paper/paper.tex` already carries the corrected numbers.

**Two numbers in the bounce budget quoted the wrong configuration.** The method
says Russian roulette is switched off, but the worst-standpoint cost (0.12 dB)
and the truncated throughput (0.0038 median, 0.021 worst) were all read off the
roulette-on row of the ladder. Recomputed from
`outputs/bounce_budget/korenmarkt_130m_budget_ladder.json` at the operating
point, `L3_roulette99` against `L8_roulette99`: worst standpoint 0.063 dB,
truncation 0.0037 median and 0.0201 worst. Fixed. In the same paragraph the file
claimed roulette is "a worse estimator at the same cost", which the measurement
does not support: `BOUNCE_BUDGET.md` finds the same relative spread to three
significant figures on all three models and 101 against 100 s of wall clock, and
says outright that roulette does nothing at this budget, neither helping nor
hurting. Replaced with what was measured.

**Item 1's residual, which the review did not name.** The review's three sentence
fix was right and was already applied, so the permittivity-against-family
distinction is in place and the two passages no longer fight. What is left is
narrower and real: the cross city comparison runs with geometric classes and no
image evidence at all, so a bounce budget justified by where material evidence
stops says nothing about ten of the eleven squares. Added a short paragraph in
IV-C that says which leg carries which runs, rather than letting the evidence
leg appear to cover the whole study.

## Per item

1. **Already fixed, plus the residual above.** IV-C now opens on family
   membership against permittivity, II-A carries the forward half-clause, and
   the convergence threshold is "not weaker so much as insufficient by itself".
   The 0.479 sits inside the evidence argument with the sentence that owns it.
2. **Already fixed but for one.** "Site" now means base station everywhere in
   the file except "available at any site with a registered panorama", changed
   to "square".
3. **Already fixed, and verified rather than assumed.** A1 says 10 m.
   `semantic_twin/propagation/directions.py` has
   `STREET_RANGE_BAND_M = (10.0, 150.0)`, so Table 2 was the correct one and the
   far-field margin clause the file added is right.
4. **Already fixed.** The body coupling block is three paragraphs.
5. **Already fixed.** A4 gives its reason (per-cell power control), and eq. (11)
   names its bracket as the same object as the A4 variant and says why it uses
   the uncontrolled law. Verified 87.9 % and 42.2 % below 5 degrees with
   `measure_below`, so the "not cosmetic" clause in A4 stands.

   > **Old illumination law, see `LAW_CHANGE.md`.** Items 3 and 5 above were closed against
   > the range band, the 10 to 150 m constant and the two weighting laws over it. Stale,
   > and both close differently under the new law rather than needing a different fix,
   > since there is no range band for either question to be about.

6. **Already fixed.** Two measured plus one corroborated, the single-run error
   points at IV-A, and V-C is a pointer rather than a restatement.
7. **Fixed.** See the lead.
8. **Fixed.** The open-sky filter now lives only where standpoints are defined,
   as the 1 % sky test that was already written there, and A6 points at it with
   a `\ref` instead of stating a slightly different filter.
9. **Fixed.** `\theta_i` and `S_{inc}` were already in Table 1 and "sky
   fraction" is now defined at its first use. Added the gloss for `k` and the
   one relation the table could not carry,
   `S_inc = S_0 Phi(u) dOmega` for a cell.
10. 10.1 **declined**: A4's clause is now a pointer to III-A rather than a
    restatement of it, and an assumption that has a reported alternative should
    say so where the assumption is made. 10.2, 10.5 already fixed. 10.3
    **fixed**, the models-used mention no longer states the identity before
    "sky fraction" exists. 10.4 **fixed**, the crop radius clause cut back as
    proposed. 10.6 **fixed**, the estimator paragraph keeps its reason and drops
    the shared conclusion.
11. **Already fixed.** Scoped to what the trace itself introduces, with the
    assumptions of Section I named as sitting underneath.
12. **Already fixed.** A1 is named and the estimator claim carries a `\ref`.
13. "Three paragraphs after this list" **fixed**, there are seven, so it now says
    "the paragraphs". The 80 was already derived; the 40 is now tied to the
    published walk, which is what it is, rather than reading as an unexplained
    subsample. Hard-coded section numbers were already `\ref`. One "worth"
    flattened. Subsection IV-A renamed to "Stratified estimate". Table 2 overfull
    fixed with `\tabcolsep`. The coined "direction dictionary", the two "We"s and
    "panorama-observed" were already gone.

## Outside the review

The `\cite{sam}` in II-A pointed at Kirillov et al. 2023 while the model that
produced the material masks is SAM 3 (`semantic_twin/sam3_concepts.py` sets
`MODEL = "facebook/sam3"`, and the material names in
`config/semantic_concepts.json` are the prompts). The sentence now cites that
paper for the promptable-segmentation idea and names SAM 3 as what ran, with a
`\todo{}` in the built PDF because the SAM 3 reference could not be verified in
this session.
