% PREV: \subsection{Sim4Life FDTD on the Thelonious phantom}\label{subsec:val-fdtd}
% NEXT: The second metric is the direction-averaged Cauchy formula~\eqref{eq:cauchy-exact}
The Mie and Fresnel tests check approximations against analytic and
semi-analytic ground truths. Full Sim4Life FDTD on the same
Thelonious mesh, matched dielectric properties, and matched
plane-wave excitation completes the comparison. Two regulatory
metrics are evaluated. The first is the IEC/IEEE~63195 peak $\APD$
averaged over a $4$~cm$^2$ patch. At $7$~GHz on three
lateral and frontal incidence directions with $\theta$-polarization,
the direction-averaged ratio of law to FDTD is $1.027$. Propagating a
$\pm 20\%$ uncertainty on the IT'IS dielectric properties~\cite{ITISv5,Gabriel1996} through
the Fresnel coefficient at $7$~GHz gives $\pm 7\%$ on
$T_0$, and the direction-averaged ratio falls inside it. The
per-direction values are $1.06$, $1.20$, and $0.83$. The spread
beyond $\pm 7\%$ reflects FDTD discretization and per-direction
polarization detail in the reference rather than the closed form.

## reviews (paragraph)

_(empty — run /review to populate)_
