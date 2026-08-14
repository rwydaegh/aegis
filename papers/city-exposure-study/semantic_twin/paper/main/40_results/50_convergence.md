% PREV: % claim: six_shadowed_standpoints
% PREV: % claim: pooled_median_wbsar_component_shares
% PREV: The component shares in Fig.~\ref{fig:route-distributions}(b) are additive shares of route-mean whole-body SAR. Direct transport is the largest body contribution at all 67 nonshadowed points. Exact order-1 specular transport is never the largest body contribution. Mexico City points 0, 1, and 3 and Tokyo Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular transport. First-diffuse transport is the only nonzero modeled contribution at these six points. Across all 73 points, the componentwise pooled median whole-body SAR shares are 77.662\% direct, 21.391\% exact order-1 specular, and 0.419\% first diffuse. The three medians need not sum to 100\% because each is taken separately over the pooled standpoint set. The small first-diffuse median therefore does not describe the six shadowed points.
% PREV:
% PREV: % claim: ray_reached_evidence_coverage
% PREV: The ray-reached audit assigns each retained material interaction to its exact
% PREV: atlas or fallback state. Pooled over the five routes and 16 seeds,
% PREV: panorama-informed interfaces account for 75.903\% of the non-direct
% PREV: body-coupled whole-body SAR contribution. The corresponding shares are
% PREV: 80.643\% for exact order-1 specular transport and 13.337\% for first-diffuse
% PREV: transport. The complete category split is given in the supplementary material.
% NEXT: % claim: paired_material_evidence_control
% NEXT: A paired material-evidence control was completed for Madrid and Mexico City. The control replaces the panorama-derived atlas with the declared geometric fallback while retaining the mesh, route, roofline source measure, body, seeds, sampling budget, and transport topology. Each reported change is $10\log_{10}(x_{\mathrm{atlas}}/x_{\mathrm{fallback}})$. The atlas-to-fallback changes in normalized whole-body SAR at Madrid are $+0.233$, $+0.249$, and $+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. The corresponding changes at Mexico City are $+24.84$, $-0.158$, and $+0.104$~dB. The large Mexico City $q_{10}$ change is set by its three shadowed points, where both paired totals are near zero and first diffuse is the only nonzero modeled contribution. The direct term is identical in every pair. At Madrid, the atlas changes the route-median specular component by $+1.89$~dB and the first-diffuse component by $-12.43$~dB, while the total median changes by only $+0.249$~dB. The control therefore measures sensitivity to the complete evidence layer, including its material parameters and nonblocking semantic state. It does not measure material accuracy or isolate reflectance alone. Pointwise and component-level comparisons are provided in the supplementary material.
% claim: replica_convergence_12_to_16
The nested 12-to-16-replica comparison separates the central route statistic from the lower tail. Every route-median whole-body SAR changes by at most $5.90\times10^{-5}$~dB. The largest lower-decile point changes are 0.032226~dB in Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and 0.019732~dB at these two sites. At 16 replicas, their 90th-percentile total-transfer standard errors are 0.1461 and 0.0310~dB, respectively. Central route statistics are stable under the retained estimator.

% claim: replica_convergence_48_to_64
A separate current-contract extension retains the exact sealed 16-replica
prefix and continues every route through 64 replicas. Between 48 and 64
replicas, the whole-body SAR $q_{10}$ changes by 0.00344~dB in Mexico City and
0.00491~dB in Tokyo Hachiko. The largest change among their six shadowed
standpoints is 0.0125 and 0.0104~dB, respectively. Both lower tails satisfy the
declared aggregate stability criteria through 64 replicas. Mexico City still
shows rare-event first-diffuse behavior, with a maximum-to-median positive
replica contribution ratio of 5738. This result remains
conditional on the fixed registered routes and excludes route-selection and
city-sampling uncertainty. The complete nested comparison is provided in the
supplementary material.
