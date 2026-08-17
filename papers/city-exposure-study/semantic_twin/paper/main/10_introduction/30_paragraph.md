% PREV: Ray tracing computes detailed propagation paths between transmitters and
% PREV: receivers in a three-dimensional city model~\cite{sionna}. It has been used for
% PREV: city-scale downlink exposure using published base-station
% PREV: locations~\cite{leeman}, and to compute propagation and body exposure along an
% PREV: outdoor pedestrian path~\cite{wydaeghe2026}. Stochastic geometry models
% PREV: describe exposure when individual transmitter locations are not
% PREV: known~\cite{wiame}, while precomputed body coefficients separate the incident
% PREV: field from the absorption calculation~\cite{varsier}. Together, these studies
% PREV: cover deterministic urban propagation, spatial source models, and the
% PREV: directional absorption step that converts the arriving field into absorbed power
% PREV: on the body. Because they use different source assumptions, their reported
% PREV: exposure values are not directly comparable without a common source
% PREV: normalization.
% NEXT: This study combines these established parts in one fixed model. Each 360-degree
% NEXT: street image is aligned with the same photogrammetric city mesh used for ray
% NEXT: tracing, and the image labels are projected onto that mesh to produce a material map. A common transmitter model distributes sources along the visible
% NEXT: roofline at every site. Rooflines are a natural choice: they are elevated, street-facing, and visible
% NEXT: from the route. Distributing transmitters in proportion to roofline length
% NEXT: avoids tying the result to any particular deployment. The ray tracer keeps the direct, specular, and diffuse components separate,
% NEXT: preserving their arrival directions, until the field is applied to the body. The transport model treats direct paths and one
% NEXT: specular reflection exactly, estimates one diffuse reflection, and stops there.
% NEXT: The route points are fixed case studies, not a population sample, and the
% NEXT: roofline transmitters are a model, not a measured deployment. To the best of the authors' knowledge, prior work has not combined aligned
% NEXT: 360-degree street images, a common roofline transmitter model, and separate
% NEXT: transport components with their arrival directions in a single route-level body
% NEXT: exposure calculation.
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

## reviews (paragraph)

_(empty — run /review to populate)_
