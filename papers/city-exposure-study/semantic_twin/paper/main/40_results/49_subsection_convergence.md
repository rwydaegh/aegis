% PREV: % claim: six_shadowed_standpoints
% PREV: % claim: pooled_median_wbsar_component_shares
% PREV: The additive component shares of route-mean whole-body SAR are shown in the
% PREV: supplementary material. Direct transport is the largest
% PREV: contribution at all 67 points with line of sight. Exact order-1 specular
% PREV: transport is never the largest. Mexico City points 0, 1, and 3 and Tokyo
% PREV: Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular
% PREV: transport. First-diffuse transport is the only nonzero contribution at these six
% PREV: points. Across all 73 points, the pooled component medians are 77.662\% direct,
% PREV: 21.391\% exact order-1 specular, and 0.419\% first diffuse. They do not sum to
% PREV: 100\% because each component has a separate median over the 73 route points. The
% PREV: small first-diffuse median therefore does not describe the six fully shadowed
% PREV: points.
% PREV:
% PREV: % claim: ray_reached_evidence_coverage
% PREV: The path audit assigns each retained material interaction to an image-mapped or
% PREV: geometry-based surface. Pooled over the five routes and 16 seeds, image-mapped
% PREV: surfaces account for 75.903\% of the reflected SAR. The
% PREV: corresponding shares are 80.643\% for exact order-1 specular transport and
% PREV: 13.337\% for first-diffuse transport. The supplementary material gives the
% PREV: complete split by material source.
% NEXT: % claim: replica_convergence_12_to_16
% NEXT: The nested 12-to-16-replica comparison separates the route median from the
% NEXT: lower tail. Every route-median whole-body SAR changes by at most
% NEXT: $5.90\times10^{-5}$~dB. The largest lower-decile changes are 0.032226~dB in
% NEXT: Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise
% NEXT: total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and
% NEXT: 0.019732~dB at these two sites. At 16 replicas, the 90th-percentile total-transfer standard errors are
% NEXT: 0.1461~dB in Mexico City and 0.0310~dB in Tokyo Hachiko. The route medians are
% NEXT: stable at 16 replicas.
% NEXT:
% NEXT: % claim: replica_convergence_48_to_64
% NEXT: A separate calculation reuses the first 16 replicas and extends every route
% NEXT: through 64 replicas. Between 48 and 64 replicas, the whole-body SAR
% NEXT: $q_{10}$ changes by 0.00344~dB in Mexico City and 0.00491~dB in Tokyo Hachiko.
% NEXT: The largest change among their six fully shadowed route points is 0.0125 and
% NEXT: 0.0104~dB. Both lower tails remain stable through 64 replicas.
% NEXT: In Mexico City, the single strongest diffuse replica at one shadowed point
% NEXT: carries 5738 times the median replica contribution.
% NEXT: This result is specific to the fixed routes and excludes route-selection and
% NEXT: city-sampling uncertainty. The complete nested comparison is given in the
% NEXT: supplementary material.
\subsection{Replica Convergence}
\label{sec:convergence}
