# TAP paper — revision plan

## Where the paper is now (2026-05-09)

Two major moves landed in `paper.tex`:

- §VII.B (cube-SAR layered analysis) is cut to the SI. The
  contributions list dropped from 5 to 4 items.
- Remark 4 in §VII (reference-level shortfall) uses committed
  phrasing: "the closed form gives a closed-form certificate that
  the existing reference level fails the basic restriction for the
  three smaller body sizes under worst-case directional exposure."

What still needs doing in one sentence: the paper has the right
content but tells it in the wrong order. The GPU/ReLU framing is
in the conclusion. The regulatory finding is one remark. The
Discussion is only regime-of-validity. The revision below fixes
that without growing the paper.

The promoted §VIII.B prose (Edit 6) uses Robin's existing Remark 4
text verbatim where possible, preserving the "two facts cancel"
sentence and the "worst-case directional exposure" caveat. No
simplification of the $\IPD_{\mathrm{max}}$ derivation.

---

## Section structure: current vs proposed

| §    | Current                      | Proposed                                                             |
| ---- | ---------------------------- | -------------------------------------------------------------------- |
| I    | Introduction (flat)          | unchanged structure, abstract sentence 2 + closer reworked, intro paragraph 1 sentences appended |
| II   | Local absorption law         | unchanged                                                            |
| III  | Pseudo-Brewster              | unchanged                                                            |
| IV   | Whole-body absorbed power    | unchanged                                                            |
| V    | Validation                   | unchanged                                                            |
| VI   | Higher-order corrections     | unchanged                                                            |
| VII  | Compliance (1 subsec)        | Remark 4 body moves to §VIII.B; one-sentence pointer stays in §VII   |
| VIII | Discussion (3 subsecs)       | **4 subsecs**: A Computational structure (NEW) + B Regulatory implications (PROMOTED) + C Regime of validity (CURRENT, condensed) + D Future directions (MOVED from conclusion) |
| IX   | Conclusion (5 paragraphs)    | **3 paragraphs**, balanced over theory, computation, and policy     |

Size budget: §VIII gains roughly one column, §IX loses roughly half
a column, §VII loses one remark. Net delta close to zero.

---

## Edits in execution order

