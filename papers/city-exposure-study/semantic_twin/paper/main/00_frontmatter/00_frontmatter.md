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
Street-level radiofrequency exposure varies along a pedestrian route because
buildings change the direct and reflected fields, surface materials affect how
much power returns to the street, and the human body absorbs differently
depending on the direction of arrival. This study projects 360-degree street
images onto a photogrammetric city mesh to identify surface materials along five
pedestrian routes at 15~GHz. Transmitters are placed along the visible
roofline in proportion to its physical length. All results are normalized per
unit product of areal source density and effective isotropic radiated power
(EIRP). The transport model treats direct
paths and one specular reflection exactly, estimates one diffuse reflection, and
stops. The arriving fields and their directions are then applied to a
56,024-element Duke body model. The five routes contain 73 fixed observation
points, each calculated with 16 independent replicas of 200,000 primary rays
and 4,096 angular output cells. In a controlled test scene, the adjoint estimate and deterministic quadrature
differ by at most 0.0616~dB for the reflected term. An independent forward
tracer gives a maximum difference of 0.0344~dB. Route-median
whole-body specific absorption rate differs by a factor of 13.34 across the
five routes. Direct paths carry the largest share at all 67 points with line of
sight, while the diffuse reflection is the only nonzero modeled contribution at
six fully shadowed points. The maximum change from 12 to 16 replicas is
0.0436~dB, though lower-tail estimates in Mexico City and Tokyo are less
stable. These results describe five selected routes under a fixed model and do
not estimate city-wide or deployed-network exposure.
\end{abstract}

\begin{keywords}
Body dosimetry, image-informed propagation, ray tracing, street imagery, urban
propagation, whole-body specific absorption rate.
\end{keywords}

\titlepgskip=-21pt
\maketitle
<!-- AUTO_END: assembled -->
