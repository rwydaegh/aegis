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

## reviews (paragraph)

_(empty — run /review to populate)_
