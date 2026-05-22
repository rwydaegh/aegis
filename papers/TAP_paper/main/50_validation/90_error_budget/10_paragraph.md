% PREV: \subsection{Error budget}\label{subsec:corr-summary}
% NEXT: \begin{figure}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\columnwidth]{error_budget_comprehensive.pdf}
% NEXT:   \caption{Error budget for the geometric law in two regimes at
% NEXT:   $28$~GHz on skin. Worst case is single body part, single direction,
% NEXT:   pointwise. Typical case is whole-body integrated,
% NEXT:   direction-averaged. Only the dielectric uncertainty stays large in
% NEXT:   the typical case.}
% NEXT:   \label{fig:err-budget}
% NEXT: \end{figure}
\Cref{fig:err-budget} reports two regimes side by side at $28$~GHz on
skin. The worst case is single body part, single direction, pointwise
local. The typical case is whole-body integrated, direction-averaged.
The dielectric input spread is $\pm 20\%$ on $\varepsilon_r$ and
$\sigma$. This is the inter-model gap between Gabriel
\textit{et~al.}~\cite{Gabriel1996} and the empirical
Gabriel-times-$1.2$ fit that Christ \textit{et~al.}~\cite{Christ2021}
obtained from $S_{11}$ measurements on $37$ volunteers at
$40$--$110$~GHz. The spread is consistent with mmWave dielectric
campaigns more
broadly~\cite{AlekseevZiskin2007,Sasaki2014,Zhadobov2011}.
We evaluate $T_0 = 4n/[(1+n)^2+\kappa^2]$ at the four corners of the
$\pm 20\%$ box. The largest deviation on skin at $28$~GHz is
$\pm 7\%$. The Fresnel approximation worst case is $5.3\%$ pointwise
local (\cref{tab:phantom}). The typical case is $1.2\%$
direction-averaged on whole-body absorbed power (Supplementary
Information, $128$-direction sweep). The diffraction worst case is
$10\%$ on a torso-scale Mie sphere (\cref{subsec:val-mie}). The
typical case is $1.2\%$ integrated on Thelonious (Supplementary
Information, GELU integration). The inter-body reflection worst
case is $4\%$ under the diffuse bound. The typical case is $1\%$
under specular at mmWave (\cref{subsec:corr-residuals}). In the
typical case every model error stays below the dielectric uncertainty.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `We evaluate $T_0 = 4n/[(1+n)^2+\kappa^2]$ at the four corners of the $\pm 20\%$ box.` -> Drop the pronoun: "Evaluating $T_0 = 4n/[(1+n)^2+\kappa^2]$ at the four corners of the $\pm 20\%$ box gives a largest skin deviation of $\pm 7\%$ at $28$~GHz." or noun-verb "$T_0$, evaluated at the four corners of the $\pm 20\%$ box, deviates by at most $\pm 7\%$ on skin."
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): `obtained from $S_{11}$ measurements on $37$ volunteers at` -> Tie the bare count: "on~$37$ volunteers" so the number cannot orphan-break, matching the near-universal tie applied elsewhere in the leaf.
    - _dismissed_ `style.anti_ai_language.in_summary_in_conclusion_opener`: "In the typical case" is a factual scope qualifier carrying a new comparison, not an "In summary/Overall" recap opener.
    - _dismissed_ `style.pet_peeves_wout.hackneyed_nouns`: "worst case"/"typical case" is the load-bearing dosimetry regime terminology the figure compares, not empty filler like factor/aspect.
    - _dismissed_ `style.anti_ai_language.internal_brand_names_in_prose`: Thelonious is a published anatomical phantom name, not an internal codebase/project brand.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `style.misused_words.obtains_gets`: "obtained from measurements" is idiomatic data-acquisition usage; swapping to "got" would read as colloquial and degrade clarity, not improve it.
    - _dismissed_ `BOOK_ELOS_style.misused_words.case_redundant`: "worst case"/"typical case" name the two regimes the figure plots; they are not deletable "in many cases" padding.
    - _dismissed_ `style.prose_structure.staccato_sentences`: The rule prefers short single-claim sentences; these are exactly that, not subordinate-clause-heavy failures.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.math.subscript_labels_upright`: $\varepsilon_r$ (relative permittivity) is the field-standard typesetting with italic r; forcing \mathrm{r} would be non-standard, merely different, not better.
    - _dismissed_ `latex.substitutions.cref_capitalized`: Lowercase \cref in mid-sentence parentheses renders "(table ...)" deliberately; \Cref is reserved for sentence-initial use, applied consistently across the leaf.
    - _dismissed_ `latex.structure_style.acronym_first_use`: GELU is a method term used throughout the paper and defined at its true first use elsewhere; this is not the first occurrence, so no expansion is owed here.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

