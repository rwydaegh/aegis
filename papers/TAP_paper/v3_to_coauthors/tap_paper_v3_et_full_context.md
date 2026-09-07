# ET co-promotor feedback: full context and decisions

## Purpose

This is a decision document for the annotations in
`v3_to_coauthors/tap_paper_v3_et.pdf`. It is not a list of instructions to
apply blindly. For every annotation it records:

1. what the v3 manuscript says and where;
2. the exact PDF feedback or replacement;
3. what the annotation appears to mean;
4. an independent verdict;
5. the recommended action or response; and
6. proposed final wording when an edit is warranted.

The PDF contains 21 non-link annotations. Two are uncommented magenta
highlights, so they do not support any definite requested change. The source
line references below are to `v3_to_coauthors/paper.tex` unless stated
otherwise.

## Decision summary

| No. | Topic | Verdict | Recommended handling |
|---:|---|---|---|
| 1 | Geometry scalar | Adapt | Clarify, but use better prose than the literal replacement |
| 2 | Polarization-aware | Reject | Keep the original technical term |
| 3 | 20% FDTD variation | Do not accept as stated | Keep out of the abstract unless verified from a primary inter-code study |
| 4 | Exposure on/of | Accept | Edit |
| 5 | Validated in four ways | Accept | Edit |
| 6 | Second geometry scalar | Adapt | Simplify to “ambient-occlusion scalar” |
| 7 | One 10 ms multiply | Adapt | Fix grammar but retain the timing result |
| 8 | Flowchart references | Accept | Add restrained equation or section references inside the diagram |
| 9 | Polarization-degenerate | Adapt | Use “common normal-incidence value” |
| 10 | Circular polarization wording | Accept | Edit |
| 11 | Linear replaced by circular | Reject literally | Treat as a copy-paste error and use “linearly polarized” |
| 12 | Highlighted Section III heading | No action | No comment exists |
| 13 | Extend to 90 degrees | Accept concern, adapt solution | Explain the 75-degree cutoff and report grazing absolute/integrated error |
| 14 | Tissue evidence only at 28 GHz | Accept concern | Run a cross-tissue frequency sweep or narrow the claim |
| 15 | Remove Table I | Accept | Delete or move to SI and retain the maximum deviation in prose |
| 16 | Highlighted Cauchy heading | No action | No comment exists |
| 17 | “Theorem” is too strong | Partly accept | Keep the result prominent but call it a proposition or identity |
| 18 | Intuition for the sphere integral | Accept strongly | Add one explanatory sentence |
| 19 | Delete “from 1841” | Adapt globally | Keep one historically precise attribution in the correct place |
| 20 | Delete compliance section | Partly accept | Compress main-paper content and move peripheral derivations to SI |
| 21 | Conservativeness relative to FDTD | Accept strongly | State that bias is not one-sided and distinguish it from conservative bounds |

## 1. “Geometry” to “geometry-dependent” in the abstract

### Manuscript context

Lines 127-132:

> For unpolarized skin at 28 GHz, pseudo-Brewster compensation keeps
> angular transmission within 5.6% of normal incidence up to 75 degrees.
> Integrating the local law over the visible nonconvex body surface yields a
> generalized Cauchy whole-body identity with one geometry scalar. A layered
> transmission term captures the sub-6 GHz whole-body dip.

The marked word is **geometry** in “one geometry scalar.”

### PDF feedback

Acrobat replacement:

> geometry-dependent

Literal result:

> ...with one geometry-dependent scalar.

### Interpretation

The comment is trying to make clear that the scalar depends on the body's
geometry rather than being a universal constant.

### Verdict

**Adapt.** The concern is valid. “Geometry scalar” is compressed and not very
idiomatic. The literal replacement is clearer, but “one geometry-dependent
scalar” can still be polished.

### Recommended handling

Accept the clarification without treating the exact replacement as mandatory.
No scientific verification is required.

### Suggested final writing

> Integrating the local law over the visible nonconvex body surface yields a
> generalized Cauchy whole-body identity governed by a single
> geometry-dependent scalar.

An equally concise alternative is “a single geometric scalar.” The first option
more explicitly expresses dependence and is therefore preferable here.

