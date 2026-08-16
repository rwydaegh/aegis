% PREV: \documentclass{ieeeaccess}
% PREV:
% PREV: \usepackage{cite}
% PREV: \usepackage{amsmath,amssymb,amsfonts}
% PREV: \usepackage{bm}
% PREV: \usepackage{booktabs}
% PREV: \usepackage{graphicx}
% PREV: \usepackage{textcomp}
% PREV: \usepackage{url}
% PREV:
% PREV: \vol{16}
% PREV: \year{2026}
% PREV:
% PREV: \graphicspath{{../figures/}{figures/}}
% PREV:
% PREV: \newcommand{\rhoA}{\rho_{\mathrm{A}}}
% PREV: \newcommand{\Peirp}{P_{\mathrm{EIRP}}}
% PREV: \newcommand{\wbsar}{\mathrm{SAR}_{\mathrm{wb}}}
% NEXT: \begin{abstract}
% NEXT: Street-level radiofrequency exposure at 15 GHz depends on the route geometry,
% NEXT: surface materials, transmitter locations, and body orientation. This study maps
% NEXT: 360-degree street images onto a photogrammetric city mesh and assigns surface materials
% NEXT: around five selected pedestrian routes. A common source model sets the expected
% NEXT: number of transmitters from their areal density and distributes them along the
% NEXT: visible roofline in proportion to its physical length. All exposure values are
% NEXT: normalized per unit areal density times effective isotropic radiated power.
% NEXT: The calculation treats direct paths and one specular reflection exactly. It
% NEXT: estimates one diffuse reflection and then stops the path.
% NEXT: The directional fields are coupled to a 56,024-element Duke body surface. The
% NEXT: five routes contain 73 route points. Each point uses 16 independent
% NEXT: replicas, 200,000 primary rays per replica, and 4,096 fixed first-diffuse angular cells. In
% NEXT: a controlled open-square case, the maximum bounced-term difference between the
% NEXT: adjoint estimator and deterministic quadrature is 0.0616 dB, and the maximum
% NEXT: total-transport difference between the adjoint and forward tracers is 0.0344
% NEXT: dB. The route medians of normalized whole-body specific
% NEXT: absorption rate differ by a factor of 13.34. Direct transport is the largest
% NEXT: term at all 67 nonshadowed points. First-diffuse transport gives the only
% NEXT: nonzero modeled contribution at six shadowed points. The maximum 12-to-16-replica change
% NEXT: in total transfer is 0.0436 dB across the five sites, although lower-tail
% NEXT: estimates in Mexico City and Tokyo are less stable. The result applies to five
% NEXT: selected routes under the fixed model and does not estimate city-wide or
% NEXT: deployed-network exposure.
% NEXT: \end{abstract}
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

## reviews (titleblock)

_(empty: run the manuscript review pass to populate)_
