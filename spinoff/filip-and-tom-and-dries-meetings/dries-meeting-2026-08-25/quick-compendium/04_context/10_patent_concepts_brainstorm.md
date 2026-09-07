# Concept slides for Alessandro: pseudo-Brewster compensation + surface confinement

CONFIDENTIAL. Internal working doc. Ref P2026/040. Written 2026-05-24.

Deliverable Alessandro asked for (post-meeting email): "some slides" explaining the
two concepts he has to relay to the external patent filer (a technical person, not an
EM specialist):

1. Pseudo-Brewster compensation
2. Surface confinement

These are the two physical reductions in the IDF's short description (Insight 1,
Insight 2) that collapse volumetric dosimetry to the surface law
`S_ab(r) = S_inc * T_0 * ReLU[n_hat . (-k_hat)]`.

---

## The one thing to get right before designing anything

Robin's unease: is the IDF implying these two concepts *are* "the patentable invention"?
Checked against the signed IDF:

- They appear as **Insight 1 / Insight 2** under "short description of the invention" =
  the enabling physics, not the claims.
- In the suggested claims, **pseudo-Brewster appears only in dependent Claim 6**
  ("transmission coefficient T_0 derived from the pseudo-Brewster compensation property").
- **Surface confinement is not a standalone claim** at all. It is the premise of
  Claim 1's surface-mesh method.
- The independent claims are the method, the exposure operator Q, the near-field
  primitives, the differentiable optimization, and the systems.

Conclusion: the IDF does **not** oversell these two as the invention. An IDF describes
the invention; the attorney decides how to claim it. So the slides do **not** need a
"the real novelty is elsewhere" argument (that would overstep the attorney's job and
risk looking like Robin is doing their work for them). What they **do** need: explain
each mechanism cleanly, and be honest *within each concept* about what is textbook /
prior art versus what Robin actually contributed. That honesty is not a strategy move,
it is the single fact the filer needs to locate the inventive step and to not get
blindsided when they read the TAP paper (which says plainly that it recovers the
empirical scalars of Kodera/Bamba/Flintoft/Zhang as special cases and that Azzam proved
the optical-substrate constancy).

This matches Robin's own pre-meeting `presentation_plan.md`, which concluded:
"present pseudo-Brewster as the enabling physics, not as the claim that carries the patent."

---

## Audience and constraints

- Primary reader: the external patent filer (technical, not EM). Secondary: Alessandro
  (PhD, IP adviser, technical). Possibly forwarded to promotors.