## 2. “Polarization-aware” to “polarization-inclusive”

### Manuscript context

Lines 133-138:

> The closed form is validated in four ways: Mie theory on lossy spheres, full
> polarization-aware Fresnel calculations on the Thelonious phantom, Sim4Life
> FDTD, and dosimetry literature across 108 volunteers and 5 FDTD phantoms.

### PDF feedback

The annotation crosses out **polarization-aware** and stores:

> inclusive

Literal result:

> full polarization-inclusive Fresnel calculations

### Interpretation

The intended concern is probably that “aware” sounds informal or
anthropomorphic and that the validation includes polarization explicitly.

### Verdict

**Reject.** “Polarization-aware” is the more precise term. The calculation
resolves the local TE and TM energy fractions. “Polarization-inclusive” is
unusual and could merely mean that several polarizations were included in a
test set.

### Recommended handling

Keep the current wording. There is no need to argue this point unless the
co-promotor asks. If a more formal alternative is desired, use
“polarization-resolved,” not “polarization-inclusive.”

### Suggested final writing

Preferred:

> ...full polarization-aware Fresnel calculations on the Thelonious phantom...

More formal alternative:

> ...full polarization-resolved Fresnel calculations on the Thelonious
> phantom...

## 3. Put the 5% error in the context of FDTD implementation differences

### Manuscript context

Lines 138-140:

> In the high-frequency regime, the error is below 5%, within the reported
> uncertainty in human-skin dielectric parameters.

The comment highlights this complete claim.

### PDF feedback

> Is it also not well within variations between FDTD implementations? I heard
> these could amount to 20% difference.

### Interpretation

The comment suggests strengthening the abstract by saying that the closed-form
error is also smaller than typical differences among FDTD implementations.

### Relevant evidence already in the draft

- Lines 1094-1101 report law-to-FDTD ratios of 1.06, 1.20, and 0.83 for three
  individual directions at 7 GHz, followed by a direction-averaged ratio of
  1.027. The manuscript calls the directional scatter FDTD reference noise.
- The paper has a sourced ±20% spread in **dielectric inputs**, not a sourced
  20% inter-implementation FDTD error. That input spread propagates to about
  ±7% on transmission.
- The matched validation controls geometry, excitation, and tissue properties.
  That makes propagated input uncertainty a more defensible comparison than a
  generic inter-code spread.

### Verdict

**Do not accept as stated. Verify if pursued.** The question is reasonable, but
“I heard” cannot support a quantitative abstract claim. Even if a 20% inter-code
spread can be sourced, using it in the abstract could look like lowering the
accuracy standard.

### Recommended handling

Do not add 20% FDTD variability to the abstract. Keep the matched
tissue-property uncertainty comparison. If a primary inter-code benchmark is
found, discuss it carefully in the FDTD validation subsection and distinguish
inter-code variability from error of the closed form.

### Suggested response to the comment

> The comparison is worth discussing, but I would not state 20% without a
> direct inter-code source. Our matched comparison is more cleanly benchmarked
> against the uncertainty propagated from measured tissue properties. The
> direction-level FDTD scatter is already reported in the validation section.

### Suggested final writing

> In the high-frequency regime, the error remains below 5%, within the
> uncertainty propagated from measured human-skin dielectric properties.

## 4. “Exposure on” to “exposure of”

### Manuscript context

Lines 151-155:

> Wireless exposure on the human body is regulated through two basic
> restrictions in the ICNIRP 2020 guidelines, IEC/IEEE 63195, and IEEE C95.1...

The PDF coordinates show that the strikeout is on **on** in the first line. It
is not attached to **in** later in the sentence.

### PDF feedback

Acrobat replacement:

> of

### Interpretation

This is a grammar and idiom correction.

### Verdict

**Accept.** “Exposure of the human body” is more natural.

### Recommended handling

Apply the change silently. The sentence can also be made slightly clearer by
saying that the restrictions are specified in the cited standards.

### Suggested final writing

> Wireless exposure of the human body is regulated through two basic
> restrictions specified in the ICNIRP 2020 guidelines, IEC/IEEE 63195, and
> IEEE C95.1: ...

