% PREV: \section{Introduction}\label{sec:introduction}
% NEXT: Ray tracing computes detailed propagation paths between transmitters and
% NEXT: receivers in a three-dimensional city model~\cite{sionna}. It has been used for
% NEXT: city-scale downlink exposure using published base-station
% NEXT: locations~\cite{leeman}, and to compute propagation and body exposure along an
% NEXT: outdoor pedestrian path~\cite{wydaeghe2026}. Stochastic geometry models
% NEXT: describe exposure when individual transmitter locations are not
% NEXT: known~\cite{wiame}, while precomputed body coefficients separate the incident
% NEXT: field from the absorption calculation~\cite{varsier}. Together, these studies
% NEXT: cover deterministic urban propagation, spatial source models, and the
% NEXT: directional absorption step that converts the arriving field into absorbed power
% NEXT: on the body. Because they use different source assumptions, their reported
% NEXT: exposure values are not directly comparable without a common source
% NEXT: normalization.
\IEEEPARstart{A}{s} wireless networks expand into higher frequency bands,
the built environment plays a larger role in determining the radiofrequency
field that reaches a pedestrian~\cite{itu2040}. Along a city street, received
power can change over a few meters. A person walking past a row of buildings
can move from a clear view of a rooftop transmitter into a shadow where
buildings block the direct field and only reflected power reaches the
street. The facade materials then determine how much power returns to the
street~\cite{itu2040,vitucci}. This variation also matters after the field
arrives: whole-body absorption depends on the direction of arrival and on how
the body is oriented, so a single power value at a single point does not
describe exposure along a walking route. A route-level calculation must keep
the arrival direction until the field is applied to the
body~\cite{icnirp}.

## reviews (paragraph)

_(empty — run /review to populate)_
