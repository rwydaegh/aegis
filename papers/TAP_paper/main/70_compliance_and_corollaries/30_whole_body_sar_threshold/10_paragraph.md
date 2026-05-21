% PREV: \subsection{Whole-body SAR threshold}\label{subsec:compl-wb}
% NEXT: Body surface area follows the Du Bois formula~\cite{DuBois1916} $A
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
    - `latex.substitutions.units_math_mode_consistent` (medium): "average SAR limit of $0.08$~W/kg for the general public" → Move the unit inside math mode: $0.08\,\mathrm{W/kg}$ rather than $0.08$~W/kg.
    - `latex.spacing_ties.thin_space_math_units` (medium): "average SAR limit of $0.08$~W/kg for the general public" → Write $0.08\,\mathrm{W/kg}$ so number and unit share math mode with a thin space, not $0.08$ in math and W/kg in text.

