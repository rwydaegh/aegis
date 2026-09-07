% PREV: Detailed photogrammetric geometry~\cite{google3d,blosm} does not identify its
% PREV: surface materials. Street images can supply this information. The Mapillary
% PREV: Vistas data set provides object classes for street scenes~\cite{vistas}.
% PREV: Kamari \emph{et al.} assign material classes from street images to city geometry
% PREV: for millimeter-wave ray tracing~\cite{mmsv}. Xia \emph{et al.} combine semantic
% PREV: point-cloud classes with detailed scenes for outdoor ray tracing at
% PREV: 2.8~GHz~\cite{xia2024}. These studies show that multimodal scene data can
% PREV: support radio propagation. They do not connect a common source model, retained
% PREV: arrival directions, and human whole-body SAR across routes in several cities.
% NEXT: The goal of this study is to compute direction-aware human whole-body SAR along
% NEXT: pedestrian routes in ten cities at 15~GHz. The routes contain 163 observation
% NEXT: points with image-derived surface materials and a body model facing along each
% NEXT: walk. Every value is normalized per unit active-source areal density and per
% NEXT: unit effective isotropic radiated power (EIRP). The selected-route medians
% NEXT: differ by a factor of 14.31. We do not estimate population exposure,
% NEXT: whole-city exposure, or exposure from a deployed network.
To address this gap, we form an AI-assisted, human-centric digital twin from
360-degree street images and photogrammetric city geometry. Mask2Former assigns
object labels. SAM~3 Agent performs the agentic AI step by assigning material
and vegetation labels on visible surfaces. A common model
places possible transmitters along rooflines. The propagation calculation keeps
direct, single-reflection specular, and single-reflection diffuse components
separate, with their arrival directions, until the body calculation. Together,
these stages connect the city scene to body absorption. The propagation model
includes one reflection.

## reviews (paragraph)

_(empty — run /review to populate)_