## 5. Insert “in” after “validated”

### Manuscript context

Lines 197-199:

> To the best of the authors' knowledge, this is the first closed-form APD law
> for the human body, validated four independent ways.

### PDF feedback

Insert:

> in

### Interpretation

This is a grammatical correction.

### Verdict

**Accept.**

### Recommended handling

Apply silently.

### Suggested final writing

> To the best of the authors' knowledge, this is the first closed-form APD law
> for the human body, validated in four independent ways.

## 6. The second “geometry-dependent” replacement

### Manuscript context

Contribution 1, lines 201-205:

> We derive closed-form APD laws from Fresnel transmission on lossy biological
> tissue and integrate them over nonconvex anatomical meshes with a generalized
> Cauchy formula. Whole-body absorbed power reduces to a flux-weighted
> transmission scalar and an ambient-occlusion geometry scalar.

The marked word is **geometry**.

### PDF feedback

Acrobat replacement:

> geometry-dependent

Literal result:

> ...an ambient-occlusion geometry-dependent scalar.

### Interpretation

As in item 1, the comment seeks to clarify what the scalar depends on.

### Verdict

**Adapt.** The current phrase is awkward, but the literal replacement is
needlessly stacked. “Ambient-occlusion scalar” already tells the reader that it
is a geometric quantity.

### Recommended handling

Simplify rather than lengthen. Keep “geometry-dependent” in the abstract if
desired, but do not force identical wording into this already technical list.

### Suggested final writing

> Whole-body absorbed power reduces to a flux-weighted transmission scalar and
> a single ambient-occlusion scalar.

## 7. Remove “one 10 ms” from the matrix-vector statement

### Manuscript context

Contribution 3, lines 212-215:

> The computation is differentiable end-to-end, the first APD map to provide
> closed-form gradients. For a body mesh under many incident paths, the
> absorbed-power map is one 10 ms matrix-vector multiply.

The strikeout spans the complete phrase **one 10 ms**.

### PDF feedback

Acrobat replacement:

> a

Literal result:

> ...the absorbed-power map is a matrix-vector multiply.

### Interpretation

The literal annotation removes the awkward compound modifier and also removes
the timing claim.

### Verdict

**Adapt.** The grammar should be fixed, but the under-10 ms result is a useful
quantitative contribution and should not be discarded.

### Recommended handling

Rewrite the sentence instead of applying the literal replacement.

### Suggested final writing

> For a body mesh under many incident paths, the absorbed-power map is a single
> matrix-vector multiplication, evaluated in under 10 ms.

## 8. Put section or equation numbers in the flowchart

### Manuscript context

Figure 1 shows the reduction chain:

- exact law;
- unpolarized law;
- geometric law;
- whole-body identity;
- sub-6 GHz layered branch; and
- regulatory outputs.

The caption, lines 340-350, explains that the arrows are justified in Sections
II-D, III, and IV-B. Those references are not visible inside the diagram.

### PDF feedback

> Maybe it's clearer to include Section or formula numbers in the flowchart. It
> should be easier to follow the exposition if it is clearly matched to the
> blocks in the flowchart.

### Interpretation

The comment is about navigation, not missing theory. Readers should be able to
match a diagram box to the corresponding derivation without decoding the
caption.

### Verdict

**Accept, with a restrained implementation.** This is good reader-oriented
feedback. Adding both section and equation references everywhere would clutter
an already dense figure.

### Recommended handling

Add automatically generated equation numbers to the formula boxes. Add section
references only where the equation number alone does not identify the relevant
discussion. Use LaTeX references rather than hard-coded numbers so the diagram
cannot drift after edits.

### Suggested final figure treatment

- Exact law: “Eq. (5), Section II-D”
- Unpolarized law: “Eq. (7), Section II-D”
- Geometric law: “Eq. (9), Section III-E”
- Whole-body identity: “Eq. (12), Section IV-B”
- Layered branch: “Section IV-C”
- Corrections: “Section V-F”

If this is visually crowded, retain only the equation tags in the boxes and
put the two section-only references beside their branch labels.

### Suggested caption adjustment

> Figure 1: Flowchart of the approach. Equation and section references in each
> block locate the corresponding derivation.

