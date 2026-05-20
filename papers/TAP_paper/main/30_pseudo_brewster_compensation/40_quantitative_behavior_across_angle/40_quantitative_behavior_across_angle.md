% PREV: \Cref{tab:fresnel-skin} quantifies the deviation of $\Tavg$ from
% NEXT: \begin{table}[!t]
# Quantitative behavior across angle

<!-- AUTO_BEGIN: assembled -->
% NEXT: \Cref{fig:apd-angle} illustrates the compensation for skin at
\subsection{Quantitative behavior across angle}\label{subsec:pB-quant}

% PREV: \subsection{Quantitative behavior across angle}\label{subsec:pB-quant}
% NEXT: \begin{figure}[!t]
\Cref{fig:apd-angle} illustrates the compensation for skin at
28~GHz. \Cref{fig:apd-angle:T} shows $T_s$, $T_p$, and $\Tavg$ versus
incidence angle. \Cref{fig:apd-angle:APD} shows the \gls{APD}
$\APD/\IPD = T(\theta)\cos\theta$ for each polarization and for the
simplified product $T_0\cos\theta$. The unpolarized curve closely
tracks the simplified prediction, and the small gap is the Fresnel
approximation error.

% PREV: \Cref{fig:apd-angle} illustrates the compensation for skin at
% NEXT: \Cref{tab:fresnel-skin} quantifies the deviation of $\Tavg$ from
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
  $\Tavg$ stays within $5.6\%$ of $T_0$ up to $75^\circ$.
  (b)~Normalized absorbed power $\APD/\IPD = T(\theta)\cos\theta$
  for the same three states. The dotted reference is the simplified
  $T_0\cos\theta$ prediction.}
  \label{fig:apd-angle}
\end{figure}

% PREV: \begin{figure}[!t]
% NEXT: # Quantitative behavior across angle
\Cref{tab:fresnel-skin} quantifies the deviation of $\Tavg$ from
$T_0$ across $[0^\circ, 75^\circ]$ on skin at 28~GHz. The maximum
deviation is $5.6\%$ at $70$--$75^\circ$. Below $30^\circ$ the agreement
is at the fourth significant figure.

% PREV: # Quantitative behavior across angle
\begin{table}[!t]
\centering
\caption{Fresnel transmission for skin at 28~GHz. Here $T_0 =
\Tavg(0)$ is the normal-incidence value, and $\Tavg/T_0$ stays
within $5.6\%$ of unity over $[0^\circ, 75^\circ]$.}
\label{tab:fresnel-skin}
\begin{tabular}{ccccc}
\toprule
$\theta$ & $T_s$ (TE) & $T_p$ (TM) & $\Tavg$ & $\Tavg/T_0$ \\
\midrule
$0^\circ$  & 0.539 & 0.539 & 0.539 & 1.000 \\
$30^\circ$ & 0.489 & 0.591 & 0.540 & 1.002 \\
$45^\circ$ & 0.422 & 0.666 & 0.544 & 1.010 \\
$60^\circ$ & 0.321 & 0.791 & 0.556 & 1.032 \\
$70^\circ$ & 0.233 & 0.902 & 0.568 & 1.054 \\
$75^\circ$ & 0.182 & 0.952 & 0.567 & 1.053 \\
\bottomrule
\end{tabular}
\end{table}
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
