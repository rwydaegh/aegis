% PREV: Street imagery and semantic scene models can supply attributes that are absent
% PREV: from an untextured city mesh. The Vistas dataset provides a street-scene
% PREV: taxonomy for dense semantic segmentation~\cite{vistas}. Kamari \emph{et al.}
% PREV: segment street-level images, project the resulting material classes onto city
% PREV: geometry, and use that geometry in millimeter-wave ray tracing~\cite{mmsv}.
% PREV: Xia \emph{et al.} use semantic point-cloud classification and detailed scene
% PREV: reconstruction for outdoor urban ray tracing at 2.8~GHz~\cite{xia2024}.
% PREV: Image-informed wireless scene construction is therefore established. The
% PREV: present work does not claim semantic segmentation, material classification, or
% PREV: image-to-geometry projection as new. It uses these operations to form a
% PREV: traceable material surface around fixed pedestrian routes, with an explicit
% PREV: fallback where the image evidence is absent or refused.
% NEXT: The study applies this method at 15~GHz to five selected routes with 73 fixed
% NEXT: standpoints. Each result is normalized per unit active-source areal density and
% NEXT: per unit equivalent isotropically radiated power. The retained transport contains
% NEXT: the exact direct term, exact one-reflection specular term, and the first diffuse
% NEXT: interaction evaluated by next-event estimation. It contains no higher specular
% NEXT: order and no path continuation after a diffuse interaction. The reported route
% NEXT: distributions are therefore results for five fixed routes under this source and
% NEXT: transport model. They are not estimates of population exposure, deployed-network
% NEXT: exposure, or a ranking of the five cities.
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

## reviews (paragraph)

_(empty — run /review to populate)_