The remainder of the existing caption can then be shortened.

## 9. “Polarization-degenerate” to “polarization-independent”

### Manuscript context

Lines 415-424:

> The corresponding power-absorption coefficients are Ts and Tp. At normal
> incidence, mu = 1 and xi = n-tilde, giving the polarization-degenerate value
> T0 = Ts(0) = Tp(0) = ...

### PDF feedback

The word **degenerate** is crossed out and replaced with:

> independent

Literal result:

> ...giving the polarization-independent value

### Interpretation

The comment seeks a less specialized term for the equality of the TE and TM
normal-incidence coefficients.

### Verdict

**Adapt.** The original is technically defensible, but “degenerate” adds jargon.
The literal replacement could be read as a claim of polarization independence
at every angle.

### Recommended handling

Make the normal-incidence scope inseparable from the phrase.

### Suggested final writing

> At normal incidence, mu = 1 and xi = n-tilde, giving the common
> normal-incidence value

followed by Eq. (3).

## 10. “Circular” to “circularly polarized”

### Manuscript context

Lines 459-464:

> The polarization correction vanishes pointwise for circular illumination, in
> expectation for random-orientation linear illumination, and to within 2.5%
> for multipath averaging above 20 paths.

The first annotation crosses out **circular**.

### PDF feedback

Replacement:

> circularly polarized

### Interpretation

The feedback makes the physical state explicit and corrects the adjectival
construction.

### Verdict

**Accept.**

### Recommended handling

Apply as part of the joint rewrite proposed under item 11.

### Suggested final writing

See item 11 for the complete sentence.

## 11. “Linear” replaced by “circularly polarized”

### Manuscript context

The same sentence continues:

> ...in expectation for random-orientation linear illumination...

The following explanatory sentences, lines 464-468, distinguish the two cases:

> First, for circular polarization the TE and TM intensities are equal at every
> point... Second, for linear polarization with random ensemble orientation...

### PDF feedback

The annotation crosses out **linear** and stores the same replacement as item
10:

> circularly polarized

Literal result:

> ...in expectation for random-orientation circularly polarized illumination...

### Interpretation

The literal replacement is incompatible with the mathematics and the next two
sentences. It is almost certainly a copy-paste error made while applying the
parallel edit in item 10. The intended term is probably **linearly polarized**.

### Verdict

**Reject the literal replacement. Accept the likely grammatical intent.**

### Recommended handling

Do not ask for clarification unless formal feedback tracking requires it. The
surrounding derivation resolves the ambiguity unambiguously.

### Suggested response to the comment

> I interpreted the second replacement as “linearly polarized.” Replacing it
> literally with “circularly polarized” would duplicate the first condition and
> contradict the ensemble-orientation derivation below.

### Suggested final writing for items 10 and 11

> The polarization correction vanishes pointwise for circularly polarized
> illumination, in expectation for randomly oriented linearly polarized
> illumination, and to within 2.5% under multipath averaging with at least 20
> paths.

## 12. Uncommented highlight on the Section III heading

### Manuscript context

Line 482:

> III. Method: pseudo-Brewster compensation

### PDF feedback

The entire heading is highlighted in magenta. The annotation contains no
comment or replacement.

### Interpretation

No reliable intent can be recovered. It may be a reading marker, an accidental
highlight, or an unrecorded reminder.

### Verdict

**No action.** A highlight without a comment is not an instruction.

### Recommended handling

Do not alter the heading and do not invent a response.

### Suggested final writing

Unchanged unless another independent editorial decision changes the section
title.

## 13. Why stop the error analysis at 75 degrees?

### Manuscript context

Lines 519-527 state that Figure 3 and Table I quantify the deviation of
`T_avg` from `T_0` over 0 to 75 degrees, with a maximum of 5.6%. The plotted
curves themselves continue toward 90 degrees.

The main-paper validation later says that local relative error rises beyond 75
degrees but those triangles carry about 15% of absorbed power. SI lines 267-285
provide the full explanation:

- grazing triangles make up 50% of illuminated area in the deliberately
  grazing-heavy top-down case;
