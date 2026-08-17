% PREV: \begin{document}
% PREV:
% PREV: \history{}
% PREV: \doi{}
% PREV:
% PREV: \title{Image-Informed Urban Propagation and Route-Level Body Exposure at 15 GHz}
% PREV:
% PREV: \author{\uppercase{Robin Wydaeghe}\authorrefmark{1},
% PREV: \uppercase{G\"unter Vermeeren}\authorrefmark{1}, \IEEEmembership{Member, IEEE},
% PREV: \uppercase{Emmeric Tanghe}\authorrefmark{1}, \IEEEmembership{Member, IEEE},
% PREV: and~\uppercase{Wout Joseph}\authorrefmark{1}, \IEEEmembership{Senior Member, IEEE}}
% PREV:
% PREV: \address[1]{Department of Information Technology, Ghent University/IMEC,
% PREV: 9052 Ghent, Belgium (e-mail: robin.wydaeghe@ugent.be)}
% PREV:
% PREV: \markboth
% PREV: {Wydaeghe \headeretal: Image-Informed Urban Propagation and Route-Level Body Exposure}
% PREV: {Wydaeghe \headeretal: Image-Informed Urban Propagation and Route-Level Body Exposure}
% PREV:
% PREV: \corresp{Corresponding author: Robin Wydaeghe
% PREV: (e-mail: robin.wydaeghe@ugent.be).}
% NEXT: \begin{keywords}
% NEXT: Body dosimetry, image-informed propagation, ray tracing, street imagery, urban
% NEXT: propagation, whole-body specific absorption rate.
% NEXT: \end{keywords}
% NEXT:
% NEXT: \titlepgskip=-21pt
% NEXT: \maketitle
\begin{abstract}
Street-level radiofrequency exposure varies along a pedestrian route because
buildings change the direct and reflected fields, surface materials affect how
much power returns to the street, and the human body absorbs differently
depending on the direction of arrival. This study projects 360-degree street
images onto a photogrammetric city mesh to identify surface materials along
pedestrian routes at 15~GHz. Transmitters are placed along the visible
roofline in proportion to its physical length. All results are normalized per
unit product of areal source density and effective isotropic radiated power
(EIRP). The transport model treats direct
paths and one specular reflection exactly, estimates one diffuse reflection, and
stops. The arriving fields and their directions are then applied to a
56,024-element Duke body model. A geometric fixed-grid diagnostic covers ten
urban locations in Europe, Latin America, and East Asia and finds a twofold
span in location-median whole-body SAR. Five of these locations are then studied
with image-derived materials along fixed pedestrian routes containing 73
observation points, each calculated with 16 independent replicas of 200,000
primary rays and 4,096 angular output cells. In a controlled test scene, the
adjoint estimate and deterministic quadrature differ by at most 0.0616~dB for
the reflected term. An independent forward tracer gives a maximum difference
of 0.0344~dB. Route-median whole-body specific absorption rate differs by a
factor of 13.34 across the five routes. Direct paths carry the largest share at
all 67 points with line of sight, while the diffuse reflection is the only
nonzero modeled contribution at six fully shadowed points. The maximum change
from 12 to 16 replicas is 0.0436~dB, though lower-tail estimates in Mexico
City and Tokyo are less stable. These results describe ten fixed-grid locations
and five selected routes under a fixed model and do not estimate city-wide or
deployed-network exposure.
\end{abstract}

## reviews (abstract)

_(empty: run the manuscript review pass to populate)_
