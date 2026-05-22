% PREV: Above $6$~GHz, \eqref{eq:cauchy-exact} matches the plateau values
% PREV: reported by Bamba, Flintoft, and Zhang. Below $6$~GHz, Flintoft and
% PREV: Zhang observe a structured dip near $3$~GHz that the homogeneous
% PREV: half-space model does not reproduce~\cite{Flintoft2014,Zhang2017thesis}. The
% PREV: dip is anatomical. Flintoft's negative
% PREV: correlation of $\langle Q^a\rangle$ with mean subcutaneous fat
% PREV: thickness $d_{\mathrm{SF}}$ is steepest at $3$~GHz
% PREV: ($-0.0061\,\mathrm{mm}^{-1}$, $R^2 = 0.40$,~\cite[Table~6]{Flintoft2014}),
% PREV: with the slope falling to $-0.0030\,\mathrm{mm}^{-1}$ at $7$--$11$~GHz.
% NEXT: Zhang derives the planar limit of this model in his
% NEXT: thesis~\cite[Sec.~2.2]{Zhang2017thesis} and observes the resonance
% NEXT: shift with fat thickness in his Figs.~2.7--2.8, writing that ``the
% NEXT: fat layer may act as a matching layer between skin and
% NEXT: muscle''~\cite[p.~21]{Zhang2017thesis}. The contribution here is to
% NEXT: embed the planar model in the body-surface integral via $\Tlay$ and
% NEXT: \eqref{eq:cauchy-exact}, which makes the resonance compatible with a
% NEXT: Cauchy-style direction average. Body-surface averaging suppresses
% NEXT: the oscillation by a factor of approximately
% NEXT: $A_{\mathrm{exposed,fat}}/A$ because different body regions carry
% NEXT: different fat thicknesses, with limbs near $2$~mm and abdomen near
% NEXT: $30$~mm, and consequently different resonance frequencies. The
% NEXT: integrated dip is shallower than the single-thickness prediction but
% NEXT: is at the same frequency. The local surface map
% NEXT: $\APD(\rr) \approx \IPD\,T_0 \Vis \pospart{\mu}$ loses pointwise
% NEXT: meaning below $6$~GHz, where the SAR penetration depth exceeds the
% NEXT: surface layer thickness. Total power remains valid via $\Tlay$
% NEXT: throughout.
The mechanism is a Fabry--P\'erot resonance in the subcutaneous fat
layer. Below $6$~GHz the SAR penetration depth in fat exceeds
$70$~mm, against fat thicknesses of $2$--$20$~mm in the Flintoft
cohort~\cite[Table~1]{Flintoft2014}. The wave passes through the fat
layer with little attenuation and reflects from the fat-muscle
interface. Constructive interference enhances absorption, and destructive
interference suppresses it. A three-layer transfer-matrix model gives the layered transmission,
stacking skin, fat, and a semi-infinite muscle half-space,
\begin{equation}\label{eq:T-lay}
  \Tlay(f, d_{\mathrm{SF}})
  = 1 - \bigl|\widetilde{\Gamma}_1(f, d_{\mathrm{SF}})\bigr|^2\, ,
\end{equation}
where $\widetilde{\Gamma}_1$ is the generalized Fresnel reflection
coefficient at the air-skin interface, computed recursively from the
fat-muscle interface upward~\cite{Chew1995,BornWolf1999}.
Section~\ref{si:layered} of the SI gives the full Chew recursion,
the standing-wave SAR per layer, and the layer-by-layer cube
integral. Fig.~\ref{fig:si-tlay-fr} of the SI shows $\Tlay(f)$ for
the canonical $2$~mm skin / $10$~mm fat / muscle stack. Replacing
$\Tbar$ with $\Tlay$ in~\eqref{eq:cauchy-exact} gives a
frequency-dependent direction-averaged absorbed power that includes
the fat-layer resonance. For a fat thickness of $10$~mm the model
predicts a $40\%$ enhancement above the homogeneous prediction at
$0.9$~GHz (quarter-wave matching) and a $27\%$ reduction at
$3.5$~GHz (destructive interference).

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.subject_verb_early` (medium): `A three-layer transfer-matrix model with skin, fat, and a semi-infinite muscle half-space gives the layered transmission` -> Front the verb and move the layer list to the end: 'A three-layer transfer-matrix model gives the layered transmission, stacking skin, fat, and a semi-infinite muscle half-space.'
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.excess_vocabulary_tiers`: enhances/suppresses is the conventional antonym pair for constructive/destructive interference; honest literal physics, not the puffery sense of the common-set word.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.prose_structure.kiss_simple_verbs`: enhances/suppresses is the standard interference vocabulary, parallel and unambiguous; swapping to increases/reduces would not improve clarity. The result verbs use the preferred simple gives, not yields.
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.structure_style.no_sentence_starting_with_acronym` (medium): `Fig.~\ref{fig:si-tlay-fr} of the SI shows $\Tlay(f)$ for` -> Spell out the abbreviation at sentence start: "Figure~\ref{fig:si-tlay-fr} of the SI shows..."
    - _dismissed_ `latex.floats_refs.fig_abbrev`: Same text as the sentence-start defect, which the dedicated no_sentence_starting_with_acronym rule owns; mid-sentence Fig.~\ref usage elsewhere is correct, so this abbrev rule is otherwise satisfied.
    - _dismissed_ `latex.structure_style.acronym_first_use`: SAR is the paper's central quantity, defined far earlier (Section 2); this Section-4 leaf is not its first use, so no first-use violation is provable from the leaf.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