- cosine weighting reduces them to about 15% of absorbed power;
- relative error becomes unstable because both APD values approach zero;
- absolute error stays at or below about 2% of peak APD; and
- integrated absorbed-power error is about 0.35% in that case.

### PDF feedback

> Why not go up to 90 degrees to see the approximation error over the full range
> of incidence angles?

### Interpretation

The 75-degree endpoint looks selective unless the reader understands why a
relative error at grazing incidence is not operationally meaningful.

### Verdict

**Accept the concern, adapt the remedy.** Do not promote a maximum relative
error through 90 degrees as the headline metric. At 90 degrees both reference
and prediction vanish under the cosine factor, making their relative difference
ill-conditioned.

### Recommended handling

Keep the curves through the full angular range. Explain the 75-degree cutoff at
its first use. Report absolute or integrated error for the grazing interval and
point to the SI. Coordinate this edit with removal of Table I under item 15.

### Suggested response to the comment

> The curves do extend to grazing incidence. We stop the relative-error summary
> at 75 degrees because both absorbed-power values vanish as cos(theta) goes to
> zero, so the ratio ceases to be informative. We should explain this in the
> main text and point to the full absolute and integrated grazing analysis in
> the SI.

### Suggested final writing

> Over 0 to 75 degrees, `T_avg/T_0` deviates from unity by at most 5.6%,
> with the maximum near 70 to 75 degrees. At more grazing angles, both the
> reference and approximate APD vanish under the cosine weight, so relative
> error becomes ill-conditioned. The full-range absolute and integrated errors
> are quantified in Section S1-C of the SI.

An optional second sentence can surface the strongest result:

> Even for top-down illumination, where grazing facets are most prevalent,
> facets above 75 degrees carry about 15% of absorbed power and the integrated
> error is about 0.35%.

## 14. The tissue-universality evidence is only at 28 GHz

### Manuscript context

Lines 574-604 say:

> All biological tissues at the wireless mmWave band cluster in the
> |n-tilde| > 2.5 region where the compensation operates. Table II lists the
> relevant parameters at 28 GHz...

The table gives skin, muscle, fat, and water at one frequency. The next
subsection evaluates frequency dependence from 0.3 to 100 GHz, but does so for
skin. The SI likewise gives a cross-tissue comparison at 28 GHz and a wideband
skin analysis.

### PDF feedback

> This is only at 28 GHz, what about a larger band of frequencies? Your title
> mentions 1 to 100 GHz.

### Interpretation

The broad paper title does not require every table to cover the full band, but
the phrase “all biological tissues at the wireless mmWave band” is broader than
the evidence shown at that point.

### Verdict

**Accept the concern.** The current universal wording is under-supported by a
single-frequency cross-tissue table. The solution should be proportional and
should not create another large main-paper table.

### Recommended handling

Preferred option:

1. Run a frequency sweep over the genuinely relevant outer tissues using the
   same IT'IS Cole-Cole data.
2. Put the full envelope or compact figure in the SI.
3. State the limiting tissue and worst deviation over the claimed 6-100 GHz
   surface-law regime in one main-text sentence.

Safe fallback if that sweep is not performed:

1. Remove “all biological tissues at the wireless mmWave band.”
2. Present Table II explicitly as a representative 28 GHz snapshot.
3. State that the wideband demonstration in the next subsection is for skin.

### Suggested response to the comment

> Agreed that the current wording is broader than the cross-tissue evidence.
> The title does not require each table to span the full band, but the
> universality claim should either be backed by a cross-tissue frequency sweep
> or narrowed to a 28 GHz snapshot.

### Suggested final writing after the preferred analysis

Use this structure with values filled only after the sweep:

> Across 6-100 GHz, the relevant outer tissues remain within [verified bound]
> of the constant-`T_0` approximation over the operational angular range. The
> limiting case is [tissue and frequency], while skin remains within [verified
> bound]. Full frequency-resolved results are given in Section [SI reference].

### Suggested final writing for the safe fallback

> Table II gives a representative cross-tissue snapshot at 28 GHz. Skin and
> muscle have |n-tilde| near 5 and angular variation below 5.6%, while fat is
> the low-index outlier. The following subsection evaluates the wideband
> frequency dependence for skin from 0.3 to 100 GHz.