- The deck must survive being read **cold, without Robin narrating**. Self-contained.
- Format: LaTeX/Beamer, formal, **no animations** (Robin's instruction). Reuse the
  patent_meeting deck's navy theme, `resultbox`, `siunitx`, etc.
- Must be **Overleaf-ready** (figures bundled into the project, no `../../papers/...`
  graphicspath dependency) so it can be co-developed with Alessandro.
- Visual QA: compile, render PNGs, inspect each, be picky about overlaps/spacing.

---

## Several ideas (then pick + adversarial pass)

### Idea A. "Two enabling reductions" (RECOMMENDED)
Each concept gets a three-beat arc: **mechanism -> the one money figure -> validity +
honest contribution.** A short setup orients the reader, a bridge slide assembles the
two reductions into the governing law, a one-line close says where they sit (enabling
physics; claims build on top). ~8 main slides + appendix.
- Pro: exactly what Alessandro asked for, two cleanly liftable explainers, honest,
  self-contained, easy to extend on request.
- Con: none worth noting. The other ideas are variations on it.

### Idea B. "Concept -> claim support"
Structure each concept around which claims it underpins (pseudo-Brewster -> the T_0
scalar in Claims 1/6; surface confinement -> the surface-mesh premise of Claim 1).
- Pro: most useful to a claim-drafter.
- Con: pre-empts the attorney's job, which is exactly the line Robin's Q1 point says not
  to cross. Reads as "here is how to write your claims." Rejected as the spine; a *light*
  version (one closing slide noting where each sits) is folded into A.

### Idea C. "Single narrative collapse"
One continuous story: FDTD intractable -> surface confinement -> pseudo-Brewster ->
governing law. ~5 slides.
- Pro: tight, fast to read.
- Con: Alessandro asked for slides *on the two concepts*; he likely wants them as two
  separable explainers he can hand over or expand, not one blended story. Also loses the
  per-concept known-vs-new nuance. Rejected.

### Idea D. "Mechanism + skeptic's rebuttal"
Each concept paired with the obvious examiner objection and the rebuttal:
"isn't constant-T just Azzam/Kodera?" -> yes for optics/empirics, the contribution is the
tissue connection + system integration; "isn't skin depth textbook?" -> yes, the move is
the surface-integral reduction and its validity window.
- Pro: arms the filer against the first objections, the most patent-useful thing
  a physics explainer can do.
- Con: as a *whole structure* it is adversarial in tone. Best as the **third beat of each
  concept in A**, not a separate deck. Folded into A.

**Decision: A, with D baked into each concept's "honest contribution" beat and a light
single-slide version of B at the close.**

---

## Adversarial pass on the chosen design (A)

1. **Overstepping into patentability.** Risk the deck argues claim strategy. Mitigation:
   stay strictly within "known physics vs Robin's contribution" per concept; the close is
   one factual orientation line, not a strategy lecture.
2. **Too much physics for a non-EM filer.** Mitigation: one money figure per concept,
   plain-language mechanism, hard numbers in callout boxes, all derivation in appendix.
3. **Surface confinement has no ready "money figure."** The TAP paper treats it as a
   one-line working assumption. Mitigation: **generate** a clean skin-depth-vs-frequency
   plot (penetration depth d_pen(f) for skin and muscle, 1-100 GHz, computed from the
   AEGIS tissue model, with a d_pen < 1 mm band above 6 GHz and a body-scale reference),
   plus a small TikZ schematic of a wave decaying into a thin surface layer. This new
   plot is probably the most useful single figure in the deck.
4. **Censored child phantom.** These two concepts mostly do not need a phantom render.
   Use the skin-depth plot + schematic + the existing `apd_angle_panel_T.pdf`. If a
   phantom heatmap is shown at all, use the already-censored TAP figure.
5. **Overleaf / figure portability.** Bundle every figure into `figures/`. No reliance on
   the sibling-repo graphicspath. Generated figure script lives in `scripts/`.
6. **Duplicating the patent_meeting A2/A3 slides.** This deck is the deeper standalone
   zoom Alessandro asked for, not a re-presentation. Reuse the figure + theme, expand the
   explanation, add the validity/known-vs-new beats the meeting deck did not have room for.
7. **Order: pseudo-Brewster first or surface confinement first?** Logical build favors
   surface-confinement-first (volume -> surface is the bigger leap). But Alessandro named
   them pseudo-Brewster (1), surface confinement (2), and the IDF and the prior
   patent_meeting deck use that order. Match the reader's expectation: **pseudo-Brewster
   first.** Trivial to flip if Robin prefers.
8. **Number consistency.** T_0 = 0.539 (skin, 28 GHz), within 5.6% to 75 deg, crossover
   ~40.4 GHz (conservative below), skin depth < 1 mm above 6 GHz. All sourced from the TAP
   paper so the deck and the paper agree (the filer may read both).

---

## Recommended deck outline (~8 main + appendix)

1. **Title.** CONFIDENTIAL, ref P2026/040. Subtitle: "Two physical reductions behind the
   geometric dosimetry law." One line: what the reader will get.
2. **Orientation.** The target law `S_ab = S_inc * T_0 * ReLU[n.(-k)]`, color-coded, with
   "two reductions get us here: (1) the material collapses to one scalar, (2) the problem
   collapses to the surface." Names the two concepts and their roles up front.
3. **Pseudo-Brewster - mechanism.** TE transmission falls, TM rises to the pseudo-Brewster
   peak, the unpolarized average stays flat. Plain words + the high-index condition |n|>~2.5.
4. **Pseudo-Brewster - the money figure.** `apd_angle_panel_T.pdf` (T_s, T_p, T_avg vs
   angle). Callout: within 5.6% of T_0 over 0-75 deg; T_0 = 0.539 for skin at 28 GHz.
5. **Pseudo-Brewster - validity + honest contribution.** Frequency window (`R_of_f.pdf`,
   conservative below ~40 GHz). Honest line: Azzam proved the optical-substrate constancy,
   Kodera/Bamba/Flintoft/Zhang measured the near-constant T empirically; the contribution
   is the derivation for tissue from Fresnel theory and the integration into a body-surface
   system, not the scalar itself.
6. **Surface confinement - mechanism.** Above 6 GHz the penetration depth is < 1 mm, so all
   transmitted power is absorbed in a thin surface layer and the body is opaque. Only the
   external shape matters. TikZ schematic of the decaying field.
7. **Surface confinement - the money figure + the collapse.** Generated skin-depth(f) plot.
   Callout: this turns a ~10^12-cell volume mesh into a ~10^4-triangle surface integral.
   Honest line: skin depth is textbook; the contribution is reducing dosimetry to a surface
   integral and bounding when it holds.
8. **Surface confinement - validity.** Holds above ~6 GHz; below ~6 GHz the penetration
   depth grows past the fat layer, Fabry-Perot resonances appear, the local map loses
   pointwise meaning (total power still valid via T_bar/T_lay).
9. **The two together -> the law.** Bridge: T_0 (from pseudo-Brewster) x ReLU[n.(-k)]
   (from surface confinement) = the governing law. One factual orientation line: these are
   the enabling physics; the IDF's independent claims (method, Q, near-field,
   differentiability, systems) build on top.

Appendix (navigable, "if they ask"): full Fresnel coefficients; tissue-universality table
(skin/muscle/water/fat at 28 GHz); the APD/IPD angle panel; sub-6 GHz layered transmission.

---

## Build plan

1. Scaffold `presentations/patent_concepts/`: `main.tex`, `preamble.tex` (adapted from
   patent_meeting, but self-contained graphicspath = `figures/` only), `math_commands.tex`.
2. Bundle figures into `figures/`: copy `apd_angle_panel_T.pdf`, `apd_angle_panel_APD.pdf`,
   `R_of_f.pdf` from the TAP paper.
3. Generate `figures/skin_depth_vs_freq.pdf` via `scripts/skin_depth_plot.py` using the
   AEGIS tissue model + `_plot_style.py` (IEEE single-column style).
4. Write the slides per the outline. TikZ schematic for the surface layer.
5. Compile (pdflatex x2), render PNGs (pdftoppm), inspect every slide for overlaps and
   spacing, iterate until clean.
6. Co-develop the email to Alessandro: polish Robin's draft, fold in the IDF-error mention
   (pending which error he means), propose Overleaf co-editing.

## Open questions for Robin

- The email says "there is an error in the IDF." Which one? Most likely the hallucinated
  prior-art references (5 of 9 wrong/fabricated, per `TODO_IDF_HALLUCINATIONS.md`). Drafting
  on that assumption, flagged for confirmation.
- Order (pseudo-Brewster first) and the one-line close are the only choices worth a glance.
