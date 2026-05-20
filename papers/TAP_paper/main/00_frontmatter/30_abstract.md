% PREV: \begin{document}
% NEXT: \begin{IEEEkeywords}
\begin{abstract}
Regulatory dosimetry on the human body relies on Finite-Difference
Time-Domain (FDTD) simulations, which grow to trillions of cells at
high mmWave frequencies. From 1 to 100~GHz, we replace these
simulations with closed-form Fresnel surface laws for opaque
biological tissue. Locally, Absorbed Power Density (APD) is Incident
Power Density (IPD) multiplied by normal-incidence transmission, an
ambient-occlusion factor, and the positive incidence cosine. For
unpolarized skin at 28~GHz, pseudo-Brewster compensation keeps
angular transmission within 5.6\% of normal incidence up to
$75^\circ$. Integrating the local law over the visible nonconvex body
surface yields a generalized Cauchy whole-body identity with one
geometry scalar. A layered transmission term captures the sub-6~GHz
whole-body dip. On a $10^4$-triangle mesh under $10^2$ incident
paths, this turns the absorbed-power map into one differentiable
matrix-vector multiply, evaluated in under $10$~ms on a GPU. The
closed form is validated in four ways: Mie theory on lossy spheres,
full polarization-aware Fresnel calculations on the Thelonious
phantom, Sim4Life FDTD, and dosimetry literature across 168
volunteers and 5 FDTD phantoms. In the high-frequency regime, the
error is below 5\%, within the reported uncertainty in human-skin
dielectric parameters. Whole-body compliance reduces to three
precomputed scalars. Antenna and beam optimization under exposure
constraints become differentiable end-to-end.
\end{abstract}

## reviews (abstract)

_(empty — run /review to populate)_