## 15. Omit Table I and keep only the maximum ratio in prose

### Manuscript context

Table I lists `T_s`, `T_p`, `T_avg`, and `T_avg/T_0` at six angles from 0 to
75 degrees. Figure 3 already plots the same quantities. Lines 524-527 already
state the maximum deviation and its angular location.

### PDF feedback

> Table could be omitted with only the maximum T_avg/T_0 mentioned in the text.

### Interpretation

This is a space-saving suggestion. The table repeats numerical samples from the
curves rather than adding a new comparison.

### Verdict

**Accept.** The figure and prose carry the argument. Exact tabulated samples
can live in the SI or released data if needed.

### Recommended handling

Delete Table I from the main paper. Report the maximum deviation rather than
only the raw ratio because “5.6%” is immediately interpretable. Use unrounded
calculation values so the prose and any retained ratio do not appear
inconsistent. Coordinate the replacement paragraph with item 13.

### Suggested final writing

> At 28 GHz, `T_avg/T_0` deviates from unity by at most 5.6% over 0 to
> 75 degrees, with the maximum near 70 to 75 degrees. Below 30 degrees, the
> deviation remains below 0.2%.

## 16. Uncommented highlight on “Generalized Cauchy formula”

### Manuscript context

Line 804:

> B. Generalized Cauchy formula

### PDF feedback

The heading is highlighted in magenta without a comment or replacement.

### Interpretation

There is no recoverable proposal. It may simply mark the beginning of the
passage discussed in the next annotations.

### Verdict

**No action.**

### Recommended handling

Do not treat it as a request to rename or delete the subsection.

### Suggested final writing

Unchanged, apart from any independent terminology decision arising from item
17.

## 17. “Theorem 1” may be overstated

### Manuscript context

Lines 806-834 present the generalized Cauchy identity as Theorem 1. The proof
exchanges the surface and direction integrals using Fubini's theorem, applies
the definition of the exposure fraction, and uses the positive-cosine integral
over the sphere.

### PDF feedback

> It's maybe a stretch to call this a theorem, it's more a simple calculation.

### Interpretation

The concern is rhetorical rather than mathematical. A short proof can still
establish a theorem, but the label may make a direct identity look oversold.

### Verdict

**Partly accept.** The result is central and should remain visually prominent
and citable. Demoting it to ordinary prose would undersell the structural
identity. Calling it a proposition or named identity strikes the right balance.

### Recommended handling

Rename the environment to “Proposition 1” or introduce a boxed “Generalized
Cauchy identity.” If the paper retains a numbered proposition, keep the proof.
Also revisit Theorem 2. Leaving only the more peripheral 10 g cube result as a
theorem would create the wrong hierarchy, particularly if item 20 moves it to
the SI.

### Suggested response to the comment

> The proof is short, but the identity is central and needs a stable reference.
> I suggest demoting “Theorem” to “Proposition” rather than folding it into
> ordinary prose.

### Suggested final writing

> **Proposition 1 (generalized Cauchy identity).** Let a body Sigma have surface
> area A, exposure fraction eta(r), and absorption area
> `A_ab = integral_Sigma eta(r) dA`. Under isotropic, unpolarized plane-wave
> illumination of intensity IPD on tissue with normal-incidence transmission
> `T_0`, the direction-averaged whole-body absorbed power is
> `<P_abs> = IPD T_0 A_ab/4`.

## 18. Add intuition for the `S^2` integral

### Manuscript context

Lines 831-833 use

> `integral over S^2 of [n-hat dot (-k-hat)]_+ dOmega = pi` for any unit
> `n-hat`.

Here `S^2` is the unit sphere of incident directions. The anatomical surface is
denoted by `Sigma` elsewhere.

### PDF feedback

> Is there a simple intuition for this formula? This is valid for any surface
> S^2?

### Interpretation

The notation has caused exactly the confusion it can cause: `S^2` may look like
another body surface. The comment asks both for geometric intuition and for the
scope of the identity.

### Verdict

**Accept strongly.** This is high-value clarification at negligible space cost.

### Recommended handling

