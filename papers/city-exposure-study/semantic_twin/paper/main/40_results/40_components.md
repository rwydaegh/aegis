% PREV: % claim: five_city_wbsar_route_quantiles
% PREV: \begin{table*}[!t]
% PREV: \caption{Fixed-route exposure summary. Whole-body SAR quantiles are normalized per unit $\rho_A P_{\mathrm{EIRP}}$ and have units m$^2$~kg$^{-1}$. Surplus is computed only at points with nonzero direct transfer. The last column is the maximum pointwise total-transfer change from 12 to 16 replicas.}
% PREV: \label{tab:route-results}
% PREV: \centering
% PREV: \begin{tabular}{lrrrrrr}
% PREV: \toprule
% PREV: Site & $q_{10}$ & $q_{50}$ & $q_{90}$ & Median surplus [dB] & \shortstack{Zero direct and\\order-1 specular} & \shortstack{Max total-transfer\\change [dB]} \\
% PREV: \midrule
% PREV: Ghent & 0.057833 & 0.062045 & 0.068672 & 1.108 & 0 & 0.0000819 \\
% PREV: Prague & 0.012157 & 0.013073 & 0.014594 & 1.061 & 0 & 0.0001559 \\
% PREV: Madrid & 0.020913 & 0.022381 & 0.023171 & 1.534 & 0 & 0.0004083 \\
% PREV: Mexico City & $9.92\times10^{-7}$ & 0.129062 & 0.295798 & 0.721 & 3 & 0.043625 \\
% PREV: Tokyo Hachiko & $3.66\times10^{-5}$ & 0.009674 & 0.025200 & 0.828 & 3 & 0.019732 \\
% PREV: \bottomrule
% PREV: \end{tabular}
% PREV: \end{table*}
% NEXT: \subsection{Replica Convergence}
% NEXT: \label{sec:convergence}
% claim: six_shadowed_standpoints
% claim: pooled_median_wbsar_component_shares
The additive component shares of route-mean whole-body SAR are shown in the
supplementary material. Of the 157 points with line of sight, direct transport
is the largest contribution at 156. At one point in Brussels, exact order-1
specular transport is the largest. Mexico City points 0, 1, and 3 and Tokyo
Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular
transport. First-diffuse transport is the only nonzero contribution at these six
points. Across all 163 points, the pooled component medians are 78.056\% direct,
20.231\% exact order-1 specular, and 0.500\% first diffuse. They do not sum to
100\% because each component has a separate median over the 163 route points. The
small first-diffuse median therefore does not describe the six fully shadowed
points.

% claim: ray_reached_evidence_coverage
The path audit assigns each retained material interaction to an image-mapped or
geometry-based surface. Pooled over the ten routes and 64 seeds, image-mapped
surfaces account for 75.903\% of the reflected SAR. The
corresponding shares are 80.643\% for exact order-1 specular transport and
13.337\% for first-diffuse transport. The supplementary material gives the
complete split by material source.
