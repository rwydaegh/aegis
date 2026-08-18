% PREV: A photogrammetric city mesh gives accurate building geometry, but its triangles
% PREV: carry no material information. Street-level images can fill that gap. The
% PREV: Mapillary Vistas dataset provides a taxonomy for dense segmentation of street
% PREV: scenes~\cite{vistas}. Kamari \emph{et al.} segment street-level images, project
% PREV: the resulting material classes onto city geometry, and use that geometry in
% PREV: millimeter-wave ray tracing~\cite{mmsv}. Xia \emph{et al.} use semantic
% PREV: point-cloud classification and detailed scene reconstruction for outdoor ray
% PREV: tracing at 2.8~GHz~\cite{xia2024}. Projecting image-derived materials onto
% PREV: city geometry is therefore established. This study does not claim any of these
% PREV: operations as new. It uses them to build a material map around fixed pedestrian
% PREV: routes, keeping the default geometry-based material wherever the images give no
% PREV: reliable label.
% NEXT: This study applies the method at 15~GHz across ten urban locations. A geometric
% NEXT: fixed-grid diagnostic first characterizes all ten locations with geometry-based
% NEXT: materials and a fixed body orientation. Five of these locations are then studied
% NEXT: with image-derived materials along fixed pedestrian routes containing 73
% NEXT: observation points. Every result is normalized per unit active-source areal
% NEXT: density and per unit effective isotropic radiated power (EIRP). The route-median
% NEXT: whole-body SAR values differ by a factor of 13.34 across the five routes. These
% NEXT: results describe fixed-grid locations and fixed routes under one source and
% NEXT: transport model. They do not estimate population exposure or deployed-network
% NEXT: exposure.
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

## reviews (paragraph)

_(empty — run /review to populate)_
