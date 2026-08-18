% PREV: \documentclass{ieeeaccess}
% PREV:
% PREV: \usepackage{cite}
% PREV: \usepackage{amsmath,amssymb,amsfonts}
% PREV: \usepackage{newtxtext}
% PREV: \usepackage{bm}
% PREV: \usepackage{booktabs}
% PREV: \usepackage{graphicx}
% PREV: \usepackage{textcomp}
% PREV: \usepackage{url}
% PREV:
% PREV: \vol{16}
% PREV: \year{2026}
% PREV:
% PREV: \graphicspath{{../}{./}}
% PREV:
% PREV: \newcommand{\rhoA}{\rho_{\mathrm{A}}}
% PREV: \newcommand{\Peirp}{P_{\mathrm{EIRP}}}
% PREV: \newcommand{\wbsar}{\mathrm{SAR}_{\mathrm{wb}}}
% NEXT: \begin{abstract}
% NEXT: Street-level radiofrequency exposure varies along a pedestrian route because
% NEXT: buildings change the direct and reflected fields, surface materials affect how
% NEXT: much power returns to the street, and the human body absorbs differently
% NEXT: depending on the direction of arrival. This study projects 360-degree street
% NEXT: images onto a photogrammetric city mesh to identify surface materials along
% NEXT: pedestrian routes at 15~GHz. Transmitters are placed along the visible
% NEXT: roofline in proportion to its physical length. All results are normalized per
% NEXT: unit product of areal source density and effective isotropic radiated power
% NEXT: (EIRP). The transport model treats direct
% NEXT: paths and one specular reflection exactly, estimates one diffuse reflection, and
% NEXT: stops. The arriving fields and their directions are then applied to a
% NEXT: 56,024-element Duke body model. A geometric fixed-grid diagnostic covers ten
% NEXT: urban locations in Europe, Latin America, and East Asia and finds a twofold
% NEXT: span in location-median whole-body SAR. Five of these locations are then studied
% NEXT: with image-derived materials along fixed pedestrian routes containing 73
% NEXT: observation points, each calculated with 16 independent replicas of 200,000
% NEXT: primary rays and 4,096 angular output cells. In a controlled test scene, the
% NEXT: adjoint estimate and deterministic quadrature differ by at most 0.0616~dB for
% NEXT: the reflected term. An independent forward tracer gives a maximum difference
% NEXT: of 0.0344~dB. Route-median whole-body specific absorption rate differs by a
% NEXT: factor of 13.34 across the five routes. Direct paths carry the largest share at
% NEXT: all 67 points with line of sight, while the diffuse reflection is the only
% NEXT: nonzero modeled contribution at six fully shadowed points. The maximum change
% NEXT: from 12 to 16 replicas is 0.0436~dB, though lower-tail estimates in Mexico
% NEXT: City and Tokyo are less stable. These results describe ten fixed-grid locations
% NEXT: and five selected routes under a fixed model and do not estimate city-wide or
% NEXT: deployed-network exposure.
% NEXT: \end{abstract}
\begin{document}

\history{}
\doi{}

\title{Image-Informed Urban Propagation and Route-Level Body Exposure Across Ten Cities at 15 GHz}

\author{\uppercase{Robin Wydaeghe}\authorrefmark{1},
\uppercase{G\"unter Vermeeren}\authorrefmark{1}, \IEEEmembership{Member, IEEE},
\uppercase{Emmeric Tanghe}\authorrefmark{1}, \IEEEmembership{Member, IEEE},
and~\uppercase{Wout Joseph}\authorrefmark{1}, \IEEEmembership{Senior Member, IEEE}}

\address[1]{Department of Information Technology, Ghent University/IMEC,
9052 Ghent, Belgium (e-mail: robin.wydaeghe@ugent.be)}

\markboth
{Wydaeghe \headeretal: Image-Informed Urban Propagation and Route-Level Body Exposure Across Ten Cities}
{Wydaeghe \headeretal: Image-Informed Urban Propagation and Route-Level Body Exposure Across Ten Cities}

\corresp{Corresponding author: Robin Wydaeghe
(e-mail: robin.wydaeghe@ugent.be).}

## reviews (titleblock)

_(empty: run the manuscript review pass to populate)_