Each edit lists location, the current text or "—" for new prose,
the proposed text in Robin voice, and a Why. Reasons cite
`CRITIQUE_HIGH_LEVEL.md` items (CRIT~#N) where they apply.

Throughout, the LaTeX prose follows the project style guides:
sentence-case headings, no em dashes, no bold for emphasis, no
semicolons in body text, "First, ... Second, ... Third, ..." in
running prose, equation-end punctuation inside math, tilde-glued
units, numeric anchors on every cost claim. The markdown of this
planning doc uses tables and bullets for navigability and is not
the prose to be transferred.

### Edit 1. Abstract sentence 2 insertion

Location: lines 137–138.

Current sentence 2:
> "We replace the simulation with a closed form derived from the
> surface Fresnel law."

Proposed (replace with two sentences):
> "We replace the simulation with a closed form derived from the
> surface Fresnel law. On a body mesh of $10^4$ triangles under
> $10^2$ incident paths, the absorbed-power map is one
> matrix-vector multiply, evaluated in under $10$~ms on a modern
> GPU."

Why: the cost claim is the paper's most quotable result and it
currently first appears in conclusion paragraph 4. The abstract
reader must see it. Number is defensible from the existing matrix
form on line 851 plus the AO timing on line 901
("tens of milliseconds"). Addresses CRIT~#6 (wall-clock number).

### Edit 2. Abstract closing sentence

Location: lines 156–159.

Current:
> "It holds quantitatively from 1--100~GHz on whole-body quantities
> and from 6--100~GHz pointwise on the surface, reducing whole-body
> compliance to three precomputed scalars."

Proposed (replace with three sentences):
> "It holds quantitatively from 1--100~GHz on whole-body quantities
> and from 6--100~GHz pointwise on the surface, with a closed-form
> cost that is independent of frequency while FDTD scales as $f^4$.
> Whole-body compliance reduces to only three precomputed scalars.
> Antenna and beam optimization under exposure constraints become
> differentiable end-to-end."

Why: new closer couples high-band validity to the cost inversion,
states the compliance reduction in Robin's exact phrasing, and
adds the differentiability line. The $f^4$ frame is already
established in intro paragraph 1, so the abstract reader has the
hook. The three scalars are not named in the abstract because
the body section §VII names them; the abstract sells the
reduction, not the contents.

### Edit 3. Introduction paragraph 1, append two sentences

Location: end of paragraph 1, after line 190.

Proposed:
> "This work shows that the surface absorbed-power map on a
> $10^4$-triangle body mesh reduces to one matrix-vector multiply,
> evaluated in under $10$~ms on a commercial modern GPU at any
> frequency from 1 to 100~GHz. The whole-body absorbed power
> reduces to only three precomputed scalars: the body mass, the
> body surface area, and the flux-weighted Fresnel transmission."

Why: same headline as Edit 1, in the body. The phrase "at any
frequency from 1 to 100~GHz" closes the loop with the $f^4$ FDTD
scaling stated in the previous sentence, so the cost inversion is
implicit and clean.

### Edit 4. Reframe of intro paragraphs 2–3 — DROPPED

Robin: "leave it as is." The "Three gaps remain ... This work
closes the three gaps" structure stays. No edit.

### Edit 5. Contribution #2 wording

Location: lines 253–255 (item 2 of the `enumerate` block).

Current text stays in the enumerate as written:
> "A polarization cancellation theorem stating that the angular
> polarization correction vanishes under any of three conditions:
> circular illumination, random ensemble, or multipath averaging."

The contribution list is intentionally compact, so the simple
"vanishes under three conditions" stays. The precision goes into
the body where the result is derived (§II.D, lines 555–576).

Body text edit: in §II.D, after "The second term vanishes under
any of three conditions." (line 557), tighten the three-conditions
prose so each condition states the sense of "vanishes" cleanly.
Current §II.D text is essentially correct already (pointwise for
circular, in expectation for random ensemble, within $2.5\%$ for
multipath above 20 paths). The only change is to make those three
senses explicit in the leading sentence, e.g.:

Proposed body sentence:
> "The polarization correction vanishes pointwise for circular
> illumination, in expectation for random-orientation linear, and
> to within $2.5\%$ for multipath averaging above 20 paths."

Then keep the existing per-condition exposition as it stands.

Why: Robin: the contribution list is too dense a location to
unpack the three senses. The body is where precision lives. This
satisfies CRIT~#4 in spirit (a sharp reviewer cannot now object
to "this isn't a theorem" when reading §II.D) without changing
the contribution list itself.

### Edit 6. Move Remark 4 from §VII to a new §VIII.B

Location: §VII Remark~4 body (lines 1547–1567) becomes the body
of §VIII.B. A pointer stays in §VII.

What is replaced and what it becomes:

In §VII, the entire body of `\begin{remark}[Reference-level
shortfall for smaller body sizes]\label{rem:reflevel-shortfall}
... \end{remark}` (lines 1547–1567) is replaced by:

> "\begin{remark}[Reference-level shortfall for smaller body sizes]
> \label{rem:reflevel-shortfall}
> Implications for the existing ICNIRP general-public reference
> level above $6$~GHz are stated in
> \cref{subsec:disc-regulatory}.
> \end{remark}"

The `\label{rem:reflevel-shortfall}` is preserved so any
`\cref{rem:reflevel-shortfall}` elsewhere in the source still
resolves. (Quick check: a `grep -n
"rem:reflevel-shortfall"` over the source returns only the
definition. No risk of dangling references. If a future `\cref`
is added that points at the remark itself, it still lands on
the one-sentence pointer.)

