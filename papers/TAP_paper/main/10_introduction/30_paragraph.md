% PREV: Several groups already capture this absorption with a single fitted
% PREV: coefficient~\cite{Bamba2014,Flintoft2014,Zhang2017thesis,ZhangRobinson2020,Kodera2024,Diao2024}.
% PREV: The coefficient is defined in different ways, as an efficiency, a
% PREV: normalized cross-section, or a transmission, but in every study it
% PREV: falls between about $0.4$ and $0.7$ above $6$~GHz. This shared range
% PREV: points to a single underlying closed-form quantity. Each coefficient
% PREV: is fitted separately for each phantom and frequency from an \gls{FDTD}
% PREV: sweep or a chamber measurement, so the values are slow to obtain, they
% PREV: differ between studies, and they provide no gradients for design. No
% PREV: study writes them as one expression, and none treats a nonconvex body
% PREV: in closed form.
% NEXT: To the best of the authors' knowledge, this paper makes the following
% NEXT: contributions.
% NEXT: \begin{enumerate}
% NEXT:   \item We derive closed-form \gls{APD} laws from Fresnel transmission
% NEXT:   on lossy biological tissue and integrate them over nonconvex
% NEXT:   anatomical meshes with a generalized Cauchy formula. Whole-body
% NEXT:   absorbed power reduces to a flux-weighted transmission scalar and an
% NEXT:   ambient-occlusion geometry scalar.
% NEXT: 
% NEXT:   \item Pseudo-Brewster compensation simplifies the law further for
% NEXT:   unpolarized incidence. \gls{TE}/\gls{TM} cancellation keeps the
% NEXT:   geometric approximation within a few percent over the relevant
% NEXT:   angular range.
% NEXT: 
% NEXT:   \item The computation is differentiable end-to-end. For a body mesh
% NEXT:   under many incident paths, the absorbed-power map is one $10$~ms
% NEXT:   matrix-vector multiply.
% NEXT: 
% NEXT:   \item Higher-order correction terms extend and delimit the closed
% NEXT:   form. A layered transmission term covers the sub-6~GHz whole-body
% NEXT:   comparison, while curvature, diffraction, and inter-body reflection
% NEXT:   terms bound the main higher-order errors.
% NEXT: 
% NEXT:   \item The theory is validated in four independent ways: Mie theory
% NEXT:   on lossy spheres, full polarization-aware Fresnel calculations on
% NEXT:   the Thelonious phantom, Sim4Life FDTD, and dosimetry literature
% NEXT:   across $168$ volunteers and $5$ FDTD phantoms.
% NEXT: \end{enumerate}
This work derives the closed form behind these coefficients. On
high-index tissue, the unpolarized Fresnel transmission becomes a
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

## reviews (paragraph)



_PaperMaker9000 sweep — all clear across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

