% PREV: The classical Cauchy formula $\langle\Aperp\rangle = A/4$ is the
% NEXT: Let $A_{\mathrm{CH}}$ be the surface area of the convex hull of the
# Generalized Cauchy formula

<!-- AUTO_BEGIN: assembled -->
\subsection{Generalized Cauchy formula}\label{subsec:cauchy-thm}

The generalized Cauchy formula is the central whole-body identity.
Let a body $\Sigma$ have surface area $A$, exposure fraction
$\eta(\rr)$, and absorption area
$\Aab \equiv \int_\Sigma \eta(\rr)\,\diff A$. Under isotropic,
unpolarized plane-wave illumination of intensity $\IPD$ on tissue
with normal-incidence transmission $T_0$, the direction-averaged
whole-body absorbed power is
\begin{equation}\label{eq:cauchy}
  \langle P_{\mathrm{abs}} \rangle = \IPD\,T_0\,\Aab/4\, .
\end{equation}

To see why, apply Fubini's theorem to exchange the surface and direction
integrals. The local law~\eqref{eq:geom-law} gives
$\APD(\rr,\khat) = \IPD\,T_0\,\Vis(\rr,\khat)\,
\pospart{\nhat\cdot(-\khat)}$. The direction average of the integrand
is
\[
  \frac{1}{4\pi}\int_{S^2}
  \IPD\,T_0\,\Vis(\rr,\khat)\,\pospart{\nhat\cdot(-\khat)}\,
  \diff\Omega
  = \frac{\IPD\,T_0}{4}\,\eta(\rr)\,,
\]
using the definition of $\eta$ and the identity $\int_{S^2}
\pospart{\nhat\cdot(-\khat)}\,\diff\Omega = \pi$ for any unit
$\nhat$. Integration over $\Sigma$ gives~\eqref{eq:cauchy}.

The classical Cauchy formula from 1841~\cite{Cauchy1841},
$\langle\Aperp\rangle = A/4$, is the special case $\eta \equiv 1$,
valid for any convex body. The
absorption area $\Aab$ reduces all geometric complexity of
self-shadowing to a single scalar. Let $A_{\mathrm{CH}}$ be the
surface area of the convex hull of the body. Energy conservation under
isotropic illumination implies
$\langle P_{\mathrm{abs}} \rangle \le \IPD\,A_{\mathrm{CH}}/4$, because
the power entering the convex hull bounds the absorbed power. For the
Thelonious phantom $A_{\mathrm{CH}}/A \approx 1.20$, so the hull bound
brackets the true absorbed power within that factor.

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

The reverberation-chamber literature has been measuring $\Tbar$
directly. Bamba's empirical efficiency $\eta(f)$
coincides with $\Tbar(f)$ to $3\%$ at $5.8$~GHz on four FDTD ellipsoid
phantoms under diffuse-field exposure~\cite{Bamba2014}. It diverges below
$3$~GHz, where the Mie contribution to absorption on a finite
ellipsoid becomes non-negligible (\cref{tab:bands}). The framework
is mainly a mmWave method.
Flintoft's plateau $\langle Q^a\rangle/\gamma_s = 0.47$--$0.49$
at $7$--$11$~GHz matches $\Tbar$ at the same frequencies to $2\%$~\cite{Flintoft2014}.
Zhang's plateau $\xi = 0.45$--$0.65$ above $6$~GHz brackets
$\Tbar\cdot\Aab/A$~\cite{Zhang2017thesis}.
<!-- AUTO_END: assembled -->








## section notes

_(AI-owned notes about this section as a whole)_