In §VIII, after the new §VIII.A (Edit 7), insert §VIII.B with the
following body. Wording follows Robin's existing remark verbatim,
broken into three short paragraphs and given a topic-sentence
opening. No simplification of the derivation; the "two facts
cancel" reasoning that produces $A$ rather than $\Aab$ in the
denominator is preserved by reference to
`\cref{eq:Sinc-max-worst}` and `\cref{tab:anthro}`. The
"worst-case directional exposure" caveat is kept because it is
load-bearing.

> ```latex
> \subsection{Regulatory implications}
> \label{subsec:disc-regulatory}
> ```
>
> "Whole-body ICNIRP compliance reduces to one inequality on three
> precomputed scalars (\cref{eq:Sinc-max-worst}). The same algebra
> evaluates the existing reference levels for under- or
> over-protection across the population without an FDTD campaign.
>
> The ICNIRP general-public reference level above $6$~GHz is
> $10$~W/m$^2$~\cite{ICNIRP2020}. Reference levels are the
> operationally measured incident-power-density limits intended to
> imply compliance with the underlying basic restriction, here
> $0.08$~W/kg whole-body SAR. Setting $\IPD_{\mathrm{max}} =
> 10$~W/m$^2$ in~\eqref{eq:Sinc-max-worst} returns the threshold
> $m/A \geq 0.16 \cdot 10 / \Tbar$~kg/m$^2$, equal to
> $33.9$~kg/m$^2$ at $\Tbar = 0.543$ ($28$~GHz on skin).
> \Cref{tab:anthro} returns $\IPD_{\mathrm{max}}$ values of $6.2$,
> $7.6$, and $9.9$~W/m$^2$ for the infant, the six-year-old child,
> and the adolescent under the worst-case directional bound
> $D \le 2A_{\mathrm{CH}}/\Aab$. The reference level exceeds these
> thresholds by $61\%$, $32\%$, and $1\%$ respectively.
>
> The closed form gives a closed-form certificate that the existing
> reference level fails the basic restriction for the three smaller
> body sizes under worst-case directional exposure. Under realistic
> plane-wave or multipath exposure the directivity is below this
> worst case, and the basic restriction is met~\cite{ICNIRP2020}.
> The closed form makes both the worst-case and the
> directional-average evaluation explicit."

Why: a regulatory finding with numeric results on infants,
children, and adolescents is Discussion-quality material, not a
remark inside a derivation section. Promoting it to a subsection
means an ICNIRP / IEC / IEEE C95 reviewer scanning the Discussion
will land on it. Addresses CRIT~#5 with the structural move that
complements Robin's recent phrasing commitment.

Style check on §VIII.B: no em dashes, no semicolons, no bold for
emphasis, sentence-case heading, equation-end punctuation inside
math, tilde-glued units, numeric anchors throughout, "First, ...
Second" enumeration not used here because the prose flows as
condition + numeric result + caveat, which is the more natural
shape. All compliant.

LaTeX check: the existing equation labels
(`eq:Sinc-max-worst`), table label (`tab:anthro`), and remark
label (`rem:reflevel-shortfall`) are all preserved or moved
intact. The new subsection adds one new label
(`subsec:disc-regulatory`). The pointer remark in §VII references
this new label. No dangling refs.

### Edit 7. New §VIII.A — Computational structure

Location: §VIII opening, immediately after the section header.

This is new prose. Material is a promotion-with-extension of
conclusion paragraph 4 (lines 1762–1768) and the
matrix-multi-source paragraphs in §II.F (lines 824–863).

The "we are tired of FDTD" sub-message is delivered by citing two
recent end-to-end exposure pipelines from the same author group,
both of which use FDTD as the back-end and document its cost as a
limiting factor. The reader joins the dots.

Proposed §VIII.A body:

