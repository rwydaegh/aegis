% PREV: The goal of this study is to compute direction-aware human whole-body SAR along
% PREV: pedestrian routes in ten cities at 15~GHz. The routes contain 163 observation
% PREV: points with image-derived surface materials and a body model facing along each
% PREV: walk. Every value is normalized per unit active-source areal density and per
% PREV: unit effective isotropic radiated power (EIRP). The selected-route medians
% PREV: differ by a factor of 14.31. We do not estimate population exposure,
% PREV: whole-city exposure, or exposure from a deployed network.
This work makes the following three contributions.
\begin{enumerate}
  \item Multimodal fusion combines 360-degree street images and city geometry
  with Mask2Former object labels and SAM~3 Agent material labels in an
  AI-assisted digital twin. Surfaces without a reliable image label keep their
  geometry-based material.

  \item A normalized roofline source model and an adjoint ray tracer keep
  direct and once-reflected power separate, with arrival directions, until the
  field is applied to the body.

  \item Results for ten routes quantify whole-body SAR, component shares,
  numerical convergence, surface-material sensitivity, and controlled
  single-reflection validation.
\end{enumerate}

## reviews (paragraph)

_(empty — run /review to populate)_
