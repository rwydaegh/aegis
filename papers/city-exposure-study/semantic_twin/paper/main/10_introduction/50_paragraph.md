% PREV: The calculation combines these established parts in one fixed model. First, each
% PREV: 360-degree street image is aligned with the same city mesh used for ray tracing.
% PREV: The image labels are then projected onto that mesh to make a material map.
% PREV: Second, the same transmitter model is used at every site, with the number of
% PREV: transmitters set independently of how finely the roofline is divided. Third,
% PREV: direct, specular, and diffuse power stays separate until its arrival direction
% PREV: is coupled to the body. The transport calculation treats direct paths and one
% PREV: specular reflection exactly, estimates one diffuse reflection, and then stops.
% PREV: The route points are fixed case studies rather than a population sample, and the
% PREV: roofline transmitters are a model rather than a measured deployment. To the best
% PREV: of the authors' knowledge, prior work has not combined aligned 360-degree street
% PREV: images, a common roofline transmitter model, these separate transport components,
% PREV: and directional body coupling along fixed routes.
% NEXT: For the first time, one fixed-route calculation combines the following three
% NEXT: contributions.
% NEXT: \begin{enumerate}
% NEXT:   \item Aligned 360-degree street images supply traceable
% NEXT:   material labels to the same city mesh used for the propagation calculation.
% NEXT:   Surfaces without a reliable image label keep their geometry-based material.
% NEXT:
% NEXT:   \item A normalized roofline transmitter model and transport calculation preserve
% NEXT:   direct, one-reflection specular, and first-diffuse power and
% NEXT:   direction until whole-body coupling.
% NEXT:
% NEXT:   \item A five-site application reports fixed-route exposure distributions,
% NEXT:   controlled first-diffuse validation, component closure, replica convergence,
% NEXT:   and the retained transport at the six route points with no direct or
% NEXT:   one-reflection specular contribution.
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
