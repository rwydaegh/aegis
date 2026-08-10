% PREV: To the best of the authors' knowledge, this is the first closed-form
% PREV: \gls{APD} law for the human body, validated in four independent ways. The
% PREV: contributions are as follows.
% PREV: \begin{enumerate}
% PREV:   \item We derive closed-form \gls{APD} laws from Fresnel transmission
% PREV:   on lossy biological tissue and integrate them over nonconvex
% PREV:   anatomical meshes with a generalized Cauchy formula. Whole-body
% PREV:   absorbed power reduces to a flux-weighted transmission scalar and a
% PREV:   single ambient-occlusion scalar.
% PREV:
% PREV:   \item Pseudo-Brewster compensation simplifies the law further for
% PREV:   unpolarized incidence. \gls{TE}/\gls{TM} cancellation keeps the
% PREV:   geometric approximation within a few percent over the relevant
% PREV:   angular range.
% PREV:
% PREV:   \item The computation is differentiable end-to-end, the first
% PREV:   \gls{APD} map to provide closed-form gradients. For a body mesh
% PREV:   under many incident paths, the absorbed-power map is a single
% PREV:   matrix-vector multiplication, evaluated in under $10$~ms.
% PREV:
% PREV:   \item Higher-order correction terms extend and delimit the closed
% PREV:   form. A layered transmission term covers the sub-6~GHz whole-body
% PREV:   comparison, whereas curvature, diffraction, and inter-body reflection
% PREV:   terms bound the main higher-order errors.
% PREV:
% PREV:   \item The theory is validated in four independent ways: Mie theory
% PREV:   on lossy spheres, full polarization-aware Fresnel calculations on
% PREV:   the Thelonious phantom, Sim4Life FDTD, and dosimetry literature
% PREV:   across $108$ volunteers and $5$ FDTD phantoms.
% PREV: \end{enumerate}
The remainder of this paper is organized as follows.
\Cref{sec:law,sec:pB,sec:cauchy} comprise the methods of this paper.
Respectively, they derive the local absorption law at a visible
surface point, reduce it to a near-constant scalar through
pseudo-Brewster compensation, and integrate the local law over the
whole nonconvex body. \Cref{sec:val} validates the theory four ways
and bounds the higher-order corrections. \Cref{sec:compliance} gives
closed-form compliance bounds. \Cref{sec:disc} discusses some
consequences and the regime of validity, while \cref{sec:conc}
concludes.

## reviews (paragraph)

_(empty — run /review to populate)_
