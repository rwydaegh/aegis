% PREV: Above $6$~GHz, \eqref{eq:cauchy-exact} matches the plateau values
% NEXT: Zhang derives the planar limit of this model in his
The mechanism is a Fabry--P\'erot resonance in the subcutaneous fat
layer. Below $6$~GHz the SAR penetration depth in fat exceeds
$70$~mm, against fat thicknesses of $2$--$20$~mm in the Flintoft
cohort~\cite[Table~1]{Flintoft2014}. The wave passes through the fat
layer with little attenuation and reflects from the fat-muscle
interface. Constructive interference enhances absorption, and destructive
interference suppresses it. A three-layer transfer-matrix model with
skin, fat, and a semi-infinite muscle half-space gives the layered
transmission
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
    - `style.positive_voice.subject_verb_early` (medium): "A three-layer transfer-matrix model with skin, fat, and a semi-infinite muscle half-space gives the layered transmission" → Front the verb and move the layer list to the end: 'A three-layer transfer-matrix model gives the layered transmission, stacking skin, fat, and a semi-infinite muscle half-space.'
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.anti_ai_language.excess_vocabulary_tiers`: enhances/suppresses is the conventional antonym pair for constructive/destructive interference; honest literal physics, not the puffery sense of the common-set word.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.prose_structure.kiss_simple_verbs`: enhances/suppresses is the standard interference vocabulary, parallel and unambiguous; swapping to increases/reduces would not improve clarity. The result verbs use the preferred simple gives, not yields.
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.structure_style.no_sentence_starting_with_acronym` (medium): "Fig.~\ref{fig:si-tlay-fr} of the SI shows $\Tlay(f)$ for" → Spell out the abbreviation at sentence start: "Figure~\ref{fig:si-tlay-fr} of the SI shows..."
    - _dismissed_ `latex.floats_refs.fig_abbrev`: Same text as the sentence-start defect, which the dedicated no_sentence_starting_with_acronym rule owns; mid-sentence Fig.~\ref usage elsewhere is correct, so this abbrev rule is otherwise satisfied.
    - _dismissed_ `latex.structure_style.acronym_first_use`: SAR is the paper's central quantity, defined far earlier (Section 2); this Section-4 leaf is not its first use, so no first-use violation is provable from the leaf.

