<!-- AUTO_BEGIN: assembled -->
\section{Introduction}\label{sec:introduction}

\IEEEPARstart{A}{s} wireless networks expand into higher frequency bands,
the built environment plays a larger role in determining the radiofrequency
field that reaches a pedestrian~\cite{itu2040}. Along a city street, received
power can change over a few meters. A person walking past a row of buildings
can move from a clear view of a rooftop transmitter into a shadow where
buildings block the direct field and only reflected power reaches the
street. The facade materials then determine how much power returns to the
street~\cite{itu2040,vitucci}. This variation also matters after the field
arrives: whole-body absorption depends on the direction of arrival and on how
the body is oriented, so a single power value at a single point does not
describe exposure along a walking route. A route-level calculation must keep
the arrival direction until the field is applied to the
body~\cite{icnirp}.

Ray tracing computes detailed propagation paths between transmitters and
receivers in a three-dimensional city model~\cite{sionna}. It has been used for
city-scale downlink exposure using published base-station
locations~\cite{leeman}, and to compute propagation and body exposure along an
outdoor pedestrian path~\cite{wydaeghe2026}. Stochastic geometry models
describe exposure when individual transmitter locations are not
known~\cite{wiame}, while precomputed body coefficients separate the incident
field from the absorption calculation~\cite{varsier}. Together, these studies
cover deterministic urban propagation, spatial source models, and the
directional absorption step that converts the arriving field into absorbed power
on the body. Because they use different source assumptions, their reported
exposure values are not directly comparable without a common source
normalization.

A photogrammetric city mesh gives accurate building geometry, but its triangles
carry no material information. Street-level images can fill that gap. The
Mapillary Vistas dataset provides a taxonomy for dense segmentation of street
scenes~\cite{vistas}. Kamari \emph{et al.} segment street-level images, project
the resulting material classes onto city geometry, and use that geometry in
millimeter-wave ray tracing~\cite{mmsv}. Xia \emph{et al.} use semantic
point-cloud classification and detailed scene reconstruction for outdoor ray
tracing at 2.8~GHz~\cite{xia2024}. Projecting image-derived materials onto
city geometry is therefore established. This study does not claim any of these
operations as new. It uses them to build a material map around fixed pedestrian
routes, keeping the default geometry-based material wherever the images give no
reliable label.

This study combines these established parts in one fixed model. Each 360-degree
street image is aligned with the same photogrammetric city mesh used for ray
tracing, and the image labels are projected onto that mesh to produce a material map. A common transmitter model distributes sources along the visible
roofline at every site. Rooflines are a natural choice: they are elevated, street-facing, and visible
from the route. Distributing transmitters in proportion to roofline length
avoids tying the result to any particular deployment. The ray tracer keeps the direct, specular, and diffuse components separate,
preserving their arrival directions, until the field is applied to the body. The transport model treats direct paths and one
specular reflection exactly, estimates one diffuse reflection, and stops there.
The route points are fixed case studies, not a population sample, and the
roofline transmitters are a model, not a measured deployment. To the best of the authors' knowledge, prior work has not combined aligned
360-degree street images, a common roofline transmitter model, and separate
transport components with their arrival directions in a single route-level body
exposure calculation.

This study applies the method at 15~GHz across ten urban locations. A geometric
fixed-grid diagnostic first characterizes all ten locations with geometry-based
materials and a fixed body orientation. Five of these locations are then studied
with image-derived materials along fixed pedestrian routes containing 73
observation points. Every result is normalized per unit active-source areal
density and per unit effective isotropic radiated power (EIRP). The route-median
whole-body SAR values differ by a factor of 13.34 across the five routes. These
results describe fixed-grid locations and fixed routes under one source and
transport model. They do not estimate population exposure or deployed-network
exposure.

This work makes the following three contributions.
\begin{enumerate}
  \item Aligned 360-degree street images supply traceable material labels to
  the same city mesh used for ray tracing. Surfaces without a reliable image
  label keep their geometry-based material.

  \item A roofline transmitter model and transport calculation keep direct,
  specular, and diffuse power separate, with arrival directions, until the
  field is applied to the body.

  \item An application across ten urban locations and five detailed pedestrian
  routes reports geometric screening, fixed-route exposure distributions,
  controlled first-diffuse validation, replica convergence, and the retained
  transport at the six observation points where buildings block all direct and
  specular paths.
\end{enumerate}
<!-- AUTO_END: assembled -->
