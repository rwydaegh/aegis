% PREV: \subsection{Quantitative behavior across angle}\label{subsec:pB-quant}
% NEXT: \begin{figure}[!t]
% NEXT:   \centering
% NEXT:   \begin{subfigure}[t]{\columnwidth}
% NEXT:     % In-figure label renamed to "Pseudo-Brewster angle" and shifted left
% NEXT:     % to clear its arrow; see scripts/apd_direction_analysis.py.
% NEXT:     \includegraphics[width=\linewidth]{apd_angle_panel_T.pdf}
% NEXT:     \caption{Fresnel transmission $T$.}
% NEXT:     \label{fig:apd-angle:T}
% NEXT:   \end{subfigure}\\[2pt]
% NEXT:   \begin{subfigure}[t]{\columnwidth}
% NEXT:     \includegraphics[width=\linewidth]{apd_angle_panel_APD.pdf}
% NEXT:     \caption{Normalized absorbed power $\APD/\IPD$.}
% NEXT:     \label{fig:apd-angle:APD}
% NEXT:   \end{subfigure}
% NEXT:   \caption{Pseudo-Brewster compensation for skin at 28~GHz
% NEXT:   ($\ntilde = 4.49 - 1.79i$, $T_0 = 0.539$). (a)~Fresnel
% NEXT:   power-absorption coefficients $T_s$ (TE), $T_p$ (TM), and
% NEXT:   $\Tavg = \tfrac{1}{2}(T_s + T_p)$ versus incidence angle $\theta$.
% NEXT:   $\Tavg/T_0$ is at most $1.056$ over $[0^\circ,90^\circ]$.
% NEXT:   (b)~Normalized absorbed power $\APD/\IPD = T(\theta)\cos\theta$
% NEXT:   for the same three states. The dotted reference is the simplified
% NEXT:   $T_0\cos\theta$ prediction.}
% NEXT:   \label{fig:apd-angle}
% NEXT: \end{figure}
\Cref{fig:apd-angle} illustrates the compensation for skin at
28~GHz. \Cref{fig:apd-angle:T} shows $T_s$, $T_p$, and $\Tavg$ versus
incidence angle. \Cref{fig:apd-angle:APD} shows the normalized absorbed power
$\APD/\IPD = T(\theta)\cos\theta$ for each polarization and for the
simplified product $T_0\cos\theta$. The unpolarized curve closely
tracks the simplified prediction, and the small gap is the Fresnel
approximation error. $\Tavg/T_0$ is at most $1.056$ across
$[0^\circ,90^\circ]$ on skin at 28~GHz. Below $20^\circ$, the
deviation stays below $0.2\%$.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).
