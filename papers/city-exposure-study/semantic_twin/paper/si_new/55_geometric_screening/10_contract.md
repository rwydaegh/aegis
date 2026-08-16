% PREV: \FloatBarrier
% PREV: \section{Separate geometric fixed-grid diagnostic}
% PREV: \label{sec:si-geometric-screening}
% NEXT: Across the ten fixed-grid descriptions, the ratio of the largest to smallest
% NEXT: normalized whole-body-SAR quantile is 2.09 for $q_{10}$, 2.10 for $q_{50}$,
% NEXT: and 2.60 for $q_{90}$. The pooled component shares range from 74.2\% to
% NEXT: 83.4\% for direct transport, 10.5\% to 20.0\% for order-1 specular transport,
% NEXT: and 4.1\% to 7.4\% for first-diffuse transport.
% NEXT:
% NEXT: Each quantile describes exactly 16 fixed observation points. Its reported
% NEXT: conditional Monte Carlo standard error is the sample standard deviation of the
% NEXT: four within-seed 16-point quantiles divided by $\sqrt{4}$. Four seeds do not
% NEXT: establish convergence, and this standard error is not total uncertainty. It
% NEXT: does not include uncertainty from the grid design, body orientation, material
% NEXT: priors, or transmitter-curve design. The values therefore describe only the
% NEXT: declared fixed-grid calculation.
% claim: geometric_fixed_grid_diagnostic
A separate diagnostic describes ten urban locations with a deterministic point
design. At each location, the calculation builds a complete 6~m walkable-ground
lattice within 90~m and retains 16 observation points evenly across its
nearest-neighbor ordering. The visible roofline transmitter curve is built from
these same 16 points. Surface properties use geometry-based priors, and the
Duke phantom faces north at every point. The calculation uses the same
first-material transport model with four seeds, 200,000 primary rays per point
and seed, and 4,096 first-diffuse output cells. The fixed-grid design remains
separate from the pedestrian-route calculations and is not combined with the
five-route results.