Explicitly define `S^2` as the sphere of directions. Choose the local normal as
the polar axis and show that the integral is the cosine-weighted solid angle of
one hemisphere. State that it holds for every unit normal, independently of the
body geometry.

### Suggested final writing

> Here `S^2` is the unit sphere of incident directions, not the body surface
> `Sigma`. Choosing `n-hat` as the polar axis reduces the positive-cosine
> integral to
> `2 pi integral_0^(pi/2) cos(theta) sin(theta) dtheta = pi`, so the identity
> holds for every unit normal independently of the body geometry. Integrating
> this local identity over `Sigma` gives Eq. (12).

## 19. Delete “from 1841” from the classical Cauchy formula

### Manuscript context

Line 836:

> The classical Cauchy formula from 1841 [11], <A_perp> = A/4, is the special
> case eta = 1, valid for any convex body.

The introduction, lines 186-189, already says:

> The local law then integrates over a nonconvex body through a generalized
> Cauchy identity from 1841 [11]...

### PDF feedback

The phrase **from 1841** is struck out without replacement.

### Interpretation

This may be a request to remove repetition. It may also reflect discomfort with
the historical aside.

### Verdict

**Adapt globally.** The local deletion is reasonable, but the introduction is
the less historically precise occurrence. It can imply that the paper's
generalized, occlusion-aware identity itself dates to 1841.

### Recommended handling

Retain one precise historical attribution. Describe the new result as a
generalization of Cauchy's 1841 surface-area identity. Then remove the repeated
date in the later sentence.

### Suggested final writing in the introduction

> The local law then integrates over a nonconvex body through a generalized
> form of Cauchy's 1841 surface-area identity, with self-shadowing represented
> by ambient occlusion.

### Suggested final writing in the Cauchy subsection

> The classical Cauchy formula [11], `<A_perp> = A/4`, is the special case
> `eta = 1`, valid for any convex body.

## 20. Omit the compliance-bounds section

### Manuscript context

Section VI begins at line 1368 and contains:

1. a worst-case whole-body SAR threshold derived from the Cauchy identity and a
   directivity bound;
2. a population table of threshold incident power densities;
3. a theorem linking local surface-averaged APD to peak spatial-average SAR in
   a 10 g cube; and
4. supporting discussion that continues into “Regulatory implications.”

The section is referenced in the abstract, contribution chain, flowchart,
roadmap, discussion, and conclusion. Removing it is therefore not an isolated
cut.

### PDF feedback

> I'm thinking that this section could be omitted to save space. IMO, it's not
> directly related to your new method.

### Interpretation

This is a scope and page-budget judgment. The comment views the regulatory
corollaries as secondary to the new dosimetry method.

### Verdict

**Partly accept. Do not delete everything.** The whole-body compliance result is
a direct consequence of the generalized Cauchy identity and demonstrates why
the new factorization matters. The 10 g cube theorem and full anthropometric
development are more peripheral and consume disproportionate space.

### Recommended handling

Preferred restructuring:

1. Keep a compact whole-body compliance corollary in the main paper.
2. Move the anthropometric table and its derivation to the SI.
3. Move the 10 g cube theorem and detailed geometry to the SI.
4. Merge the remaining practical consequence into the Discussion subsection
   “Regulatory implications.”
5. Shorten the abstract and flowchart claims if the corresponding detail is no
   longer in the main paper.

This addresses the co-promotor's valid focus concern without discarding the
application most directly enabled by the method.

### Suggested response to the comment

> I agree that the current section is too long relative to the core method. I
> would keep the whole-body compliance result because it follows directly from
> the Cauchy identity, but move the population table and 10 g cube derivation to
> the SI and merge the remaining result into the discussion.

### Suggested condensed main-paper writing

> **Whole-body compliance corollary.** Combining the direction-averaged identity
> `<P_abs> = IPD T_bar A_ab/4` with the directional bound
> `D(k-hat) <= 2A/A_ab` gives the worst-case threshold
> `IPD_max = 0.16 m/(T_bar A)` for the ICNIRP whole-body SAR limit of
> 0.08 W/kg. Thus the exposure threshold depends only on body mass, surface
> area, and tissue transmission. Population scaling and the corresponding
> 10 g cube bound are derived in the SI.

