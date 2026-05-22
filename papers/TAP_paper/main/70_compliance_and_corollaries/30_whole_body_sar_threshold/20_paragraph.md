% PREV: The ICNIRP 2020 guidelines~\cite{ICNIRP2020} specify a whole-body
% PREV: average SAR limit of $0.08$~W/kg for the general public. The bound
% PREV: $\Aperp(\khat) \le A/2$ on closed surfaces gives
% PREV: $D(\khat) \le 2A/\Aab$. With $\mathrm{SAR}_{\mathrm{wb}} =
% PREV: P_{\mathrm{abs}}/m$ and the conservative replacement $\Aab \le A$,
% PREV: the worst-case threshold is
% PREV: \begin{equation}\label{eq:Sinc-max-worst}
% PREV:   \IPD_{\mathrm{max}} = \frac{0.16\,m}{\Tbar\,A}\, ,
% PREV: \end{equation}
% PREV: a closed-form function of body mass $m$, body surface area $A$,
% PREV: and tissue transmission $\Tbar$, none of which requires an FDTD
% PREV: solve on the specific exposure scenario.
% NEXT: Implications for the existing ICNIRP general-public reference level
% NEXT: above $6$~GHz are stated in \cref{subsec:disc-regulatory}.
Body surface area follows the Du Bois formula~\cite{DuBois1916} $A
\approx 0.007184\,m^{0.425}\,h^{0.725}$ with mass in kg and height in
cm, so $\IPD_{\mathrm{max}}$ scales as $m/A \propto
\mathrm{BMI}^{0.575}\,h^{0.425}$. \Cref{tab:anthro} evaluates
\eqref{eq:Sinc-max-worst} on a representative population at
$28$~GHz with $\Tbar = 0.543$. The scaling
matches the observation in the dosimetry
literature~\cite{Hirata2007corr,Dimbylow2002} that absorption
cross-section scales with surface area while mass scales with
volume. Section~\ref{si:anthro} of the SI derives the Du Bois
scaling and bounds the linearly polarized worst-case correction to
\eqref{eq:Sinc-max-worst} via the body polarization directivity.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — 1 flag(s), 53 cleared:
    - `BOOK_ELOS_style.misused_words.while_as_although` (low): `absorption cross-section scales with surface area while mass scales with volume` -> Replace contrastive "while" with "whereas": "...scales with surface area, whereas mass scales with volume."
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: Paper-wide convention spells "Section" and uses \ref for SI cross-refs (a dozen identical "Section~\ref{si:...} of the SI" instances); not a \cref needing capitalization.
    - _dismissed_ `latex.floats_refs.label_prefix_conventions`: si: is the deliberate prefix for supplementary-information sections throughout the paper, kept distinct from main-text sec:.
    - _dismissed_ `latex.spacing_ties.tilde_number_unit`: Matches the universal paper convention (number then ~unit in text, e.g. 28~GHz, $6$~GHz, $100$~GHz); siunitx is not adopted, so this is consistent, not a violation.
- **incremental (2026-05-22)** — pass (3 new/edited rules cleared).

