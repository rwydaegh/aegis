% PREV: Body surface area follows the Du Bois formula~\cite{DuBois1916} $A
% PREV: \approx 0.007184\,m^{0.425}\,h^{0.725}$ with mass in kg and height in
% PREV: cm, so $\IPD_{\mathrm{max}}$ scales as $m/A \propto
% PREV: \mathrm{BMI}^{0.575}\,h^{0.425}$. \Cref{tab:anthro} evaluates
% PREV: \eqref{eq:Sinc-max-worst} on a representative population at
% PREV: $28$~GHz with $\Tbar = 0.543$. The scaling
% PREV: matches the observation in the dosimetry
% PREV: literature~\cite{Hirata2007corr,Dimbylow2002} that absorption
% PREV: cross-section scales with surface area while mass scales with
% PREV: volume. Section~\ref{si:anthro} of the SI derives the Du Bois
% PREV: scaling and bounds the linearly polarized worst-case correction to
% PREV: \eqref{eq:Sinc-max-worst} via the body polarization directivity.
% NEXT: \begin{table}[!t]
% NEXT: \centering
% NEXT: \caption{Worst-case compliance threshold across the human
% NEXT: population at $28$~GHz with $\Tbar = 0.543$. The threshold
% NEXT: varies by a factor of about two between an infant and a large adult.}
% NEXT: \label{tab:anthro}
% NEXT: \small
% NEXT: \setlength{\tabcolsep}{3pt}
% NEXT: \begin{tabular}{lccc}
% NEXT: \toprule
% NEXT: Body type & $m$\,[kg] & $h$\,[cm] & $\IPD_{\mathrm{max}}$\,[W/m$^2$] \\
% NEXT: \midrule
% NEXT: Infant ($1$~yr) & 8   & 70  & 6.2  \\
% NEXT: Child ($6$~yr)  & 20  & 110 & 7.6  \\
% NEXT: Adolescent      & 50  & 160 & 9.9  \\
% NEXT: Adult (ref.)    & 70  & 170 & 11.4 \\
% NEXT: Large adult     & 100 & 180 & 13.5 \\
% NEXT: \bottomrule
% NEXT: \end{tabular}
% NEXT: \end{table}
Implications for the existing ICNIRP general-public reference level
above $6$~GHz are stated in \cref{subsec:disc-regulatory}.

## reviews (paragraph)



_PaperMaker9000 sweep — 3 flag(s) across 4 lens(es)._

- **sentence-craft** — 2 flag(s), 12 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `Implications for the existing ICNIRP general-public reference level above $6$~GHz are stated in \cref{subsec:disc-regulatory}.` -> Make the cross-ref the active subject: "\cref{subsec:disc-regulatory} states the implications for the existing ICNIRP general-public reference level above $6$~GHz."
    - `style.positive_voice.subject_verb_early` (medium): `Implications for the existing ICNIRP general-public reference level above $6$~GHz are stated` -> Front the verb: "\cref{subsec:disc-regulatory} states the implications ..." lands subject-verb within the first three words.
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.tilde_spacing` (high): `above $6$~GHz` -> Add a tie before the number: "above~$6$~GHz" so the value cannot break from its preceding word.
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.cref_capitalized`: The reference sits mid-sentence (after "stated in"), so lowercase \cref renders the correct mid-sentence label; \Cref is only for sentence-initial position.
    - _dismissed_ `latex.spacing_ties.tilde_number_unit`: The number-unit tie ($6$~GHz) is already present and correct; the missing tie before $6$ is a word-before-number case outside this number-unit rule (it belongs to the Wout tilde-spacing rule, not here).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

