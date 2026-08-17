% PREV: Street images can supply surface information that is absent
% PREV: from an untextured city mesh. The Vistas dataset provides a street-scene
% PREV: taxonomy for dense semantic segmentation~\cite{vistas}. Kamari \emph{et al.}
% PREV: segment street-level images, project the resulting material classes onto city
% PREV: geometry, and use that geometry in millimeter-wave ray tracing~\cite{mmsv}.
% PREV: Xia \emph{et al.} use semantic point-cloud classification and detailed scene
% PREV: reconstruction for outdoor urban ray tracing at 2.8~GHz~\cite{xia2024}.
% PREV: Image-informed city modeling is therefore established. The
% PREV: present work does not claim semantic segmentation, material classification, or
% PREV: image-to-geometry projection as new. It uses these operations to form a
% PREV: traceable material map around fixed pedestrian routes. The map keeps the
% PREV: geometry-based material wherever the images give no reliable label.
% NEXT: The study applies this method at 15~GHz to five selected routes with 73 fixed
% NEXT: route points. Each result is normalized per unit active-source areal density and
% NEXT: per unit equivalent isotropically radiated power. The calculation treats direct
% NEXT: paths and one specular reflection exactly, then estimates one diffuse reflection
% NEXT: by next-event estimation. It omits further reflections. The reported route
% NEXT: distributions are therefore results for five fixed routes under this source and
% NEXT: transport model. They do not estimate population exposure or deployed-network
% NEXT: exposure, and they do not rank the five cities.
This study combines these established parts in one fixed model. Each 360-degree
street image is aligned with the same photogrammetric city mesh used for ray
tracing, and the image labels are projected onto that mesh to produce a material map. A common transmitter model distributes sources along the visible
roofline at every site. Rooflines are a natural choice: they are elevated, street-facing, and visible
from the route. Distributing transmitters in proportion to roofline length
avoids tying the result to any particular deployment. The ray tracer keeps the direct, specular, and diffuse components separate,
preserving their arrival directions, until the field is applied to the body. The transport model treats direct paths and one
specular reflection exactly, estimates one diffuse reflection, and stops there.
The route points are fixed case studies, not a population sample, and the
roofline transmitters are a model, not a measured deployment. To the best of the author's knowledge, prior work has not combined aligned
360-degree street images, a common roofline transmitter model, and separate
transport components with their arrival directions in a single route-level body
exposure calculation.

## reviews (paragraph)

_(empty — run /review to populate)_
