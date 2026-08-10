% PREV: \Cref{fig:apd-angle} illustrates the compensation for skin at
% PREV: 28~GHz. \Cref{fig:apd-angle:T} shows $T_s$, $T_p$, and $\Tavg$ versus
% PREV: incidence angle. \Cref{fig:apd-angle:APD} shows the normalized absorbed power
% PREV: $\APD/\IPD = T(\theta)\cos\theta$ for each polarization and for the
% PREV: simplified product $T_0\cos\theta$. The unpolarized curve closely
% PREV: tracks the simplified prediction, and the small gap is the Fresnel
% PREV: approximation error. $\Tavg/T_0$ is at most $1.056$ across
% PREV: $[0^\circ,90^\circ]$ on skin at 28~GHz. Below $20^\circ$, the
% PREV: deviation stays below $0.2\%$.
\begin{figure}[!t]
  \centering
  \begin{subfigure}[t]{\columnwidth}
    % In-figure label renamed to "Pseudo-Brewster angle" and shifted left
    % to clear its arrow; see scripts/apd_direction_analysis.py.
    \includegraphics[width=\linewidth]{apd_angle_panel_T.pdf}
    \caption{Fresnel transmission $T$.}
    \label{fig:apd-angle:T}
  \end{subfigure}\\[2pt]
  \begin{subfigure}[t]{\columnwidth}
    \includegraphics[width=\linewidth]{apd_angle_panel_APD.pdf}
    \caption{Normalized absorbed power $\APD/\IPD$.}
    \label{fig:apd-angle:APD}
  \end{subfigure}
  \caption{Pseudo-Brewster compensation for skin at 28~GHz
  ($\ntilde = 4.49 - 1.79i$, $T_0 = 0.539$). (a)~Fresnel
  power-absorption coefficients $T_s$ (TE), $T_p$ (TM), and
  $\Tavg = \tfrac{1}{2}(T_s + T_p)$ versus incidence angle $\theta$.
  $\Tavg/T_0$ is at most $1.056$ over $[0^\circ,90^\circ]$.
  (b)~Normalized absorbed power $\APD/\IPD = T(\theta)\cos\theta$
  for the same three states. The dotted reference is the simplified
  $T_0\cos\theta$ prediction.}
  \label{fig:apd-angle}
\end{figure}

## reviews (figure)



_PaperMaker9000 sweep — 1 flag(s) across 1 lens(es)._

- **figure** — 1 flag(s), 42 cleared:
    - `figures.conventions.axis_units` (high): `Incidence angle $\theta$ [deg]` -> x-axis uses square-bracket units [deg] but both dimensionless y-axes (Transmission T(theta), APD/IPD) carry no unit bracket; add [-] (or [1]) to the y-labels so every axis states a unit in one consistent bracket style.

## grinder notes
- **label**: fig:apd-angle:T
- **caption_preview**: Fresnel transmission $T$.
