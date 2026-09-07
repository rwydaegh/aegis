% NEXT: % claim: geometric_fixed_grid_diagnostic
% NEXT: A separate diagnostic describes ten urban locations with a deterministic point
% NEXT: design. At each location, the calculation builds a complete 6~m walkable-ground
% NEXT: lattice within 90~m and retains 64 observation points evenly across its
% NEXT: nearest-neighbor ordering. The visible roofline transmitter curve is built from
% NEXT: these same 64 points. Surface properties use geometry-based priors, and the
% NEXT: Duke phantom faces north at every point. The calculation uses the same
% NEXT: first-material transport model with 16 seeds, 200,000 primary rays per point
% NEXT: and seed, and 4,096 first-diffuse output cells. The fixed-grid design remains
% NEXT: separate from the pedestrian-route calculations and is not combined with the
% NEXT: route results.
\FloatBarrier
\section{Separate geometric fixed-grid diagnostic}
\label{sec:si-geometric-screening}
