<!-- AUTO_BEGIN: assembled -->
\section{Introduction}\label{sec:introduction}

\IEEEPARstart{R}{ealistic} radiofrequency electromagnetic-field (RF-EMF)
exposure assessment must connect the field in a real environment to the power
absorbed by the human body. This link matters for street-level exposure
monitoring and for exposure estimates used in epidemiological research. Along
a city street, buildings can block the direct field, and facade materials
change the reflected power~\cite{itu2040,vitucci}. Human whole-body absorption
also depends on the arrival direction and body orientation~\cite{icnirp}.
Therefore, exposure assessment along a walking route must retain direction
until the field is applied to the body.

Prior exposure studies provide several parts of this link. Ray tracing gives
detailed paths in three-dimensional city models~\cite{sionna}. Ray tracing has supported
city-scale downlink exposure calculations with known base-station
locations~\cite{leeman} and realistic 28~GHz body exposure along an outdoor
path~\cite{wydaeghe2026}. Stochastic geometry represents unknown transmitter
locations~\cite{wiame}. SAR conversion factors connect incident fields to
absorption~\cite{varsier}. These studies use different source assumptions.
A common normalization is needed before their exposure values can be compared.

Detailed photogrammetric geometry~\cite{google3d,blosm} does not identify its
surface materials. Street images can supply this information. The Mapillary
Vistas data set provides object classes for street scenes~\cite{vistas}.
Kamari \emph{et al.} assign material classes from street images to city geometry
for millimeter-wave ray tracing~\cite{mmsv}. Xia \emph{et al.} combine semantic
point-cloud classes with detailed scenes for outdoor ray tracing at
2.8~GHz~\cite{xia2024}. These studies show that multimodal scene data can
support radio propagation. They do not connect a common source model, retained
arrival directions, and human whole-body SAR across routes in several cities.

To address this gap, we form an AI-assisted, human-centric digital twin from
360-degree street images and photogrammetric city geometry. Mask2Former assigns
object labels. SAM~3 Agent performs the agentic AI step by assigning material
and vegetation labels on visible surfaces. A common model
places possible transmitters along rooflines. The propagation calculation keeps
direct, single-reflection specular, and single-reflection diffuse components
separate, with their arrival directions, until the body calculation. The model
includes one reflection only.

The goal of this study is to compute direction-aware human whole-body SAR along
pedestrian routes in ten cities at 15~GHz. The routes contain 163 observation
points with image-derived surface materials and a body model facing along each
walk. Every value is normalized per unit active-source areal density and per
unit effective isotropic radiated power (EIRP). The selected-route medians
differ by a factor of 14.31. We do not estimate population exposure,
whole-city exposure, or exposure from a deployed network.

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
<!-- AUTO_END: assembled -->
