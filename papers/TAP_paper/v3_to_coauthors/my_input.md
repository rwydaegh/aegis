# Robin's decisions on ET's feedback

## Purpose

For each annotation, I choose one of the following:

- **ET**: accept Emmeric's suggestion.
- **AI**: use the assistant's recommendation.
- **RW**: use my wording, decision, or additional information.

We will later prepare a clear response document in which Emmeric, my
co-promotor, can see which comments were accepted, adapted, or declined.

## Decisions

### 1. Geometry-dependent scalar

**Decision: ET.**

Accept “geometry-dependent.” Use polished final wording rather than a literal
single-word substitution:

> Integrating the local law over the visible nonconvex body surface yields a
> generalized Cauchy whole-body identity governed by a single
> geometry-dependent scalar.

### 2. Polarization-aware versus polarization-inclusive

**Decision: AI.**

Keep “polarization-aware.” Explain the choice in the response report.

Suggested response:

> We retained “polarization-aware” because the calculation resolves the local
> TE and TM energy fractions. “Polarization-inclusive” could suggest only that
> several polarizations were included in the validation set.

### 3. Variation among FDTD implementations

**Decision: RW.**

Do not add the alleged 20% inter-implementation variation to the abstract.
Explain in the response report that the abstract uses the better-controlled
tissue-property uncertainty comparison. Do not state that the 20% figure is
established unless we obtain a direct primary source for inter-code variation.

Suggested response:

> We agree that numerical-reference variability is relevant, but we prefer not
> to add it to the abstract. The matched validation is more cleanly compared
> with the uncertainty propagated from measured tissue properties. The
> direction-level FDTD scatter is reported in the validation section.

### 4. Exposure on or of the human body

**Decision: ET.**

Change “exposure on the human body” to “exposure of the human body.”

### 5. Validated in four independent ways

**Decision: ET.**

Insert “in”:

> ...validated in four independent ways.

### 6. Ambient-occlusion scalar

**Decision: AI.**

Use the shorter wording:

> Whole-body absorbed power reduces to a flux-weighted transmission scalar and
> a single ambient-occlusion scalar.

### 7. Matrix-vector multiplication and timing

**Decision: AI.**

Fix the grammar but retain the timing result:

> For a body mesh under many incident paths, the absorbed-power map is a single
> matrix-vector multiplication, evaluated in under 10 ms.

### 8. Section or equation numbers in the flowchart

**Decision: RW.**

Do not add the references to the figure. Explain that they made the flowchart
too crowded and that the caption already maps the reductions to the relevant
derivations.

Suggested response:

> I tried adding equation and section references to the flowchart, but the
> result became too crowded. The caption already maps each reduction to the
> relevant derivation, so I retained the cleaner figure. I can share the
> alternate version if you would like to compare them.

### 9. Polarization-independent value

**Decision: ET, with the scope made explicit.**

Use:

> At normal incidence, $\mu=1$ and $\xi=\tilde n$, giving the
> polarization-independent normal-incidence value...

This avoids implying polarization independence at oblique incidence.

### 10. Circularly polarized illumination

**Decision: ET.**

Change “circular illumination” to “circularly polarized illumination.”

### 11. Linearly polarized illumination

**Decision: ET's likely intent.**

Use “linearly polarized,” not the literal copied replacement “circularly
polarized.” Do not mention the apparent copy-paste error in the response report.

Final sentence for items 10 and 11:

> The polarization correction vanishes pointwise for circularly polarized
> illumination, in expectation for randomly oriented linearly polarized
> illumination, and to within 2.5% under multipath averaging with at least 20
> paths.

### 12. Uncommented Section III highlight

**Decision: ask jointly with item 16.**

No manuscript change is justified by the highlight alone.

### 13. Extend Figure 3 to 90 degrees

**Decision: ET.**

Extend both Figure 3 panels to $90^\circ$. The correct generator is
`scripts/apd_direction_analysis.py`. It currently samples and displays only
$0^\circ$ to $85^\circ$.

Required script changes:

- Change `theta_deg = np.linspace(0, 85, 400)` to include $90^\circ$.
- Change both x-limits from 85 to 90.
- Add 90 to both x-tick lists.
- Regenerate `figures/apd_angle_panel_T.pdf` and
  `figures/apd_angle_panel_APD.pdf` in PDF mode.

Keep the text simple, but do not describe the full-range approximation error as
5.6%. See item 15.

### 14. Frequency range of the pseudo-Brewster evidence

**Decision: RW.**

