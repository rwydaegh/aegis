# ET annotations on TAP paper v3

Source: `tap_paper_v3_et.pdf`

Annotation author recorded in the PDF: `Seau`

This file transcribes all 21 non-link annotations and identifies the text or
paper element to which each one applies. For Acrobat replacement markup, the
popup content is the proposed replacement, not the text that was crossed out.
Two magenta highlights have no attached text and therefore have no reliably
recoverable requested action.

These are advisory comments from a co-promotor, not an accepted change list.
The editorial assessment at the end of this file independently evaluates each
suggestion.

## Main feedback themes

- Tighten terminology and grammar through several direct replacements.
- Make the flowchart map more explicitly onto the paper's sections or equations.
- Broaden or better justify the evidence over incidence angle and frequency.
- Reduce space spent on a numerical table and possibly the compliance section.
- Explain the Cauchy identity more intuitively and avoid overselling it as a
  theorem.
- State whether the closed form is conservative relative to FDTD.

## Page 1

### 1. Make the geometry scalar explicitly geometry-dependent

Location: Abstract, `paper.tex` lines 129-131.

Marked text:

> ...a generalized Cauchy whole-body identity with one **geometry** scalar.

Replacement stored in the strikeout annotation:

> geometry-dependent

Intended edit:

> ...with one **geometry-dependent** scalar.

### 2. Replace “polarization-aware” with “polarization-inclusive”

Location: Abstract validation list, `paper.tex` lines 135-137.

Marked text:

> full **polarization-aware** Fresnel calculations

Replacement stored in the strikeout annotation:

> inclusive

Intended edit:

> full **polarization-inclusive** Fresnel calculations

### 3. Compare the claimed error with variation among FDTD implementations

Location: Abstract, the sentence claiming that the high-frequency error is
below 5% and within uncertainty in human-skin dielectric parameters,
`paper.tex` lines 138-140.

Exact comment:

> Is it also not well within variations between FDTD implementations? I heard these could amount to 20% difference.

Meaning: the comment asks for the 5% error to be put in the context of inter-FDTD
variation as well as dielectric-parameter uncertainty. The 20% figure is
presented as something he has heard, so it needs verification and a suitable
source before it is stated in the paper.

### 4. “Exposure on” to “exposure of”

Location: First sentence of the introduction, `paper.tex` line 153.

The strikeout is physically attached to **on** in the first line, not to **in**
in the following line.

Marked text:

> Wireless exposure **on** the human body is regulated...

Replacement stored in the strikeout annotation:

> of

Intended edit:

> Wireless exposure **of** the human body is regulated...

### 5. Insert “in” after “validated”

Location: End of the introduction's novelty statement, `paper.tex` lines
197-199.

Marked text:

> ...the first closed-form APD law for the human body, validated four independent ways.

Inserted text:

> in

Intended edit:

> ...validated **in** four independent ways.

### 6. Repeat “geometry-dependent” in contribution 1

Location: Contribution 1, `paper.tex` lines 201-205.

Marked text:

> ...a flux-weighted transmission scalar and an ambient-occlusion **geometry** scalar.

Replacement stored in the strikeout annotation:

> geometry-dependent

Intended edit:

> ...an ambient-occlusion **geometry-dependent** scalar.

## Page 2

### 7. Remove the duplicated timing phrase in contribution 3

Location: Contribution 3, `paper.tex` lines 212-215.

The strikeout covers the complete phrase **one 10 ms** and stores **a** as its
replacement.

Marked text:

> ...the absorbed-power map is **one 10 ms** matrix-vector multiply.

Intended edit:

> ...the absorbed-power map is **a** matrix-vector multiply.

This removes the timing from this sentence rather than producing “a 10 ms
matrix-vector multiply.” The timing is already stated elsewhere.

### 8. Put section or equation numbers inside the flowchart

Location: Figure 1 and its caption, beginning “Flowchart of our approach,”
around `paper.tex` lines 250-350. The highlight is on the opening of the
caption, but the requested change is to the flowchart blocks.

Exact comment:

> Maybe it's clearer to include Section or formula numbers in the flowchart. It should be easier to follow the exposition if it is clearly matched to the blocks in the flowchart.

Meaning: label the boxes or reduction arrows with the corresponding section
numbers and/or equation numbers. The goal is a direct visual mapping from the
figure to the order of exposition, rather than leaving that mapping only in the
caption.

## Page 3

### 9. “Polarization-degenerate” to “polarization-independent”

Location: Definition of the normal-incidence value immediately before Eq. (3),
`paper.tex` lines 418-421.

