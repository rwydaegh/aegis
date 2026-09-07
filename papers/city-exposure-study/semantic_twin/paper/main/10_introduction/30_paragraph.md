% PREV: Prior exposure studies provide several parts of this link. Ray tracing gives
% PREV: detailed paths in three-dimensional city models~\cite{sionna}. Ray tracing has supported
% PREV: city-scale downlink exposure calculations with known base-station
% PREV: locations~\cite{leeman} and realistic 28~GHz body exposure along an outdoor
% PREV: path~\cite{wydaeghe2026}. Stochastic geometry represents unknown transmitter
% PREV: locations~\cite{wiame}. SAR conversion factors connect incident fields to
% PREV: absorption~\cite{varsier}. These studies use different source assumptions.
% PREV: A common normalization is needed before their exposure values can be compared.
% NEXT: To address this gap, we form an AI-assisted, human-centric digital twin from
% NEXT: 360-degree street images and photogrammetric city geometry. Mask2Former assigns
% NEXT: object labels. SAM~3 Agent performs the agentic AI step by assigning material
% NEXT: and vegetation labels on visible surfaces. A common model
% NEXT: places possible transmitters along rooflines. The propagation calculation keeps
% NEXT: direct, single-reflection specular, and single-reflection diffuse components
% NEXT: separate, with their arrival directions, until the body calculation. The model
% NEXT: includes one reflection only.
The combined calculation also needs surface materials. Detailed
photogrammetric geometry~\cite{google3d,blosm} does not identify its
surface materials. Street images can supply this information. The Mapillary
Vistas data set provides object classes for street scenes~\cite{vistas}.
Kamari \emph{et al.} assign material classes from street images to city geometry
for millimeter-wave ray tracing~\cite{mmsv}. Xia \emph{et al.} combine semantic
point-cloud classes with detailed scenes for outdoor ray tracing at
2.8~GHz~\cite{xia2024}. These studies show that multimodal scene data can
support radio propagation. These scene methods have not been joined with a
common source model and direction-aware body calculation across routes in
several cities.

## reviews (paragraph)

_(empty — run /review to populate)_
