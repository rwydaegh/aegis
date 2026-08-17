% PREV: \section{Introduction}\label{sec:introduction}
% NEXT: Urban radio ray tracing provides detailed paths between specified transmitters
% NEXT: and receivers~\cite{sionna}. It has been used for city-scale downlink exposure
% NEXT: with base-station locations from public deployment records~\cite{leeman}, and in
% NEXT: hybrid propagation and anatomical dosimetry calculations along an outdoor user
% NEXT: path~\cite{wydaeghe2026}. Stochastic site models provide a different description
% NEXT: when individual transmitters are not fixed~\cite{wiame}, while normalized body
% NEXT: coefficients separate incident fields from later exposure
% NEXT: calculations~\cite{varsier}. Together, these studies include deterministic urban
% NEXT: transport, spatial source models, and body coupling. Because these studies use
% NEXT: different source assumptions, their reported quantities are not directly
% NEXT: comparable without a common source law.
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