Marked text:

> ...giving the **polarization-degenerate** value

Replacement stored in the strikeout annotation:

> independent

Intended edit:

> ...giving the **polarization-independent** value

### 10. Expand “circular” to “circularly polarized”

Location: Summary of the conditions under which the polarization correction
vanishes, `paper.tex` line 462.

Marked text:

> ...vanishes pointwise for **circular** illumination...

Replacement stored in the strikeout annotation:

> circularly polarized

Intended edit:

> ...vanishes pointwise for **circularly polarized** illumination...

### 11. Replacement attached to “linear” is probably a copy-paste error

Location: The next line in the same sentence, `paper.tex` lines 462-463.

Marked text:

> ...in expectation for random-orientation **linear** illumination...

Literal replacement stored in the PDF:

> circularly polarized

Taken literally, this would produce:

> ...in expectation for random-orientation circularly polarized illumination...

That literal edit conflicts with both the preceding condition and the detailed
explanation immediately below. Circular polarization already makes the
correction vanish pointwise, while the ensemble-average argument in lines
466-468 explicitly concerns linear polarization. The likely intended parallel
copyedit is therefore **linearly polarized**, not **circularly polarized**:

> ...in expectation for random-orientation **linearly polarized** illumination...

This item should be confirmed rather than applying the PDF replacement
literally.

### 12. Uncommented highlight on the Section III heading

Location: Entire heading “III. Method: pseudo-Brewster compensation,”
`paper.tex` line 482.

The heading is highlighted in magenta, but the annotation has no comment or
replacement text. No exact requested edit can be recovered. It may be a reading
marker or a reminder about the section's naming, but it is not safe to infer a
change from the highlight alone.

## Page 4

### 13. Show or discuss approximation error through 90 degrees

Location: Figure 3, near the high-angle end of panel (a). This also applies to
the surrounding analysis and Table I, which currently quantify the
approximation only over 0 to 75 degrees, `paper.tex` lines 520-572.

Exact comment:

> Why not go up to 90 degrees to see the approximation error over the full range of incidence angles?

Meaning: justify the 75-degree cutoff or extend the quantitative error analysis
to grazing incidence. Although the plotted curves visually approach 90
degrees, the stated error range, caption, and table stop at 75 degrees.

### 14. The cross-tissue evidence is only at 28 GHz

Location: “Tissue universality,” specifically “Table II lists the relevant
parameters **at 28 GHz**,” `paper.tex` lines 574-604.

Exact comment:

> This is only at 28 GHz, what about a larger band of frequencies? Your title mentions 1 to 100 GHz.

Meaning: the broad 1-100 GHz title creates an expectation that the
cross-tissue universality claim is supported across frequency, not at one
frequency only. The following subsection does sweep frequency, but primarily
for skin. The comment asks for broader-frequency support or a clearer
scope statement for the multi-tissue claim.

### 15. Omit Table I and retain only its maximum ratio in prose

Location: Table I, “Fresnel transmission for skin at 28 GHz,” especially the
maximum values 1.054 and 1.053 in the last column, `paper.tex` lines 554-572.

Exact comment:

> Table could be omitted with only the maximum T_avg/T_0 mentioned in the text.

Meaning: save space by deleting the angle-by-angle numerical table. Preserve
the main result in the prose, namely that the maximum displayed
`T_avg/T_0` is 1.054, corresponding to about a 5.4% increase over `T_0`
(reported elsewhere with rounding as a 5.6% maximum deviation).

## Page 6

### 16. Uncommented highlight on “Generalized Cauchy formula”

Location: Subsection heading “B. Generalized Cauchy formula,” `paper.tex` line
804.

The heading is highlighted in magenta with no attached comment or replacement
text. As with the Section III heading on page 3, there is no recoverable
actionable request.

### 17. Do not present the identity as a theorem

Location: “Theorem 1” and the statement of Eq. (12), `paper.tex` lines 806-817.

Exact comment:

> It's maybe a stretch to call this a theorem, it's more a simple calculation.

Meaning: lower the rhetorical status of the result. Present it as an identity,
proposition, result, or direct calculation rather than a formally numbered
theorem.

### 18. Add intuition and clarify what the `S^2` integral means

Location: The proof step

> `integral over S^2 of [n-hat dot (-k-hat)]_+ dOmega = pi for any unit n-hat`

at `paper.tex` lines 831-833.

Exact comment:

> Is there a simple intuition for this formula? This is valid for any surface S^2?

