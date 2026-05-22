% PREV: The human body is not convex. Concavities such as the armpits, the
% PREV: gap between the legs, and the neck region cause one part of the body
% PREV: to shadow another. The binary visibility $\Vis(\rr,\khat) \in \{0,1\}$
% PREV: in~\eqref{eq:geom-law} is the ambient-occlusion primitive of computer
% PREV: graphics introduced by Zhukov \textit{et~al.}~\cite{Zhukov1998} and brought
% PREV: into production rendering by Landis~\cite{Landis2002}. Modern GPUs
% PREV: evaluate $\Vis(\rr,\khat)$ at interactive frame
% PREV: rates~\cite{AkenineMoller2018}.
% NEXT: The exposure fraction $\eta$ is mathematically identical to the
% NEXT: self-shadowing factor $\gamma_s$ that Flintoft \textit{et~al.}\ define as
% NEXT: ``the proportion of total surface area of the body that is illuminated
% NEXT: by the reverberant field''~\cite[p.~3301]{Flintoft2014} and estimate
% NEXT: geometrically as $0.75$--$0.85$ from Tomita's surface-area
% NEXT: data~\cite{Tomita1999}. The Flintoft estimate is geometric and
% NEXT: posture-dependent. The construction here is computational and
% NEXT: posture-resolved. For the Thelonious phantom, an ambient-occlusion
% NEXT: solver returns the area-weighted mean
% NEXT: $\bar{\eta} = \Aab/A = 0.865$. This is near the upper end of
% NEXT: Flintoft's band $[0.75, 0.85]$~\cite{Tomita1999}, and is rendered
% NEXT: on the phantom in \cref{fig:phantom}\subref{fig:phantom:eta-front}
% NEXT: and \cref{fig:phantom}\subref{fig:phantom:eta-side}. Most of the
% NEXT: body has $\eta \approx 1$. Reductions occur in concavities. The
% NEXT: medial sides of the legs and arms, the armpits, the underside of
% NEXT: the chin, and the soles of the feet are the dominant such regions.
% NEXT: On a $10^4$--$10^5$ triangle mesh the solver evaluates $\eta$ in
% NEXT: tens of milliseconds on commodity hardware.
The \emph{exposure fraction} $\eta$ at a surface point $\rr$ is the cosine-weighted
fraction of the upper hemisphere from which $\rr$ is unobstructed,
\begin{equation}\label{eq:eta-def}
  \eta(\rr) = \frac{1}{\pi}\int_{S^2}
  \pospart{\nhat(\rr)\cdot(-\khat)}\,\Vis(\rr,\khat)\,\diff\Omega\, .
\end{equation}
For convex bodies $\Vis \equiv 1$ and $\eta \equiv 1$. For nonconvex
bodies $\eta \in [0,1]$.

## reviews (paragraph)



_PaperMaker9000 sweep — 1 flag(s) across 4 lens(es)._

- **sentence-craft** — pass (14 rules cleared).
- **voice-tells** — pass (22 rules cleared).
- **lexical-spotcheck** — pass (54 rules cleared).
- **latex-micro** — 1 flag(s), 40 cleared:
    - `latex.structure_style.first_coinage_italics` (low): `The \textit{exposure fraction} $\eta$ at a surface point` -> Use \emph{exposure fraction} rather than \textit{} for the coined term; \emph is the semantic command for first-use coinage and toggles correctly inside any italic context.
- **incremental (2026-05-22)** — pass (2 new/edited rules cleared).

