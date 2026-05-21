% PREV: Below $6$~GHz the ICNIRP basic restriction is the peak spatial-average
% NEXT: The bound follows from energy conservation on the cube footprint,
The following bound links the cube quantity to APD.
\begin{theorem}\label{thm:apd-bound}
For an axis-aligned $10$~g cube placed per IEC/IEEE~62704-1 on a planar
three-layer body, the peak spatial-average SAR satisfies
\begin{equation}\label{eq:apd-bound}
  \mathrm{psSAR}_{10\mathrm{g}}
  \;\le\; \frac{\sqrt{2}\,\APDAvg}{\rho_m\,L}\, ,
\end{equation}
where $L = (m/\rho_m)^{1/3} = 21.5$~mm and $\APDAvg$ is the local
absorbed power density. At the ICNIRP basic restriction
$\APDAvg \le 10$~W/m$^2$, this implies
$\mathrm{psSAR}_{10\mathrm{g}} \le 0.66$~W/kg, a factor of three below
the head and trunk basic restriction of $2$~W/kg and a factor of six
below the limb restriction of $4$~W/kg.
\end{theorem}

## reviews (paragraph)


_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
    - _dismissed_ `style.pet_peeves_wout.hackneyed_nouns`: Here factor is the multiplicative ratio sense (factor of three, factor of six), a concrete quantitative comparison, not the empty-filler factor the rule targets.
- **lexical-spotcheck** — pass (54 rules cleared).
    - _dismissed_ `BOOK_ELOS_style.misused_words.factor_hackneyed`: factor of three and factor of six are exact multiplicative ratios (the bound versus the 2 and 4 W/kg restrictions), not the X is a key factor in Y filler the rule targets.
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.math.subscript_labels_upright`: The m subscript on rho is the mass density m, the same italic mass variable used standalone in L = (m/\rho_m)^{1/3}; making it \mathrm{m} would mismatch that variable, and the form is used consistently paper-wide.
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: The paper's consistent house style is $<number>$~<unit> with text-mode units and a tilde (hundreds of instances: $28$~GHz, $0.08$~W/kg); this matches the tilde_number_unit positive example 100~mW, no siunitx is used, and switching one leaf to math-mode units would break paper-wide consistency.
    - _dismissed_ `latex.math.thin_space_units`: Same house-style convention: the number sits in math mode and the unit follows in text mode with a tilde, applied uniformly across the paper rather than the \,\mathrm{} math-mode form.