> ```latex
> \subsection{Computational structure}
> \label{subsec:disc-primitives}
> ```
>
> "The matrix form~\eqref{eq:mat-multi} is a single-hidden-layer
> rectified-linear network whose weights are the path directions
> and powers from a ray tracer~\cite{SionnaRT}. Three properties
> follow.
>
> First, the network is differentiable in every input. Replacing
> the hard $[\cdot]_+$ gate with the smooth GELU
> activation~\eqref{eq:gelu} preserves the chain rule. Gradients
> of regulatory quantities propagate to antenna positions, antenna
> orientations, beam codebooks, and reconfigurable-intelligent-
> surface phases through standard backpropagation. End-to-end
> exposure assessment in current practice carries a per-scenario
> FDTD evaluation on the user phantom as the back-end
> step~\cite{Wydaeghe2022access,Wydaeghe2026npj}. With the closed
> form replacing that step, exposure-constrained network design
> becomes a continuous optimization problem.
>
> Second, the per-triangle absorbed-power map for $M \approx 10^4$
> triangles and $N \approx 10^2$ paths is one matrix-vector
> multiply on a modern GPU, evaluated in under $10$~ms. The cost
> is independent of frequency. Against an FDTD reference whose
> cost scales as $f^4$, the speed advantage grows by roughly
> $10^4$ from $6$ to $60$~GHz, exactly the band where the Fresnel
> approximation is sharpest and the closed form holds pointwise
> within $3\%$ of FDTD (\cref{tab:bands}). The cosine gate is
> rectified shading. The visibility matrix $\mathbf{V}$ is ambient
> occlusion, one of the most optimized computations in real-time
> rendering~\cite{AkenineMoller2018}.
>
> Third, the whole-body identity~\eqref{eq:cauchy-exact} factorizes
> the body dependence into a single scalar $\Aab = \bar\eta\,A$.
> For a given phantom and posture, $\bar\eta$ is computed once, in
> tens of milliseconds, and cached. Population studies that
> previously required one FDTD solve per body and per direction
> reduce to one Fresnel quadrature shared across the population
> and one occlusion pass per body."

Citations to add to the bibliography (place in numerical order
after `Wydaeghe2026`). Both DOIs verified against IEEE Xplore /
NPJ Wireless Technology metadata:

```latex
\bibitem{Wydaeghe2022access}
R.~Wydaeghe, S.~Shikhantsov, E.~Tanghe, G.~Vermeeren, L.~Martens,
  P.~Demeester, and W.~Joseph, ``Realistic human exposure at
  3.5 and 28~GHz for distributed and collocated MaMIMO in indoor
  environments using hybrid ray-tracing and FDTD,'' \emph{IEEE
  Access}, vol.~10, pp.~130\,996--131\,004, 2022, doi:
  \doi{10.1109/ACCESS.2022.3227107}.

\bibitem{Wydaeghe2026npj}
R.~Wydaeghe, S.~Shikhantsov, G.~Vermeeren, L.~Martens, E.~Tanghe,
  and W.~Joseph, ``Hybrid ray-tracing-QuaDRiGa/FDTD method for
  realistic 28~GHz exposure with 6G CF-MaMIMO in 3D outdoor
  environments,'' \emph{npj Wireless Technol.}, vol.~2, no.~1,
  art.~no.~13, Apr. 2026, doi: \doi{10.1038/s44459-026-00031-4}.
```

Why: this places the GPU/ReLU/wall-clock argument in one
subsection with the implicit "FDTD is dead in 2026" message
delivered through citation rather than rhetoric. Both cited
papers themselves document FDTD as the bottleneck step in
end-to-end exposure assessment, so a reader who follows the
citations sees the direct evidence. Addresses CRIT~#6 in full
plus the Wout-vibe of fast-and-accurate at 60~GHz.

### Edit 8. Condense current Discussion subsections to §VIII.C

Location: current §VIII opening + §VIII.A + §VIII.B + §VIII.C
(lines 1592–1719) collapse into one new subsection, §VIII.C
"Regime of validity".

Cuts and keeps in detail:

