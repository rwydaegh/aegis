% PREV: The flowchart next integrates the geometric local law over the body.
# Whole-body absorbed power

<!-- AUTO_BEGIN: assembled -->
\section{Method: whole-body absorbed power}\label{sec:cauchy}

Next, as shown in the flowchart~(\cref{fig:flowchart}), this section
turns surface \gls{APD} into direction-averaged whole-body absorbed
power. The needed new ingredient is visibility:
nonconvex body parts can shadow one another.

\subsection{Self-shadowing and ambient occlusion}\label{sec:self-shadow}

The human body is not convex. Concavities, e.g., the armpits, the
gap between the legs, and the neck region, cause one part of the body
to shadow another. The binary visibility $\Vis(\rr,\khat) \in \{0,1\}$
in~\eqref{eq:geom-law} is the ambient-occlusion primitive of computer
graphics that Zhukov \textit{et~al.}~\cite{Zhukov1998} introduced and
Landis~\cite{Landis2002} brought into production rendering. Modern GPUs
evaluate $\Vis(\rr,\khat)$ as a standard ambient-occlusion
pass~\cite{AkenineMoller2018}. The \emph{exposure fraction} $\eta$ at
a surface point $\rr$ is the cosine-weighted fraction of the upper
hemisphere from which $\rr$ is unobstructed,
\begin{equation}\label{eq:eta-def}
  \eta(\rr) = \frac{1}{\pi}\int_{S^2}
  \pospart{\nhat(\rr)\cdot(-\khat)}\,\Vis(\rr,\khat)\,\diff\Omega\, .
\end{equation}
For convex bodies $\Vis \equiv 1$ and $\eta \equiv 1$. For nonconvex
bodies $\eta \in [0,1]$.

The exposure fraction $\eta$ is mathematically identical to the
self-shadowing factor $\gamma_s$ that Flintoft \textit{et~al.}\ define as
``the proportion of total surface area of the body that is illuminated
by the reverberant field''~\cite[p.~3301]{Flintoft2014} and estimate
geometrically as $0.75$--$0.85$ from Tomita's surface-area
data~\cite{Tomita1999}. The Flintoft estimate is geometric and
posture-dependent. The construction here is computational and
posture-resolved. For the Thelonious phantom, an ambient-occlusion
solver returns the area-weighted mean
$\bar{\eta} = \Aab/A = 0.865$. This is near the upper end of
Flintoft's band $[0.75, 0.85]$~\cite{Tomita1999}.
\Cref{fig:phantom}\subref{fig:phantom:eta-front} and
\subref{fig:phantom:eta-side} render it on the phantom. Most of the
body has $\eta \approx 1$. Reductions occur in concavities. The
medial sides of the legs and arms, the armpits, and the underside of
the jaw are the dominant such regions.
Because $\eta$ depends only on body shape, the solver precomputes it
once per posture.

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

\subsection{Layered transmission below 6~GHz}\label{subsec:fp}

Above $6$~GHz, \eqref{eq:cauchy-exact} matches the plateau values
reported by Bamba, Flintoft, and Zhang. Below $6$~GHz, Flintoft and
Zhang observe a structured dip near $3$~GHz that the homogeneous
half-space model does not reproduce~\cite{Flintoft2014,Zhang2017thesis}. The
dip is anatomical. Flintoft's data show $\langle Q^a\rangle$
correlating negatively with mean subcutaneous fat
thickness $d_{\mathrm{SF}}$, steepest at $3$~GHz
($-0.0061\,\mathrm{mm}^{-1}$, $R^2 = 0.40$,~\cite[Table~6]{Flintoft2014}),
with the slope falling to $-0.0030\,\mathrm{mm}^{-1}$ at $7$--$11$~GHz.

The mechanism is a Fabry--P\'erot resonance in the subcutaneous fat
layer. Below $6$~GHz the SAR penetration depth in fat exceeds
$70$~mm, against fat thicknesses of $2$--$20$~mm in the Flintoft
cohort~\cite[Table~1]{Flintoft2014}. The wave passes through the fat
layer with little attenuation and reflects from the fat-muscle
interface. Constructive interference enhances absorption, and destructive
interference suppresses it. A three-layer transfer-matrix model gives the layered transmission,
stacking skin, fat, and a semi-infinite muscle half-space,
\begin{equation}\label{eq:T-lay}
  \Tlay(f, d_{\mathrm{SF}})
  = 1 - \bigl|\widetilde{\Gamma}_1(f, d_{\mathrm{SF}})\bigr|^2\, ,
\end{equation}
where $\widetilde{\Gamma}_1$ is the generalized Fresnel reflection
coefficient at the air-skin interface, computed recursively from the
fat-muscle interface upward~\cite{Chew1995,BornWolf1999}.
Section~\ref{si:layered} of the SI gives the full Chew recursion,
the standing-wave SAR per layer, and the layer-by-layer cube
integral. Fig.~\ref{fig:si-tlay-fr} of the SI shows $\Tlay(f)$ for
the canonical $2$~mm skin / $10$~mm fat / muscle stack. Replacing
$\Tbar$ with $\Tlay$ in~\eqref{eq:cauchy-exact} gives a
frequency-dependent direction-averaged absorbed power that includes
the fat-layer resonance. For a fat thickness of $10$~mm the model
predicts a $40\%$ enhancement above the homogeneous prediction at
$0.9$~GHz (quarter-wave matching) and a $27\%$ reduction at
$3.5$~GHz (destructive interference).

Zhang derives the planar limit of this model in his
thesis~\cite[Sec.~2.2]{Zhang2017thesis} and observes the resonance
shift with fat thickness in his Figs.~2.7--2.8, writing that ``the
fat layer may act as a matching layer between skin and
muscle''~\cite[p.~21]{Zhang2017thesis}. The contribution here is to
embed the planar model in the body-surface integral via $\Tlay$ and
\eqref{eq:cauchy-exact}, which makes the resonance compatible with a
Cauchy-style direction average. Body-surface averaging suppresses
the oscillation by a factor of approximately
$A_{\mathrm{exposed,fat}}/A$ because different body regions carry
different fat thicknesses, with limbs near $2$~mm and abdomen near
$30$~mm, and consequently different resonance frequencies. The
integrated dip is shallower than the single-thickness prediction but
is at the same frequency. The local surface map
$\APD(\rr) \approx \IPD\,T_0 \Vis \pospart{\mu}$ loses pointwise
meaning below $6$~GHz, where the SAR penetration depth exceeds the
surface layer thickness. Total power remains valid via $\Tlay$
throughout.
<!-- AUTO_END: assembled -->










## section notes

_(AI-owned notes about this section as a whole)_
