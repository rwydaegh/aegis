% PREV: The exposure fraction $\eta$ is mathematically identical to the
# Self-shadowing and ambient occlusion

<!-- AUTO_BEGIN: assembled -->
% NEXT: The human body is not convex.
\subsection{Self-shadowing and ambient occlusion}\label{sec:self-shadow}

% PREV: \subsection{Self-shadowing and ambient occlusion}\label{sec:self-shadow}
% NEXT: The \textit{exposure fraction} $\eta$ at a surface point $\rr$ is the cosine-weighted
The human body is not convex. Concavities such as the armpits, the
gap between the legs, and the neck region cause one part of the body
to shadow another. The binary visibility $\Vis(\rr,\khat) \in \{0,1\}$
in~\eqref{eq:geom-law} is the ambient-occlusion primitive of computer
graphics introduced by Zhukov \textit{et~al.}~\cite{Zhukov1998} and brought
into production rendering by Landis~\cite{Landis2002}. Modern GPUs
evaluate $\Vis(\rr,\khat)$ at interactive frame
rates~\cite{AkenineMoller2018}.

% PREV: The human body is not convex.
% NEXT: The exposure fraction $\eta$ is mathematically identical to the
The \textit{exposure fraction} $\eta$ at a surface point $\rr$ is the cosine-weighted
fraction of the upper hemisphere from which $\rr$ is unobstructed,
\begin{equation}\label{eq:eta-def}
  \eta(\rr) = \frac{1}{\pi}\int_{S^2}
  \pospart{\nhat(\rr)\cdot(-\khat)}\,\Vis(\rr,\khat)\,\diff\Omega\, .
\end{equation}
For convex bodies $\Vis \equiv 1$ and $\eta \equiv 1$. For nonconvex
bodies $\eta \in [0,1]$.

% PREV: The \textit{exposure fraction} $\eta$ at a surface point $\rr$ is the cosine-weighted
% NEXT: # Self-shadowing and ambient occlusion
The exposure fraction $\eta$ is mathematically identical to the
self-shadowing factor $\gamma_s$ that Flintoft \textit{et~al.}\ define as
``the proportion of total surface area of the body that is illuminated
by the reverberant field''~\cite[p.~3301]{Flintoft2014} and estimate
geometrically as $0.75$--$0.85$ from Tomita's surface-area
data~\cite{Tomita1999}. The Flintoft estimate is geometric and
posture-dependent. The construction here is computational and
posture-resolved. For the Thelonious phantom, an ambient-occlusion
solver returns the area-weighted mean
$\bar{\eta} = \Aab/A = 0.865$. This is near the upper end of
Flintoft's band $[0.75, 0.85]$~\cite{Tomita1999}, and is rendered
on the phantom in \cref{fig:phantom}\subref{fig:phantom:eta-front}
and \cref{fig:phantom}\subref{fig:phantom:eta-side}. Most of the
body has $\eta \approx 1$. Reductions occur in concavities. The
medial sides of the legs and arms, the armpits, the underside of
the chin, and the soles of the feet are the dominant such regions.
On a $10^4$--$10^5$ triangle mesh the solver evaluates $\eta$ in
tens of milliseconds on commodity hardware.
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
