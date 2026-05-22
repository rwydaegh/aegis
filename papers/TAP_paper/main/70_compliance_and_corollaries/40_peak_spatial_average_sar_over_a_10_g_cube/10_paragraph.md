% PREV: \subsection{Peak spatial-average SAR over a 10~g cube}\label{subsec:compl-cube}
% NEXT: The following bound links the cube quantity to APD.
% NEXT: \begin{theorem}\label{thm:apd-bound}
% NEXT: For an axis-aligned $10$~g cube placed per IEC/IEEE~62704-1 on a planar
% NEXT: three-layer body, the peak spatial-average SAR satisfies
% NEXT: \begin{equation}\label{eq:apd-bound}
% NEXT:   \mathrm{psSAR}_{10\mathrm{g}}
% NEXT:   \;\le\; \frac{\sqrt{2}\,\APDAvg}{\rho_m\,L}\, ,
% NEXT: \end{equation}
% NEXT: where $L = (m/\rho_m)^{1/3} = 21.5$~mm and $\APDAvg$ is the local
% NEXT: absorbed power density. At the ICNIRP basic restriction
% NEXT: $\APDAvg \le 10$~W/m$^2$, this implies
% NEXT: $\mathrm{psSAR}_{10\mathrm{g}} \le 0.66$~W/kg, a factor of three below
% NEXT: the head and trunk basic restriction of $2$~W/kg and a factor of six
% NEXT: below the limb restriction of $4$~W/kg.
% NEXT: \end{theorem}
Below $6$~GHz the ICNIRP basic restriction is the peak spatial-average
SAR over a $10$~g cube~\cite{ICNIRP2020,62704-1}. An
energy-conservation argument on the cube footprint bounds this
restriction by the absorbed power density, so no explicit cube search
is needed.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.units_math_mode_consistent`: Number-in-math, unit-in-text+tilde ($N$~unit) is the paper's deliberate and overwhelmingly dominant convention (hundreds of uses; no siunitx anywhere); this leaf follows it, so flagging would break consistency rather than improve it.
    - _dismissed_ `latex.structure_style.acronym_first_use`: Section 70 leaf deep in the paper; SAR is defined far earlier on first use, so expanding it here would be wrong, not an improvement.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

