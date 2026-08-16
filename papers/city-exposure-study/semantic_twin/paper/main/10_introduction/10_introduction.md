<!-- AUTO_BEGIN: assembled -->
\section{Introduction}\label{sec:introduction}

\IEEEPARstart{U}{rban} wireless systems operate in a built environment that
strongly shapes radio propagation~\cite{itu2040}. Propagation can change over a
few meters along a pedestrian route. A person can move from direct visibility of a roofline to a
region where buildings block the direct field and reflected power arrives from
another direction. The surface materials then affect how much power is returned
to the street~\cite{itu2040,vitucci}. This local variation also matters after propagation.
Whole-body absorption depends on the arrival direction and on the orientation of
the body, so one incident-power value at one receiver position does not describe
exposure along a route. A route calculation must retain position and arrival
direction until the field is coupled to the body~\cite{icnirp}.

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

Street images can supply surface information that is absent
from an untextured city mesh. The Vistas dataset provides a street-scene
taxonomy for dense semantic segmentation~\cite{vistas}. Kamari \emph{et al.}
segment street-level images, project the resulting material classes onto city
geometry, and use that geometry in millimeter-wave ray tracing~\cite{mmsv}.
Xia \emph{et al.} use semantic point-cloud classification and detailed scene
reconstruction for outdoor urban ray tracing at 2.8~GHz~\cite{xia2024}.
Image-informed city modeling is therefore established. The
present work does not claim semantic segmentation, material classification, or
image-to-geometry projection as new. It uses these operations to form a
traceable material map around fixed pedestrian routes. The map keeps the
geometry-based material wherever the images give no reliable label.

The calculation combines these established parts in one fixed model. First, each
360-degree street image is aligned with the same city mesh used for ray tracing.
The image labels are then projected onto that mesh to make a material map.
Second, the same transmitter model is used at every site, with the number of
transmitters set independently of how finely the roofline is divided. Third,
direct, specular, and diffuse power stays separate until its arrival direction
is coupled to the body. The transport calculation treats direct paths and one
specular reflection exactly, estimates one diffuse reflection, and then stops.
The route points are fixed case studies rather than a population sample, and the
roofline transmitters are a model rather than a measured deployment. To the best
of the authors' knowledge, prior work has not combined aligned 360-degree street
images, a common roofline transmitter model, these separate transport components,
and directional body coupling along fixed routes.

The study applies this method at 15~GHz to five selected routes with 73 fixed
route points. Each result is normalized per unit active-source areal density and
per unit equivalent isotropically radiated power. The calculation treats direct
paths and one specular reflection exactly, then estimates one diffuse reflection
by next-event estimation. It omits further reflections. The reported route
distributions are therefore results for five fixed routes under this source and
transport model. They do not estimate population exposure or deployed-network
exposure, and they do not rank the five cities.

For the first time, one fixed-route calculation combines the following three
contributions.
\begin{enumerate}
  \item Aligned 360-degree street images supply traceable
  material labels to the same city mesh used for the propagation calculation.
  Surfaces without a reliable image label keep their geometry-based material.

  \item A normalized roofline transmitter model and transport calculation preserve
  direct, one-reflection specular, and first-diffuse power and
  direction until whole-body coupling.

  \item A five-site application reports fixed-route exposure distributions,
  controlled first-diffuse validation, component closure, replica convergence,
  and the retained transport at the six route points with no direct or
  one-reflection specular contribution.
\end{enumerate}
<!-- AUTO_END: assembled -->















## Aggregation notes (AI-owned)
