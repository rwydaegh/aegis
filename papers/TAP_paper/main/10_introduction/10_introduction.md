% PREV: \section{Introduction}\label{sec:introduction}
% NEXT: \IEEEPARstart{W}{ireless} exposure on the human body is regulated
# Introduction

<!-- AUTO_BEGIN: assembled -->
\section{Introduction}\label{sec:introduction}

\IEEEPARstart{W}{ireless} exposure on the human body is regulated
through two basic restrictions in the \gls{ICNIRP} 2020
guidelines~\cite{ICNIRP2020}, IEC/IEEE~63195, and IEEE~C95.1: the
mass-averaged \gls{SAR} below 6~GHz, with peak values evaluated as
\gls{psSAR10g}, and the surface-averaged absorbed power density
(\gls{APD}) above 6~GHz. Direct evaluation uses
\gls{FDTD} simulations on an anatomical
phantom~\cite{Kodera2024,Diao2024,Hirata2021,Wydaeghe2026}. Resolving the submillimeter
absorption layer at ten cells per in-tissue wavelength
sets a cell count of $10^{8}$ at 6~GHz, growing to $10^{12}$ near
100~GHz. A simulation campaign that covers frequencies, postures, and
incidence directions takes weeks on \gls{GPU} clusters. Whole-body
simulations above 30~GHz become computationally difficult~\cite{Wydaeghe2026}.
This work shows that the surface absorbed-power map on a
$10^4$-triangle body mesh reduces to one matrix-vector multiply,
evaluated in under $10$~ms on a commercial modern GPU at any
frequency from 1 to 100~GHz. The whole-body absorbed power
reduces to only three precomputed scalars: the body mass, the
body surface area, and the flux-weighted Fresnel transmission.

Several groups already capture this absorption with a single fitted
coefficient~\cite{Bamba2014,Flintoft2014,Zhang2017thesis,ZhangRobinson2020,Kodera2024,Diao2024}.
The coefficient is defined in different ways, as an efficiency, a
normalized cross-section, or a transmission, but in every study it
falls between about $0.4$ and $0.7$ above $6$~GHz. This shared range
points to a single underlying closed-form quantity. Each coefficient
is fitted separately for each phantom and frequency from an \gls{FDTD}
sweep or a chamber measurement, so the values are slow to obtain, they
differ between studies, and they provide no gradients for design. No
study writes them as one expression, and none treats a nonconvex body
in closed form.

This work derives the closed form behind these coefficients. On
high-index tissue, the unpolarized Fresnel transmission collapses to a
near-constant scalar~\cite{Azzam2015}. The local law then integrates
over a nonconvex body through a generalized Cauchy
formula~\cite{Cauchy1841}, with self-shadowing from ambient
occlusion~\cite{Zhukov1998,Landis2002,AkenineMoller2018}. A layered
correction in the fat layer covers the $3$~GHz dip~\cite{Flintoft2014}.
The five fitted coefficients are special cases of this expression. In
the mmWave band it reproduces \gls{FDTD} to within the tissue
dielectric uncertainty, at a small fraction of the cost. Because it is
also differentiable, antenna and beam design under exposure limits
becomes a continuous optimization.

To the best of the authors' knowledge, this paper makes the following
contributions.
\begin{enumerate}
  \item We derive closed-form \gls{APD} laws from Fresnel transmission
  on lossy biological tissue and integrate them over nonconvex
  anatomical meshes with a generalized Cauchy formula. Whole-body
  absorbed power reduces to a flux-weighted transmission scalar and an
  ambient-occlusion geometry scalar.

  \item Pseudo-Brewster compensation simplifies the law further for
  unpolarized incidence. \gls{TE}/\gls{TM} cancellation keeps the
  geometric approximation within a few percent over the relevant
  angular range.

  \item The computation is differentiable end-to-end. For a body mesh
  under many incident paths, the absorbed-power map is one $10$~ms
  matrix-vector multiply.

  \item Higher-order correction terms extend and delimit the closed
  form. A layered transmission term covers the sub-6~GHz whole-body
  comparison, while curvature, diffraction, and inter-body reflection
  terms bound the main higher-order errors.

  \item The theory is validated in four independent ways: Mie theory
  on lossy spheres, full polarization-aware Fresnel calculations on
  the Thelonious phantom, Sim4Life FDTD, and dosimetry literature
  across $168$ volunteers and $5$ FDTD phantoms.
\end{enumerate}
<!-- AUTO_END: assembled -->








## section notes

_(AI-owned notes about this section as a whole)_
