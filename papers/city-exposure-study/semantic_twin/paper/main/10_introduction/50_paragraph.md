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
The study applies this method at 15~GHz to five selected routes with 73 fixed
route points. Each result is normalized per unit active-source areal density and
per unit equivalent isotropically radiated power. The calculation treats direct
paths and one specular reflection exactly, then estimates one diffuse reflection
by next-event estimation. It omits further reflections. The reported route
distributions are therefore results for five fixed routes under this source and
transport model. They do not estimate population exposure or deployed-network
exposure, and they do not rank the five cities.

## reviews (paragraph)

_(empty — run /review to populate)_
