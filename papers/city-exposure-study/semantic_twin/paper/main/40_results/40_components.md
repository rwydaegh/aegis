% PREV: % claim: five_city_wbsar_route_quantiles
% PREV: \begin{table*}[!t]
% PREV: \caption{Fixed-route exposure summary. Whole-body SAR quantiles are normalized per unit $\rho_A P_{\mathrm{EIRP}}$ and have units m$^2$~kg$^{-1}$. Surplus uses finite-direct points only. The last column is the maximum pointwise total-transfer change from 12 to 16 replicas.}
% PREV: \label{tab:route-results}
% PREV: \centering
% PREV: \begin{tabular}{lrrrrrr}
% PREV: \toprule
% PREV: Site & $q_{10}$ & $q_{50}$ & $q_{90}$ & Median surplus [dB] & \shortstack{Zero direct and\\order-1 specular} & \shortstack{Max total-transfer\\change [dB]} \\
% PREV: \midrule
% PREV: Korenmarkt & 0.057833 & 0.062045 & 0.068672 & 1.108 & 0 & 0.0000819 \\
% PREV: Prague & 0.012157 & 0.013073 & 0.014594 & 1.061 & 0 & 0.0001559 \\
% PREV: Madrid & 0.020913 & 0.022381 & 0.023171 & 1.534 & 0 & 0.0004083 \\
% PREV: Mexico City & $9.92\times10^{-7}$ & 0.129062 & 0.295798 & 0.721 & 3 & 0.043625 \\
% PREV: Tokyo Hachiko & $3.66\times10^{-5}$ & 0.009674 & 0.025200 & 0.828 & 3 & 0.019732 \\
% PREV: \bottomrule
% PREV: \end{tabular}
% PREV: \end{table*}
% NEXT: % claim: replica_convergence_12_to_16
% NEXT: The nested 12-to-16-replica comparison separates the central route statistic from the lower tail. Every route-median whole-body SAR changes by at most $5.90\times10^{-5}$~dB. The largest lower-decile point changes are 0.032226~dB in Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and 0.019732~dB at these two sites. At 16 replicas, their 90th-percentile total-transfer standard errors are 0.1461 and 0.0310~dB, respectively. Central route statistics are stable under the retained estimator.
% NEXT:
% NEXT: % claim: replica_convergence_48_to_64
% NEXT: A separate calculation retains the exact verified 16-replica
% NEXT: prefix and continues every route through 64 replicas. Between 48 and 64
% NEXT: replicas, the whole-body SAR $q_{10}$ changes by 0.00344~dB in Mexico City and
% NEXT: 0.00491~dB in Tokyo Hachiko. The largest change among their six shadowed
% NEXT: route points is 0.0125 and 0.0104~dB, respectively. Both lower tails satisfy the
% NEXT: stated aggregate stability criteria through 64 replicas. Mexico City still
% NEXT: shows rare-event first-diffuse behavior, with a maximum-to-median positive
% NEXT: replica contribution ratio of 5738. This result remains
% NEXT: specific to the fixed routes and excludes route-selection and
% NEXT: city-sampling uncertainty. The complete nested comparison is provided in the
% NEXT: supplementary material.
% claim: six_shadowed_standpoints
% claim: pooled_median_wbsar_component_shares
The additive component shares of route-mean whole-body SAR are shown in the
supplementary material. Direct transport is the largest
contribution at all 67 points with line of sight. Exact order-1 specular
transport is never the largest. Mexico City points 0, 1, and 3 and Tokyo
Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular
transport. First-diffuse transport is the only nonzero contribution at these six
points. Across all 73 points, the pooled component medians are 77.662\% direct,
21.391\% exact order-1 specular, and 0.419\% first diffuse. They do not sum to
100\% because each component has a separate median over the 73 route points. The
small first-diffuse median therefore does not describe the six fully shadowed
points.

% claim: ray_reached_evidence_coverage
The path audit assigns each retained material interaction to an image-mapped or
geometry-based surface. Pooled over the five routes and 16 seeds, image-mapped
surfaces account for 75.903\% of the reflected SAR. The
corresponding shares are 80.643\% for exact order-1 specular transport and
13.337\% for first-diffuse transport. The supplementary material gives the
complete split by material source.
