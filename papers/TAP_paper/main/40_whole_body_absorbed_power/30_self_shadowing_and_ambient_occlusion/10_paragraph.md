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

## reviews (paragraph)

_(empty — run /review to populate)_