Meaning: explain that `S^2` here is the unit sphere of incident directions,
not the anatomical body surface `Sigma`. Rotational symmetry makes the result
independent of the particular unit normal. Choosing that normal as the polar
axis reduces the positive-cosine integral over the illuminated hemisphere to
`2 pi integral_0^(pi/2) cos(theta) sin(theta) dtheta = pi`. The comment also
wants the scope made explicit: this directional identity holds for any unit
normal, while the subsequent surface integration is what extends it over the
body geometry.

### 19. Delete “from 1841” in the later classical-formula sentence

Location: “The classical Cauchy formula from 1841 [11],” `paper.tex` line 836.

The strikeout covers **from 1841** and contains no replacement text.

Intended edit:

> The classical Cauchy formula [11], ...

This is a local deletion. It does not necessarily object to mentioning 1841
elsewhere in the introduction.

## Page 11

### 20. Consider omitting the entire compliance-bounds section

Location: Section VI, “Compliance bounds,” beginning at `paper.tex` line 1368
and continuing through both the whole-body SAR and 10 g cube bounds before
Section VII.

Exact comment:

> I'm thinking that this section could be omitted to save space. IMO, it's not directly related to your new method.

Meaning: this refers to all of Section VI, not just its heading. The co-promotor
sees the regulatory bound derivations as peripheral to the new closed-form
dosimetry method and suggests cutting them to reduce paper length.

## Page 12

### 21. State the direction of bias relative to FDTD

Location: Highlight on the subsection heading “B. Regulatory implications,”
`paper.tex` line 1508. “This or the previous section” most naturally refers to
Discussion VII-B or the preceding Discussion VII-A.

Exact comment:

> In this or the previous section, could you say something about the conservativeness of your method? Compared to FDTD, does your method tend to over- or underestimate APD?

Meaning: do not report only error magnitude. State whether comparisons show a
systematic positive or negative bias, whether the sign changes with frequency
or geometry, and in what sense any compliance result is conservative. If there
is no consistent sign, say that explicitly rather than implying the method is
always an upper or lower bound.

## Ambiguities requiring confirmation

1. The replacement of **linear** by **circularly polarized** on page 3 is almost
   certainly inconsistent with the surrounding physics. **Linearly polarized**
   is the likely intended wording.

2. The magenta highlights on the Section III and subsection IV-B headings have
   no attached text. They should be retained as undocumented markers, not
   translated into edits without clarification.

## Independent editorial assessment

Recommendation labels:

- **Accept** means the proposed change is sound as written or needs only trivial
  polishing.
- **Adapt** means the concern is valid, but a different implementation is
  stronger.
- **Verify** means the point may be useful but needs evidence before it enters
  the paper.
- **Decline** means the current wording or argument is preferable.
- **No action** means there is no recoverable proposal to assess.

### Assessment 1: “geometry” to “geometry-dependent”

**Recommendation: Adapt. Confidence: high.**

The original “one geometry scalar” is compressed and slightly unnatural.
“Geometry-dependent” is clearer, but the strongest abstract wording is **“a
single geometry-dependent scalar”** rather than “one geometry-dependent
scalar.” “A single geometric scalar” is even tighter, although it emphasizes
what kind of scalar it is rather than what it depends on.

### Assessment 2: “polarization-aware” to “polarization-inclusive”

**Recommendation: Decline. Confidence: high.**

“Polarization-aware Fresnel calculations” is established and immediately
understandable. “Polarization-inclusive” is unusual and could mean that several
polarizations were merely included in a test set. The calculation actually
resolves the local TE/TM content, so “polarization-aware” is more precise.

### Assessment 3: compare with 20% variation among FDTD implementations

**Recommendation: Decline the abstract change and verify the underlying claim.
Confidence: high.**

The comment raises a fair validation question, but “I heard” is not sufficient
support for a quantitative statement. More importantly, inter-code variation
is not the cleanest accuracy benchmark. The paper uses matched geometry,
dielectric properties, and excitation, so its most meaningful uncertainty
comparison is the propagated tissue-property uncertainty. A broad claim that
FDTD implementations differ by 20% could sound like lowering the validation
bar.

The existing paper already reports roughly ±15% scatter across three individual
FDTD directions at 7 GHz and calls it FDTD reference noise, while the
direction-averaged ratio is 1.027. That belongs in the validation discussion,
not the abstract. If a primary inter-code benchmark substantiates a 20% spread,
it could be mentioned there with careful qualification.

### Assessment 4: “exposure on” to “exposure of”

**Recommendation: Accept. Confidence: high.**

“Wireless exposure of the human body” is more idiomatic. It also avoids the
momentary spatial reading of “exposure on the body.”

