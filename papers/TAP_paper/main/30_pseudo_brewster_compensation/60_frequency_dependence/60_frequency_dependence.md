% PREV: \begin{figure}[!t]
# Frequency dependence

<!-- AUTO_BEGIN: assembled -->
% NEXT: The accuracy of the constant-$T_0$ approximation has a clean
\subsection{Frequency dependence}\label{subsec:pB-freq}

% PREV: \subsection{Frequency dependence}\label{subsec:pB-freq}
% NEXT: \begin{figure}[!t]
The accuracy of the constant-$T_0$ approximation has a clean
frequency dependence. Define the sphere ratio $R(f)$
\begin{equation}\label{eq:R-of-f}
  R(f) \equiv T_0(f) / \Tbar(f),
  \qquad
  \Tbar(f) \equiv 2\int_0^1 \Tavg(\mu, f)\,\mu\,\diff\mu\,,
\end{equation}
where $\Tbar(f)$ is the flux-weighted Fresnel transmission. $R(f) =
1$ when the constant-$T_0$ approximation is exact on a
direction-averaged quantity. $R < 1$ means $T_0$ underestimates
absorbed power. $R > 1$ means it overestimates. \Cref{fig:R-of-f}
shows that for skin the crossover is at 40.4~GHz, where the
compensation is exact. Below this
frequency the approximation underestimates absorbed power. Above, it
overestimates by at most $3.5\%$ at 100~GHz. The root-mean-square error
remains below $5\%$ across $0.3$--100~GHz. Frequency-resolved
Cole--Cole values for skin and the angle family
$\Tavg(\theta)\cos\theta$ at six representative frequencies are in
Table~\ref{tab:itis-fvs} and Fig.~\ref{fig:si-angle-family} of the SI.

% PREV: The accuracy of the constant-$T_0$ approximation has a clean
% NEXT: # Frequency dependence
\begin{figure}[!t]
  \centering
  % Legend entries capitalized (Conservative / Non-conservative); see
  % scripts/R_of_f_landscape.py.
  \includegraphics[width=\columnwidth]{R_of_f.pdf}
  \caption{Sphere ratio $R(f) = T_0/\Tbar$ versus frequency for skin
  (IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}). $R = 1$ indicates that the
  constant-$T_0$ approximation is exact on the direction-averaged
  quantity; $R < 1$ means $T_0$ underestimates absorbed power and
  $R > 1$ means it overestimates. The dashed horizontal lines mark
  the $\pm 4\%$ band.}
  \label{fig:R-of-f}
\end{figure}
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
