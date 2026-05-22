% PREV: The closed-form Cauchy prediction approaches unity at the upper end
# Sim4Life FDTD on the Thelonious phantom

<!-- AUTO_BEGIN: assembled -->
\subsection{Sim4Life FDTD on the Thelonious phantom}\label{subsec:val-fdtd}

The Mie and Fresnel tests check approximations against analytic and
semi-analytic ground truths. Full Sim4Life FDTD on the same
Thelonious mesh, matched dielectric properties, and matched
plane-wave excitation completes the comparison. Two regulatory
metrics are evaluated. The first is the IEC/IEEE~63195 peak $\APD$
averaged over a $4$~cm$^2$ patch. At $7$~GHz on three
lateral and frontal incidence directions with $\theta$-polarization,
the direction-averaged ratio of law to FDTD is $1.027$. A
$\pm 20\%$ uncertainty on the IT'IS dielectric properties~\cite{ITISv5,Gabriel1996} propagates
through the Fresnel coefficient at $7$~GHz to $\pm 7\%$ on
$T_0$. The direction-averaged ratio falls inside this band. The
per-direction values are $1.06$, $1.20$, and $0.83$. The spread
beyond $\pm 7\%$ comes from FDTD discretization and per-direction
polarization detail in the reference, not the closed form.

The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
across $12$ directions and $2$ polarizations at $5.8$~GHz. The ratio
of law to FDTD on direction-averaged total absorbed power is
$1.012$, with $\Aab/A = 0.865$ and $\Tbar(f)$ from \cref{tab:Tbar}.
\Cref{fig:val-fdtd} extends the comparison
across $0.45$--$5.8$~GHz.

\begin{figure}[!t]
  \centering
  \includegraphics[width=\columnwidth]{fig_kernels_vs_fdtd.pdf}
  \caption{Closed-form prediction versus Sim4Life FDTD on the
  Thelonious phantom. Twelve directions and two polarizations per
  frequency from $0.45$--$5.8$~GHz; error bars show the spread
  across directions. The kernel curves switch on the corrections of
  \cref{subsec:corr-residuals} in sequence: ``Fresnel only'' uses
  $T_s/T_p$ at the convex limit, ``+ polarization'' adds the
  polarization-aware $\Teff$, ``+ curvature \& diffraction'' adds
  the $1/(kR)$ refinement, ``Full kernel'' is the constant-$T_0$
  geometric law without occlusion, ``Full + occlusion'' multiplies
  by $\Vis(\rr,\khat)$. The Cauchy stars are the closed-form
  whole-body identity, giving $1.012$ at $5.8$~GHz. The layered
  $\Tlay$ of \cref{subsec:fp} recovers the
  sub-$6$~GHz dip qualitatively.}
  \label{fig:val-fdtd}
\end{figure}

The closed-form Cauchy prediction approaches unity at the upper end
of the band. Below $6$~GHz the surface law underestimates because
body-scale Mie and resonance effects do not enter a surface-only law,
in line with the Mie analysis on a sphere of comparable size
parameter.
<!-- AUTO_END: assembled -->






## section notes

_(AI-owned notes about this section as a whole)_