## 21. State whether the method over- or underestimates FDTD

### Manuscript context

The comment is anchored to “Regulatory implications” on page 12 and asks for a
statement either there or in the preceding discussion subsection.

The evidence in the paper is not one-sided:

- Full Fresnel on the 28 GHz phantom: the simplified law has a mean local error
  of -2.6% for facets below 75 degrees.
- The SI 128-direction sweep: mean bias is -1.2% with a 0.5% standard
  deviation.
- Mie at 28 GHz: the law underestimates absorption because omitted diffraction
  feeds the geometric shadow.
- Sim4Life: direction-averaged law-to-FDTD ratios are 1.027 at 7 GHz and 1.012
  at 5.8 GHz, while individual directions occur on both sides of unity.
- Below 6 GHz, the uncorrected surface law tends to underestimate because it
  omits body-scale Mie and layered-resonance effects.
- The constant-`T_0` direction average changes sign with frequency. For skin it
  underestimates below the approximately 40.4 GHz crossover and overestimates
  above it by at most 3.5% at 100 GHz.

There is also an important internal sign error to resolve. SI lines 364-367 and
the labels in `scripts/R_of_f_landscape.py` call `R < 1` “conservative.” With
`R = T_0/T_bar`, however, `R < 1` means that `T_0` underestimates absorbed
power. At fixed incident power this is non-conservative, and substituting `T_0`
for `T_bar` in a compliance threshold would overestimate the allowed incident
power. Conversely, `R > 1` overestimates absorbed power and is the conservative
side. The figure labels and the parenthetical statement in the SI should be
reversed unless a different definition of conservativeness was intended.

### PDF feedback

> In this or the previous section, could you say something about the
> conservativeness of your method? Compared to FDTD, does your method tend to
> over- or underestimate APD?

### Interpretation

The comment correctly distinguishes error magnitude from error direction. A
method used in compliance assessment needs a clear statement about whether it
is an upper bound, a lower bound, or neither.

### Verdict

**Accept strongly, with qualification.** The honest conclusion is not that the
closed form always overestimates or always underestimates. Its bias depends on
frequency, observable, geometry, and which correction is omitted.

The compliance calculation can still be conservative, but for a different
reason: it applies explicit inequalities such as `A_ab <= A` and the
directivity bound. That conservativeness must not be attributed to a systematic
positive bias in the APD approximation.

### Recommended handling

Add a short paragraph in the discussion before the regulatory implications.
Report the observed signs and state explicitly that the approximation is not a
one-sided bound. Then explain which later inequalities make the regulatory
threshold conservative. Correct the reversed conservative/non-conservative
labels in the `R(f)` figure and SI at the same time.

### Suggested response to the comment

> Good point. The comparisons do not support one universal bias sign. The local
> Fresnel and Mie approximations usually bias low in the tested cases, whereas
> the direction-averaged Sim4Life ratios are slightly above unity. The
> compliance result is conservative because of explicit geometric and
> directivity bounds, not because the APD law always overpredicts.

### Suggested final writing

> The closed form is not a one-sided approximation to FDTD. In the tested
> 28 GHz Fresnel and Mie cases, omitted angular and diffraction corrections
> bias absorbed power low, whereas the matched Sim4Life direction averages are
> 1.2% to 2.7% above FDTD and individual directions fall on both sides. The
> direction-averaged constant-`T_0` bias also changes sign near 40.4 GHz for
> skin. Consequently, conservativeness of the compliance threshold comes from
> the explicit bounds on absorption area and directivity, not from systematic
> overestimation by the APD law.

## Recommended implementation order

If these decisions are later applied to the manuscript, the efficient order is:

1. Resolve the two substantive scope decisions: the cross-tissue frequency
   sweep in item 14 and the compliance-section restructuring in item 20.
2. Revise the conservativeness discussion in item 21 using the final retained
   validation evidence.
3. Remove Table I and rewrite the grazing-angle explanation jointly under items
   13 and 15.
4. Update the Cauchy presentation jointly under items 17-19.
5. Update the flowchart after section and equation structure is stable.
6. Apply the remaining local copyedits last.

This ordering avoids polishing references and diagram labels that may move
during the structural edits.