### Assessment 5: insert “in” after “validated”

**Recommendation: Accept. Confidence: high.**

“Validated in four independent ways” is the standard construction and reads
better than “validated four independent ways.”

### Assessment 6: the second “geometry-dependent” replacement

**Recommendation: Adapt. Confidence: high.**

The existing “ambient-occlusion geometry scalar” is awkward. The proposed
replacement is clearer, but **“an ambient-occlusion scalar”** is cleaner still.
The preceding phrase already says that the calculation operates over anatomical
meshes, so repeating “geometry-dependent” is not essential. If parallelism with
the abstract matters, use the proposed wording consistently in both places.

### Assessment 7: remove “one 10 ms” from contribution 3

**Recommendation: Adapt. Confidence: high.**

The current phrase “one 10 ms matrix-vector multiply” is indeed poor English,
but deleting the timing loses a useful quantitative contribution. Prefer:

> ...the absorbed-power map is a single matrix-vector multiplication,
> evaluated in under 10 ms.

This preserves both structural simplicity and measured performance.

### Assessment 8: put section or equation numbers in the flowchart

**Recommendation: Accept, with restrained implementation. Confidence: high.**

This is strong navigational feedback. The caption currently contains the
mapping, but the reader has to translate it back into the diagram. Small,
automatically referenced equation numbers in the formula boxes would help most.
Section references can go on the reduction arrows or in small box subtitles.
Adding both everywhere would clutter the figure, so equation numbers should be
the priority.

### Assessment 9: “polarization-degenerate” to “polarization-independent”

**Recommendation: Adapt. Confidence: high.**

The proposed term is more accessible, but “polarization-independent” can sound
like a statement about the response at all angles. The equality is specifically
at normal incidence. The clearest wording is:

> ...giving the common normal-incidence value

Alternatively, “the polarization-independent normal-incidence value” is safe.
The original “degenerate” is technically defensible but unnecessarily
specialized here.

### Assessment 10: “circular” to “circularly polarized”

**Recommendation: Accept. Confidence: high.**

The proposed wording is both grammatically and physically clearer.

### Assessment 11: replace “linear” with “circularly polarized”

**Recommendation: Accept the likely intent, reject the literal replacement.
Confidence: very high.**

This is almost certainly a copied replacement value. The correct parallel phrase
is **“random-orientation linearly polarized illumination.”** The literal PDF
replacement would duplicate the circular-polarization case and contradict the
derivation in the next sentences.

### Assessment 12: uncommented Section III highlight

**Recommendation: No action. Confidence: high.**

There is no comment to evaluate. The heading should not be changed merely
because it was highlighted.

### Assessment 13: extend the angular error analysis to 90 degrees

**Recommendation: Adapt. Confidence: high.**

The concern is valid because the 75-degree cutoff otherwise looks selective.
Extending the headline relative-error bound to 90 degrees is not the right
solution. At grazing incidence both the predicted and reference APD vanish due
to the cosine factor, so their ratio becomes unstable and the relative error is
physically uninformative. The plotted curves already extend toward 90 degrees.

The main text should instead justify the cutoff immediately where it is
introduced. The SI already contains the correct explanation: triangles above
75 degrees contribute about 15% of absorbed power in the deliberately
grazing-heavy top-down test, their absolute error is at most about 2% of peak
APD, and the integrated error is about 0.35%. Bring a concise version of that
logic into the main paper and keep the full treatment in the SI.

### Assessment 14: broader frequency support for tissue universality

**Recommendation: Accept the concern and adapt the presentation. Confidence:
high.**

The title does not require every individual experiment to cover 1-100 GHz, but
the sentence “all biological tissues at the wireless mmWave band” is broader
than a four-material snapshot at 28 GHz. The next subsection gives a wideband
analysis for skin, not for all listed tissues.

The best response is not a large new main-paper table. Compute a small
cross-tissue envelope over the claimed 6-100 GHz range, place the full result in
the SI, and summarize the worst case or limiting tissue in one main-text
sentence. If that analysis does not support the universal wording, narrow the
claim instead.

### Assessment 15: omit Table I

**Recommendation: Accept. Confidence: high.**

The figure already conveys the angular behavior, and the prose already reports
the maximum deviation and where it occurs. The table repeats six samples of the
same curves. Removing it saves valuable space without weakening the argument.
If exact values are useful for reproducibility, move the table to the SI or rely
on the released data and script.

