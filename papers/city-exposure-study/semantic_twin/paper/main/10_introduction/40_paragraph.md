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

## reviews (paragraph)

_(empty — run /review to populate)_