| Current lines | Current content | Proposed action | Why |
| --- | --- | --- | --- |
| 1592–1602 | Section opening paragraph (1–100 GHz validity, three lower scales, two upper scales) | KEEP verbatim as the opening of §VIII.C | This is the topic-sentence paragraph the reader needs to navigate the rest |
| 1604–1619 | §VIII.A "Low-frequency boundary" opening (opacity criterion + skin-depth numbers across muscle frequencies) | KEEP the opacity criterion sentence and the 700~MHz / 250~MHz threshold sentence. REPLACE the muscle penetration depth list at lines 1611–1614 with one summary: "The IT'IS Cole–Cole model gives muscle skin-depth values that exceed limb cross-sections below approximately 1~GHz and torso cross-sections below approximately 250~MHz." | The SI does not separately tabulate muscle, so this is not a duplication cut. The list is intermediate detail; the threshold conclusion is what the reader needs |
| 1621–1641 | Mie regime paragraph (geometric-optics limit, $ka$ values across body parts and frequencies) | CUT to two sentences: "The Mie regime sets a second lower limit. The geometric-optics asymptote holds with sub-percent residual once $ka \gtrsim 30$ on a body characteristic dimension, and \cref{subsec:val-mie} quantifies the residual on body-scale spheres." | The detailed $ka$ table repeats `\cref{subsec:val-mie}` and `\cref{tab:bands}` without adding evidence |
| 1643–1681 | Whole-body resonance paragraph (300 MHz threshold, dipole resonance, current hot-spots) | CUT to two sentences: "Whole-body resonance dominates below approximately 300~MHz, where the body acts as a half-wave dipole and surface absorbed power is unrelated to internal hot-spots~\cite{Durney1986}. Below this frequency the framework reduces to volumetric solvers." | Outside the claimed validity, so deserves a flag rather than a paragraph |
| 1683–1704 | §VIII.B "High-frequency boundary" (Azzam softening + skin roughness) | KEEP verbatim | Both mechanisms are within the claimed band's edge; both deserve the current treatment |
| 1706–1719 | §VIII.C "Other regime boundaries" (near-field, dielectric uncertainty) | KEEP verbatim, fold into §VIII.C as the closing two paragraphs | Both are operational caveats the reader needs |

Net effect: §VIII.C is roughly two thirds of the current Discussion
length, freeing one column for §VIII.A and §VIII.B. The
table `\cref{tab:bands}` stays in place. No new prose; this is
purely cuts.

Why: the current Discussion is one long catalog. Condensing makes
room for the two new Discussion subsections without growing the
section.

### Edit 9. New §VIII.D — Future directions

Location: §VIII closing.

Three items per Robin's instructions: keep sub-1~GHz, talk about
coherent MIMO as a topic without citing paper~C, and add the
near-field generalisation with the equation from
`monograph_v2.tex` §sec:near-field.

Proposed §VIII.D body (the LaTeX block is in a code fence so the
math source survives the markdown render):

```latex
\subsection{Future directions}
\label{subsec:disc-future}

Three open problems sit outside the present scope. First, the
sub-$1$~GHz regime, where whole-body resonance dominates and
internal currents replace surface absorption as the relevant
physics, requires a coupled-current treatment that the surface
law does not provide.

Second, the coherent-beamforming regime. When $M$ antenna elements
radiate with controlled complex weights at short range from the
body, fields add as amplitudes rather than powers, and the
whole-body absorbed power becomes a Hermitian quadratic form
$\mathbf{x}^H \mathbf{Q}\,\mathbf{x}$ in the precoder
$\mathbf{x}$. The exposure operator $\mathbf{Q}$ has, in every
published instance, been calibrated by per-configuration FDTD on
the SAR-matrix formulation of Hochwald \textit{et
al.}~\cite{Hochwald2014}. Constructing $\mathbf{Q}$ in closed
form from the same propagation paths used by the present
framework is a natural extension.

Third, the near-field generalisation. At mmWave the
reactive-near-field boundary $d < \lambda/(2\pi)$ shrinks to
$1.7$~mm at $28$~GHz and $0.8$~mm at $60$~GHz, so all
device-body geometries beyond direct contact with the antenna
fall in the locally plane-wave regime. The local law generalises
by replacing the constant $\IPD$ and $\khat$ with their
point-source counterparts:
\begin{equation}\label{eq:near-field}
  \APD(\rr) = \frac{P_t\,G(\hat{k}(\rr))}{4\pi\,d(\rr)^2}\,T_0\,
              \pospart{\nhat(\rr)\cdot(-\hat{k}(\rr))}\,,
\end{equation}
where $P_t$ is the total radiated power, $G(\hat{u})$ the
antenna gain pattern, $d(\rr) = |\rr - \rr_s|$ the
source-to-surface distance, and $\hat{k}(\rr) = (\rr - \rr_s)/d(\rr)$
the local incidence direction. This enables fast and
differentiable near-field compliance testing of mmWave devices.
```

