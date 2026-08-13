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
% NEXT: The calculation considered here requires the established parts in one declared
% NEXT: model. Registered panoramas must refer to the same city geometry that supports
% NEXT: the propagation calculation. A source model must remain fixed across sites, and
% NEXT: its physical scale must be separate from the numerical source quadrature.
% NEXT: Direct, specular, and diffuse power must remain separate until their arrival
% NEXT: directions are coupled to the body. The method in this paper meets these
% NEXT: requirements with a panorama-derived material surface, a route-aligned roofline
% NEXT: source measure, and a transport model that stops after the first diffuse material
% NEXT: interaction. This combination defines a conditional comparison of local scenes
% NEXT: without treating the available standpoints as a population sample or the
% NEXT: roofline sources as a measured deployment. To the best of the authors'
% NEXT: knowledge, prior work has not combined registered street panoramas, a common roofline source law, component-resolved
% NEXT: first-material transport, and directional body coupling along fixed routes.
Street imagery and semantic scene models can supply attributes that are absent
from an untextured city mesh. The Vistas dataset provides a street-scene
taxonomy for dense semantic segmentation~\cite{vistas}. Kamari \emph{et al.}
segment street-level images, project the resulting material classes onto city
geometry, and use that geometry in millimeter-wave ray tracing~\cite{mmsv}.
Xia \emph{et al.} use semantic point-cloud classification and detailed scene
reconstruction for outdoor urban ray tracing at 2.8~GHz~\cite{xia2024}.
Image-informed wireless scene construction is therefore established. The
present work does not claim semantic segmentation, material classification, or
image-to-geometry projection as new. It uses these operations to form a
traceable material surface around fixed pedestrian routes, with an explicit
fallback where the image evidence is absent or refused.

## reviews (paragraph)

_(empty — run /review to populate)_
