% PREV: This study combines these established parts in one fixed model. Each 360-degree
% PREV: street image is aligned with the same photogrammetric city mesh used for ray
% PREV: tracing, and the image labels are projected onto that mesh to produce a material map. A common transmitter model distributes sources along the visible
% PREV: roofline at every site. Rooflines are a natural choice: they are elevated, street-facing, and visible
% PREV: from the route. Distributing transmitters in proportion to roofline length
% PREV: avoids tying the result to any particular deployment. The ray tracer keeps the direct, specular, and diffuse components separate,
% PREV: preserving their arrival directions, until the field is applied to the body. The transport model treats direct paths and one
% PREV: specular reflection exactly, estimates one diffuse reflection, and stops there.
% PREV: The route points are fixed case studies, not a population sample, and the
% PREV: roofline transmitters are a model, not a measured deployment. To the best of the authors' knowledge, prior work has not combined aligned
% PREV: 360-degree street images, a common roofline transmitter model, and separate
% PREV: transport components with their arrival directions in a single route-level body
% PREV: exposure calculation.
% NEXT: This work makes the following three contributions.
% NEXT: \begin{enumerate}
% NEXT:   \item Aligned 360-degree street images supply traceable material labels to
% NEXT:   the same city mesh used for ray tracing. Surfaces without a reliable image
% NEXT:   label keep their geometry-based material.
% NEXT:
% NEXT:   \item A roofline transmitter model and transport calculation keep direct,
% NEXT:   specular, and diffuse power separate, with arrival directions, until the
% NEXT:   field is applied to the body.
% NEXT:
% NEXT:   \item An application across ten urban locations and five detailed pedestrian
% NEXT:   routes reports geometric screening, fixed-route exposure distributions,
% NEXT:   controlled first-diffuse validation, replica convergence, and the retained
% NEXT:   transport at the six observation points where buildings block all direct and
% NEXT:   specular paths.
% NEXT: \end{enumerate}
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

## reviews (paragraph)

_(empty — run /review to populate)_
