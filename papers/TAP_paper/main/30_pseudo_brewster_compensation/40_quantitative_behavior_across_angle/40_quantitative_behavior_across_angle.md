% PREV: \Cref{tab:fresnel-skin} quantifies the deviation of $\Tavg$ from
% NEXT: \begin{table}[!t]
# Quantitative behavior across angle

<!-- AUTO_BEGIN: assembled -->
\subsection{Quantitative behavior across angle}\label{subsec:pB-quant}

\Cref{fig:apd-angle} illustrates the compensation for skin at
28~GHz. \Cref{fig:apd-angle:T} shows $T_s$, $T_p$, and $\Tavg$ versus
incidence angle. \Cref{fig:apd-angle:APD} shows the normalized absorbed power
$\APD/\IPD = T(\theta)\cos\theta$ for each polarization and for the
simplified product $T_0\cos\theta$. The unpolarized curve closely
tracks the simplified prediction, and the small gap is the Fresnel
approximation error. $\Tavg/T_0$ is at most $1.056$ across
$[0^\circ,90^\circ]$ on skin at 28~GHz. Below $20^\circ$, the
deviation stays below $0.2\%$.

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
<!-- AUTO_END: assembled -->









## section notes

_(AI-owned notes about this section as a whole)_
