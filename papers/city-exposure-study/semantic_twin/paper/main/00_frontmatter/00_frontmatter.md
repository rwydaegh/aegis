<!-- AUTO_BEGIN: assembled -->
\documentclass{ieeeaccess}

\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{bm}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{url}

\vol{16}
\year{2026}

\graphicspath{{../figures/}{figures/}}

\newcommand{\rhoA}{\rho_{\mathrm{A}}}
\newcommand{\Peirp}{P_{\mathrm{EIRP}}}
\newcommand{\wbsar}{\mathrm{SAR}_{\mathrm{wb}}}

\begin{document}

% PROVISIONAL AUTHOR METADATA: Robin-only draft pending final author confirmation.
% Publication history and DOI are supplied after acceptance.
% FUNDING: insert the confirmed sponsor statement with \tfootnote before submission.
\history{}
\doi{}

\title{Image-Informed Urban Propagation and Route-Level Body Exposure at 15 GHz}

\author{\uppercase{Robin Wydaeghe}\authorrefmark{1}}

\address[1]{WAVES Research Group, Department of Information Technology,
Ghent University--imec, Technologiepark-Zwijnaarde 126, 9052 Ghent, Belgium
(e-mail: robin.wydaeghe@ugent.be)}

\markboth
{R. Wydaeghe: Image-Informed Urban Propagation and Route-Level Body Exposure}
{R. Wydaeghe: Image-Informed Urban Propagation and Route-Level Body Exposure}

\corresp{Corresponding author: Robin Wydaeghe
(e-mail: robin.wydaeghe@ugent.be).}

\begin{abstract}
Street-level radiofrequency exposure at 15 GHz depends on the route geometry,
surface materials, transmitter locations, and body orientation. This study maps
360-degree street images onto a photogrammetric city mesh and assigns surface materials
around five selected pedestrian routes. A common source model sets the expected
number of transmitters from their areal density and distributes them along the
visible roofline in proportion to its physical length. All exposure values are
normalized per unit areal density times effective isotropic radiated power.
The calculation treats direct paths and one specular reflection exactly. It
estimates one diffuse reflection and then stops the path.
The directional fields are coupled to a 56,024-element Duke body surface. The
five routes contain 73 route points. Each point uses 16 independent
replicas, 200,000 primary rays per replica, and 4,096 fixed first-diffuse angular cells. In
a controlled open-square case, the maximum bounced-term difference between the
adjoint estimator and deterministic quadrature is 0.0616 dB, and the maximum
total-transport difference between the adjoint and forward tracers is 0.0344
dB. The route medians of normalized whole-body specific
absorption rate differ by a factor of 13.34. Direct transport is the largest
term at all 67 nonshadowed points. First-diffuse transport gives the only
nonzero modeled contribution at six shadowed points. The maximum 12-to-16-replica change
in total transfer is 0.0436 dB across the five sites, although lower-tail
estimates in Mexico City and Tokyo are less stable. The result applies to five
selected routes under the fixed model and does not estimate city-wide or
deployed-network exposure.
\end{abstract}

\begin{keywords}
Body dosimetry, image-informed propagation, ray tracing, street imagery, urban
propagation, whole-body specific absorption rate.
\end{keywords}

\titlepgskip=-21pt
\maketitle
<!-- AUTO_END: assembled -->
















## Aggregation notes (AI-owned)