The prose should report the maximum **deviation**, not only the raw maximum
ratio, because “1.054” is less immediately interpretable than “about 5.4%.” The
small discrepancy with the paper's rounded 5.6% statement should also be made
internally consistent.

### Assessment 16: uncommented Cauchy-heading highlight

**Recommendation: No action. Confidence: high.**

There is no attached proposal. It may simply mark the start of the passage being
commented on.

### Assessment 17: demote “Theorem 1”

**Recommendation: Adapt. Confidence: medium-high.**

A result can be a theorem even when its proof is short, so “simple calculation”
is not by itself a mathematical objection. Still, the formal theorem label risks
making the paper sound as if it is inflating a direct Fubini and cosine-integral
identity. I would retain the result as a visually distinct, numbered
**proposition** or **generalized Cauchy identity**, not dissolve it into ordinary
prose. It is central enough to deserve emphasis.

If this is changed, inspect “Theorem 2” as well. Leaving only the secondary 10 g
cube bound as a theorem would produce the wrong hierarchy.

### Assessment 18: add intuition for the `S^2` identity

**Recommendation: Accept. Confidence: very high.**

This is excellent feedback. The notation uses `S^2` for the sphere of incident
directions and `Sigma` for the body surface, which is easy to misread. One
sentence choosing the normal as the polar axis explains both the value `pi` and
its independence from body geometry. This clarification costs almost no space
and makes the key derivation much more memorable.

### Assessment 19: delete “from 1841”

**Recommendation: Adapt across both occurrences. Confidence: high.**

Deleting the date here is reasonable if it remains in the introduction, but the
introduction currently says “a generalized Cauchy identity from 1841.” That can
incorrectly suggest that the generalized, occlusion-aware identity itself dates
to 1841.

Use one historically precise formulation in the introduction, such as:

> ...through a generalized form of Cauchy's 1841 surface-area identity...

Then the later sentence can simply say “The classical Cauchy formula [11].” The
goal should be one precise attribution, not merely deleting a repeated date.

### Assessment 20: omit the compliance-bounds section

**Recommendation: Adapt substantially, not a blanket deletion. Confidence:
medium-high.**

The concern about focus and length is fair. The whole-body compliance result is
a direct corollary of the new Cauchy identity and gives the method a concrete
regulatory payoff. Removing it entirely would also require retracting claims
from the abstract, flowchart, roadmap, discussion, and conclusion.

The 10 g cube theorem is more peripheral. A stronger structure would be:

1. Keep a short whole-body compliance corollary in the main paper.

2. Move the detailed anthropometric table, the full 10 g cube derivation, and
   supporting geometry to the SI.

3. Merge the remaining compliance consequence into “Regulatory implications”
   in the discussion.

This preserves the application most directly enabled by the method while
recovering much of the space and reducing the detour.

### Assessment 21: state whether the method over- or underestimates FDTD

**Recommendation: Accept, with an important qualification. Confidence: very
high.**

The paper should state the sign of the observed bias, but it cannot honestly
claim one universal direction:

- The simplified Fresnel law underestimates the full-Fresnel result on the
  28 GHz phantom by about 2.6% locally on average. The 128-direction SI sweep has
  about a 1.2% negative mean bias.

- The Mie comparison at 28 GHz also underestimates absorption because omitted
  diffraction feeds the geometric shadow.

- Against Sim4Life, the reported direction-averaged ratios are slightly above
  unity, 1.027 at 7 GHz and 1.012 at 5.8 GHz, while individual directions occur
  on both sides.

- Below 6 GHz, the uncorrected surface law tends to underestimate because it
  omits body-scale Mie and layered-resonance effects.

- The constant-`T_0` direction average changes sign with frequency. The paper
  already states that it underestimates below the roughly 40.4 GHz crossover
  and overestimates above it.

Therefore the **approximation itself is not uniformly conservative**. The
compliance result becomes conservative only when separate inequalities replace
the geometry or exposure quantities by upper bounds, such as `A_ab <= A` and
the directivity bound. That distinction should be stated explicitly. It answers
the comment accurately and prevents readers from confusing “small average
error” with “guaranteed upper bound.”

## Overall disposition

My suggested treatment of the 21 annotations is:

- Accept directly: 4, 5, 8, 10, 15, 18, and 21.
- Accept the concern but implement differently: 1, 6, 7, 9, 11, 13, 14, 17,
  19, and 20.
- Verify but do not add as currently phrased: 3.
- Decline: 2 and the literal form of 11.
- No action because no comment exists: 12 and 16.

3. The suggested 20% spread among FDTD implementations is hearsay in the
   comment. It needs verification before being used as a quantitative claim.