Notes:
- Item 1 keeps the original future-work item with a verb
  ("requires") and a concrete physics claim ("coupled-current
  treatment").
- Item 2 introduces the coherent-MIMO topic as a natural extension.
  Cites Hochwald \textit{et al.} as the foundational SAR-matrix
  paper. No mention of any specific follow-up paper, no suggestive
  language. paper~C will eventually cover this and read as a
  natural next paper, without the present paper telegraphing it.
- Item 3 is the near-field generalisation. The equation matches
  `monograph_v2.tex` line 2748 (`\cref{eq:Sab-point}`), translated
  into TAP notation ($\IPD$/$\APD$ instead of $\Sinc$/$\Sab$, and
  `\pospart{}` instead of `\ReLU`). Closing sentence is Robin's
  exact phrasing: "fast and differentiable near-field compliance
  testing of mmWave devices."

Citations to add to the bibliography:

```latex
\bibitem{Hochwald2014}
B.~M. Hochwald, D.~J. Love, S.~Yan, P.~Fay, and J.-M. Jin,
  ``Incorporating specific absorption rate constraints into wireless
  signal design,'' \emph{IEEE Commun. Mag.}, vol.~52, no.~9,
  pp.~126--133, Sep. 2014, doi: \doi{10.1109/MCOM.2014.6894463}.
```

Why: Robin specified each of these moves. The third item with
the explicit equation positions the near-field extension as a
short, immediately graspable next step rather than a vague
gesture. The DOI for Hochwald is verified: 10.1109/MCOM.2014.6894463.

### Edit 10. Conclusion — balanced over the whole paper

Location: §IX (lines 1721–1781).

Per Cargill §9.2 (`Writing_Scientific_Research_Articles.md`), the
Conclusion of a paper with a separate Discussion should restate
the most important findings in compressed form, with the
implications, in a way that reflects the full arc of the paper.
The previous proposed one-paragraph version covered only theory.
That is too narrow.

The new conclusion mirrors the structure of the paper as it now
stands: theory + validation, computation, regulatory implication.
Three short paragraphs, ordered so that each one closes on the
strongest claim of its thread.

Proposed:

> "The local APD on opaque biological tissue reduces to
> $\APD(\rr) = \IPD\,T_0\,\Vis(\rr,\khat)\,
> \pospart{\nhat\cdot(-\khat)}$. The direction-averaged whole-body
> absorbed power on any body opaque at the wavelength reduces to
> $\langle P_{\mathrm{abs}}\rangle = \IPD\,\Tbar(f)\,\Aab/4$. The
> collapse rests on a pseudo-Brewster compensation that places
> biological tissue in the high-index regime described by
> Azzam~\cite{Azzam2015} for optical substrates, and on a
> generalized Cauchy formula in which the self-shadowing factor
> is the ambient-occlusion primitive of computer graphics. From
> 1 to 100~GHz the closed form matches every published ground
> truth within the $\pm 7\%$ that the $\pm 20\%$ tissue
> dielectric uncertainty implies for $T_0$. The five empirical
> scalars reported by Bamba, Flintoft, Zhang, Diao, and Kodera
> reduce to two closed-form quantities, $\Tbar(f)$ and $\Aab/A$.
>
> The dosimetry block at the end of any ray tracer is one
> matrix-vector multiply with positive-part gating. On a
> $10^4$-triangle body mesh under $10^2$ incident paths, a full
> per-triangle absorbed-power map evaluates in under $10$~ms on a
> modern GPU at any frequency from 1 to 100~GHz. The cost is
> independent of frequency where FDTD scales as $f^4$, and
> gradients propagate to antenna positions, antenna orientations,
> beam codebooks, and reconfigurable-intelligent-surface phases
> through standard backpropagation.
>
> Whole-body ICNIRP compliance reduces to a closed-form function
> of three precomputed scalars: the body mass $m$, the body
> surface area $A$, and the flux-weighted Fresnel transmission
> $\Tbar$. Under the worst-case directional bound, the existing
> $10$~W/m$^2$ general-public reference level exceeds the
> basic-restriction threshold by $61\%$, $32\%$, and $1\%$ for
> infants, six-year-old children, and adolescents respectively.
> A regulatory campaign that takes weeks of FDTD reduces to one
> Fresnel quadrature against the IT'IS catalog and one
> ambient-occlusion pass on the body mesh."

Notes:
- Paragraph 1 is theory + validation + the synthesis-of-empirical-
  scalars line. Closes on the five-to-two reduction.
- Paragraph 2 is computational. Mirrors §VIII.A. Closes on the
  differentiability handle.
- Paragraph 3 is regulatory + operational close. Mirrors §VIII.B.
  Closes on the strongest one-line summary of the entire paper.

The mapping from current conclusion paragraphs is: current
paragraphs 1, 2, 3 → new paragraph 1; current paragraph 4 →
new paragraph 2 (with cost numbers added); current paragraph 5 →
split, with the regulatory finding lifted into new paragraph 3 and
the validity-bounds + future-work removed (those live in §VIII).

Why: per Cargill, the Conclusion should reflect every major
thread of the paper, not just one. The new Discussion adds two
threads (computation, regulation), so the Conclusion has to
acknowledge them. Three short paragraphs do this without growing
the section, since the moved-out paragraphs (4: GPU/ReLU; 5:
validity + future work) free more lines than the new content
adds.

---

## AI critique inventory: status

| #   | Item                                              | Status                       |
| --- | ------------------------------------------------- | ---------------------------- |
| 1   | Cut cube-SAR / sub-6 layered to SI                | DONE by Robin                |
| 2   | Lead §II with the answer                          | NOT DONE (would compete with Fig. 1; flagged for Robin) |
| 3   | Reframe "three gaps" as five-scalars synthesis    | DROPPED per Robin            |
| 4   | Demote polarization "theorem"                     | Edit 5 (precision goes into body §II.D, contribution-list wording stays) |
| 5   | Promote reference-level shortfall                 | Phrasing committed by Robin; structural move via Edit 6 |
| 6   | Move II.F + add wall-clock number + GPU section   | Edits 1, 3, 7                |
| 7   | Stronger Azzam optical-substrate hook             | NOT DONE (optional polish; see Decisions) |
| 8   | Body-text clarifications                          | NOT DONE (one-sentence fixes; see Decisions) |
| 9   | Re-render Fig. 5 without censor bars              | Robin's call                 |
| 10  | Length and venue fit                              | Largely fixed by item 1      |
| 11  | Tighten title                                     | Robin's call                 |

---

## Decisions Robin needs to make

1. **Abstract aggressiveness.** Edits 1+2 together insert four new
   sentences and remove one. Either commit to both, or commit only
   to Edit 1.

2. **§VIII.A length.** Three numbered properties as drafted, or
   condensed to one paragraph.

Once these two are picked, Edits 1–10 run mechanically. Citations
in Edits 7 and 9 are verified and ready to add as drafted.
