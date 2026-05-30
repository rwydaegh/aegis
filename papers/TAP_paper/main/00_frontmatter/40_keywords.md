% PREV: \begin{abstract}
% PREV: Regulatory dosimetry on the human body relies on Finite-Difference
% PREV: Time-Domain (FDTD) simulations, which grow to trillions of cells at
% PREV: high mmWave frequencies. From 1 to 100~GHz, we replace these
% PREV: simulations with closed-form Fresnel surface laws for opaque
% PREV: biological tissue. Locally, Absorbed Power Density (APD) is Incident
% PREV: Power Density (IPD) multiplied by normal-incidence transmission, an
% PREV: ambient-occlusion factor, and the positive incidence cosine. For
% PREV: unpolarized skin at 28~GHz, pseudo-Brewster compensation keeps
% PREV: angular transmission within 5.6\% of normal incidence up to
% PREV: $75^\circ$. Integrating the local law over the visible nonconvex body
% PREV: surface yields a generalized Cauchy whole-body identity with one
% PREV: geometry scalar. A layered transmission term captures the sub-6~GHz
% PREV: whole-body dip. On a $10^4$-triangle mesh under $10^2$ incident
% PREV: paths, this turns the absorbed-power map into one differentiable
% PREV: matrix-vector multiply, evaluated in under $10$~ms on a GPU. The
% PREV: closed form is validated in four ways: Mie theory on lossy spheres,
% PREV: full polarization-aware Fresnel calculations on the Thelonious
% PREV: phantom, Sim4Life FDTD, and dosimetry literature across 168
% PREV: volunteers and 5 FDTD phantoms. In the high-frequency regime, the
% PREV: error is below 5\%, within the reported uncertainty in human-skin
% PREV: dielectric parameters. Whole-body compliance reduces to three
% PREV: precomputed scalars. Antenna and beam optimization under exposure
% PREV: constraints become differentiable end-to-end.
% PREV: \end{abstract}
% NEXT: \IEEEpeerreviewmaketitle
\begin{IEEEkeywords}
APD, dosimetry, FDTD, Fresnel transmission, ICNIRP, mmWave, SAR.
\end{IEEEkeywords}

## reviews (keywords)

_(empty — run /review to populate)_
