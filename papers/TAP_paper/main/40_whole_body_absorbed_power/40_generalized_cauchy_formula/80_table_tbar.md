% PREV: The constant-$T_0$ approximation in~\eqref{eq:cauchy} is accurate to
% PREV: $5\%$ root-mean-square across $0.3$--$100$~GHz, but it is not
% PREV: exact. The same direction-averaged identity becomes exact when $T_0$
% PREV: is replaced by the angle-dependent $\Tavg(\theta)$. The
% PREV: cosine-weighted angular integral becomes $\Tbar$
% PREV: via~\eqref{eq:R-of-f}, so for any body opaque at the wavelength
% PREV: \begin{equation}\label{eq:cauchy-exact}
% PREV:   \langle P_{\mathrm{abs}} \rangle = \IPD\,\Tbar(f)\,\Aab/4 \,.
% PREV: \end{equation}
% PREV: \Cref{eq:cauchy-exact} requires only electromagnetic opacity, a
% PREV: condition met above approximately $1$~GHz on a torso and above
% PREV: approximately $6$~GHz on a finger. \Cref{tab:Tbar} lists $T_0$,
% PREV: $\Tbar$, and the ratio $R = T_0/\Tbar$ for skin from $0.3$--$100$~GHz.
% NEXT: The reverberation-chamber literature has been measuring $\Tbar$
% NEXT: directly. Bamba's empirical efficiency $\eta(f)$
% NEXT: coincides with $\Tbar(f)$ to $3\%$ at $5.8$~GHz on four FDTD ellipsoid
% NEXT: phantoms under diffuse-field exposure~\cite{Bamba2014}. It diverges below
% NEXT: $3$~GHz, where the Mie contribution to absorption on a finite
% NEXT: ellipsoid becomes non-negligible (\cref{tab:bands}). The framework
% NEXT: is mainly a mmWave method.
% NEXT: Flintoft's plateau $\langle Q^a\rangle/\gamma_s = 0.47$--$0.49$
% NEXT: at $7$--$11$~GHz matches $\Tbar$ at the same frequencies to $2\%$~\cite{Flintoft2014}.
% NEXT: Zhang's plateau $\xi = 0.45$--$0.65$ above $6$~GHz brackets
% NEXT: $\Tbar\cdot\Aab/A$~\cite{Zhang2017thesis}.
\begin{table}[!t]
\centering
\caption{Normal-incidence transmission $T_0$, flux-weighted
transmission $\Tbar$, and their ratio $R = T_0/\Tbar$ for skin
(IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}).}\label{tab:Tbar}
\begin{tabular}{rcccc}
\toprule
$f$\,[GHz] & $|\ntilde|$ & $T_0$ & $\Tbar$ & $R$ \\
\midrule
0.3 & 7.93 & 0.381 & 0.406 & 0.938 \\
0.9 & 6.70 & 0.445 & 0.465 & 0.957 \\
2.4 & 6.29 & 0.470 & 0.488 & 0.964 \\
6.0 & 6.07 & 0.481 & 0.497 & 0.968 \\
10  & 5.87 & 0.489 & 0.504 & 0.971 \\
28  & 4.84 & 0.536 & 0.543 & 0.988 \\
40  & 4.30 & 0.570 & 0.571 & 1.000 \\
60  & 3.68 & 0.622 & 0.613 & 1.015 \\
100 & 3.01 & 0.701 & 0.677 & 1.035 \\
\bottomrule
\end{tabular}
\end{table}

## reviews (table)



_PaperMaker9000 sweep — all clear across 1 lens(es)._

- **table** — pass (10 rules cleared).

## grinder notes
- **label**: tab:Tbar
- **caption_preview**: Normal-incidence transmission $T_0$, flux-weighted transmission $\Tbar$, and their ratio $R = T_0/\T
