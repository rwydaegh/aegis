% PREV: \subsection{Tissue universality}\label{subsec:pB-tissues}
% NEXT: \begin{table}[!t]
% NEXT: \centering
% NEXT: \caption{Pseudo-Brewster compensation across tissue types at
% NEXT: 28~GHz. The variation column is the maximum deviation of
% NEXT: $\Tavg/T_0$ from unity over $[0^\circ, 75^\circ]$.}
% NEXT: \label{tab:materials}
% NEXT: \begin{tabular}{lccccc}
% NEXT: \toprule
% NEXT: Tissue & $\varepsilon_r$ & $\sigma$\,[S/m] & $|\ntilde|$ & $T_0$
% NEXT:   & $\Tavg$ var. \\
% NEXT: \midrule
% NEXT: Skin   & 17.0 & 25.0 & 4.84 & 0.54 & $5.6\%$ \\
% NEXT: Muscle & 25.0 & 30.0 & 5.62 & 0.48 & $4.8\%$ \\
% NEXT: Fat    &  4.0 &  2.0 & 2.05 & 0.77 & $8.2\%$ \\
% NEXT: Water  & 25.0 & 55.0 & 6.62 & 0.45 & $3.9\%$ \\
% NEXT: \bottomrule
% NEXT: \end{tabular}
% NEXT: \end{table}
All biological tissues in the wireless mmWave band cluster in the
$|\ntilde| > 2.5$ region where the compensation operates.
\Cref{tab:materials} lists the relevant parameters at 28~GHz from
the IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}. Skin and
muscle have $|\ntilde|$ near $5$ and an angular variation below
$5.6\%$. Water has $|\ntilde| > 6$ and a variation below $4\%$.
Fat is the outlier, with $|\ntilde| \approx 2$ and an $8.2\%$
variation, but fat is rarely the outermost tissue at exposure sites
of regulatory interest. Above $6$~GHz, the relevant outermost
tissues are skin and vitreous humor.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
    - _dismissed_ `latex.substitutions.approx_text_vs_math`: This is a genuine math-mode relation between the quantity $|\ntilde|$ and a value, not \approx standing in for the prose word 'approximately' (the rule's '$\approx 5\%$' failure mode); legitimate use.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).
