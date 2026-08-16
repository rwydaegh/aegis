% PREV: Urban radio ray tracing provides detailed paths between specified transmitters
% PREV: and receivers~\cite{sionna}. It has been used for city-scale downlink exposure
% PREV: with base-station locations from public deployment records~\cite{leeman}, and in
% PREV: hybrid propagation and anatomical dosimetry calculations along an outdoor user
% PREV: path~\cite{wydaeghe2026}. Stochastic site models provide a different description
% PREV: when individual transmitters are not fixed~\cite{wiame}, while normalized body
% PREV: coefficients separate incident fields from later exposure
% PREV: calculations~\cite{varsier}. Together, these studies include deterministic urban
% PREV: transport, spatial source models, and body coupling. Because these studies use
% PREV: different source assumptions, their reported quantities are not directly
% PREV: comparable without a common source law.
% NEXT: The calculation combines these established parts in one fixed model. First, each
% NEXT: 360-degree street image is aligned with the same city mesh used for ray tracing.
% NEXT: The image labels are then projected onto that mesh to make a material map.
% NEXT: Second, the same transmitter model is used at every site, with the number of
% NEXT: transmitters set independently of how finely the roofline is divided. Third,
% NEXT: direct, specular, and diffuse power stays separate until its arrival direction
% NEXT: is coupled to the body. The transport calculation treats direct paths and one
% NEXT: specular reflection exactly, estimates one diffuse reflection, and then stops.
% NEXT: The route points are fixed case studies rather than a population sample, and the
% NEXT: roofline transmitters are a model rather than a measured deployment. To the best
% NEXT: of the authors' knowledge, prior work has not combined aligned 360-degree street
% NEXT: images, a common roofline transmitter model, these separate transport components,
% NEXT: and directional body coupling along fixed routes.
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

## reviews (paragraph)

_(empty — run /review to populate)_
