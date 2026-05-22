% PREV: This work derives the closed form behind these coefficients. On
% PREV: high-index tissue, the unpolarized Fresnel transmission collapses to a
% PREV: near-constant scalar~\cite{Azzam2015}. The local law then integrates
% PREV: over a nonconvex body through a generalized Cauchy
% PREV: formula~\cite{Cauchy1841}, with self-shadowing from ambient
% PREV: occlusion~\cite{Zhukov1998,Landis2002,AkenineMoller2018}. A layered
% PREV: correction in the fat layer covers the $3$~GHz dip~\cite{Flintoft2014}.
% PREV: The five fitted coefficients are special cases of this expression. In
% PREV: the mmWave band it reproduces \gls{FDTD} to within the tissue
% PREV: dielectric uncertainty, at a small fraction of the cost. Because it is
% PREV: also differentiable, antenna and beam design under exposure limits
% PREV: becomes a continuous optimization.
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

## reviews (paragraph)



_PaperMaker9000 sweep — 3 flag(s) across 4 lens(es)._

- **sentence-craft** — 1 flag(s), 13 cleared:
    - `style.positive_voice.no_passive_no_we` (high): `We derive closed-form \gls{APD} laws from Fresnel transmission` -> Drop "we": "The paper derives closed-form APD laws..." to match the third-person noun-verb framing of items 2-4.
- **voice-tells** — 1 flag(s), 21 cleared:
    - `style.pet_peeves_wout.first_time_framing` (high): `To the best of the authors' knowledge, this paper makes the following contributions.` -> Recast the contribution items with explicit first-time framing, e.g. open the list with a sentence stating that the closed-form APD law and its four-way validation are derived for the first time, and attach a distinct novelty claim to the load-bearing items.
- **lexical-spotcheck** — 1 flag(s), 53 cleared:
    - `BOOK_ELOS_style.misused_words.while_as_although` (low): `A layered transmission term covers the sub-6~GHz whole-body   comparison, while curvature, diffraction, and inter-body reflection   terms bound the main higher-order errors.` -> Replace contrastive 'while' with 'whereas' (the two clauses contrast roles, not time): '...whole-body comparison, whereas curvature, diffraction, and inter-body reflection terms bound the main higher-order errors.'
- **latex-micro** — pass (41 rules cleared).
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

