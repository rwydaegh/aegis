% PREV: \IEEEPARstart{A}{s} wireless networks expand into higher frequency bands,
% PREV: the built environment plays a larger role in determining the radiofrequency
% PREV: field that reaches a pedestrian~\cite{itu2040}. Along a city street, received
% PREV: power can change over a few meters. A person walking past a row of buildings
% PREV: can move from a clear view of a rooftop transmitter into a shadow where
% PREV: buildings block the direct field and only reflected power reaches the
% PREV: street. The facade materials then determine how much power returns to the
% PREV: street~\cite{itu2040,vitucci}. This variation also matters after the field
% PREV: arrives: whole-body absorption depends on the direction of arrival and on how
% PREV: the body is oriented, so a single power value at a single point does not
% PREV: describe exposure along a walking route. A route-level calculation must keep
% PREV: the arrival direction until the field is applied to the
% PREV: body~\cite{icnirp}.
% NEXT: A photogrammetric city mesh gives accurate building geometry, but its triangles
% NEXT: carry no material information. Street-level images can fill that gap. The
% NEXT: Mapillary Vistas dataset provides a taxonomy for dense segmentation of street
% NEXT: scenes~\cite{vistas}. Kamari \emph{et al.} segment street-level images, project
% NEXT: the resulting material classes onto city geometry, and use that geometry in
% NEXT: millimeter-wave ray tracing~\cite{mmsv}. Xia \emph{et al.} use semantic
% NEXT: point-cloud classification and detailed scene reconstruction for outdoor ray
% NEXT: tracing at 2.8~GHz~\cite{xia2024}. Projecting image-derived materials onto
% NEXT: city geometry is therefore established. This study does not claim any of these
% NEXT: operations as new. It uses them to build a material map around fixed pedestrian
% NEXT: routes, keeping the default geometry-based material wherever the images give no
% NEXT: reliable label.
Ray tracing computes detailed propagation paths between transmitters and
receivers in a three-dimensional city model~\cite{sionna}. It has been used for
city-scale downlink exposure using published base-station
locations~\cite{leeman}, and to compute propagation and body exposure along an
outdoor pedestrian path~\cite{wydaeghe2026}. Stochastic geometry models
describe exposure when individual transmitter locations are not
known~\cite{wiame}, while precomputed body coefficients separate the incident
field from the absorption calculation~\cite{varsier}. Together, these studies
cover deterministic urban propagation, spatial source models, and the
directional absorption step that converts the arriving field into absorbed power
on the body. Because they use different source assumptions, their reported
exposure values are not directly comparable without a common source
normalization.

## reviews (paragraph)

_(empty — run /review to populate)_