Make no change. Omit this item from the response report.

### 15. Replace Table I with concise text

**Decision: RW.**

Remove Table I and thank Emmeric for the space-saving suggestion in the
response report.

Final writing:

> $T_{\mathrm{avg}}/T_0$ is at most 1.056 across
> $[0^\circ,90^\circ]$ on skin at 28 GHz. Below $20^\circ$, the deviation
> stays below 0.2%.

Suggested response:

> Thank you. We removed the redundant angle-by-angle table and retained the key
> behavior in the text. We also extended Figure 3 to $90^\circ$ so that the
> grazing-incidence behavior is visible.

### 16. Uncommented Cauchy-heading highlight

**Decision: ask jointly with item 12.**

Suggested one-sentence question:

> You highlighted the headings “Method: pseudo-Brewster compensation” and
> “Generalized Cauchy formula” without an attached comment. Did you intend a
> change to either heading?

### 17. Remove both theorem environments

**Decision: RW.**

Agree with Emmeric that the result does not need to be presented as a theorem.
Do not replace it with “Proposition 1.”

Keep the opening sentence:

> The generalized Cauchy formula is the central whole-body identity.

Then place the current theorem statement in normal, non-italic text. Continue
directly into the derivation without a separate proof heading or a QED box.
Replace:

> Apply Fubini's theorem...

with:

> To see why, apply Fubini's theorem...

Apply the same treatment to Theorem 2 in the compliance section. Remove the
theorem environment and keep the statement in normal, non-italic text. Do not
start a new paragraph after “The following bound links the cube quantity to
APD.” Continue directly:

> The following bound links the cube quantity to APD. For an axis-aligned 10 g
> cube placed per IEC/IEEE 62704-1 on a planar three-layer body, the peak
> spatial-average SAR satisfies

Then display Eq. (18) and continue with “where...” in normal text. Do not add a
theorem heading, proof heading, QED box, or extra line break before “For an
axis-aligned 10 g cube.”

Suggested response:

> Agreed. We removed both theorem environments. The generalized Cauchy result
> is now presented as the central whole-body identity followed directly by its
> short derivation, and the 10 g cube bound is stated directly in the compliance
> text.

### 18. Intuition for the $S^2$ identity

**Decision: RW.**

Do not change the manuscript. Give only a brief explanation in the response
report.

Suggested response:

> Here $S^2$ denotes the sphere of all incident directions, not the body
> surface. Choosing the local normal as the polar axis reduces the identity to
> the elementary cosine integral over one hemisphere, which equals $\pi$.

### 19. Delete “from 1841”

**Decision: RW.**

Make no manuscript change. Omit this item from the response report.

### 20. Omit the compliance-bounds section

**Decision: RW.**

Keep the section. Omit this item from the response report.

### 21. Conservativeness relative to FDTD

**Decision: RW.**

Make no manuscript change now. Omit this item from the response report. Revisit
the conservativeness wording and the `R(f)` sign labels later.

## Bibliographic update

The current reference reads:

> R. Wydaeghe et al., “Environmental and auto-induced RF-EMF adult and children
> far-field exposure simulations between 450 MHz and 26 GHz,” Phys. Med. Biol.,
> 2026, under review.

The paper has now been accepted. For now, use:

> R. Wydaeghe et al., “Environmental and auto-induced RF-EMF adult and children
> far-field exposure simulations between 450 MHz and 26 GHz,” Phys. Med. Biol.,
> accepted for publication, 2026.

Do not include a DOI yet. Revisit the bibliographic details later.

## Latexdiff deliverable for Emmeric

After all accepted manuscript changes are complete, prepare a compiled
before-and-after LaTeX diff for Emmeric.

- Use `v3_to_coauthors/paper.tex` as the unmodified before version.
- Use the final revised manuscript source as the after version.
- Generate the diff with `latexdiff --flatten` so included content is expanded.
- Compile the diff to PDF and inspect every changed region visually.
- Send the latexdiff PDF with the response document.
- If the SI changes, prepare a separate SI latexdiff using
  `v3_to_coauthors/paper_SI.tex` as its before version.

Planned command structure:

```bash
latexdiff --flatten v3_to_coauthors/paper.tex FINAL_PAPER.tex \
  > v3_to_coauthors/tap_paper_v3_et_latexdiff.tex
latexmk -pdf v3_to_coauthors/tap_paper_v3_et_latexdiff.tex
```

Replace `FINAL_PAPER.tex` with the actual revised source path after the edits
are complete.
