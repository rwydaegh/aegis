<!-- AUTO_BEGIN: assembled -->
\section{Introduction}\label{sec:introduction}

\IEEEPARstart{U}{rban} propagation can change over a few meters along a
pedestrian route. A person can move from direct visibility of a roofline to a
region where buildings block the direct field and reflected power arrives from
another direction. The surface materials then affect how much power is returned
to the street~\cite{itu2040,vitucci}. This local variation also matters after propagation.
Whole-body absorption depends on the arrival direction and on the orientation of
the body, so one incident-power value at one receiver position does not describe
exposure along a route. A route calculation must retain position and direction
until the field is coupled to the body~\cite{icnirp}.

Urban radio ray tracing provides detailed paths between specified transmitters
and receivers~\cite{sionna}. It has been used for city-scale downlink exposure
with base-station locations from public deployment records~\cite{leeman}, and in
hybrid propagation and anatomical dosimetry calculations along an outdoor user
path~\cite{wydaeghe2026}. Stochastic site models provide a different description
when individual transmitters are not fixed~\cite{wiame}, while normalized body
coefficients separate incident fields from later exposure
calculations~\cite{varsier}. Together, these studies include deterministic urban
transport, spatial source models, and body coupling. Because these studies use
different source assumptions, their reported quantities are not directly
comparable without a common source law.

Street imagery and semantic scene models can supply attributes that are absent
from an untextured city mesh. The Vistas dataset provides a street-scene
taxonomy for dense semantic segmentation~\cite{vistas}. Kamari \emph{et al.}
segment street-level images, project the resulting material classes onto city
geometry, and use that geometry in millimeter-wave ray tracing~\cite{mmsv}.
Xia \emph{et al.} use semantic point-cloud classification and detailed scene
reconstruction for outdoor urban ray tracing at 2.8~GHz~\cite{xia2024}.
Image-informed wireless scene construction is therefore established. The
present work does not claim semantic segmentation, material classification, or
image-to-geometry projection as new. It uses these operations to form a
traceable material surface around fixed pedestrian routes, with an explicit
fallback where the image evidence is absent or refused.

The calculation considered here requires the established parts in one declared
model. Registered panoramas must refer to the same city geometry that supports
the propagation calculation. A source model must remain fixed across sites, and
its physical scale must be separate from the numerical source quadrature.
Direct, specular, and diffuse power must remain separate until their arrival
directions are coupled to the body. The method in this paper meets these
requirements with a panorama-derived material surface, a route-aligned roofline
source measure, and a transport model that stops after the first diffuse material
interaction. This combination defines a conditional comparison of local scenes
without treating the available standpoints as a population sample or the
roofline sources as a measured deployment. To the best of the authors'
knowledge, prior work has not combined registered street panoramas, a common roofline source law, component-resolved
first-material transport, and directional body coupling along fixed routes.

The study applies this method at 15~GHz to five selected routes with 73 fixed
standpoints. Each result is normalized per unit active-source areal density and
per unit equivalent isotropically radiated power. The retained transport contains
the exact direct term, exact one-reflection specular term, and the first diffuse
interaction evaluated by next-event estimation. It contains no higher specular
order and no path continuation after a diffuse interaction. The reported route
distributions are therefore results for five fixed routes under this source and
transport model. They are not estimates of population exposure, deployed-network
exposure, or a ranking of the five cities.

The contributions are as follows.
\begin{enumerate}
  \item A scene-construction method binds registered panorama
  evidence to the transport mesh. Every image-derived assignment retains its
  provenance, and unobserved or refused regions retain a declared geometric
  fallback.

  \item A normalized roofline source model and transport calculation preserve
  direct, one-reflection specular, and first-diffuse power and
  direction until whole-body coupling.

  \item A five-site application reports fixed-route exposure distributions,
  controlled first-diffuse validation, component closure, replica convergence,
  and the retained transport at the six standpoints with no direct or
  one-reflection specular contribution.
\end{enumerate}
<!-- AUTO_END: assembled -->





## Aggregation notes (AI-owned)
