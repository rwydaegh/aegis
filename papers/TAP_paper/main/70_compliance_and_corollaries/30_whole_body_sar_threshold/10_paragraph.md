% PREV: \subsection{Whole-body SAR threshold}\label{subsec:compl-wb}
% NEXT: Body surface area follows the Du Bois formula~\cite{DuBois1916} $A
% NEXT: \approx 0.007184\,m^{0.425}\,h^{0.725}$ with mass in kg and height in
% NEXT: cm, so $\IPD_{\mathrm{max}}$ scales as $m/A \propto
% NEXT: \mathrm{BMI}^{0.575}\,h^{0.425}$. \Cref{tab:anthro} evaluates
% NEXT: \eqref{eq:Sinc-max-worst} on a representative population at
% NEXT: $28$~GHz with $\Tbar = 0.543$. The scaling
% NEXT: matches the observation in the dosimetry
% NEXT: literature~\cite{Hirata2007corr,Dimbylow2002} that absorption
% NEXT: cross-section scales with surface area while mass scales with
% NEXT: volume. Section~\ref{si:anthro} of the SI derives the Du Bois
% NEXT: scaling and bounds the linearly polarized worst-case correction to
% NEXT: \eqref{eq:Sinc-max-worst} via the body polarization directivity.
The ICNIRP 2020 guidelines~\cite{ICNIRP2020} specify a whole-body
average SAR limit of $0.08$~W/kg for the general public. The bound
$\Aperp(\khat) \le A/2$ on closed surfaces gives
$D(\khat) \le 2A/\Aab$. With $\mathrm{SAR}_{\mathrm{wb}} =
P_{\mathrm{abs}}/m$ and the conservative replacement $\Aab \le A$,
the worst-case threshold is
\begin{equation}\label{eq:Sinc-max-worst}
  \IPD_{\mathrm{max}} = \frac{0.16\,m}{\Tbar\,A}\, ,
\end{equation}
a closed-form function of body mass $m$, body surface area $A$,
and tissue transmission $\Tbar$, none of which requires an FDTD
solve on the specific exposure scenario.

## reviews (paragraph)



_PaperMaker9000 sweep — 2 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — 2 flag(s), 39 cleared:
    - `latex.substitutions.units_math_mode_consistent` (medium): `average SAR limit of $0.08$~W/kg for the general public` -> Move the unit inside math mode: $0.08\,\mathrm{W/kg}$ rather than $0.08$~W/kg.
    - `latex.spacing_ties.thin_space_math_units` (medium): `average SAR limit of $0.08$~W/kg for the general public` -> Write $0.08\,\mathrm{W/kg}$ so number and unit share math mode with a thin space, not $0.08$ in math and W/kg in text.
- **incremental (2026-05-22)** — pass (3 new/edited rules cleared).

