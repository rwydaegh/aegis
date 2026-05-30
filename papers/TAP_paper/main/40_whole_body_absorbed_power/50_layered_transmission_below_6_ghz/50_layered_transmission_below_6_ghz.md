% PREV: Zhang derives the planar limit of this model in his
# Layered transmission below 6~GHz

<!-- AUTO_BEGIN: assembled -->
\subsection{Layered transmission below 6~GHz}\label{subsec:fp}

Above $6$~GHz, \eqref{eq:cauchy-exact} matches the plateau values
reported by Bamba, Flintoft, and Zhang. Below $6$~GHz, Flintoft and
Zhang observe a structured dip near $3$~GHz that the homogeneous
half-space model does not reproduce~\cite{Flintoft2014,Zhang2017thesis}. The
dip is anatomical. Flintoft's negative
correlation of $\langle Q^a\rangle$ with mean subcutaneous fat
thickness $d_{\mathrm{SF}}$ is steepest at $3$~GHz
($-0.0061\,\mathrm{mm}^{-1}$, $R^2 = 0.40$,~\cite[Table~6]{Flintoft2014}),
with the slope falling to $-0.0030\,\mathrm{mm}^{-1}$ at $7$--$11$~GHz.

The mechanism is a Fabry--P\'erot resonance in the subcutaneous fat
layer. Below $6$~GHz the SAR penetration depth in fat exceeds
$70$~mm, against fat thicknesses of $2$--$20$~mm in the Flintoft
cohort~\cite[Table~1]{Flintoft2014}. The wave passes through the fat
layer with little attenuation and reflects from the fat-muscle
interface. Constructive interference enhances absorption, and destructive
interference suppresses it. A three-layer transfer-matrix model with
skin, fat, and a semi-infinite muscle half-space gives the layered
transmission
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
