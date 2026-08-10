% PREV: The classical Cauchy formula from 1841~\cite{Cauchy1841},
% PREV: $\langle\Aperp\rangle = A/4$, is the special case $\eta \equiv 1$,
% PREV: valid for any convex body. The
% PREV: absorption area $\Aab$ reduces all geometric complexity of
% PREV: self-shadowing to a single scalar. Let $A_{\mathrm{CH}}$ be the
% PREV: surface area of the convex hull of the body. Energy conservation under
% PREV: isotropic illumination implies
% PREV: $\langle P_{\mathrm{abs}} \rangle \le \IPD\,A_{\mathrm{CH}}/4$, because
% PREV: the power entering the convex hull bounds the absorbed power. For the
% PREV: Thelonious phantom $A_{\mathrm{CH}}/A \approx 1.20$, so the hull bound
% PREV: brackets the true absorbed power within that factor.
% NEXT: \begin{table}[!t]
% NEXT: \centering
% NEXT: \caption{Normal-incidence transmission $T_0$, flux-weighted
% NEXT: transmission $\Tbar$, and their ratio $R = T_0/\Tbar$ for skin
% NEXT: (IT'IS tissue-properties database~\cite{ITISv5,Gabriel1996}).}\label{tab:Tbar}
% NEXT: \begin{tabular}{rcccc}
% NEXT: \toprule
% NEXT: $f$\,[GHz] & $|\ntilde|$ & $T_0$ & $\Tbar$ & $R$ \\
% NEXT: \midrule
% NEXT: 0.3 & 7.93 & 0.381 & 0.406 & 0.938 \\
% NEXT: 0.9 & 6.70 & 0.445 & 0.465 & 0.957 \\
% NEXT: 2.4 & 6.29 & 0.470 & 0.488 & 0.964 \\
% NEXT: 6.0 & 6.07 & 0.481 & 0.497 & 0.968 \\
% NEXT: 10  & 5.87 & 0.489 & 0.504 & 0.971 \\
% NEXT: 28  & 4.84 & 0.536 & 0.543 & 0.988 \\
% NEXT: 40  & 4.30 & 0.570 & 0.571 & 1.000 \\
% NEXT: 60  & 3.68 & 0.622 & 0.613 & 1.015 \\
% NEXT: 100 & 3.01 & 0.701 & 0.677 & 1.035 \\
% NEXT: \bottomrule
% NEXT: \end{tabular}
% NEXT: \end{table}
The constant-$T_0$ approximation in~\eqref{eq:cauchy} is accurate to
$5\%$ root-mean-square across $0.3$--$100$~GHz, but it is not
exact. The same direction-averaged identity becomes exact when $T_0$
is replaced by the angle-dependent $\Tavg(\theta)$. The
cosine-weighted angular integral becomes $\Tbar$
via~\eqref{eq:R-of-f}, so for any body opaque at the wavelength
\begin{equation}\label{eq:cauchy-exact}
  \langle P_{\mathrm{abs}} \rangle = \IPD\,\Tbar(f)\,\Aab/4 \,.
\end{equation}
\Cref{eq:cauchy-exact} requires only electromagnetic opacity, a
condition met above approximately $1$~GHz on a torso and above
approximately $6$~GHz on a finger. \Cref{tab:Tbar} lists $T_0$,
$\Tbar$, and the ratio $R = T_0/\Tbar$ for skin from $0.3$--$100$~GHz.

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).
