% PREV: % claim: six_shadowed_standpoints
% PREV: % claim: pooled_median_wbsar_component_shares
% PREV: The component shares in Fig.~\ref{fig:route-distributions}(b) are additive
% PREV: shares of route-mean whole-body SAR. Direct transport is the largest body
% PREV: contribution at all 67 nonshadowed points. Exact order-1 specular transport is
% PREV: never the largest. Mexico City points 0, 1, and 3 and Tokyo Hachiko points 13,
% PREV: 14, and 15 have zero direct and zero order-1 specular transport. First-diffuse
% PREV: transport is the only nonzero modeled contribution at these six points. Across
% PREV: all 73 points, the pooled component medians are 77.662\% direct, 21.391\% exact
% PREV: order-1 specular, and 0.419\% first diffuse. They do not sum to 100\% because
% PREV: each component has a separate median over the 73 route points. The small
% PREV: first-diffuse median therefore does not describe the six shadowed points.
% PREV:
% PREV: % claim: ray_reached_evidence_coverage
% PREV: The path audit assigns each retained material interaction to an image-mapped or
% PREV: geometry-based material. Pooled over the five routes and 16 seeds,
% PREV: image-mapped surfaces account for 75.903\% of the non-direct
% PREV: body-coupled whole-body SAR contribution. The corresponding shares are
% PREV: 80.643\% for exact order-1 specular transport and 13.337\% for first-diffuse
% PREV: transport. The supplementary material gives the complete split by material source.
% NEXT: % claim: paired_material_evidence_control
% NEXT: A paired material-map control was completed for Madrid and Mexico City. The
% NEXT: control replaces all image-mapped materials with the geometry-based materials
% NEXT: while retaining the mesh, route, roofline transmitter model, body, seeds,
% NEXT: sampling budget, and transport steps. Each reported change is
% NEXT: $10\log_{10}(x_{\mathrm{image}}/x_{\mathrm{geometry}})$. The image-to-geometry
% NEXT: changes in normalized whole-body SAR at Madrid are $+0.233$, $+0.249$, and
% NEXT: $+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. The corresponding changes at
% NEXT: Mexico City are $+24.84$, $-0.158$, and $+0.104$~dB. The large Mexico City
% NEXT: $q_{10}$ change comes from its three shadowed points, where both totals are near
% NEXT: zero and first diffuse is the only nonzero modeled contribution. The direct
% NEXT: term is identical in every pair. At Madrid, the image-derived map changes the
% NEXT: route-median specular component by $+1.89$~dB and the first-diffuse component by
% NEXT: $-12.43$~dB, although the total median changes by $+0.249$~dB. The control tests
% NEXT: the complete material map, including its material parameters and the treatment
% NEXT: of woody vegetation as nonblocking. It does not measure material accuracy or
% NEXT: isolate reflectance alone. The supplementary material gives pointwise and
% NEXT: component-level comparisons.
% claim: replica_convergence_12_to_16
The nested 12-to-16-replica comparison separates the central route statistic from the lower tail. Every route-median whole-body SAR changes by at most $5.90\times10^{-5}$~dB. The largest lower-decile point changes are 0.032226~dB in Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and 0.019732~dB at these two sites. At 16 replicas, their 90th-percentile total-transfer standard errors are 0.1461 and 0.0310~dB, respectively. Central route statistics are stable under the retained estimator.

% claim: replica_convergence_48_to_64
A separate calculation retains the exact verified 16-replica
prefix and continues every route through 64 replicas. Between 48 and 64
replicas, the whole-body SAR $q_{10}$ changes by 0.00344~dB in Mexico City and
0.00491~dB in Tokyo Hachiko. The largest change among their six shadowed
route points is 0.0125 and 0.0104~dB, respectively. Both lower tails satisfy the
stated aggregate stability criteria through 64 replicas. Mexico City still
shows rare-event first-diffuse behavior, with a maximum-to-median positive
replica contribution ratio of 5738. This result remains
specific to the fixed routes and excludes route-selection and
city-sampling uncertainty. The complete nested comparison is provided in the
supplementary material.
