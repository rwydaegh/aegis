% PREV: To address this gap, we form an AI-assisted, human-centric digital twin from
% PREV: 360-degree street images and photogrammetric city geometry. Mask2Former assigns
% PREV: object labels. SAM~3 Agent performs the agentic AI step by assigning material
% PREV: and vegetation labels on visible surfaces. A common model
% PREV: places possible transmitters along rooflines. The propagation calculation keeps
% PREV: direct, single-reflection specular, and single-reflection diffuse components
% PREV: separate, with their arrival directions, until the body calculation. The model
% PREV: includes one reflection only.
% NEXT: This work makes the following three contributions.
% NEXT: \begin{enumerate}
% NEXT:   \item Multimodal fusion combines 360-degree street images and city geometry
% NEXT:   with Mask2Former object labels and SAM~3 Agent material labels in an
% NEXT:   AI-assisted digital twin. Surfaces without a reliable image label keep their
% NEXT:   geometry-based material.
% NEXT:
% NEXT:   \item A normalized roofline source model and an adjoint ray tracer keep
% NEXT:   direct and once-reflected power separate, with arrival directions, until the
% NEXT:   field is applied to the body.
% NEXT:
% NEXT:   \item Results for ten routes quantify whole-body SAR, component shares,
% NEXT:   numerical convergence, surface-material sensitivity, and controlled
% NEXT:   single-reflection validation.
% NEXT: \end{enumerate}
The goal of this study is to compute direction-aware human whole-body SAR along
pedestrian routes in ten cities at 15~GHz. The routes contain 163 observation
points with image-derived surface materials and a body model facing along each
walk. Every value is normalized per unit active-source areal density and per
unit effective isotropic radiated power (EIRP). The selected-route medians
differ by a factor of 14.31. These values describe the 163 fixed observations
under the stated source model.

## reviews (paragraph)

_(empty — run /review to populate)_
