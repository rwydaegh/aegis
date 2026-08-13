% PREV: \IEEEPARstart{U}{rban} propagation can change over a few meters along a
% PREV: pedestrian route. A person can move from direct visibility of a roofline to a
% PREV: region where buildings block the direct field and reflected power arrives from
% PREV: another direction. The surface materials then affect how much power is returned
% PREV: to the street~\cite{itu2040,vitucci}. This local variation also matters after propagation.
% PREV: Whole-body absorption depends on the arrival direction and on the orientation of
% PREV: the body, so one incident-power value at one receiver position does not describe
% PREV: exposure along a route. A route calculation must retain position and direction
% PREV: until the field is coupled to the body~\cite{icnirp}.
% NEXT: Street imagery and semantic scene models can supply attributes that are absent
% NEXT: from an untextured city mesh. The Vistas dataset provides a street-scene
% NEXT: taxonomy for dense semantic segmentation~\cite{vistas}. Kamari \emph{et al.}
% NEXT: segment street-level images, project the resulting material classes onto city
% NEXT: geometry, and use that geometry in millimeter-wave ray tracing~\cite{mmsv}.
% NEXT: Xia \emph{et al.} use semantic point-cloud classification and detailed scene
% NEXT: reconstruction for outdoor urban ray tracing at 2.8~GHz~\cite{xia2024}.
% NEXT: Image-informed wireless scene construction is therefore established. The
% NEXT: present work does not claim semantic segmentation, material classification, or
% NEXT: image-to-geometry projection as new. It uses these operations to form a
% NEXT: traceable material surface around fixed pedestrian routes, with an explicit
% NEXT: fallback where the image evidence is absent or refused.
Urban radio ray tracing provides detailed paths between specified transmitters
and receivers~\cite{sionna}. It has been used for city-scale downlink exposure
with base-station locations from public deployment records~\cite{leeman}, and in
hybrid propagation and anatomical dosimetry calculations along an outdoor user
path~\cite{wydaeghe2026}. Stochastic site models provide a different description
when individual transmitters are not fixed~\cite{wiame}, while normalized body
coefficients separate incident fields from later exposure
calculations~\cite{varsier}. Together, these studies include deterministic urban
transport, spatial source models, and body coupling. Because these studies use
different source assumptions, their reported quantities are not directly
comparable without a common source law.

## reviews (paragraph)

_(empty — run /review to populate)_
