% PREV: \FloatBarrier
% PREV: \section{Separate geometric fixed-grid diagnostic}
% PREV: \label{sec:si-geometric-screening}
% NEXT: Across the ten fixed-grid descriptions, the ratio of the largest to smallest
% NEXT: normalized whole-body-SAR quantile is 2.02 for $q_{10}$, 2.01 for $q_{50}$,
% NEXT: and 2.23 for $q_{90}$. The pooled component shares range from 75.2\% to
% NEXT: 80.6\% for direct transport, 13.1\% to 19.6\% for order-1 specular transport,
% NEXT: and 4.1\% to 7.1\% for first-diffuse transport.
% NEXT:
% NEXT: Changing the design from 16 to 64 points, evaluated with the first four seeds,
% NEXT: moved the site quantiles by at most 2.26~dB for $q_{10}$, 1.38~dB for
% NEXT: $q_{50}$, and 3.47~dB for $q_{90}$. By contrast, the change from eight to
% NEXT: 16 seeds moved them by at most 0.0036, 0.0017, and 0.0020~dB. With the
% NEXT: 64-point transmitter curve fixed, the change from 32 to 64 receiver points was
% NEXT: as large as 1.36, 0.219, and 0.636~dB. The calculation is therefore far more
% NEXT: sensitive to point selection than to the number of seeds.
% NEXT:
% NEXT: Each quantile describes exactly 64 fixed observation points. Its reported
% NEXT: conditional Monte Carlo standard error is the sample standard deviation of the
% NEXT: 16 within-seed 64-point quantiles divided by $\sqrt{16}$. This standard error
% NEXT: is not total uncertainty. It does not include uncertainty from the grid design,
% NEXT: body orientation, material
% NEXT: priors, or transmitter-curve design. The values therefore describe only the
% NEXT: declared fixed-grid calculation.
% claim: geometric_fixed_grid_diagnostic
A separate diagnostic describes ten urban locations with a deterministic point
design. At each location, the calculation builds a complete 6~m walkable-ground
lattice within 90~m and retains 64 observation points evenly across its
nearest-neighbor ordering. The visible roofline transmitter curve is built from
these same 64 points. Surface properties use geometry-based priors, and the
Duke phantom faces north at every point. The calculation uses the same
first-material transport model with 16 seeds, 200,000 primary rays per point
and seed, and 4,096 first-diffuse output cells. The fixed-grid design remains
separate from the pedestrian-route calculations and is not combined with the
route results.
