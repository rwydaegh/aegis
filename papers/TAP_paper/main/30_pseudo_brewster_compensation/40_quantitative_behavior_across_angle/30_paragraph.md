% PREV: \begin{figure}[!t]
% PREV:   \centering
% PREV:   \begin{subfigure}[t]{\columnwidth}
% PREV:     % In-figure label renamed to "Pseudo-Brewster angle" and shifted left
% PREV:     % to clear its arrow; see scripts/apd_direction_analysis.py.
% PREV:     \includegraphics[width=\linewidth]{apd_angle_panel_T.pdf}
% PREV:     \caption{Fresnel transmission $T$.}
% PREV:     \label{fig:apd-angle:T}
% PREV:   \end{subfigure}\\[2pt]
% PREV:   \begin{subfigure}[t]{\columnwidth}
% PREV:     \includegraphics[width=\linewidth]{apd_angle_panel_APD.pdf}
% PREV:     \caption{Normalized absorbed power $\APD/\IPD$.}
% PREV:     \label{fig:apd-angle:APD}
% PREV:   \end{subfigure}
% PREV:   \caption{Pseudo-Brewster compensation for skin at 28~GHz
% PREV:   ($\ntilde = 4.49 - 1.79i$, $T_0 = 0.539$). (a)~Fresnel
% PREV:   power-absorption coefficients $T_s$ (TE), $T_p$ (TM), and
% PREV:   $\Tavg = \tfrac{1}{2}(T_s + T_p)$ versus incidence angle $\theta$.
% PREV:   $\Tavg$ stays within $5.6\%$ of $T_0$ up to $75^\circ$.
% PREV:   (b)~Normalized absorbed power $\APD/\IPD = T(\theta)\cos\theta$
% PREV:   for the same three states. The dotted reference is the simplified
% PREV:   $T_0\cos\theta$ prediction.}
% PREV:   \label{fig:apd-angle}
% PREV: \end{figure}
% NEXT: \begin{table}[!t]
% NEXT: \centering
% NEXT: \caption{Fresnel transmission for skin at 28~GHz. Here $T_0 =
% NEXT: \Tavg(0)$ is the normal-incidence value, and $\Tavg/T_0$ stays
% NEXT: within $5.6\%$ of unity over $[0^\circ, 75^\circ]$.}
% NEXT: \label{tab:fresnel-skin}
% NEXT: \begin{tabular}{ccccc}
% NEXT: \toprule
% NEXT: $\theta$ & $T_s$ (TE) & $T_p$ (TM) & $\Tavg$ & $\Tavg/T_0$ \\
% NEXT: \midrule
% NEXT: $0^\circ$  & 0.539 & 0.539 & 0.539 & 1.000 \\
% NEXT: $30^\circ$ & 0.489 & 0.591 & 0.540 & 1.002 \\
% NEXT: $45^\circ$ & 0.422 & 0.666 & 0.544 & 1.010 \\
% NEXT: $60^\circ$ & 0.321 & 0.791 & 0.556 & 1.032 \\
% NEXT: $70^\circ$ & 0.233 & 0.902 & 0.568 & 1.054 \\
% NEXT: $75^\circ$ & 0.182 & 0.952 & 0.567 & 1.053 \\
% NEXT: \bottomrule
% NEXT: \end{tabular}
% NEXT: \end{table}
\Cref{tab:fresnel-skin} quantifies the deviation of $\Tavg$ from
$T_0$ across $[0^\circ, 75^\circ]$ on skin at 28~GHz. The maximum
deviation is $5.6\%$ at $70$--$75^\circ$. Below $30^\circ$ the agreement
is at the fourth significant figure.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

